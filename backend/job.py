"""
InboxCopilot scheduled job.

Not a web server -- GitHub Actions runs this directly on a cron schedule
(Task 9). So far it:

  1. Finishes any pending "Connect Gmail" flow: exchanges the one-time
     authorization code the frontend captured for a long-lived refresh
     token, and stores that on the user's Firestore doc.
  2. For every active watch task belonging to a connected user, fetches
     the full text of recent threads from that task's sender -- trailing
     replies included.
  3. Scans that text for the task's keyword and prints just the relevant
     sentence(s), instead of the whole thread.

Actually sending alerts (Task 8) and running this on a real schedule
(Task 9) come next.
"""

from dotenv import load_dotenv

load_dotenv()  # picks up backend/.env for local runs

from firestore_client import get_db
from gmail_client import (
    exchange_code_for_tokens,
    get_access_token,
    list_thread_ids_from_sender,
    get_thread_full_text,
)
from matcher import find_relevant_sentences


def connect_pending_gmail(db, user_doc):
    """If this user has an unconsumed authorization code, exchange it now."""
    data = user_doc.to_dict()
    code = data.get("gmailPendingCode")
    redirect_uri = data.get("gmailRedirectUri", "http://localhost:5173/")

    if not code or data.get("gmailConnected"):
        return data

    print(f"  Connecting Gmail for {data.get('email')}...")
    print(f"  DEBUG redirect_uri used: {redirect_uri!r}")
    print(f"  DEBUG code (first/last 6 chars): {code[:6]}...{code[-6:]} (len={len(code)})")
    try:
        tokens = exchange_code_for_tokens(code, redirect_uri)
    except Exception as e:
        print(f"  ! Failed to exchange code (it may have expired): {e}")
        # Leave gmailPendingCode as-is; the user will need to reconnect
        # from the dashboard, which requests a fresh code.
        return data

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("  ! Google didn't return a refresh token (already connected before "
              "without 'prompt=consent'?). User needs to reconnect.")
        return data

    user_doc.reference.update({
        "gmailRefreshToken": refresh_token,
        "gmailConnected": True,
        "gmailPendingCode": None,
    })
    print("  Connected.")
    data["gmailRefreshToken"] = refresh_token
    data["gmailConnected"] = True
    return data


def process_user_tasks(db, uid, user_data):
    refresh_token = user_data.get("gmailRefreshToken")
    if not refresh_token:
        return

    tasks_ref = db.collection("users", uid, "tasks").where("active", "==", True)
    tasks = list(tasks_ref.stream())
    if not tasks:
        return

    access_token = get_access_token(refresh_token)

    for task_doc in tasks:
        task = task_doc.to_dict()
        sender = task.get("sender")
        keyword = task.get("keyword")
        print(f"  Task '{keyword}' watching {sender}...")

        thread_ids = list_thread_ids_from_sender(access_token, sender, max_results=10)
        print(f"    Found {len(thread_ids)} recent thread(s) from {sender}.")

        for thread_id in thread_ids:
            full_text = get_thread_full_text(access_token, thread_id)
            matches = find_relevant_sentences(full_text, keyword)

            if matches:
                print(f"    \u2713 MATCH in thread [{thread_id}]:")
                for snippet in matches:
                    print(f"        - {snippet}")
                # Task 8 will send an alert for genuinely NEW matches here
                # (dedup against already-notified message/thread ids).
            else:
                print(f"    (no mention of '{keyword}' in thread [{thread_id}])")


def main():
    db = get_db()
    users = list(db.collection("users").stream())
    print(f"Checking {len(users)} user(s)...")

    for user_doc in users:
        user_data = connect_pending_gmail(db, user_doc)
        if not user_data.get("gmailConnected"):
            continue
        process_user_tasks(db, user_doc.id, user_data)

    print("Done.")


if __name__ == "__main__":
    main()
