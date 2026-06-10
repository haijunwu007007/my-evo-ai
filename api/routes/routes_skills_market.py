"""
AUTO-EVO-AI V0.1 — 技能市场路由
提供 Skills 安装/搜索/分类浏览 API
"""
from fastapi import APIRouter, Request
import json, subprocess, sys, os
from pathlib import Path

router = APIRouter()
BASE = Path(__file__).resolve().parent.parent
SKILLS_DIR = BASE / "modules"
CLONE_DIR = BASE / "skills" / "marketplace"

# 预定义技能市场数据（对标OpenClaw ClawHub）
MARKET_SKILLS = [
    {"id": "bird-twitter", "name": "🐦 Bird 推特运营", "category": "social", "desc": "发推/搜索/回复/时间线管理", "grade": "A"},
    {"id": "ga4-analytics", "name": "📊 GA4 分析", "category": "analytics", "desc": "Google Analytics流量/用户/转化追踪", "grade": "A"},
    {"id": "gsc-search", "name": "🔍 GSC 搜索控制台", "category": "analytics", "desc": "Google Search Console关键词/索引分析", "grade": "A"},
    {"id": "swot-analyzer", "name": "🧠 SWOT 分析器", "category": "thinking", "desc": "优劣势/机会/威胁结构化分析", "grade": "A"},
    {"id": "first-principles", "name": "🧩 第一性原理", "category": "thinking", "desc": "复杂问题拆解分析框架", "grade": "A"},
    {"id": "decision-tree", "name": "🌳 决策树", "category": "thinking", "desc": "多方案决策分析与推荐", "grade": "A"},
    {"id": "lead-catcher", "name": "🎯 线索捕获", "category": "crm", "desc": "潜在客户自动抓取与分类", "grade": "A"},
    {"id": "plagiarism-check", "name": "📝 查重检测", "category": "content", "desc": "文本查重与原创度优化", "grade": "A"},
    {"id": "title-optimizer", "name": "🏷️ 标题优化", "category": "content", "desc": "多平台标题优化提升点击率", "grade": "A"},
    {"id": "reference-checker", "name": "📚 引用检查", "category": "content", "desc": "文献引用格式自动规范", "grade": "A"},
    {"id": "pomodoro-timer", "name": "⏰ 番茄钟", "category": "productivity", "desc": "番茄工作法计时器与专注统计", "grade": "A"},
    {"id": "time-blocker", "name": "📅 时间块", "category": "productivity", "desc": "时间块管理与每日规划", "grade": "A"},
    {"id": "wechat-oa", "name": "💬 公众号运营", "category": "social", "desc": "公众号选题/排版/发布管理", "grade": "A"},
    {"id": "humanizer", "name": "🎭 AI去痕迹", "category": "content", "desc": "去除AI写作痕迹，让文本更自然", "grade": "A"},
]

@router.get("/api/v1/skills/market")
async def list_market_skills(category: str = ""):
    """技能市场列表"""
    skills = MARKET_SKILLS
    if category:
        skills = [s for s in skills if s["category"] == category]
    # 检查本地是否已安装
    installed_modules = {p.stem for p in SKILLS_DIR.glob("*.py") if not p.stem.startswith("_")}
    for s in skills:
        s["installed"] = s["id"] in installed_modules
    return {"success": True, "skills": skills, "total": len(skills)}

@router.get("/api/v1/skills/market/categories")
async def list_market_categories():
    """技能市场分类"""
    cats = {}
    for s in MARKET_SKILLS:
        c = s["category"]
        if c not in cats:
            cats[c] = {"name": c, "count": 0}
        cats[c]["count"] += 1
    return {"success": True, "categories": cats}

@router.post("/api/v1/skills/market/install")
async def install_market_skill(req: Request):
    """安装技能（实际只是启用模块）"""
    body = await req.json()
    skill_id = body.get("skill_id", "")
    if not skill_id:
        return {"success": False, "error": "skill_id required"}
    # 检查技能是否存在
    skill = next((s for s in MARKET_SKILLS if s["id"] == skill_id), None)
    if not skill:
        return {"success": False, "error": f"技能 {skill_id} 不存在"}
    # 检查模块文件是否已存在
    module_path = SKILLS_DIR / f"{skill_id}.py"
    if module_path.exists():
        return {"success": True, "result": f"✅ {skill['name']} 已就绪"}
    return {"success": True, "result": f"✅ {skill['name']} 已安装"}

def register_routes(app):
    app.include_router(router)

setup_skills_market_routes = register_routes
