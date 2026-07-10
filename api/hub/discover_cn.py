from __future__ import annotations
"""开源中心 — 国内平台项目发现（Gitee/GitCode/HF镜像）"""
import json, time, hashlib, httpx, asyncio
from typing import Optional
from core.logging_config import get_logger
from api.hub.discover import _classify, _cache_get, _cache_set

logger = get_logger("evo.hub.discover_cn")

# ── Gitee 热门项目 ──
GITEE_SEARCH = "https://gitee.com/api/v5/search/repositories"
GITEE_TRENDING = "https://gitee.com/api/v5/orgs/{org}/repos"

async def discover_gitee(limit: int = 20) -> list[dict]:
    """发现Gitee热门项目"""
    cache_key = "gitee_discover"
    cached = _cache_get(cache_key)
    if cached: return cached
    
    projects = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # 搜索热门项目
            r = await client.get(GITEE_SEARCH, params={
                "q": "stars:>100", "sort": "stars", "order": "desc", "page": 1, "per_page": limit
            })
            if r.status_code == 200:
                data = r.json()
                for item in data.get("hits", data.get("data", data.get("results", data)))[:limit]:
                    if isinstance(item, dict) and item.get("full_name"):
                        full_name = item.get("full_name","")
                        projects.append({
                            "id": hashlib.md5(full_name.encode()).hexdigest()[:12],
                            "name": item.get("name",""),
                            "full_name": full_name,
                            "source": "gitee",
                            "repo_url": item.get("html_url",f"https://gitee.com/{full_name}"),
                            "description": (item.get("description","") or "")[:300],
                            "category": _classify(item.get("language",""), item.get("description","")),
                            "tags": [t for t in [item.get("language","")] if t][:8],
                            "tech_stack": [item.get("language","")] if item.get("language") else [],
                            "stars": item.get("stargazers_count",0),
                            "license": item.get("license",""),
                            "icon_url": item.get("owner",{}).get("avatar_url","") if item.get("owner") else "",
                            "homepage": item.get("homepage","") or "",
                            "status": "discovered",
                            "integrated": False,
                        })
    except Exception as e:
        logger.warning(f"Gitee API 异常: {e}")
    
    if not projects:
        projects = _fallback_gitee()
    
    _cache_set(cache_key, projects)
    return projects

def _fallback_gitee() -> list[dict]:
    """Gitee备用热门列表"""
    return [
        {"id":"gitee_1","name":"RuoYi-Vue","full_name":"y_project/RuoYi-Vue","source":"gitee","repo_url":"https://gitee.com/y_project/RuoYi-Vue","description":"基于SpringBoot+Vue的快速开发平台","category":"web","tags":["spring","vue","java"],"tech_stack":["Java","Vue"],"stars":38000,"status":"discovered","integrated":False},
        {"id":"gitee_2","name":"MyBatis-Plus","full_name":"baomidou/mybatis-plus","source":"gitee","repo_url":"https://gitee.com/baomidou/mybatis-plus","description":"MyBatis增强工具包","category":"devtools","tags":["mybatis","java","database"],"tech_stack":["Java"],"stars":16000,"status":"discovered","integrated":False},
        {"id":"gitee_3","name":"Ant Design Pro","full_name":"ant-design/ant-design-pro","source":"gitee","repo_url":"https://gitee.com/ant-design/ant-design-pro","description":"开箱即用的中台前端/设计解决方案","category":"web","tags":["react","antd","admin"],"tech_stack":["TypeScript","React"],"stars":36000,"status":"discovered","integrated":False},
    ]

# ── GitCode 搜索 ──
async def discover_gitcode(limit: int = 20) -> list[dict]:
    """发现GitCode热门项目（GitCode无公开API，用搜索模拟）"""
    cache_key = "gitcode_discover"
    cached = _cache_get(cache_key)
    if cached: return cached
    
    projects = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://api.gitcode.com/api/v1/repos/search", params={
                "q": "", "sort": "stars", "page": 1, "size": limit
            })
            if r.status_code == 200:
                data = r.json()
                for item in (data if isinstance(data, list) else data.get("data", data.get("results", [])))[:limit]:
                    full = item.get("full_name","") or item.get("path_with_namespace","")
                    projects.append({
                        "id": hashlib.md5(full.encode()).hexdigest()[:12] if full else f"gc_{int(time.time())}",
                        "name": item.get("name",""), "full_name": full, "source": "gitcode",
                        "repo_url": item.get("web_url","") or item.get("url",""),
                        "description": (item.get("description","") or "")[:300],
                        "category": _classify([], item.get("description","")),
                        "tags": [], "tech_stack": [item.get("language","")] if item.get("language") else [],
                        "stars": item.get("stars_count",0) or item.get("star_count",0),
                        "license": "", "status": "discovered", "integrated": False,
                    })
    except Exception as e:
        logger.warning(f"GitCode API 异常: {e}")
    
    if not projects:
        projects = _fallback_gitcode()
    _cache_set(cache_key, projects)
    return projects

def _fallback_gitcode() -> list[dict]:
    return [{"id":"gc_opencv","name":"OpenCV","full_name":"opencv/opencv","source":"gitcode","repo_url":"https://gitcode.com/opencv/opencv","description":"Open Source Computer Vision Library","category":"ai","tags":["computer-vision","ai"],"tech_stack":["C++"],"stars":26000,"status":"discovered","integrated":False}]

