from __future__ import annotations
#!/usr/bin/env python3
"""开源中心 — 多平台项目发现引擎"""
import json, time, hashlib, httpx, asyncio
from typing import Optional
from core.logging_config import get_logger

logger = get_logger("evo.hub.discover")

# ── 缓存 ──
_cache: dict = {}
_CACHE_TTL = 3600

def _cached(key: str, data=None):
    if data is not None:
        _cache[key] = {"data": data, "ts": time.time()}
        return data
    if key in _cache and time.time() - _cache[key]["ts"] < _CACHE_TTL:
        return _cache[key]["data"]
    return None

# ── 分类 ──
_CATS = {
    "ai": ["llm","agent","rag","chatbot","nlp","transformer","diffusion","gpt"],
    "web": ["vue","react","nextjs","fastapi","django","frontend","backend","cms"],
    "devtools": ["cli","ide","cicd","testing","monitoring","logging","git"],
    "data": ["database","analytics","etl","visualization","bi","sql"],
    "security": ["security","encryption","auth","vpn","firewall","sso"],
    "media": ["image","video","audio","3d","design","svg"],
    "infra": ["docker","kubernetes","devops","cloud","terraform","nginx"],
    "mobile": ["android","ios","flutter","react-native","swift"],
}

def _classify(desc: str, topics: list = None) -> str:
    text = (desc + " " + " ".join(topics or [])).lower()
    scores = {cat: sum(1 for kw in kwds if kw in text) for cat, kwds in _CATS.items()}
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "other"

def _mkid(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

def _format(project: dict) -> dict:
    """统一格式化"""
    return {
        "id": project["id"], "name": project["name"],
        "full_name": project.get("full_name", project["name"]),
        "source": project.get("source", "github"),
        "repo_url": project.get("repo_url", ""),
        "description": (project.get("description") or "")[:300],
        "category": project.get("category", "other"),
        "tags": project.get("tags", [])[:8],
        "tech_stack": project.get("tech_stack", []),
        "stars": project.get("stars", 0),
        "license": project.get("license", ""),
        "icon_url": project.get("icon_url", ""),
        "homepage": project.get("homepage", ""),
        "status": "discovered",
        "integrated": False,
    }

# ═══════════════════════════════════════════════════════
# GitHub 发现
# ═══════════════════════════════════════════════════════

GITHUB_API = "https://api.github.com"

async def fetch_github(since="daily", language="") -> list:
    key = f"github_{since}_{language}"
    cached = _cached(key)
    if cached: return cached

    query = f"created:>{_d(since)}"
    if language: query += f"+language:{language}"

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{GITHUB_API}/search/repositories", params={
                "q": query, "sort": "stars", "order": "desc", "per_page": 30
            }, headers={"Accept": "application/vnd.github.v3+json"})
            if r.status_code != 200:
                logger.warning(f"GitHub {r.status_code}")
                return _fallback("github")
            items = r.json().get("items", [])
    except Exception as e:
        logger.warning(f"GitHub err: {e}")
        return _fallback("github")

    projects = []
    for item in items[:30]:
        topics = item.get("topics", []) or []
        projects.append(_format({
            "id": _mkid(item["full_name"]),
            "name": item["name"], "full_name": item["full_name"],
            "source": "github", "repo_url": item["html_url"],
            "description": item.get("description",""),
            "category": _classify(item.get("description",""), topics),
            "tags": topics[:8],
            "tech_stack": [item.get("language","")] if item.get("language") else [],
            "stars": item.get("stargazers_count", 0),
            "license": item.get("license",{}).get("spdx_id","") if item.get("license") else "",
            "icon_url": item.get("owner",{}).get("avatar_url","") if item.get("owner") else "",
            "homepage": item.get("homepage","") or "",
        }))
    _cached(key, projects)
    return projects

async def search_github(query: str, page=1) -> list:
    key = f"github_search_{query}_{page}"
    cached = _cached(key)
    if cached: return cached
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{GITHUB_API}/search/repositories", params={
                "q": query, "sort": "stars", "order": "desc", "per_page": 20, "page": page
            }, headers={"Accept": "application/vnd.github.v3+json"})
            if r.status_code != 200: return _fallback("github")
            items = r.json().get("items", [])
    except: return _fallback("github")
    projects = []
    for item in items[:20]:
        topics = item.get("topics", []) or []
        projects.append(_format({
            "id": _mkid(item["full_name"]),
            "name": item["name"], "full_name": item["full_name"],
            "source": "github", "repo_url": item["html_url"],
            "description": item.get("description",""),
            "category": _classify(item.get("description",""), topics),
            "tags": topics[:8],
            "tech_stack": [item.get("language","")] if item.get("language") else [],
            "stars": item.get("stargazers_count", 0),
            "license": item.get("license",{}).get("spdx_id","") if item.get("license") else "",
            "icon_url": item.get("owner",{}).get("avatar_url","") if item.get("owner") else "",
            "homepage": item.get("homepage","") or "",
        }))
    _cached(key, projects)
    return projects

# ═══════════════════════════════════════════════════════
# HuggingFace 发现
# ═══════════════════════════════════════════════════════

HF_API = "https://huggingface.co/api"

