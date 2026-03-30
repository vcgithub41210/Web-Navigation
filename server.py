from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import multiprocessing

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_context_cache: dict = {}


def _is_apply_intent(message: str) -> bool:
    """Returns True if the message is asking to apply for / search for jobs."""
    keywords = ["apply", "job", "linkedin", "search jobs", "find job",
                "get me a job", "autoapply", "auto apply"]
    msg = message.lower()
    return any(kw in msg for kw in keywords)


def _get_or_build_context(user_id: str) -> dict:
    """
    Downloads and parses the user's resume on first call, then caches the result.
    Subsequent calls for the same user_id return instantly from cache.
    The temp resume file is deleted after extraction; the autoapply subprocess
    re-downloads it when needed for file upload.
    """
    if user_id in _context_cache:
        print(f"[Server] Using cached context for user: {user_id}")
        return _context_cache[user_id]

    from utils.supabase_manager import download_resume, delete_temp_resume
    from utils.user_context_extractor import extract_user_context
    from utils.firebase_manager import get_user_profile_fields

    print(f"[Server] Building context for the first time for user: {user_id}")
    resume_path = None
    try:
        resume_path = download_resume(user_id)
        user_context = extract_user_context(resume_path)
        try:
            profile = get_user_profile_fields(user_id)
            if profile.get("jobTitle"):
                user_context["desired_role"] = profile["jobTitle"]
            if profile.get("about"):
                user_context["about"] = profile["about"]
        except Exception as profile_err:
            print(f"[Server] Profile augmentation warning (non-fatal): {profile_err}")
        _context_cache[user_id] = user_context
        return user_context
    finally:
        if resume_path:
            delete_temp_resume(resume_path)


class ChatRequest(BaseModel):
    message: str
    user_id: str


class CustomFormRequest(BaseModel):
    message: str
    user_id: str


def agent_process(message, user_id, user_context, return_dict, job_log):
    """
    Process auto-apply agent request. user_context is pre-built by the parent
    process (already cached). Downloads the resume file only for the actual
    upload step during applications.
    """
    from agentest import run_orchestrator
    from utils.supabase_manager import download_resume, delete_temp_resume
    from utils.firebase_manager import ensure_job_tracking_fields, update_applied_job

    resume_path = None

    try:
        try:
            ensure_job_tracking_fields(user_id)
        except Exception as fb_err:
            print(f"[Server] Firebase field init warning (non-fatal): {fb_err}")

        print(f"[Server] Downloading resume for file upload: {user_id}")
        resume_path = download_resume(user_id)
        def on_job_applied(job_details: dict):
            try:
                update_applied_job(user_id, job_details)
            except Exception as fb_err:
                print(f"[Server] Firebase update warning (non-fatal): {fb_err}")

        print(f"[Server] Running orchestrator for user: {user_context.get('name', 'Unknown')}")
        result = run_orchestrator(message, user_context, resume_path, on_job_applied, job_log)

        return_dict["result"] = result
        return_dict["error"] = None

    except (KeyboardInterrupt, SystemExit):
        count = len(list(job_log))
        return_dict["result"] = (
            f"Server was interrupted. AutoApply stopped after {count} application"
            f"{'s' if count != 1 else ''}. Check the Applications page for results."
        )
        return_dict["error"] = "interrupted"

    except Exception as e:
        error_msg = f"Agent process error: {str(e)}"
        print(f"[Server] ERROR: {error_msg}")
        return_dict["result"] = (
            "I encountered an error processing your request. "
            "Please make sure you've uploaded your resume."
        )
        return_dict["error"] = error_msg

    finally:
        if resume_path:
            print(f"[Server] Cleaning up temporary resume file: {resume_path}")
            delete_temp_resume(resume_path)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint: handles both conversational queries and LinkedIn auto-apply.
    """
    try:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        try:
            user_context = _get_or_build_context(request.user_id)
        except Exception as ctx_err:
            print(f"[Server] Context build warning (non-fatal): {ctx_err}")
            user_context = {}

        if not _is_apply_intent(request.message):
            from agentest import run_chat_response
            reply = run_chat_response(request.message, user_context)
            return {"reply": reply, "status": "ok"}

        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        job_log = manager.list()

        p = multiprocessing.Process(
            target=agent_process,
            args=(request.message, request.user_id, user_context, return_dict, job_log),
        )

        p.start()
        p.join()

        if not return_dict.get("result"):
            count = len(list(job_log))
            return {
                "reply": (
                    f"The server process was interrupted unexpectedly. "
                    f"AutoApply stopped after {count} application{'s' if count != 1 else ''}. "
                    "Check the Applications page for logged results."
                ),
                "status": "error",
            }

        if return_dict.get("error"):
            print(f"[Server] Agent returned error: {return_dict.get('error')}")

        return {
            "reply": return_dict.get("result", "No response"),
            "status": "ok" if not return_dict.get("error") else "error",
        }

    except Exception as e:
        print(f"[Server] /api/chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def custom_form_process(message, user_id, return_dict):
    """
    Process custom-form agent request.
    Returns the agent's actual final response (success / failure message).
    """
    from googleform import run_agent
    from utils.supabase_manager import download_resume, delete_temp_resume

    resume_path = None
    try:
        print(f"[Server] Downloading resume for custom form: {user_id}")
        resume_path = download_resume(user_id)

        print(f"[Server] Running custom form agent")
        # Pass the dynamic resume_path to your agent
        result = run_agent(message, resume_path) 
        
        return_dict["result"] = result if result else "Form agent returned no response."
        return_dict["error"] = None

    except (KeyboardInterrupt, SystemExit):
        return_dict["result"] = "Form filling was interrupted by the server."
        return_dict["error"] = "interrupted"

    except Exception as e:
        error_msg = str(e)
        print(f"[Server] ERROR: {error_msg}")
        return_dict["result"] = f"Form filling failed: {error_msg}"
        return_dict["error"] = error_msg
        
    finally:
        # Ensure the temp file gets deleted just like in agent_process
        if resume_path:
            print(f"[Server] Cleaning up temporary resume file: {resume_path}")
            delete_temp_resume(resume_path)


@app.post("/api/customform")
async def custom_form(request: CustomFormRequest):
    """
    Custom-form endpoint: fills any external form (e.g. Google Forms) using the
    provided message/URL. Returns the agent's success or failure response.
    """
    try:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        manager = multiprocessing.Manager()
        return_dict = manager.dict()

        p = multiprocessing.Process(
            target=custom_form_process,
            # Add request.user_id to the args tuple
            args=(request.message, request.user_id, return_dict), 
        )

        p.start()
        p.join()

        if not return_dict.get("result"):
            return {
                "reply": "The form filling process was interrupted unexpectedly. Please try again.",
                "status": "error",
            }

        if return_dict.get("error"):
            print(f"[Server] Custom form agent error: {return_dict.get('error')}")

        return {
            "reply": return_dict.get("result", "No response"),
            "status": "ok" if not return_dict.get("error") else "error",
        }

    except Exception as e:
        print(f"[Server] /api/customform error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
