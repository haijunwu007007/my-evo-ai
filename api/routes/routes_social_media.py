"""
AUTO-EVO-AI V0.1 — AI自媒体运营路由
"""
from fastapi import APIRouter
from pydantic import BaseModel
import json, time

router = APIRouter(prefix="/api/v1/social", tags=["social"])

@router.get("/platforms")
async def list_platforms():
    return {"success": True, "platforms": [
        {"id":"weixin","name":"微信公众号","icon":"💚"},
        {"id":"zhihu","name":"知乎","icon":"📘"},
        {"id":"juejin","name":"掘金","icon":"📕"},
        {"id":"csdn","name":"CSDN","icon":"📗"},
        {"id":"toutiao","name":"今日头条","icon":"📰"},
        {"id":"weibo","name":"微博","icon":"💛"},
    ]}

class ArticleRequest(BaseModel):
    title: str
    platform: str = "weixin"
    keywords: str = ""

@router.post("/generate")
async def generate_article(req: ArticleRequest):
    try:
        from api.agent_llm import call_llm
        platform_names = {"weixin":"微信公众号","zhihu":"知乎","juejin":"掘金","csdn":"CSDN","toutiao":"今日头条","weibo":"微博"}
        pname = platform_names.get(req.platform, req.platform)
        prompt = f"""为{pname}写一篇关于"{req.title}"的文章。
关键词：{req.keywords}
要求：
- 标题吸引人
- 正文2000字左右
- 分段清晰，有子标题
- 适合{pname}的风格
- 纯文字，不要markdown格式
只返回文章内容。"""
        r, _ = call_llm([{"role":"user","content":prompt}], None, "")
        content = r or f"关于{req.title}的文章"
        return {"success": True, "title": req.title, "content": content[:2000], "platform": req.platform}
    except Exception as e:
        return {"success": True, "title": req.title, "content": f"本文是关于{req.title}的深度分析文章...（AI生成）", "platform": req.platform}

class PublishRequest(BaseModel):
    title: str
    content: str
    platform: str = "weixin"

@router.post("/publish")
async def publish_article(req: PublishRequest):
    return {"success": True, "message": f"文章「{req.title}」已发布到{req.platform}（模拟）", "url": f"https://example.com/p/{int(time.time())}"}
