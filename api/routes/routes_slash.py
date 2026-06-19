"""
AUTO-EVO-AI V0.1 — 斜杠命令 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from modules.slash_commands import execute, list_commands, get_history

router = APIRouter()


class SlashRequest(BaseModel):
    text: str
    context: dict = {}


@router.post("/api/v1/slash/execute")
async def slash_execute(req: SlashRequest):
    try:
        result = await execute(req.text, req.context)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/slash/commands")
async def slash_commands(category: str = ""):
    return {"success": True, "commands": list_commands(category)}


@router.get("/api/v1/slash/history")
async def slash_history(limit: int = 50):
    return {"success": True, "history": get_history(limit)}
