"""
万能Skill市场聚合 — 连接 Composio / skills-mcp / SkillSeekers
支持一键搜索、安装、执行外部Skill
"""
import os, json, logging, subprocess
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("skill_market")
router = APIRouter(prefix="/api/v1/skill-market", tags=["skill_market"])

class SkillSearch(BaseModel):
    q: str = ""
    platform: str = "all"
    limit: int = 20

class SkillInstall(BaseModel):
    name: str
    source: str = "github"
    repo: str = ""

_skill_cache = []

@router.get("/status")
def status():
    return {"success": True, "platforms": ["composio", "skills-mcp", "skillseekers", "workbuddy"], "cached": len(_skill_cache)}

@router.post("/search")
def search_skills(req: SkillSearch):
    results = []
    # 本地WorkBuddy skills
    import glob
    for sk in glob.glob(os.path.expanduser("~/.workbuddy/skills/*/SKILL.md")):
        name = os.path.basename(os.path.dirname(sk))
        if not req.q or req.q.lower() in name.lower():
            results.append({"name": name, "source": "workbuddy", "path": sk})
    # GitHub搜索
    if req.platform in ("all", "github"):
        try:
            import urllib.request
            r = urllib.request.urlopen(f"https://api.github.com/search/repositories?q={req.q}+skill+SKILL.md&sort=stars&per_page={req.limit}", timeout=10)
            data = json.loads(r.read())
            for repo in data.get("items", []):
                results.append({"name": repo["full_name"], "desc": repo["description"][:200], "stars": repo["stargazers_count"], "source": "github"})
        except: pass
    _skill_cache.extend(results)
    return {"success": True, "total": len(results), "results": results[:req.limit]}

@router.post("/install")
def install_skill(req: SkillInstall):
    if req.source == "github" and req.repo:
        target = os.path.expanduser(f"~/.workbuddy/skills/imported/{req.name}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            subprocess.run(["git", "clone", "--depth", "1", f"https://github.com/{req.repo}", target], capture_output=True, timeout=120)
            return {"success": True, "path": target}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}
    return {"success": False, "error": "需要提供GitHub仓库地址"}
