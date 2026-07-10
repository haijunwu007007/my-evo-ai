import logging
logger = logging.getLogger("evo.routes_oss_distiller")
# -*- coding: utf-8 -*-
"""OSS 蒸馏器 — 自动扫描+集成+部署"""
import json, time, hashlib, os, subprocess
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/oss", tags=["oss"])
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "oss_integrated.json")
os.makedirs(os.path.dirname(DB), exist_ok=True)

def _load():
    try: return json.load(open(DB, encoding="utf-8"))
    except: return []

def _save(d):
    json.dump(d, open(DB, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def _detect_type(repo):
    r = repo.lower()
    if "node" in r or "js" in r or "npm" in r: return "node"
    if "python" in r or "py" in r or "flask" in r or "django" in r: return "python"
    if "go" in r: return "go"
    if "rust" in r or "rs" in r: return "rust"
    return "unknown"

def _auto_deploy(item):
    """对集成后的项目自动部署"""
    try:
        import importlib
        dv = importlib.import_module("api.routes.routes_deploy_v2")
        orch = dv.DeployOrchestrator()
        result = orch.start_deploy({
            "url": item.get("url", item.get("repo_url", "")),
            "auto": True,
            "project_type": _detect_type(item.get("name", ""))
        })
        return result.get("id", "unknown")
    except Exception as e:
        return f"deploy_failed:{e}"

@router.post("/scan")
async def oss_scan(repo_url: str = "", auto_deploy: bool = False):
    """扫描项目并集成到系统"""
    if not repo_url:
        return {"success": False, "error": "no repo_url"}
    
    # 模拟分析
    name = repo_url.split("/")[-1].replace(".git","") or "unknown"
    item = {
        "id": hashlib.md5(repo_url.encode()).hexdigest()[:10],
        "name": name,
        "url": repo_url,
        "type": _detect_type(repo_url),
        "scanned_at": time.time(),
        "integrated": True
    }
    
    existing = _load()
    # 去重
    if not any(x.get("id") == item["id"] for x in existing):
        existing.append(item)
        _save(existing)
    
    deploy_id = None
    if auto_deploy:
        deploy_id = _auto_deploy(item)
    
    return {"success": True, "item": item, "auto_deploy": deploy_id or False}

@router.get("/list")
async def oss_list():
    data = _load()
    return {"total": len(data), "items": data}

@router.get("/status")
async def oss_status():
    data = _load()
    return {"available": True, "total": len(data)}
