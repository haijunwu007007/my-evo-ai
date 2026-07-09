"""
AUTO-EVO-AI V0.1 — 批量蒸馏引擎 + 全平台内容发现
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json, time, os, re, hashlib, asyncio
from pathlib import Path

router = APIRouter(prefix="/api/v1/distill", tags=["distill_batch"])
BASE = Path(__file__).resolve().parent.parent.parent
SKILLS_CUSTOM = BASE / "skills" / "custom"

# ── 发现引擎 ──────────────────────────

async def _search_web(q: str, num: int = 8) -> list:
    """统一搜索接口：先尝试内置搜索，失败则返回空"""
    results = []
    try:
        from skills.builtin.search_web import execute as web_search
        r = web_search({"query": q, "count": num})
        if isinstance(r, dict):
            items = r.get("results", [])
            for item in items[:num]:
                title = item.get("title","") or item.get("name","")
                link = item.get("link","") or item.get("url","")
                snippet = item.get("snippet","") or item.get("desc","")
                if title and link:
                    results.append({"title":title[:80],"url":link[:200],"desc":snippet[:120]})
    except: pass
    return results

async def _search_platform(platform: str, queries: list[str]) -> list[dict]:
    """搜索指定平台的内容"""
    sources = []
    seen = set()
    for q in queries:
        items = await _search_web(q, num=6)
        for item in items:
            url = item.get("url","")
            # 去重
            key = url[:80]
            if key in seen: continue
            seen.add(key)
            sources.append({
                "type": platform,
                "name": item.get("title","")[:60],
                "url": url,
                "desc": item.get("desc","")[:100]
            })
            if len(sources) >= 8: break
        if len(sources) >= 8: break
    return sources

@router.get("/discover")
async def discover_sources():
    """全平台自动发现可蒸馏内容"""
    all_sources = []
    seen = set()

    def add(s):
        key = s["url"][:60]
        if key not in seen:
            seen.add(key)
            all_sources.append(s)

    # 并行搜索各平台
    tasks = []
    
    # B站
    tasks.append(_search_platform("bilibili", [
        "site:bilibili.com AI教程 2026",
        "site:bilibili.com Python入门 2026",
        "site:bilibili.com 热门技术 2026",
        "site:bilibili.com 编程 教程 2026",
    ]))
    
    # 抖音
    tasks.append(_search_platform("douyin", [
        "site:douyin.com AI 教程 2026",
        "site:douyin.com 编程 教学 2026",
        "site:douyin.com 技术 干货 2026",
    ]))
    
    # 快手
    tasks.append(_search_platform("kuaishou", [
        "site:kuaishou.com AI 2026",
        "site:kuaishou.com 编程 2026",
        "site:kuaishou.com 教程 2026",
    ]))
    
    # 知乎
    tasks.append(_search_platform("zhihu", [
        "site:zhihu.com AI Agent 2026",
        "site:zhihu.com Python 入门 2026",
        "site:zhihu.com 编程 经验 2026",
    ]))
    
    # 微信公众号
    tasks.append(_search_platform("wechat", [
        "site:mp.weixin.qq.com AI 技术 2026",
        "site:mp.weixin.qq.com 编程 教程 2026",
    ]))
    
    # 视频号
    tasks.append(_search_platform("video", [
        "site:weixin.qq.com 视频号 AI 2026",
        "视频号 编程教程 2026",
        "视频号 技术分享 2026",
    ]))
    
    # 朋友圈
    tasks.append(_search_platform("moments", [
        "朋友圈 AI 技术 2026",
        "朋友圈 编程 2026",
    ]))
    
    # 掘金
    tasks.append(_search_platform("juejin", [
        "site:juejin.cn AI 教程 2026",
        "site:juejin.cn Python 2026",
        "site:juejin.cn 架构 2026",
    ]))
    
    # CSDN
    tasks.append(_search_platform("csdn", [
        "site:csdn.net AI 入门 2026",
        "site:csdn.net Python 项目 2026",
    ]))
    
    # GitHub
    tasks.append(_search_platform("github", [
        "site:github.com AI agent 教程",
        "site:github.com Python project 2026",
    ]))
    
    # 并行执行
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for platform_sources in results:
        if isinstance(platform_sources, list):
            for s in platform_sources:
                add(s)
    
    # 如果搜索结果太少，补上热门内置来源
    if len(all_sources) < 6:
        fallback = [
            {"type":"bilibili","name":"B站 - 李沐AI教程","url":"https://www.bilibili.com/video/BV1Mh411e7VU","desc":"李沐《动手学深度学习》系列教程"},
            {"type":"bilibili","name":"B站 - 小甲鱼Python","url":"https://www.bilibili.com/video/BV1Fs411z7pq","desc":"小甲鱼零基础入门Python教程"},
            {"type":"zhihu","name":"知乎AI话题","url":"https://www.zhihu.com/topic/19559436","desc":"AI相关热门问答"},
            {"type":"github","name":"GitHub热榜","url":"https://github.com/trending","desc":"每日GitHub趋势项目"},
            {"type":"wechat","name":"阮一峰技术周刊","url":"https://www.ruanyifeng.com/blog/","desc":"科技前沿动态每周更新"},
            {"type":"juejin","name":"掘金AI频道","url":"https://juejin.cn/","desc":"掘金技术社区AI板块"},
        ]
        for f in fallback:
            add(f)
    
    return {"success": True, "sources": all_sources, "total": len(all_sources), "has_search": len(all_sources) > 6}

# ── 自定义来源管理 ──────────────────────
_CUSTOM_SOURCES: list = []

class CustomSource(BaseModel):
    name: str
    query: str

@router.get("/sources")
async def list_custom_sources():
    return {"success": True, "sources": _CUSTOM_SOURCES, "total": len(_CUSTOM_SOURCES)}

@router.post("/sources/add")
async def add_custom_source(src: CustomSource):
    _CUSTOM_SOURCES.append({"name": src.name, "query": src.query, "added": time.time()})
    return {"success": True, "sources": _CUSTOM_SOURCES, "total": len(_CUSTOM_SOURCES)}

@router.delete("/sources/{idx}")
async def remove_custom_source(idx: int):
    if 0 <= idx < len(_CUSTOM_SOURCES):
        _CUSTOM_SOURCES.pop(idx)
    return {"success": True, "sources": _CUSTOM_SOURCES}
