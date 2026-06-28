"""LLM Chat - AutoDL/Qwen + Zhipu GLM-4-Flash fallback"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import httpx, json, random, os
logger = get_logger("evo.api.llm_chat")
router = APIRouter()

class LLMChatRequest(BaseModel):
    message: str = ""
    prompt: str = ""
    provider: Optional[str] = "zhipu"
    model: Optional[str] = "GLM-4-Flash"
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
    "zhipu": {
        "name": "GLM-4-Flash",
        "emoji": "\u2728",
        "endpoint": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "auth": "bearer",
        "default_model": "GLM-4-Flash",
        "models": ["GLM-4-Flash"],
    },
}

def _get_zhipu_key():
    for src in [os.environ.get("ZHIPU_API_KEY")]:
        if src: return src
    from api.agent_llm import _get_key
    return _get_key()

def _build_messages(req):
    text = req.prompt or req.message or ""
    return [{"role":"user","content":text}]

async def _call_zhipu(messages, timeout=30):
    api_key = _get_zhipu_key()
    if not api_key:
        return {"success": False, "error": "ZHIPU_API_KEY not configured"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            body = {"model":"GLM-4-Flash","messages":messages,"max_tokens":8192}
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            r = await client.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", json=body, headers=headers)
            data = r.json()
            content = data.get("choices",[{}])[0].get("message",{}).get("content","")
            if content:
                return {"success": True, "data": {"choices":[{"message":{"content":content}}]}}
        return {"success": False, "error": "zhipu returned empty"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/llm/chat")
async def chat(req: LLMChatRequest):
    pid = req.provider or "zhipu"
    p = PROVIDERS.get(pid)
    if not p: return {"success":False,"error":f"Provider {pid} not found"}

    # Zhipu provider
    if pid == "zhipu":
        return await _call_zhipu(_build_messages(req))

    # AutoDL / Qwen provider
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            body = {"messages": _build_messages(req), "max_tokens": 2000}
            if req.model: body["model"] = req.model
            r = await client.post(p["endpoint"], json=body)
            data = r.json()
            return {"success":True,"data":data}
    except Exception as e:
        # AutoDL failover to Zhipu
        logger.warning(f"[LLM] AutoDL failed ({e}), falling back to Zhipu")
        return await _call_zhipu(_build_messages(req))

@router.get("/api/v1/llm/providers")
async def list_providers():
    return {k:{"name":v["name"],"emoji":v["emoji"],"models":v["models"]} for k,v in PROVIDERS.items()}

@router.get("/api/v1/llm/default")
async def default_provider():
    return {"provider":"zhipu","model":"GLM-4-Flash"}

