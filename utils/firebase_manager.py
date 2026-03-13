import os
from datetime import datetime

_firebase_initialized = False


def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            key_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
            if not os.path.exists(key_path):
                raise FileNotFoundError(
                    f"Firebase service account key not found at '{key_path}'. "
                    "Download it from Firebase Console → Project Settings → Service Accounts."
                )
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)

        _firebase_initialized = True
        print("[Firebase] Admin SDK initialized successfully.")
    except ImportError:
        raise ImportError(
            "firebase-admin is not installed. Run: pip install firebase-admin"
        )


def get_user_profile_fields(user_id: str) -> dict:
    """
    Returns a dict with 'jobTitle' and 'about' from the user's Firestore document.
    Falls back to empty strings if the fields are absent.
    """
    _init_firebase()
    from firebase_admin import firestore

    client = firestore.client()
    ref = client.collection("users").document(user_id)
    doc = ref.get()

    if not doc.exists:
        return {"jobTitle": "", "about": ""}

    data = doc.to_dict()
    return {
        "jobTitle": data.get("jobTitle", ""),
        "about": data.get("about", ""),
    }


def ensure_job_tracking_fields(user_id: str):
    """
    Ensures 'jobsAppliedCount' and 'appliedJobs' fields exist on the user document.
    Creates them (set to 0 / []) if missing. Safe to call on every run.
    """
    _init_firebase()
    from firebase_admin import firestore

    client = firestore.client()
    ref = client.collection("users").document(user_id)
    doc = ref.get()

    if not doc.exists:
        print(f"[Firebase] User document not found for uid: {user_id}")
        return

    data = doc.to_dict()
    updates = {}

    if "jobsAppliedCount" not in data:
        updates["jobsAppliedCount"] = 0
    if "appliedJobs" not in data:
        updates["appliedJobs"] = []

    if updates:
        ref.update(updates)
        print(f"[Firebase] Initialized job tracking fields for user: {user_id}")


def update_applied_job(user_id: str, job_details: dict):
    """
    Appends a job entry to the user's 'appliedJobs' list and increments
    'jobsAppliedCount' in Firestore. Called after each successful application.

    job_details = {
        "position": str,   # job title
        "company": str,    # company name (best-effort)
        "link": str,       # URL to the job posting
    }
    """
    _init_firebase()
    from firebase_admin import firestore

    client = firestore.client()
    ref = client.collection("users").document(user_id)
    doc = ref.get()

    if not doc.exists:
        print(f"[Firebase] Cannot update jobs — user document not found: {user_id}")
        return

    data = doc.to_dict()
    current_count = data.get("jobsAppliedCount", 0)
    current_jobs = data.get("appliedJobs", [])

    job_entry = {
        "id": len(current_jobs) + 1,
        "company": job_details.get("company", "Unknown"),
        "position": job_details.get("position", "Unknown"),
        "status": "applied",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "link": job_details.get("link", ""),
    }

    current_jobs.append(job_entry)

    ref.update(
        {
            "jobsAppliedCount": current_count + 1,
            "appliedJobs": current_jobs,
            "updatedAt": datetime.now(),
        }
    )

    print(
        f"[Firebase] Updated jobs for user {user_id}: "
        f"count={current_count + 1}, latest='{job_entry['position']}' @ '{job_entry['company']}'"
    )
