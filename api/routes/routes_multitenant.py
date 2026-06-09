"""多租户隔离 — API Key 隔离数据 + 独立项目配置"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import os, json, time, hashlib, secrets, sqlite3
from pathlib import Path

logger = get_logger("evo.api.tenant")
router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_TENANT_DB = BASE_DIR / "core" / "adaptive_engine.db"

def _init_tenant():
    conn = sqlite3.connect(str(_TENANT_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS tenant_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, api_key TEXT UNIQUE, plan TEXT DEFAULT 'free', config TEXT, created_at REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS tenant_data (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, data_type TEXT, data_key TEXT, data_value TEXT, created_at REAL)")
    conn.commit(); conn.close()
_init_tenant()

class ProjectReq(BaseModel):
    name: str; plan: str = "free"; config: dict = {}

@router.post("/api/v1/tenant/projects")
async def create_project(req: ProjectReq):
    api_key = f"evo_proj_{secrets.token_hex(16)}"
    config_json = json.dumps(req.config, ensure_ascii=False)
    conn = sqlite3.connect(str(_TENANT_DB))
    try:
        cur = conn.execute("INSERT INTO tenant_projects (name, api_key, plan, config, created_at) VALUES (?,?,?,?,?)",
                          (req.name, api_key, req.plan, config_json, time.time()))
        conn.commit()
        return {"success": True, "project_id": cur.lastrowid, "api_key": api_key}
    except Exception as e:
        return {"success": False, "detail": str(e)}
    finally: conn.close()

@router.get("/api/v1/tenant/projects")
async def list_projects():
    conn = sqlite3.connect(str(_TENANT_DB))
    rows = conn.execute("SELECT id, name, api_key, plan, config, created_at FROM tenant_projects ORDER BY id DESC").fetchall()
    conn.close()
    projects = [{"id":r[0],"name":r[1],"api_key":r[2],"plan":r[3],"config":json.loads(r[4]) if r[4] else {},"created_at":r[5]} for r in rows]
    return {"success": True, "projects": projects, "total": len(projects)}

@router.get("/api/v1/tenant/verify")
async def verify_key(api_key: str = ""):
    conn = sqlite3.connect(str(_TENANT_DB))
    row = conn.execute("SELECT id, name, plan FROM tenant_projects WHERE api_key=?", (api_key,)).fetchone()
    conn.close()
    if row: return {"success": True, "project_id": row[0], "name": row[1], "plan": row[2]}
    return {"success": False, "detail": "无效的 API Key"}

@router.post("/api/v1/tenant/data/{project_id}")
async def set_tenant_data(project_id: int, data_type: str = "", data_key: str = "", data_value: str = ""):
    conn = sqlite3.connect(str(_TENANT_DB))
    conn.execute("INSERT OR REPLACE INTO tenant_data (project_id, data_type, data_key, data_value, created_at) VALUES (?,?,?,?,?)",
                 (project_id, data_type, data_key, data_value, time.time()))
    conn.commit(); conn.close()
    return {"success": True}

@router.get("/api/v1/tenant/data/{project_id}")
async def get_tenant_data(project_id: int, data_type: str = ""):
    conn = sqlite3.connect(str(_TENANT_DB))
    if data_type:
        rows = conn.execute("SELECT data_key, data_value FROM tenant_data WHERE project_id=? AND data_type=?", (project_id, data_type)).fetchall()
    else:
        rows = conn.execute("SELECT data_key, data_value FROM tenant_data WHERE project_id=?", (project_id,)).fetchall()
    conn.close()
    return {"success": True, "data": {r[0]: r[1] for r in rows}}
