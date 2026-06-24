"""
AUTO-EVO-AI V0.1 — 知识图谱 API
POST /api/v1/knowledge/node        添加节点
POST /api/v1/knowledge/edge        添加关系
POST /api/v1/knowledge/query       搜索节点
POST /api/v1/knowledge/neighbors   邻居查询
GET  /api/v1/knowledge/stats       图谱统计
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("routes_knowledge")
router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

try:
    from modules.knowledge_graph import KnowledgeGraphManager
    _kg = KnowledgeGraphManager()
except Exception as e:
    _kg = None
    logger.error(f"KnowledgeGraph 加载失败: {e}")

class NodeReq(BaseModel):
    name: str
    node_type: str = "concept"
    properties: dict = {}

class EdgeReq(BaseModel):
    source_id: str
    target_id: str
    rel_type: str = "related_to"
    properties: dict = {}

class QueryReq(BaseModel):
    keyword: str = ""
    node_type: str = ""
    limit: int = 50

class NeighborReq(BaseModel):
    node_id: str
    depth: int = 1

@router.post("/node")
async def add_node(req: NodeReq):
    if not _kg: return {"success": False, "error": "KG 未加载"}
    return _kg.add_node(req.name, req.node_type, req.properties)

@router.post("/edge")
async def add_edge(req: EdgeReq):
    if not _kg: return {"success": False, "error": "KG 未加载"}
    return _kg.add_edge(req.source_id, req.target_id, req.rel_type, req.properties)

@router.post("/query")
async def query(req: QueryReq):
    if not _kg: return {"success": False, "error": "KG 未加载"}
    return _kg.query(req.keyword, req.node_type, req.limit)

@router.post("/neighbors")
async def neighbors(req: NeighborReq):
    if not _kg: return {"success": False, "error": "KG 未加载"}
    return _kg.get_neighbors(req.node_id, req.depth)

@router.get("/stats")
async def kg_stats():
    if not _kg: return {"success": False, "error": "KG 未加载"}
    return _kg.get_stats()

# === Graphiti 风格时间感知端点 ===

class TemporalEdgeReq(BaseModel):
    source_id: str; target_id: str; rel_type: str = "related_to"; properties: dict = {}

@router.post("/edge/temporal")
async def add_edge_temporal(req: TemporalEdgeReq):
    """时间感知添加关系（自动版本管理）"""
    if not _kg: return {"success": False, "error": "KG 未加载"}
    return _kg.add_edge_temporal(req.source_id, req.target_id, req.rel_type, req.properties)

@router.get("/temporal/query")
async def temporal_query(time_point: str = None):
    """时间点查询：只返回指定时间有效的关系"""
    if not _kg: return {"success": False, "error": "KG 未加载"}
    return {"relations": _kg.get_temporal_query(time_point)}

@router.get("/fact/history")
async def fact_history(source_id: str = None, target_id: str = None, rel_type: str = None):
    """查看事实的历史版本"""
    if not _kg: return {"success": False, "error": "KG 未加载"}
    return {"relations": _kg.get_fact_history(source_id, target_id, rel_type)}
