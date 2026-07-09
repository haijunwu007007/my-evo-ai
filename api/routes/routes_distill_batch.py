"""
AUTO-EVO-AI V0.1 — 批量蒸馏引擎
支持：批量URL/YouTube频道/博客/文本 -> 一键生成合集技能
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json, time, os, re, hashlib
from pathlib import Path

router = APIRouter(prefix="/api/v1/distill", tags=["distill_batch"])
BASE = Path(__file__).resolve().parent.parent.parent
SKILLS_CUSTOM = BASE / "skills" / "custom"

class BatchRequest(BaseModel):
    type: str = "urls"  # urls / youtube / blog / texts
    items: list[str] = []
    name: str = "批量蒸馏"

@router.get("/discover")
async def discover_sources():
    """自动发现可蒸馏的热门来源"""
    sources = []
    seen = set()
    
    def add(s):
        key = s["url"][:60]
        if key not in seen:
            seen.add(key)
            sources.append(s)
    
    # 1. 尝试动态搜索（web_search skill）
    try:
        from skills.builtin.search_web import search
        for q in ["AI Agent 教程", "Python 入门教程", "开源项目", "2026 AI 工具"]:
            try:
                res = search(q, num=5)
                if isinstance(res, dict) and res.get("success"):
                    items = res.get("results", res.get("data", []))
                    for item in items[:3]:
                        add({"type": "search", "name": item.get("title","")[:60], "url": item.get("link","") or item.get("url",""), "desc": item.get("snippet","")[:100]})
            except: pass
    except: pass
    
    # 2. 内置热门来源（真实中文技术社区）
    builtin = [
        {"type":"blog","name":"阮一峰的技术周刊","url":"https://www.ruanyifeng.com/blog/","desc":"每周分享科技前沿动态，涵盖AI/编程/科技"},
        {"type":"blog","name":"美团技术团队","url":"https://tech.meituan.com/","desc":"美团技术博客，Java/分布式/系统设计"},
        {"type":"blog","name":"阿里云开发者社区","url":"https://developer.aliyun.com/","desc":"阿里云技术分享，云计算/大数据/AI"},
        {"type":"blog","name":"腾讯云开发者社区","url":"https://cloud.tencent.com/developer","desc":"腾讯云技术博客，AI/云原生/架构"},
        {"type":"blog","name":"字节跳动技术团队","url":"https://juejin.cn/user/1838039172387262","desc":"字节跳动技术博客"},
        {"type":"blog","name":"GitHub 热榜","url":"https://github.com/trending","desc":"GitHub每日趋势，发现开源好项目"},
        {"type":"blog","name":"知乎AI话题","url":"https://www.zhihu.com/topic/19559436","desc":"知乎AI相关热门问答和文章"},
        {"type":"blog","name":"开源中国","url":"https://www.oschina.net/","desc":"开源技术社区，新闻/博客/问答"},
        {"type":"blog","name":"InfoQ 中文","url":"https://www.infoq.cn/","desc":"技术趋势/架构实践/AI应用"},
        {"type":"blog","name":"V2EX 技术","url":"https://www.v2ex.com/","desc":"技术交流社区，编程/创业/分享"},
        {"type":"blog","name":"CSDN AI频道","url":"https://www.csdn.net/","desc":"中文开发者社区，AI/编程/教程"},
        {"type":"blog","name":"掘金 AI","url":"https://juejin.cn/","desc":"开发者技术社区，前端/AI/后端"},
    ]
    for b in builtin:
        add(b)
    
    return {"success": True, "sources": sources, "total": len(sources)}

@router.post("/batch")
async def batch_distill(req: BatchRequest):
    items = req.items[:100]
    total = len(items)
    if total == 0:
        return {"success": False, "error": "内容为空"}
    
    # 生成技能ID
    name = req.name or "批量蒸馏"
    skill_id = "batch_" + hashlib.md5(name.encode()).hexdigest()[:8]
    
    # 分析内容类型和数量
    type_count = {"url": 0, "youtube": 0, "blog": 0, "text": 0}
    for item in items:
        s = item.strip().lower()
        if "youtube.com" in s or "youtu.be" in s:
            type_count["youtube"] += 1
        elif s.startswith("http"):
            type_count["url"] += 1
        elif len(s) > 50:
            type_count["blog"] += 1
        else:
            type_count["text"] += 1
    
    # LLM生成技能摘要
    summary = ""
    try:
        from api.agent_llm import call_llm
        source_preview = "\n".join([item[:100] for item in items[:8]])
        prompt = f"以下是一个创作者/系列的内容标题列表（共{total}项）:\n{source_preview}\n...\n\n请分析这批内容的主题领域和核心知识点，生成一段100字以内的技能描述。输出格式: 描述内容。"
        r, _ = call_llm([{"role": "user", "content": prompt}], timeout=30)
        if r: summary = r.strip()
    except Exception:
        summary = f"基于 {total} 项内容的批量蒸馏技能"
    
    # 创建SKILL.md
    target = SKILLS_CUSTOM / skill_id
    target.mkdir(parents=True, exist_ok=True)
    
    tags = []
    if type_count["youtube"] > 0: tags.append("视频")
    if type_count["blog"] > 0: tags.append("博客")
    if type_count["url"] > 0: tags.append("网页")
    tags.append("批量蒸馏")
    
    skill_md = f"""---
name: "{name}"
description: "{summary}"
version: "1.0.0"
author: "AUTO-EVO-AI"
category: "批量蒸馏"
tags: [{','.join(f'"{t}"' for t in tags)}]
total_items: {total}
sources:
"""
    for item in items[:20]:
        skill_md += f"  - \"{item[:120]}\"\n"
    if total > 20:
        skill_md += f"  - \"... 共{total}项\"\n"
    skill_md += f"""---

# {name}

## 来源
批量蒸馏自 {total} 项内容。

## 使用方法
在聊天中输入「{name}」或「{skill_id}」来激活此技能。

## 内容清单（{total}项）
"""
    for i, item in enumerate(items[:50], 1):
        skill_md += f"{i}. {item[:120]}\n"
    if total > 50:
        skill_md += f"\n... 共{total}项\n"
    
    (target / "SKILL.md").write_text(skill_md, encoding="utf-8")
    
    # 创建简单main.py
    main_py = f'''"""
{name} — 批量蒸馏技能
来源: {total} 项内容
"""
__version__ = "1.0.0"

def execute(params=None, context=None):
    """执行批量蒸馏技能"""
    if params and params.get("action") == "summary":
        return {{"success": True, "name": "{name}", "total": {total}, "summary": """{summary}"""}}
    return {{"success": True, "name": "{name}", "total": {total}, "status": "ready"}}

def get_status():
    return {{"success": True, "module": "{skill_id}", "total_items": {total}, "ready": True}}

module_class = type("{skill_id}", (), {{"execute": execute, "get_status": get_status}})
'''
    (target / "main.py").write_text(main_py, encoding="utf-8")
    
    return {
        "success": True,
        "skill_id": skill_id,
        "skill_name": name,
        "total": total,
        "processed": total,
        "summary": summary[:200],
        "path": str(target)
    }
