"""
AUTO-EVO-AI V0.1 — 重排序引擎
基于查询词命中率重排序，用于 RAG 检索结果精排
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import re, math

router = APIRouter()


class RerankRequest(BaseModel):
    query: str = ""
    documents: Optional[list[str]] = None
    top_k: int = 5


def _score_document(query: str, doc: str) -> float:
    """计算文档与查询的匹配分数"""
    q_words = set(re.findall(r'\w+', query.lower()))
    d_words = re.findall(r'\w+', doc.lower())
    if not q_words or not d_words:
        return 0.0
    # 词重叠率
    overlap = sum(1 for w in q_words if w in d_words)
    word_overlap = overlap / len(q_words)
    # 精确短语命中加成
    phrase_bonus = 0.0
    if len(query) > 2 and query.lower() in doc.lower():
        phrase_bonus = 0.3
    # 位置权重（越靠前越好）
    position_weight = max(0, 1.0 - len(d_words) / 5000)
    return word_overlap * 0.5 + phrase_bonus + position_weight * 0.2


@router.post("/api/v1/rerank")
async def rerank_documents(req: RerankRequest):
    """对文档列表进行重排序"""
    if not req.query or not req.documents:
        return {"success": True, "results": [], "total": 0}
    scored = []
    for doc in req.documents:
        score = _score_document(req.query, doc)
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [
        {"index": i, "score": round(score, 4), "document": doc[:500]}
        for i, (score, doc) in enumerate(scored[:req.top_k])
    ]
    return {"success": True, "results": results, "total": len(req.documents)}


def register_routes(app):
    """兼容性入口"""
    app.include_router(router)


setup_rerank_routes = register_routes
