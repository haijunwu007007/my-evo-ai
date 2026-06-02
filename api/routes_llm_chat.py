"""LLM Chat — 真实 AI 对话，非规则匹配"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import httpx, json

logger = get_logger("evo.api.llm_chat")
router = APIRouter()

class LLMChatRequest(BaseModel):
    message: str
    api_key: Optional[str] = None
    model: Optional[str] = "gpt-3.5-turbo"
    context: Optional[list] = []

@router.post("/api/v1/chat/llm")
async def llm_chat(req: LLMChatRequest):
    if not req.message.strip():
        raise HTTPException(400, detail="说点什么")

    key = req.api_key or ""
    if not key:
        # 无 API Key 时尝试调用本地模型或 LiteLLM
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post("http://localhost:8000/v1/chat/completions",
                    json={"model": "local", "messages": [
                        {"role": "user", "content": req.message}
                    ]})
                if r.status_code == 200:
                    data = r.json()
                    return {"success": True, "result": data["choices"][0]["message"]["content"], "model": "local"}
        except:
            pass
        return {"success": False, "error": "no_api_key", "hint": "请先在系统后台配置 API Key，或输入「你会什么」查看帮助"}

    # 有 API Key → 调用 OpenAI/兼容 API
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            messages = [{"role": "system", "content": "你是 AUTO-EVO-AI 助手，用中文回答，简洁直接。"}]
            for ctx in (req.context or [])[-6:]:
                if isinstance(ctx, dict):
                    messages.append({"role": ctx.get("role", "user"), "content": str(ctx.get("content", ""))})
            messages.append({"role": "user", "content": req.message})

            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": req.model, "messages": messages, "temperature": 0.7, "max_tokens": 1024}
            )
            if r.status_code == 200:
                data = r.json()
                return {"success": True, "result": data["choices"][0]["message"]["content"], "model": data["model"] if "model" in data else req.model}
            else:
                return {"success": False, "error": f"API 返回 {r.status_code}", "detail": r.text[:200]}
    except Exception as e:
        # 降级到规则匹配
        return {"success": False, "error": str(e), "fallback": True}
