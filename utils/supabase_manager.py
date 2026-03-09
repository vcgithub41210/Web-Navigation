import os
from supabase import create_client, Client
from dotenv import load_dotenv
import tempfile

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def download_resume(firebase_uid: str) -> str:
    
    try:
        # Path in Supabase: resume_bucket/{firebase_uid}/resume.pdf
        file_path = f"{firebase_uid}/resume.pdf"
        
        response = supabase.storage.from_("resume_bucket").download(file_path)
        
        if not response:
            raise Exception(f"Resume not found for user {firebase_uid}")
        
        temp_dir = os.path.join(os.getcwd(), "temp_resumes")
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file_path = os.path.join(temp_dir, f"resume.pdf")
        
        with open(temp_file_path, "wb") as f:
            f.write(response)
        
        print(f"[Supabase] Downloaded resume to: {temp_file_path}")
        return temp_file_path
        
    except Exception as e:
        print(f"[Supabase] Error downloading resume: {str(e)}")
        raise Exception(f"Failed to download resume: {str(e)}")


def delete_temp_resume(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[Supabase] Deleted temp file: {file_path}")
    except Exception as e:
        print(f"[Supabase] Warning: Failed to delete temp file: {str(e)}")
