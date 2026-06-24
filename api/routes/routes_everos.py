"""
AUTO-EVO-AI V0.1 — EverOS 记忆系统 API 路由
"""
import logging
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger("routes_everos")
router = APIRouter(prefix="/api/v1/everos", tags=["everos"])

try:
    from modules.everos_memory import EverOSMemory
    engine = EverOSMemory()
except Exception as e:
    engine = None
    logger.error(f"EverOS load failed: {e}")

class AddMemoryRequest(BaseModel):
    scope: str = "default"
    content: str
    type: str = "note"
    entities: List[str] = []
    session_id: Optional[str] = None

class QueryRequest(BaseModel):
    q: str
    scope: Optional[str] = None
    limit: int = 10

@router.get("/status")
def everos_status():
    if not engine:
        return {"success": False, "error": "EverOS not loaded"}
    return engine.status()

@router.post("/add")
def everos_add(req: AddMemoryRequest):
    if not engine:
        return {"success": False, "error": "EverOS not loaded"}
    return engine.add_memory(req.scope, req.content, req.type, req.entities, req.session_id)

@router.post("/query")
def everos_query(req: QueryRequest):
    if not engine:
        return {"success": False, "error": "EverOS not loaded"}
    return engine.query(req.q, req.scope, req.limit)

@router.get("/session/{session_id}")
def everos_session(session_id: str):
    if not engine:
        return {"success": False, "error": "EverOS not loaded"}
    return engine.get_session(session_id)

@router.get("/entities")
def everos_entities():
    if not engine:
        return {"success": False, "error": "EverOS not loaded"}
    return engine.get_entities()

@router.post("/consolidate")
def everos_consolidate():
    if not engine:
        return {"success": False, "error": "EverOS not loaded"}
    return engine.consolidate()
