from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

import asyncio
import multiprocessing

def agent_process(message, return_dict):
    #from agentest import run_orchestrator
    #result = run_orchestrator(message)

    from googleform import run_agent
    result = run_agent(message)
    return_dict["result"] = result

@app.post("/api/chat")
async def chat(request: ChatRequest):
    manager = multiprocessing.Manager()
    return_dict = manager.dict()

    p = multiprocessing.Process(
        target=agent_process,
        args=(request.message, return_dict)
    )

    p.start()
    p.join()

    return {
        "reply": return_dict.get("result", "No response"),
        "status": "ok"
    }
