"""LLM Chat - Only Qwen3.6 (AutoDL)"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import httpx, json, random
logger = get_logger("evo.api.llm_chat")
router = APIRouter()

class LLMChatRequest(BaseModel):
    message: str = ""
    prompt: str = ""
    provider: Optional[str] = "autodl"
    model: Optional[str] = "Qwen3.6-35B-Q4_K_M"
    context: Optional[list] = []

PROVIDERS = {
    "autodl": {
        "name": "Qwen3.6-35B",
        "emoji": "\u26a1",
        "endpoint": "http://127.0.0.1:5999/v1/chat/completions",
        "auth": "",
        "default_model": "Qwen3.6-35B-Q4_K_M",
        "models": ["Qwen3.6-35B-Q4_K_M"],
    },
}

def _build_messages(req):
    text = req.prompt or req.message or ""
    return [{"role":"user","content":text}]

@router.post("/api/v1/llm/chat")
async def chat(req: LLMChatRequest):
    pid = req.provider or "autodl"
    p = PROVIDERS.get(pid)
    if not p: return {"success":False,"error":f"Provider {pid} not found"}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            body = {"messages": _build_messages(req), "max_tokens": 2000}
            if req.model: body["model"] = req.model
            r = await client.post(p["endpoint"], json=body)
            data = r.json()
            return {"success":True,"data":data}
    except Exception as e:
        return {"success":False,"error":str(e)}

@router.get("/api/v1/llm/providers")
async def list_providers():
    return {k:{"name":v["name"],"emoji":v["emoji"],"models":v["models"]} for k,v in PROVIDERS.items()}

@router.get("/api/v1/llm/default")
async def default_provider():
    return {"provider":"autodl","model":"Qwen3.6-35B-Q4_K_M"}
