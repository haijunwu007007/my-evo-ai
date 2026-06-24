"""
AUTO-EVO-AI V0.1 — Hyper-Extract 知识提取 API
POST /api/v1/extract/entities     提取实体
POST /api/v1/extract/keywords     提取关键词
POST /api/v1/extract/summary      提取摘要
POST /api/v1/extract/classify     文本分类
POST /api/v1/extract/analyze      全量分析
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("routes_extract")
router = APIRouter(prefix="/api/v1/extract", tags=["extract"])

try:
    from modules.hyper_extract import HyperExtract
    _extractor = HyperExtract()
except Exception as e:
    _extractor = None
    logger.error(f"HyperExtract 加载失败: {e}")

class TextReq(BaseModel):
    text: str
    top_n: int = 10
    max_sentences: int = 3

@router.post("/entities")
async def extract_entities(req: TextReq):
    if not _extractor: return {"success": False, "error": "Extractor 未加载"}
    return _extractor.extract_entities(req.text)

@router.post("/keywords")
async def extract_keywords(req: TextReq):
    if not _extractor: return {"success": False, "error": "Extractor 未加载"}
    return _extractor.extract_keywords(req.text, req.top_n)

@router.post("/summary")
async def extract_summary(req: TextReq):
    if not _extractor: return {"success": False, "error": "Extractor 未加载"}
    return _extractor.extract_summary(req.text, req.max_sentences)

@router.post("/classify")
async def classify_text(req: TextReq):
    if not _extractor: return {"success": False, "error": "Extractor 未加载"}
    return _extractor.classify_text(req.text)

@router.post("/analyze")
async def full_analysis(req: TextReq):
    if not _extractor: return {"success": False, "error": "Extractor 未加载"}
    return _extractor.full_analysis(req.text)

@router.get("/status")
async def extract_status():
    return {"success": True, "available": _extractor is not None, "version": "V0.1"}
