# -*- coding: utf-8 -*-
"""NLP意图识别 — 自然语言→工作流"""
from fastapi import APIRouter
from pydantic import BaseModel
import json

class _Req(BaseModel):
    text: str

router = APIRouter(prefix="/api/v1/nlp", tags=["nlp"])

@router.post("/interpret")
async def interpret(req: _Req):
    text = req.text
    """解析自然语言指令为可执行工作流"""
    t = text.lower()
    steps = []
    
    # 博客
    if any(w in t for w in ["博客","blog","网站","site"]):
        steps = [
            {"step":"generate","tool":"project_generator","params":{"type":"blog"}},
            {"step":"deploy","tool":"deploy_v2","params":{"auto":True}},
            {"step":"configure","tool":"dns","params":{"domain":"auto"}}
        ]
    # 文档/合同
    elif any(w in t for w in ["文档","doc","合同","contract"]):
        steps = [{"step":"generate","tool":"docx_processor","params":{}}]
    # 视频
    elif any(w in t for w in ["视频","video"]):
        steps = [{"step":"generate","tool":"video","params":{"engine":"pixelle"}}]
    # 数据分析
    elif any(w in t for w in ["分析","分析","图表","chart"]):
        steps = [{"step":"analyze","tool":"lida_visualize","params":{}}]
    # 默认
    else:
        steps = [{"step":"ask","tool":"llm","params":{"prompt":t[:200]}}]
    
    return {"success": True, "intent": t[:30], "steps": steps, "total": len(steps)}

@router.get("/status")
async def nlp_status():
    return {"available": True, "mode": "rule-based"}
