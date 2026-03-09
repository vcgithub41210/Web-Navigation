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

class ChatRequest(BaseModel):
    message: str
    user_id: str


def agent_process(message, user_id, return_dict):
    """
    Process agent request with dynamic user context from resume.
    """
    from agentest import run_orchestrator
    from utils.supabase_manager import download_resume, delete_temp_resume
    from utils.user_context_extractor import extract_user_context
    
    resume_path = None
    
    try:
        print(f"[Server] Downloading resume for user: {user_id}")
        resume_path = download_resume(user_id)
        
        print(f"[Server] Extracting user context from resume")
        user_context = extract_user_context(resume_path)
        
        print(f"[Server] Running orchestrator with user context")
        result = run_orchestrator(message, user_context, resume_path)
        
        return_dict["result"] = result
        return_dict["error"] = None
        
    except Exception as e:
        error_msg = f"Agent process error: {str(e)}"
        print(f"[Server] ERROR: {error_msg}")
        return_dict["result"] = "I encountered an error processing your request. Please make sure you've uploaded your resume."
        return_dict["error"] = error_msg
        
    finally:
        if resume_path:
            delete_temp_resume(resume_path)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint that processes messages with user-specific context.
    """
    try:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        manager = multiprocessing.Manager()
        return_dict = manager.dict()

        p = multiprocessing.Process(
            target=agent_process,
            args=(request.message, request.user_id, return_dict)
        )

        p.start()
        p.join()

        if return_dict.get("error"):
            print(f"[Server] Agent returned error: {return_dict.get('error')}")

        return {
            "reply": return_dict.get("result", "No response"),
            "status": "ok" if not return_dict.get("error") else "error"
        }
        
    except Exception as e:
        print(f"[Server] Chat endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))