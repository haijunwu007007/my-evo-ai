"""
AUTO-EVO-AI V0.1 — AI自媒体运营路由
功能：AI生成文章 + 多渠道发布 + 发布历史
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json, time, os
from pathlib import Path

router = APIRouter(prefix="/api/v1/social", tags=["social"])

class GenerateRequest(BaseModel):
    topic: str
    style: str = "专业深度"
    word_count: str = "中篇"
    platforms: list[str] = []

class PublishRequest(BaseModel):
    article: str
    platforms: list[str]
    topic: str = ""

_HISTORY: list = []
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DATA_DIR.mkdir(exist_ok=True)

def _load_history():
    global _HISTORY
    p = _DATA_DIR / "social_history.json"
    if p.exists():
        try:
            _HISTORY = json.loads(p.read_text(encoding="utf-8"))
        except: _HISTORY = []

def _save_history():
    p = _DATA_DIR / "social_history.json"
    p.write_text(json.dumps(_HISTORY[-50:], ensure_ascii=False), encoding="utf-8")

_load_history()

@router.post("/generate")
async def generate_article(req: GenerateRequest):
    """AI生成文章"""
    try:
        from api.agent_llm import call_llm
        wc_map = {"短篇":"800-1200","中篇":"1500-2500","长篇":"3000-5000"}
        wc = wc_map.get(req.word_count, "1500-2500")
        platforms_str = ", ".join(req.platforms) if req.platforms else "通用"
        prompt = f"""请以「{req.style}」的风格，撰写一篇关于「{req.topic}」的文章。
要求：字数约{wc}字，适合发布在{platforms_str}平台。
标题要吸睛，开篇有吸引力，正文有深度，结尾有总结。
直接输出文章内容，不要输出额外说明。"""
        article, _ = call_llm([{"role":"user","content":prompt}], None, "")
        if not article:
            article = f"# {req.topic}\n\n（AI生成内容暂不可用，请稍后重试）\n\n---\n\n*本文由 AUTO-EVO-AI 自动生成*"
        word_count = len(article.replace("\n",""))
        return {"success": True, "article": article, "word_count": word_count, "topic": req.topic}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/publish")
async def publish_article(req: PublishRequest):
    """发布文章到指定平台（模拟 + 记录）"""
    results = []
    for platform in req.platforms:
        try:
            # 模拟发布成功
            results.append({"platform": platform, "success": True, "url": f"https://{platform}.com/evopost/{int(time.time())}", "time": time.time()})
        except Exception as e:
            results.append({"platform": platform, "success": False, "error": str(e)})
    record = {
        "time": time.time(),
        "topic": req.topic or "未命名",
        "platforms": req.platforms,
        "word_count": len(req.article.replace("\n","")),
        "results": results,
    }
    _HISTORY.insert(0, record)
    _save_history()
    return {"success": True, "results": results}

@router.get("/history")
async def get_history(limit: int = 20):
    return {"success": True, "history": _HISTORY[:limit]}
