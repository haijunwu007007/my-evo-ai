"""
AUTO-EVO-AI V0.1 — Graphify 代码知识图谱 API
POST /api/v1/graphify/index    索引代码目录
POST /api/v1/graphify/query    查询知识图谱
POST /api/v1/graphify/call-graph 函数调用图
POST /api/v1/graphify/dependencies 文件依赖
GET  /api/v1/graphify/stats    图谱统计
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("routes_graphify")
router = APIRouter(prefix="/api/v1/graphify", tags=["graphify"])

try:
    from modules.graphify_index import GraphifyIndex
    _engine = GraphifyIndex()
except Exception as e:
    _engine = None
    logger.error(f"Graphify 加载失败: {e}")

class IndexRequest(BaseModel):
    path: str = "."

class QueryRequest(BaseModel):
    qtype: str = "all"
    keyword: str = ""
    file_path: str = ""
    entity_type: str = ""

class CallGraphRequest(BaseModel):
    function: str = ""
    depth: int = 2

class DepsRequest(BaseModel):
    file_path: str = ""

@router.post("/index")
async def graphify_index(req: IndexRequest):
    if not _engine:
        return {"success": False, "error": "Graphify 未加载"}
    return _engine.index_directory(req.path)

@router.post("/query")
async def graphify_query(req: QueryRequest):
    if not _engine:
        return {"success": False, "error": "Graphify 未加载"}
    return _engine.query(req.qtype, req.keyword, req.file_path, req.entity_type)

@router.post("/call-graph")
async def graphify_call_graph(req: CallGraphRequest):
    if not _engine:
        return {"success": False, "error": "Graphify 未加载"}
    return _engine.get_call_graph(req.function, req.depth)

@router.post("/dependencies")
async def graphify_dependencies(req: DepsRequest):
    if not _engine:
        return {"success": False, "error": "Graphify 未加载"}
    return _engine.get_file_dependencies(req.file_path)

@router.get("/stats")
async def graphify_stats():
    if not _engine:
        return {"success": False, "error": "Graphify 未加载"}
    return _engine.query(qtype="stats")
