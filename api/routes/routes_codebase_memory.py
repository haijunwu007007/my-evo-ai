"""
AUTO-EVO-AI V0.1 — Codebase Memory MCP 桥接路由
功能：索引代码库、查询代码库、代码理解、知识检索（类似 codebase-memory-mcp）
"""
import os, json, logging, time
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("routes_codebase_memory")
router = APIRouter(prefix="/api/v1/codebase-memory", tags=["codebase"])

try:
    from modules.codebase_engine import CodebaseIndexer, CodebaseAgent
    _indexer = CodebaseIndexer()
    _agent = CodebaseAgent()
    _available = True
except Exception as e:
    _indexer = _agent = None
    _available = False
    logger.warning(f"CodebaseMemory 模块加载失败: {e}")

class QueryRequest(BaseModel):
    query: str = ""
    path: str = ""
    depth: int = 3

@router.get("/status")
def get_status():
    return {
        "success": True,
        "available": _available,
        "engine": "codebase-memory-mcp",
        "indexed_files": getattr(_indexer, "_indexed_files", 0) if _indexer else 0
    }

@router.post("/index")
def index_codebase(req: QueryRequest):
    """索引代码库"""
    if not _indexer:
        return {"success": False, "error": "模块未加载"}
    try:
        path = req.path or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = _indexer.index_path(path, depth=req.depth)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

@router.post("/query")
def query_codebase(req: QueryRequest):
    """查询代码库知识"""
    if not _agent:
        return {"success": False, "error": "模块未加载"}
    try:
        result = _agent.query(req.query)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

@router.post("/analyze")
def analyze_file(req: QueryRequest):
    """分析指定文件"""
    if not _agent:
        return {"success": False, "error": "模块未加载"}
    try:
        if not req.path or not os.path.isfile(req.path):
            return {"success": False, "error": "文件路径无效"}
        result = _agent.analyze_file(req.path)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}
