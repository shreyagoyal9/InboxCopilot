"""
InboxCopilot scheduled job.

Not a web server -- GitHub Actions runs this directly on a cron schedule
(Task 9). For now (Task 6) it does two things:

  1. Finishes any pending "Connect Gmail" flow: exchanges the one-time
     authorization code the frontend captured for a long-lived refresh
     token, and stores that on the user's Firestore doc.
  2. For every active watch task belonging to a connected user, fetches
     the full text of recent threads from that task's sender -- trailing
     replies included -- and logs them.

Keyword-matching (Task 7) and actually sending alerts (Task 8) come next;
this task's job is just proving the pipeline can read real Gmail data.
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
            preview = full_text[:200].replace("\n", " ")
            print(f"    [{thread_id}] {preview}...")
            # Task 7 will scan `full_text` for `keyword` here.
            # Task 8 will send an alert if it's a genuine, new match.


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
