"""
Handles two things:
1. The one-time OAuth code -> refresh token exchange (finishes what the
   frontend's "Connect Gmail" step started back in Task 4).
2. Using that refresh token to read Gmail: find threads from a sender, and
   pull the FULL text of a thread -- every message in it, including
   trailing replies. That's the whole point of this project.
"""

import os
import re
import base64
import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"

CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")


def exchange_code_for_tokens(code, redirect_uri):
    """One-time only: the authorization code from the frontend is single-use
    and expires within minutes. Must be exchanged the same run it's found."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if not resp.ok:
        # Google's response body explains exactly what went wrong (e.g.
        # "redirect_uri_mismatch", "invalid_grant") -- surface it instead of
        # a generic "400 Bad Request" so we can actually diagnose it.
        raise RuntimeError(f"Token exchange failed ({resp.status_code}): {resp.text}")
    return resp.json()  # {access_token, refresh_token, expires_in, ...}


def get_access_token(refresh_token):
    """Every run: exchange the long-lived refresh token for a fresh,
    short-lived access token to actually call the Gmail API with."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def list_thread_ids_from_sender(access_token, sender_email, max_results=20):
    """Recent threads from a given sender, newest first."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"q": f"from:{sender_email}", "maxResults": max_results}
    resp = requests.get(f"{GMAIL_API}/threads", headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return [t["id"] for t in resp.json().get("threads", [])]


def _decode_part(data):
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _strip_html(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_text_from_payload(payload):
    """Recursively pull plain text out of a (possibly multipart) message
    payload, falling back to stripped HTML if that's all there is."""
    texts = []
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")
    parts = payload.get("parts", [])

    if mime_type == "text/plain" and body_data:
        texts.append(_decode_part(body_data))
    elif mime_type == "text/html" and body_data and not parts:
        texts.append(_strip_html(_decode_part(body_data)))

    for part in parts:
        texts.extend(_extract_text_from_payload(part))

    return texts


def get_thread_full_text(access_token, thread_id):
    """The core of InboxCopilot: fetch every message in a thread -- not
    just the latest one -- and return it as one block of plain text, so
    the relevance-matching step (Task 7) can scan trailing replies too."""
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(
        f"{GMAIL_API}/threads/{thread_id}",
        headers=headers,
        params={"format": "full"},
        timeout=15,
    )
    resp.raise_for_status()
    thread = resp.json()

    message_blocks = []
    for message in thread.get("messages", []):
        texts = _extract_text_from_payload(message.get("payload", {}))
        message_blocks.append("\n".join(texts).strip())

    return "\n\n---\n\n".join(block for block in message_blocks if block)
