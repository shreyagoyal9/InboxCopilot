"""
InboxCopilot scheduled job.

This is NOT a web server. There's no Cloud Run here — GitHub Actions runs
this script directly on a cron schedule (see .github/workflows/ once we
add it in a later task). This keeps the whole project free with no
billing account required anywhere.

For every registered user, this script will (in later tasks):
  1. Fetch new mail from the watched sender (Gmail API)
  2. Read the full thread body, including trailing replies
  3. Check it for anything relevant to the user's group/batch label
  4. If relevant and not already seen -> send a notification
  5. Mark the message as seen in Firestore, so it's never alerted twice
"""


def main():
    print("InboxCopilot job — placeholder. Real logic comes in Task 5/6/7/9.")


if __name__ == "__main__":
    main()
