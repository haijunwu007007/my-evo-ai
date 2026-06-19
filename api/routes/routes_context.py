"""
AUTO-EVO-AI V0.1 — 上下文监控 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from modules.context_monitor import get_monitor

router = APIRouter()


class AddMessageRequest(BaseModel):
    role: str = "user"
    content: str = ""


@router.get("/api/v1/context/status")
async def context_status():
    m = get_monitor()
    return {"success": True, **m.get_status()}


@router.post("/api/v1/context/compact")
async def context_compact():
    m = get_monitor()
    result = m.compact()
    return {"success": True, **result}


@router.post("/api/v1/context/clear")
async def context_clear():
    m = get_monitor()
    m.clear()
    return {"success": True, "cleared": True}


@router.get("/api/v1/context/history")
async def context_history():
    m = get_monitor()
    return {"success": True, "snapshots": m.get_history()}


@router.post("/api/v1/context/add")
async def context_add(req: AddMessageRequest):
    m = get_monitor()
    m.add_message(req.role, req.content)
    return {"success": True, **m.get_status()}
