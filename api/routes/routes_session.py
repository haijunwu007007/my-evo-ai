"""
AUTO-EVO-AI V0.1 — 会话恢复 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from modules.session_resume import get_session_resume

router = APIRouter()


class CreateSessionRequest(BaseModel):
    label: str = "新会话"
    summary: str = ""


class ResumeRequest(BaseModel):
    session_id: str


@router.post("/api/v1/sessions/create")
async def session_create(req: CreateSessionRequest = CreateSessionRequest()):
    sr = get_session_resume()
    sid = sr.create_session(req.label, req.summary)
    return {"success": True, "session_id": sid}


@router.get("/api/v1/sessions/list")
async def session_list(limit: int = 20):
    sr = get_session_resume()
    return {"success": True, "sessions": sr.get_recent_sessions(limit)}


@router.post("/api/v1/sessions/resume/{session_id}")
async def session_resume(session_id: str):
    sr = get_session_resume()
    ok = sr.set_active(session_id)
    if not ok:
        raise HTTPException(404, "会话不存在")
    info = sr.get_session_info(session_id)
    return {"success": True, "session": info, "messages": sr.get_messages(session_id)}


@router.get("/api/v1/sessions/{session_id}")
async def session_info(session_id: str):
    sr = get_session_resume()
    info = sr.get_session_info(session_id)
    if not info:
        raise HTTPException(404, "会话不存在")
    return {"success": True, "session": info}


@router.get("/api/v1/sessions/{session_id}/messages")
async def session_messages(session_id: str, limit: int = 200):
    sr = get_session_resume()
    msgs = sr.get_messages(session_id, limit)
    return {"success": True, "messages": msgs, "count": len(msgs)}


@router.delete("/api/v1/sessions/{session_id}")
async def session_delete(session_id: str):
    sr = get_session_resume()
    sr.delete_session(session_id)
    return {"success": True, "deleted": True}
