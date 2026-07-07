"""Gitea — 自托管 Git 服务桥接 (50k⭐)"""
from fastapi import APIRouter, HTTPException
from api.infra import registry
router = APIRouter()

GITEA_URL = os.environ.get("GITEA_URL", "http://localhost:3000")

@router.get("/api/v1/tools/gitea")
async def gitea_status():
    return {
        "name": "Gitea",
        "version": "latest",
        "status": "configured",
        "url": GITEA_URL,
        "description": "轻量级自托管 Git 服务 — 代码托管、PR 审查、CI/CD",
    }

@router.get("/api/v1/tools/gitea/health")
async def gitea_health():
    import urllib.request, json
    try:
        r = urllib.request.urlopen(f"{GITEA_URL}/api/v1/version", timeout=5)
        d = json.loads(r.read())
        return {"healthy": True, "version": d.get("version", "unknown")}
    except Exception as e:
        return {"healthy": False, "error": str(e)}

async def _register():
    registry.modules["routes_gitea"] = __import__("api.routes_gitea", fromlist=["routes_gitea"])
