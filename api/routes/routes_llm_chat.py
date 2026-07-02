"""LLM Chat — 统一走 agent_llm.call_llm() → LLMPool（自动故障转移/多Provider）"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
from api.agent_llm import call_llm, get_active_model
logger = get_logger("evo.api.llm_chat")
router = APIRouter()

class LLMChatRequest(BaseModel):
    message: str = ""
    prompt: str = ""
    provider: Optional[str] = ""
    model: Optional[str] = ""
    context: Optional[list] = []
    system_prompt: Optional[str] = ""
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096


@router.post("/api/v1/llm/chat")
async def chat(req: LLMChatRequest):
    """LLM对话 — 统一经 agent_llm → LLMPool，自动故障转移/多Provider"""
    text = req.prompt or req.message or ""
    if not text:
        return {"success": False, "error": "消息内容为空"}

    # 构造 messages
    messages = []
    if req.system_prompt:
        messages.append({"role": "system", "content": req.system_prompt})
    if req.context:
        messages.extend(req.context[-6:])
    messages.append({"role": "user", "content": text})

    content, tool_calls = call_llm(messages, timeout=30)
    if content:
        return {"success": True, "data": {"choices": [{"message": {"content": content}}]}}
    return {"success": False, "error": "LLM 无返回（请检查 API Key 配置）"}


@router.get("/api/v1/llm/providers")
async def list_providers():
    """列出所有 Provider（从 LLMPool 读取）"""
    model_info = get_active_model()
    return {"success": True, "providers": model_info}


@router.get("/api/v1/llm/default")
async def default_provider():
    """当前默认 Provider"""
    model_info = get_active_model()
    return {
        "provider": model_info.get("provider", ""),
        "model": model_info.get("model", ""),
        "active": model_info.get("active", False),
    }
