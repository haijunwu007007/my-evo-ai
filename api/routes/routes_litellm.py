"""
AUTO-EVO-AI V0.1 — LiteLLM AI 网关路由
=====================================
统一对话 API，支持 100+ LLM 提供商自动切换
"""

import os, json, asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from core.logging_config import get_logger
from pydantic import BaseModel

router = APIRouter()
logger = get_logger("evo.api.litellm")


class LiteLLMChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class LiteLLMChatRequest(BaseModel):
    model: str = ""
    messages: List[LiteLLMChatMessage] = []
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False


def _get_gateway():
    """懒加载 LiteLLM 网关"""
    try:
        from modules.llm_litellm import get_litellm
        return get_litellm()
    except Exception as e:
        logger.warning(f"[LiteLLM] 网关不可用: {e}")
        return None


@router.get("/api/v1/litellm/providers")
async def list_providers():
    """列出已配置的 LLM 提供商"""
    gw = _get_gateway()
    if not gw:
        return {"success": True, "providers": [], "configured": False}
    return {"success": True, "providers": gw.get_providers(), "configured": True}


@router.get("/api/v1/litellm/models")
async def list_models():
    """列出可用模型"""
    gw = _get_gateway()
    if not gw:
        return {"success": True, "models": [], "configured": False}
    return {"success": True, "models": gw.get_models(), "configured": True}


@router.get("/api/v1/litellm/stats")
async def get_stats():
    """获取使用统计"""
    gw = _get_gateway()
    if not gw:
        return {"success": True, "stats": {}, "configured": False}
    return {"success": True, "stats": gw.get_stats(), "configured": True}


@router.get("/api/v1/litellm/health")
async def health():
    """健康检查"""
    gw = _get_gateway()
    if not gw:
        return {"success": True, "status": "unavailable", "configured": False}
    return {"success": True, **gw.health_check(), "configured": True}


@router.post("/api/v1/litellm/chat")
async def chat(req: LiteLLMChatRequest):
    """LiteLLM 统一对话接口"""
    gw = _get_gateway()
    if not gw:
        raise HTTPException(status_code=503, detail="LiteLLM 网关未初始化")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    result = await gw.chat(
        messages=messages,
        model=req.model or "",
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        stream=req.stream,
    )
    return result


@router.post("/api/v1/litellm/chat/stream")
async def chat_stream(req: LiteLLMChatRequest):
    """LiteLLM SSE 流式对话"""
    gw = _get_gateway()
    if not gw:
        raise HTTPException(status_code=503, detail="LiteLLM 网关未初始化")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    result = await gw.chat(
        messages=messages,
        model=req.model or "",
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        stream=True,
    )

    async def stream_response():
        try:
            import litellm
            litellm.api_key = os.environ.get("OPENAI_API_KEY", "")
            response = await litellm.acompletion(
                model=req.model or "gpt-4o",
                messages=messages,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield f"data: {json.dumps({'content': delta.content})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(stream_response(), media_type="text/event-stream")
