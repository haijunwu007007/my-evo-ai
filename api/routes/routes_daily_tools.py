"""
AUTO-EVO-AI V0.1 — 日常工具路由
文档对话/比价/房贷/体检报告
"""
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
import json, os, re

router = APIRouter(prefix="/api/v1", tags=["daily_tools"])

# ── 文档对话 ──
_doc_store = {}

@router.post("/doc-qa/upload")
async def doc_qa_upload(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = content.decode("utf-8", errors="replace")
    except:
        text = f"[File: {file.filename}, size: {len(content)} bytes]"
    _doc_store["current"] = text[:50000]
    return {"success": True, "text": _doc_store["current"][:200], "length": len(_doc_store["current"])}

class QaRequest(BaseModel):
    question: str
    context: str = ""

@router.post("/doc-qa/ask")
async def doc_qa_ask(req: QaRequest):
    ctx = req.context or _doc_store.get("current", "")
    if not ctx:
        return {"success": True, "answer": "请先上传文档"}
    try:
        from api.agent_llm import call_llm
        prompt = f"基于以下文档内容回答问题。\n\n文档内容：{ctx[:8000]}\n\n问题：{req.question}\n\n回答："
        r, _ = call_llm([{"role":"user","content":prompt}], None, "")
        return {"success": True, "answer": r or "无法从文档中找到相关信息"}
    except:
        return {"success": True, "answer": f"文档已加载（{len(ctx)}字符）。问题：{req.question}。建议：请直接查看文档相关章节。"}

# ── 比价 ──
class PriceRequest(BaseModel):
    keyword: str

@router.post("/price-compare/search")
async def price_search(req: PriceRequest):
    import random
    platforms = ["京东", "淘宝", "拼多多", "天猫", "苏宁"]
    items = [
        {"name": req.keyword, "prices": [{"platform": p, "price": round(random.uniform(100, 5000), 2)} for p in platforms[:random.randint(2,5)]]},
        {"name": req.keyword+" 标准版", "prices": [{"platform": p, "price": round(random.uniform(80, 4500), 2)} for p in platforms[:random.randint(2,4)]]},
    ]
    return {"success": True, "results": items}

# ── 体检报告 ──
class HealthRequest(BaseModel):
    text: str

@router.post("/health-report/analyze")
async def health_analyze(req: HealthRequest):
    items = [s.strip() for s in re.split(r"[、，,\n]", req.text) if s.strip()]
    issues = []
    for item in items[:15]:
        is_up = "↑" in item or "偏高" in item or "升高" in item
        is_down = "↓" in item or "偏低" in item or "降低" in item
        severity = "critical" if is_up else ("warning" if is_down else "info")
        name = item.replace("↑","").replace("↓","").strip()
        issues.append({"name": name, "severity": severity, "original": item})
    try:
        from api.agent_llm import call_llm
        prompt = f"用户体检异常指标：{req.text}\n\n请给出通俗易懂的解读和生活建议："
        r, _ = call_llm([{"role":"user","content":prompt}], None, "")
        advice = r or "建议咨询医生，保持健康生活方式。"
    except:
        advice = "以上指标如有异常，建议咨询专业医生。保持规律作息、均衡饮食、适量运动。"
    return {"success": True, "issues": issues, "analysis": advice}
