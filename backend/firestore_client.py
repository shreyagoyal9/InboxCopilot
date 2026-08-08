"""
Connects to Firestore from Python using a Firebase service account -- this
is what lets the backend job read/write the SAME database the frontend
writes to, without needing a public API in between.
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore


def get_db():
    if not firebase_admin._apps:
        service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")

        if service_account_json:
            # Used in GitHub Actions: the whole JSON key file contents,
            # stored as a repo secret (see Task 9).
            cred = credentials.Certificate(json.loads(service_account_json))
        elif service_account_path:
            # Used for local testing: path to the downloaded JSON key file.
            cred = credentials.Certificate(service_account_path)
        else:
            raise RuntimeError(
                "Set FIREBASE_SERVICE_ACCOUNT_PATH (local) or "
                "FIREBASE_SERVICE_ACCOUNT_JSON (CI) before running this."
            )
        firebase_admin.initialize_app(cred)

    return firestore.client()
