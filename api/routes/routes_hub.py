"""开源中心 — 核心API路由"""
from __future__ import annotations
from fastapi import APIRouter
import json, time, hashlib
from core.logging_config import get_logger

logger = get_logger("evo.api.hub")
router = APIRouter(prefix="/api/v1/hub")

from api.hub.models import add_project, get_project, list_projects, update_project, delete_project, add_compose, list_composes, add_template, list_templates, _get_conn
from api.hub.discover import discover_all, search_all
from api.hub.integrate import deploy_project, get_deploy_status, stop_project

# ─── 发现 ───

@router.get("/discover")
async def hub_discover(source: str = "all", category: str = "", page: int = 1, limit: int = 30):
    src_map = {"all":["github","huggingface","gitee"],"github":["github"],"huggingface":["huggingface"],"gitee":["gitee"]}
    srcs = src_map.get(source, ["github","huggingface","gitee"])
    projects = await discover_all(srcs)
    if category: projects = [p for p in projects if p.get("category")==category]
    integrated_ids = {p["id"] for p in list_projects().get("projects",[])}
    for p in projects: p["integrated"] = p["id"] in integrated_ids
    total = len(projects)
    paged = projects[(page-1)*limit:page*limit]
    return {"success": True, "projects": paged, "total": total, "page": page, "limit": limit}

@router.get("/search")
async def hub_search(q: str = "", source: str = "all"):
    src_map = {"all":["github","huggingface","gitee"],"github":["github"],"huggingface":["huggingface"],"gitee":["gitee"]}
    srcs = src_map.get(source, ["github","huggingface","gitee"])
    if q.strip():
        projects = await search_all(q, srcs)
    else:
        projects = await discover_all(srcs)
    integrated_ids = {p["id"] for p in list_projects().get("projects",[])}
    for p in projects: p["integrated"] = p["id"] in integrated_ids
    return {"success": True, "projects": projects}

# ─── 项目管理 ───

@router.get("/projects")
async def hub_list_projects(status: str = "", category: str = "", page: int = 1, limit: int = 50):
    return list_projects(status=status, category=category, page=page, limit=limit)

@router.post("/projects")
async def hub_add_project(data: dict):
    pid = data.get("id") or hashlib.md5((data.get("name","")+str(time.time())).encode()).hexdigest()[:12]
    data["id"] = pid
    data["status"] = "ready"
    add_project(data)
    return {"success": True, "id": pid, "status": "ready", "message": f"{data.get('name','')} 已加入工作区"}

@router.get("/projects/{pid}")
async def hub_get_project(pid: str):
    proj = get_project(pid)
    if not proj: return {"success": False, "error": "项目不存在"}
    return {"success": True, "project": proj}

@router.get("/projects/{pid}/status")
async def hub_project_status(pid: str):
    return await get_deploy_status(pid)

@router.post("/projects/{pid}/integrate")
async def hub_integrate(pid: str, config: dict = {}):
    return await deploy_project(pid, config)

@router.post("/projects/{pid}/start")
async def hub_start(pid: str):
    return await deploy_project(pid)

@router.post("/projects/{pid}/stop")
async def hub_stop(pid: str):
    return await stop_project(pid)

@router.post("/projects/{pid}/restart")
async def hub_restart(pid: str):
    await stop_project(pid)
    return await deploy_project(pid)

@router.delete("/projects/{pid}")
async def hub_delete(pid: str):
    await stop_project(pid)
    delete_project(pid)
    return {"success": True}

@router.patch("/projects/{pid}")
async def hub_update(pid: str, data: dict):
    updates = {}
    for k in ("name","config","port","auto_start","status"):
        if k in data: updates[k] = json.dumps(data[k]) if isinstance(data.get(k), dict) else data[k]
    if updates: update_project(pid, updates)
    return {"success": True}

# ─── 组合 ───

@router.post("/composes")
async def hub_create_compose(data: dict):
    cid = hashlib.md5((data.get("name","")+str(time.time())).encode()).hexdigest()[:12]
    data["id"] = cid; add_compose(data)
    return {"success": True, "id": cid}

@router.get("/composes")
async def hub_list_composes():
    return {"success": True, "composes": list_composes()}

@router.get("/composes/{compose_id}")
async def hub_get_compose(compose_id: str):
    conn = _get_conn()
    r = conn.execute("SELECT * FROM composes WHERE id=?", (compose_id,)).fetchone()
    conn.close()
    if not r: return {"success": False, "error": "组合不存在"}
    return {"success": True, "compose": dict(r)}

@router.delete("/composes/{compose_id}")
async def hub_delete_compose(compose_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM composes WHERE id=?", (compose_id,))
    conn.commit(); conn.close()
    return {"success": True}

# ─── 模板 ───

@router.post("/templates")
async def hub_create_template(data: dict):
    tid = hashlib.md5((data.get("name","")+str(time.time())).encode()).hexdigest()[:12]
    data["id"] = tid; add_template(data)
    return {"success": True, "id": tid}

@router.get("/templates")
async def hub_list_templates(category: str = ""):
    return {"success": True, "templates": list_templates(category)}