async def fetch_huggingface() -> list:
    key = "huggingface"
    cached = _cached(key)
    if cached: return cached
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{HF_API}/models", params={"sort": "downloads", "direction": "-1", "limit": 30})
            if r.status_code != 200: return _fallback("huggingface")
            items = r.json()
    except: return _fallback("huggingface")
    projects = []
    for item in items[:30]:
        pid = item.get("modelId","") or item.get("id","")
        projects.append(_format({
            "id": _mkid(pid),
            "name": pid.split("/")[-1] if "/" in pid else pid,
            "full_name": pid, "source": "huggingface",
            "repo_url": f"https://huggingface.co/{pid}",
            "description": item.get("description","") or item.get("cardData",{}).get("tags",[]),
            "category": "ai",
            "tags": item.get("cardData",{}).get("tags",[])[:8] if item.get("cardData") else [],
            "tech_stack": ["Python"],
            "stars": item.get("likes",0),
            "icon_url": "https://huggingface.co/front/assets/huggingface_logo.svg",
        }))
    _cached(key, projects)
    return projects

# ═══════════════════════════════════════════════════════
# Gitee 发现
# ═══════════════════════════════════════════════════════

GITEE_API = "https://gitee.com/api/v5"

async def fetch_gitee() -> list:
    key = "gitee"
    cached = _cached(key)
    if cached: return cached
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{GITEE_API}/repos/organizations/opensource/repos",
                            params={"type": "public", "sort": "stargazers_count", "page": 1, "per_page": 30})
            if r.status_code != 200: return _fallback("gitee")
            items = r.json()
    except: return _fallback("gitee")
    projects = []
    for item in items[:30]:
        owner = item.get("owner",{}) or {}
        projects.append(_format({
            "id": _mkid(item.get("full_name","")),
            "name": item.get("name",""), "full_name": item.get("full_name",""),
            "source": "gitee", "repo_url": item.get("html_url",""),
            "description": item.get("description",""),
            "category": _classify(item.get("description",""), item.get("language","")),
            "tags": [item.get("language","")] if item.get("language") else [],
            "tech_stack": [item.get("language","")] if item.get("language") else [],
            "stars": item.get("stargazers_count",0),
            "icon_url": owner.get("avatar_url","") if owner else "",
        }))
    _cached(key, projects)
    return projects

# ═══════════════════════════════════════════════════════
# 统一入口
# ═══════════════════════════════════════════════════════

async def discover_all(sources: list = None) -> list:
    if sources is None: sources = ["github", "huggingface", "gitee"]
    tasks = []
    if "github" in sources: tasks.append(fetch_github())
    if "huggingface" in sources: tasks.append(fetch_huggingface())
    if "gitee" in sources: tasks.append(fetch_gitee())
    if not tasks: tasks = [fetch_github()]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_projects = []
    for r in results:
        if isinstance(r, list): all_projects.extend(r)
    # 按stars排序去重
    seen = set()
    unique = []
    for p in sorted(all_projects, key=lambda x: -x["stars"]):
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)
    return unique

async def search_all(query: str, sources: list = None) -> list:
    if sources is None: sources = ["github", "huggingface"]
    tasks = []
    if "github" in sources: tasks.append(search_github(query))
    if "huggingface" in sources: tasks.append(fetch_huggingface())  # HF搜索有限，取热门
    if not tasks: tasks = [search_github(query)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_projects = []
    for r in results:
        if isinstance(r, list): all_projects.extend(r)
    ql = query.lower()
    filtered = [p for p in all_projects if ql in p["name"].lower() or ql in p.get("description","").lower()]
    seen = set()
    unique = []
    for p in sorted(filtered, key=lambda x: -x["stars"]):
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)
    return unique

# ═══════════════════════════════════════════════════════
# 回退数据
# ═══════════════════════════════════════════════════════

def _d(since: str) -> str:
    import datetime
    days = {"daily": 1, "weekly": 7, "monthly": 30}
    return (datetime.date.today() - __import__('datetime').timedelta(days=days.get(since, 7))).isoformat()

_KNOWN = [
    ("ollama/ollama","Ollama","ai","本地LLM运行框架",128000,"Go"),
    ("open-webui/open-webui","Open WebUI","ai","LLM聊天界面",52000,"Svelte"),
    ("AUTOMATIC1111/stable-diffusion-webui","SD WebUI","media","AI绘图",148000,"Python"),
    ("langchain-ai/langchain","LangChain","ai","LLM应用框架",98000,"Python"),
    ("n8n-io/n8n","n8n","devtools","工作流自动化",53000,"TypeScript"),
    ("langgenius/dify","Dify","ai","LLM应用平台",58000,"Python"),
    ("nocodb/nocodb","NocoDB","data","开源Airtable",53000,"Vue"),
    ("appsmithorg/appsmith","Appsmith","web","低代码平台",36000,"React"),
    ("apache/superset","Superset","data","BI数据分析",64000,"Python"),
    ("calcom/cal.com","Cal.com","web","日程调度",35000,"React"),
    ("portainer/portainer","Portainer","infra","Docker管理",32000,"Go"),
    ("go-gitea/gitea","Gitea","devtools","Git服务",47000,"Go"),
    ("home-assistant/core","Home Assistant","infra","智能家居",75000,"Python"),
    ("twentyhq/twenty","Twenty CRM","web","客户管理",24000,"React"),
    ("makeplane/plane","Plane","devtools","项目管理",33000,"TypeScript"),
    ("autohome/AutoHome","AutoHome","web","智能家居",12000,"Python"),
]

def _fallback(source: str) -> list:
    projects = []
    for full, name, cat, desc, stars, lang in _KNOWN:
        projects.append(_format({
            "id": _mkid(full), "name": name, "full_name": full,
            "source": source, "repo_url": f"https://{source}.com/{full}" if source != "gitee" else f"https://gitee.com/{full}",
            "description": desc, "category": cat,
            "tags": [cat, lang.lower()], "tech_stack": [lang],
            "stars": stars, "license": "",
            "icon_url": f"https://github.com/{full.split('/')[0]}.png" if source == "github" else "",
        }))
    return projects
