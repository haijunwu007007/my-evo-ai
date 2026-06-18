"""自修复引擎 — 部署失败自动回滚 + 重试"""
from fastapi import APIRouter
from datetime import datetime, timedelta
import os, json, subprocess, time

router = APIRouter(tags=["selfheal"])

_DEPLOY_HISTORY: list[dict] = []
_MAX_HISTORY = 100

@router.post("/api/v1/selfheal/record")
async def record_deployment(name: str, success: bool, error: str = ""):
    """记录部署历史"""
    _DEPLOY_HISTORY.append({
        "name": name, "success": success, "error": error,
        "timestamp": datetime.now().isoformat()
    })
    if len(_DEPLOY_HISTORY) > _MAX_HISTORY:
        _DEPLOY_HISTORY.pop(0)
    return {"success": True}

@router.post("/api/v1/selfheal/rollback/{name}")
async def rollback_deploy(name: str):
    """回滚部署"""
    # 停止并删除当前容器
    subprocess.run(["docker", "stop", name], capture_output=True, timeout=30)
    subprocess.run(["docker", "rm", name], capture_output=True, timeout=30)
    # 尝试回退到上一个版本
    old_tag = f"evo/{name}:prev"
    r = subprocess.run(["docker", "run", "-d", "--name", f"{name}-rollback", old_tag],
                       capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        return {"success": True, "message": f"{name} 已回滚到上一版本", "container": r.stdout.strip()}
    return {"success": False, "error": "无上一版本可回滚"}

@router.get("/api/v1/selfheal/history")
async def get_history():
    """获取部署历史"""
    return {"success": True, "history": _DEPLOY_HISTORY[-20:]}

@router.post("/api/v1/selfheal/retry/{name}")
async def retry_deploy(name: str):
    """重试失败的部署"""
    # 从history找到失败记录
    failed = [h for h in _DEPLOY_HISTORY if h["name"] == name and not h["success"]]
    if not failed:
        return {"success": False, "error": "无失败记录可重试"}
    # 尝试重新部署
    tag = f"evo/{name}:latest"
    r = subprocess.run(["docker", "run", "-d", "--name", name, "--restart", "unless-stopped", tag],
                       capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        return {"success": True, "message": f"{name} 重试成功", "container": r.stdout.strip()}
    return {"success": False, "error": f"重试失败: {r.stderr[:200]}"}
