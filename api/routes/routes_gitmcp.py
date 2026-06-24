"""GitMCP转换器 — 任意GitHub仓库→Skill"""
import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("gitmcp")
router = APIRouter(prefix="/api/v1/gitmcp", tags=["gitmcp"])

try:
    from modules.gitmcp_converter import GitMCPConverter
    _mod = GitMCPConverter()
    _ok = True
except Exception as e:
    _ok = False
    logger.warning(f"GitMCP加载失败: {e}")

@router.get("/status")
def status():
    return {"success": True, "available": _ok, "module": "GitMCP Converter"}

class ConvertRequest(BaseModel):
    repo: str
    name: str = ""

@router.post("/convert")
def convert(req: ConvertRequest):
    if not _ok:
        return {"success": False, "error": "模块未加载"}
    return _mod.convert(req.repo, req.name)
