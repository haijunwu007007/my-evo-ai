"""万能部署API路由 — 一键部署任意GitHub项目"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.infra import BASE_DIR

router = APIRouter(tags=["deploy"])

class DeployRequest(BaseModel):
    url: str
    name: str = ""

@router.post("/api/v1/deploy/universal")
async def api_universal_deploy(req: DeployRequest):
    """一键部署任意GitHub开源项目"""
    from api.hub.universal_deploy import universal_deploy
    result = universal_deploy(req.url)
    return {"success": result.get("success", False), "data": result}

@router.get("/api/v1/deploy/status")
async def deploy_status():
    """查看已部署项目列表"""
    import subprocess
    r = subprocess.run(["docker", "ps", "--format", '{{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'],
                       capture_output=True, text=True, timeout=10)
    containers = []
    for line in r.stdout.strip().split("\n"):
        if not line.strip(): continue
        parts = line.split("\t")
        if len(parts) >= 3 and parts[1].startswith("evo/"):
            containers.append({"name": parts[0], "image": parts[1], "ports": parts[2], "status": parts[3] if len(parts) > 3 else ""})
    return {"success": True, "containers": containers}

@router.post("/api/v1/deploy/stop/{name}")
async def stop_deploy(name: str):
    """停止并删除部署"""
    import subprocess
    subprocess.run(["docker", "stop", name], capture_output=True, timeout=30)
    subprocess.run(["docker", "rm", name], capture_output=True, timeout=30)
    return {"success": True, "message": f"{name} 已停止"}
