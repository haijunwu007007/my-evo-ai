#!/usr/bin/env python3
"""GitHub 一键自动部署引擎"""
import os, json, time, hashlib, re, httpx, asyncio, subprocess, shutil
from pathlib import Path
from typing import Optional
from core.logging_config import get_logger
from api.hub.models import add_project, get_project, update_project, _get_conn
from api.hub.integrate import deploy_project, stop_project

logger = get_logger("evo.hub.github_autodeploy")
BASE = Path(__file__).resolve().parent.parent.parent
HUBS_DIR = BASE / "hub_projects"
HUBS_DIR.mkdir(exist_ok=True)

_LLM_CACHE = {}

def _llm_quick(prompt: str) -> str:
    from api.agent_llm import call_llm
    cache_key = hashlib.md5(prompt.encode()).hexdigest()
    if cache_key in _LLM_CACHE:
        return _LLM_CACHE[cache_key]
    try:
        text, _ = call_llm([{"role":"user","content":prompt}])
        if text:
            _LLM_CACHE[cache_key] = text.strip()
            return text.strip()
    except Exception as e:
        logger.warning(f"LLM failed: {e}")
    return ""

def _classify_by_llm(name: str, desc: str, lang: str = "") -> str:
    cat = _llm_quick(
        f"将项目 '{name}' ({desc[:200]}) 归为以下类别之一（只输出类别名）："
        f"AI工具/DevOps/数据库/Web框架/编辑器/监控/安全/消息队列/存储/企业应用"
    )
    if cat in ("AI工具","DevOps","数据库","Web框架","编辑器","监控","安全","消息队列","存储","企业应用"):
        return cat
    return "AI工具"

async def search_github_async(query: str, limit: int = 15) -> list:
    try:
        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token: headers["Authorization"] = f"token {token}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": "stars", "order": "desc", "per_page": limit},
                headers=headers
            )
            if r.status_code == 200:
                data = r.json()
                results = []
                for item in data.get("items", [])[:limit]:
                    full_name = item.get("full_name", "")
                    results.append({
                        "id": hashlib.md5(full_name.encode()).hexdigest()[:12],
                        "name": item.get("name", ""),
                        "full_name": full_name,
                        "repo_url": item.get("html_url", f"https://github.com/{full_name}"),
                        "description": (item.get("description") or "")[:300],
                        "stars": item.get("stargazers_count", 0),
                        "forks": item.get("forks_count", 0),
                        "language": item.get("language") or "",
                        "license": item.get("license", {}).get("spdx_id", "") if item.get("license") else "",
                        "topics": item.get("topics", [])[:5],
                        "default_branch": item.get("default_branch", "main"),
                        "has_docker": None,  # 稍后检测
                        "source": "github",
                        "status": "discovered",
                    })
                return results
    except Exception as e:
        logger.warning(f"GitHub API error: {e}")
    return []

async def has_docker_compose(repo_url: str, branch: str = "main") -> dict:
    """检测项目是否有 Docker 配置（通过 GitHub API，绕过 raw 被墙问题）"""
    result = {"has_docker_config": False, "deploy_type": "", "files": []}
    m = re.search(r"github\.com/([^/]+/[^/]+?)(?:/|$|\.git)", repo_url)
    if not m:
        return result
    full_name = m.group(1)
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token: headers["Authorization"] = f"token {token}"
    check_files = ["docker-compose.yml", "docker-compose.yaml", "Dockerfile", "compose.yaml"]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"https://api.github.com/repos/{full_name}/contents/",
                params={"ref": branch}, headers=headers
            )
            if r.status_code == 200:
                items = r.json()
                for item in items:
                    fn = item.get("name", "")
                    if fn in check_files:
                        result["has_docker_config"] = True
                        result["files"].append(fn)
                        if "compose" in fn:
                            result["deploy_type"] = "compose"
                        elif "Dockerfile" == fn:
                            if result["deploy_type"] != "compose":
                                result["deploy_type"] = "dockerfile"
    except Exception as e:
        logger.warning(f"Docker check API error: {e}")
    # Fallback: search topics/description for docker keywords
    if not result["has_docker_config"]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r2 = await client.get(
                    f"https://api.github.com/repos/{full_name}",
                    headers=headers
                )
                if r2.status_code == 200:
                    repo = r2.json()
                    topics = repo.get("topics", [])
                    desc = (repo.get("description") or "").lower()
                    all_text = " ".join(topics).lower() + " " + desc
                    if any(kw in all_text for kw in ["docker", "compose", "container"]):
                        result["has_docker_config"] = True
                        result["deploy_type"] = "compose"
                        result["files"].append("docker-compose.yml (inferred)")
        except: pass
    return result

