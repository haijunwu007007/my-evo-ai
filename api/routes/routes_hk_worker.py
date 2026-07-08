# -*- coding: utf-8 -*-
"""
🌉 香港 Worker 桥接 — 把 GitHub 克隆/Docker 构建/CLI 工具转发到香港服务器
"""
import httpx, asyncio, json
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/hk", tags=["hk-worker"])
HK_URL = os.environ.get("HK_WORKER_URL", "http://43.129.75.222:8766")

@router.get("/health")
async def hk_health():
    """检查香港 Worker 状态"""
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            r = await cli.get("http://localhost:18766/health")
            return {"success": True, "hk": r.json()}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}

@router.post("/exec")
async def hk_exec(data: dict):
    """在港服执行命令 (Git 克隆/Docker 构建等)"""
    try:
        async with httpx.AsyncClient(timeout=180) as cli:
            r = await cli.post(f"{HK_URL}/exec", json={"cmd": data.get("cmd",""), "timeout": data.get("timeout",120)})
            return {"success": r.status_code == 200, "result": r.json()}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}

@router.post("/clone")
async def hk_clone(data: dict):
    """在港服克隆 GitHub 仓库"""
    try:
        async with httpx.AsyncClient(timeout=200) as cli:
            r = await cli.post(f"{HK_URL}/clone", json={"url": data.get("url","")})
            return {"success": r.status_code == 200, "result": r.json()}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}

@router.post("/deploy")
async def hk_deploy_redirect(data: dict):
    """香港直连部署：克隆→Docker构建→运行"""
    url = data.get("url","")
    if not url:
        return {"success": False, "error": "需要 url"}
    try:
        async with httpx.AsyncClient(timeout=300) as cli:
            r = await cli.post(f"{HK_URL}/exec", json={"cmd": f"git clone --depth 1 {url} /tmp/deploy", "timeout": 180})
            return {"success": r.status_code == 200, "hk_result": r.json(), "note": "克隆完成，Docker构建由港服处理"}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}
