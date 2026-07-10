from __future__ import annotations
"""开源中心 — API 路由"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any
import json, time, hashlib
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.api.hub")
router = APIRouter(prefix="/api/v1/hub")

from api.hub.models import (
    add_project, get_project, list_projects, update_project, delete_project,
    add_connection, list_connections,
    add_compose, list_composes, _get_conn,
    add_fork, list_forks,
    add_template, list_templates,
)
from api.hub.integrate import deploy_project, stop_project, get_deploy_status
from api.hub.compose_deploy import deploy_compose

# ─── 发现 ───

@router.get("/discover")
async def hub_discover(source: str = "gitee", page: int = 1):
    """发现多平台开源项目"""
    from api.hub.discover_cn import discover_all
    projects = await discover_all(source)
    integrated_ids = {p.get("id","") for p in list_projects().get("projects", [])}
    for p in projects: p["integrated"] = p.get("id","") in integrated_ids
    return {"success": True, "projects": projects, "total": len(projects)}

# ─── 项目CRUD ───

@router.post("/projects")
async def hub_add_project(data: dict):
    pid = data.get("id") or hashlib.md5((data.get("name","")+str(time.time())).encode()).hexdigest()[:12]
    data["id"] = pid
    data["status"] = "ready"
    add_project(data)
    return {"success": True, "id": pid, "status": "ready", "message": f'{data.get("name","")} 已加入工作区'}

@router.get("/projects")
async def hub_list_projects(status: str = "", page: int = 1, limit: int = 50):
    return list_projects(status=status, page=page, limit=limit)

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
async def hub_update_project(pid: str, data: dict):
    updates = {}
    for k in ("name","config","port","auto_start","canvas_x","canvas_y","status"):
        if k in data: updates[k] = json.dumps(data[k]) if k == "config" and isinstance(data[k], dict) else data[k]
    if updates: update_project(pid, updates)
    return {"success": True}

# ─── 组合 ───

@router.post("/composes")
async def hub_create_compose(data: dict):
    cid = hashlib.md5((data.get("name","")+str(time.time())).encode()).hexdigest()[:12]
    data["id"] = cid
    add_compose(data)
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

@router.post("/composes/deploy")
async def hub_compose_deploy(data: dict):
    try:
        nodes = data.get("nodes", [])
        name = data.get("name", "compose")
        result = deploy_compose(name, nodes)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"compose deploy: {e}")
        return {"success": False, "error": str(e)}

# ─── 模板 ───

@router.post("/templates")
async def hub_create_template(data: dict):
    tid = hashlib.md5((data.get("name","")+str(time.time())).encode()).hexdigest()[:12]
    data["id"] = tid
    add_template(data)
    return {"success": True, "id": tid}

@router.get("/templates")
async def hub_list_templates(category: str = ""):
    return {"success": True, "templates": list_templates(category)}

# ─── 监控 ───

@router.get("/monitor")
async def hub_monitor():
    import subprocess
    try:
        r = subprocess.run(["docker","ps","--format","{{.Names}}\t{{.Status}}"], capture_output=True, text=True, timeout=10)
        containers = [{"name": l.split("\t")[0], "status": l.split("\t")[1]} for l in r.stdout.strip().split("\n") if l.strip()]
        return {"success": True, "projects": containers}
    except Exception as e:
        return {"success": True, "projects": [], "note": str(e)}