async def auto_deploy_github_async(repo_url: str, extra_config: dict = None) -> dict:
    try:
        cfg = extra_config or {}
        # extract owner/name
        m = re.search(r"github\.com/([^/]+/[^/]+?)(?:/|$|\.git)", repo_url)
        if not m: return {"success": False, "error": "无法解析仓库地址"}
        full_name = m.group(1).rstrip("/")
        api_url = f"https://api.github.com/repos/{full_name}"
        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token: headers["Authorization"] = f"token {token}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(api_url, headers=headers)
            if r.status_code != 200:
                return {"success": False, "error": f"GitHub API: {r.status_code}"}
            repo = r.json()
        name = repo.get("name", full_name.split("/")[-1])
        branch = repo.get("default_branch", "main")
        desc = (repo.get("description") or name)[:300]
        stars = repo.get("stargazers_count", 0)
        topics = repo.get("topics", [])[:5]
        docker_check = await has_docker_compose(repo_url, branch)
        deploy_type = docker_check.get("deploy_type", "manual")
        # 用 LLM 分类
        category = _classify_by_llm(name, desc, repo.get("language", ""))
        port = cfg.get("port", 0)
        if deploy_type == "compose":
            # 读取 compose 文件检测端口
            cf = "docker-compose.yml" if "docker-compose.yml" in docker_check["files"] else "compose.yaml"
            raw_url = f"https://raw.githubusercontent.com/{full_name}/{branch}/{cf}"
            try:
                async with httpx.AsyncClient(timeout=10) as c:
                    r2 = await c.get(raw_url)
                    if r2.status_code == 200:
                        for line in r2.text.split("\n"):
                            m2 = re.search(r'"(\d+):\d+', line)
                            if not m2: m2 = re.search(r'^\s*-\s*["\']?(\d+):\d+', line)
                            if m2:
                                port = int(m2.group(1))
                                break
            except: pass
        # 创建项目
        pid = hashlib.md5(full_name.encode()).hexdigest()[:12]
        proj = {
            "id": pid, "name": name, "full_name": full_name,
            "repo_url": repo_url, "description": desc,
            "category": category, "source": "github",
            "tags": json.dumps(topics),
            "tech_stack": json.dumps([repo.get("language","")] + topics[:3]),
            "stars": stars, "deploy_type": deploy_type,
            "port": port, "status": "ready",
            "icon_url": repo.get("owner",{}).get("avatar_url","") if repo.get("owner") else "",
            "homepage": repo.get("homepage","") or "",
        }
        add_project(proj)
        # 如果是compose，直接部署
        if deploy_type == "compose":
            asyncio.create_task(_do_compose_deploy(pid, full_name, branch, port))
            return {"success": True, "project_id": pid, "name": name,
                    "message": f"项目已添加并启动部署", "deploy_type": deploy_type, "port": port}
        elif deploy_type == "dockerfile":
            asyncio.create_task(_do_dockerfile_deploy(pid, full_name, branch, port))
            return {"success": True, "project_id": pid, "name": name,
                    "message": f"Dockerfile 部署已启动", "deploy_type": deploy_type, "port": port}
        # 源码自动构建（无 Docker 时）
        asyncio.create_task(_do_source_build(pid, full_name, branch))
        return {"success": True, "project_id": pid, "name": name,
                "message": f"项目已添加，正在源码自动构建", "deploy_type": "source_build"}
    except Exception as e:
        logger.error(f"auto_deploy_github: {e}")
        return {"success": False, "error": str(e)}

async def _do_compose_deploy(pid: str, full_name: str, branch: str, port: int):
    try:
        update_project(pid, {"status": "deploying"})
        repo_url = f"https://github.com/{full_name}.git"
        proj_dir = HUBS_DIR / full_name.replace("/", "_")
        if proj_dir.exists():
            shutil.rmtree(proj_dir)
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth=1", "-b", branch, repo_url, str(proj_dir),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.wait()
        if proc.returncode != 0:
            update_project(pid, {"status": "error"})
            return
        # 启动 compose
        proc2 = await asyncio.create_subprocess_exec(
            "docker-compose", "-f", str(proj_dir / "docker-compose.yml"), "up", "-d",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc2.wait()
        if proc2.returncode == 0:
            update_project(pid, {"status": "running", "port": port or 8080})
        else:
            update_project(pid, {"status": "error"})
    except Exception as e:
        logger.error(f"compose_deploy error: {e}")
        update_project(pid, {"status": "error"})

async def _do_source_build(pid: str, full_name: str, branch: str):
    """源码项目自动构建"""
    from api.hub.auto_build import auto_deploy_source
    proj_dir = HUBS_DIR / full_name.replace("/", "_")
    if proj_dir.exists():
        shutil.rmtree(proj_dir)
    repo_url = f"https://github.com/{full_name}.git"
    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth=1", "-b", branch, repo_url, str(proj_dir),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await proc.wait()
    if proc.returncode != 0:
        update_project(pid, {"status": "error"})
        return
    await auto_deploy_source(pid, full_name, branch)

async def _do_dockerfile_deploy(pid: str, full_name: str, branch: str, port: int):
    try:
        update_project(pid, {"status": "deploying"})
        proj_dir = HUBS_DIR / full_name.replace("/", "_")
        prj_name = full_name.split("/")[-1].lower()
        # docker build
        proc = await asyncio.create_subprocess_exec(
            "docker", "build", "-t", f"evo-{prj_name}", str(proj_dir),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.wait()
        if proc.returncode != 0:
            update_project(pid, {"status": "error"})
            return
        p = port or 8080
        proc2 = await asyncio.create_subprocess_exec(
            "docker", "run", "-d", "--name", f"evo-{prj_name}",
            *(["-p", f"{p}:{p}"] if p else []), f"evo-{prj_name}",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc2.wait()
        update_project(pid, {"status": "running" if proc2.returncode == 0 else "error", "port": p})
    except Exception as e:
        logger.error(f"dockerfile_deploy error: {e}")
        update_project(pid, {"status": "error"})