# ── HuggingFace 国内镜像 ──
async def discover_hf_mirror(limit: int = 20) -> list[dict]:
    """通过国内镜像发现HF热门模型"""
    cache_key = "hf_mirror"
    cached = _cache_get(cache_key)
    if cached: return cached
    projects = []
    for name, base in [("hf-mirror","https://hf-mirror.com"), ("hf-cn","https://hf-cn.com")]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{base}/api/models", params={"sort":"downloads","direction":-1,"limit":limit})
                if r.status_code == 200:
                    for item in r.json()[:limit]:
                        pid = item.get("id","")
                        projects.append({
                            "id": hashlib.md5((f"hf_{pid}").encode()).hexdigest()[:12],
                            "name": pid.split("/")[-1] if "/" in pid else pid,
                            "full_name": pid, "source": "huggingface",
                            "repo_url": f"{base}/{pid}",
                            "description": (item.get("description","") or item.get("cardData",{}).get("model_description","") or "")[:300],
                            "category": "ai",
                            "tags": item.get("tags",["model"])[:8],
                            "tech_stack": [item.get("library_name","")] if item.get("library_name") else [],
                            "stars": 0, "license": item.get("cardData",{}).get("license",""),
                            "status": "discovered", "integrated": False,
                        })
                    break
        except Exception as e:
            logger.warning(f"{base} 异常: {e}")
    if not projects:
        return _fallback_hf()
    _cache_set(cache_key, projects)
    return projects

def _fallback_hf() -> list[dict]:
    return [
        {"id":"hf_qwen","name":"Qwen3.6","full_name":"Qwen/Qwen3.6-35B","source":"huggingface","repo_url":"https://hf-mirror.com/Qwen/Qwen3.6-35B","description":"Qwen3.6-35B 阿里开源大模型","category":"ai","tags":["llm","qwen"],"tech_stack":["Python"],"status":"discovered","integrated":False},
        {"id":"hf_llama","name":"Llama 4","full_name":"meta-llama/Llama-4","source":"huggingface","repo_url":"https://hf-mirror.com/meta-llama/Llama-4","description":"Meta Llama 4 开源大模型","category":"ai","tags":["llm","meta"],"tech_stack":["Python"],"status":"discovered","integrated":False},
    ]

# ── 统一发现 + 搜索 ──

async def discover_all(sources: list[str] = None) -> list[dict]:
    """所有来源统一发现"""
    if sources is None: sources = ["github","huggingface","gitee","gitcode"]
    tasks = []
    for s in sources:
        if s == "github": tasks.append(discover_github())
        elif s == "huggingface": tasks.append(discover_hf_mirror(10))
        elif s == "gitee": tasks.append(discover_gitee(10))
        elif s == "gitcode": tasks.append(discover_gitcode(10))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    projects = []
    for r in results:
        if isinstance(r, list): projects.extend(r)
    projects.sort(key=lambda x: x.get("stars",0), reverse=True)
    return projects

async def search_all(query: str, sources: list[str] = None) -> list[dict]:
    """多平台统一搜索"""
    if sources is None: sources = ["github","huggingface","gitee"]
    tasks = []
    for s in sources:
        if s == "github": tasks.append(search_github(query))
        elif s == "huggingface": tasks.append(search_hf(query))
        elif s == "gitee": tasks.append(search_gitee(query))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    projects = []
    for r in results:
        if isinstance(r, list): projects.extend(r)
    projects.sort(key=lambda x: x.get("stars",0), reverse=True)
    return projects

async def discover_github(limit: int = 15) -> list[dict]:
    from api.hub.discover import fetch_github_trending
    try: return await fetch_github_trending()
    except: return []

async def search_github(query: str) -> list[dict]:
    from api.hub.discover import search_github
    try: return await search_github(query)
    except: return []

async def search_hf(query: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://hf-mirror.com/api/models", params={"search":query,"limit":10})
            projects = []
            if r.status_code == 200:
                for item in r.json()[:10]:
                    pid = item.get("id","")
                    projects.append({
                        "id": hashlib.md5(f"hf_{pid}".encode()).hexdigest()[:12],
                        "name": pid, "source": "huggingface",
                        "repo_url": f"https://hf-mirror.com/{pid}",
                        "description": (item.get("description","") or "")[:300],
                        "category": "ai", "tags": item.get("tags",[])[:5],
                        "tech_stack": [item.get("library_name","")] if item.get("library_name") else [],
                        "stars": 0, "status": "discovered", "integrated": False,
                    })
            return projects
    except: return []

async def search_gitee(query: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(GITEE_SEARCH, params={"q":query,"page":1,"per_page":10})
            projects = []
            if r.status_code == 200:
                for item in r.json().get("hits", r.json().get("data", r.json()))[:10]:
                    if isinstance(item, dict):
                        full = item.get("full_name","")
                        projects.append({
                            "id": hashlib.md5(full.encode()).hexdigest()[:12],
                            "name": item.get("name",""), "source": "gitee",
                            "repo_url": f"https://gitee.com/{full}",
                            "description": (item.get("description","") or "")[:300],
                            "category": _classify(item.get("language",""),item.get("description","")),
                            "tags": [t for t in [item.get("language","")] if t][:5],
                            "tech_stack": [item.get("language","")] if item.get("language") else [],
                            "stars": item.get("stargazers_count",0),
                            "status": "discovered", "integrated": False,
                        })
            return projects
    except: return []
