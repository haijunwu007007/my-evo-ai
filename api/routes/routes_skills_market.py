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
    body = await req.json()
    skill_id = body.get("skill_id", "")
    if not skill_id:
        return {"success": False, "error": "skill_id required"}
    skill = next((s for s in MARKET_SKILLS if s["id"] == skill_id), None)
    if not skill:
        return {"success": False, "error": "skill not found"}
    mp = SKILLS_DIR / (skill_id + ".py")
    if mp.exists():
        return {"success": True, "result": skill["name"] + " ready"}
    sid = skill_id.replace("-", "_")
    cn = "".join(x.capitalize() for x in sid.split("_"))
    c = json.dumps({"id": skill_id, "name": cn, "version": "V0.1", "group": skill["category"], "grade": "A", "description": skill["desc"]}, ensure_ascii=False)
    c += "\nfrom modules._base.enterprise_module import EnterpriseModule"
    c += "\nclass " + cn + "(EnterpriseModule):"
    c += '\n    async def execute(self,action="run",params=None):'
    c += '\n        return {"success":True,"module":"' + skill_id + '","action":action}'
    c += '\nmodule_class = ' + cn
    try:
        mp.write_text(c, encoding="utf-8")
        return {"success": True, "result": skill["name"] + " installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/skills/clawhub/install")
async def install_from_clawhub(req: Request):
    body = await req.json()
    sn = body.get("skill_name", "")
    if not sn:
        return {"success": False, "error": "skill_name required"}
    import subprocess as _sp
    safe = sn.replace("/","_").replace(" ","_")
    try:
        r = _sp.run(["npx","clawhub","install",sn], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return {"success": False, "error": r.stderr[:500]}
        bp = SKILLS_DIR / ("clawhub_" + safe + ".py")
        cn = "".join(x.capitalize() for x in safe.split("_"))
        bc = '"""ClawHub: ' + sn + '"""\n'
        bc += 'import subprocess as _sp\n'
        bc += 'from modules._base.enterprise_module import EnterpriseModule\n'
        bc += 'class ' + cn + '(EnterpriseModule):\n'
        bc += '    async def execute(self,action="run",params=None):\n'
        bc += '        try:\n'
        bc += '            r = _sp.run(["npx","clawhub","run","' + sn + '"], capture_output=True, text=True, timeout=30)\n'
        bc += '            return {"success": r.returncode == 0, "output": r.stdout[:2000]}\n'
        bc += '        except Exception as e:\n'
        bc += '            return {"success": False, "error": str(e)}\n'
        bc += 'module_class = ' + cn
        bp.write_text(bc, encoding="utf-8")
        return {"success": True, "result": "ClawHub " + sn + " bridged", "module": "clawhub_" + safe}
    except FileNotFoundError:
        return {"success": False, "error": "npx not found"}
    except _sp.TimeoutExpired:
        return {"success": False, "error": "timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}
def register_routes(app):
    app.include_router(router)

setup_skills_market_routes = register_routes
