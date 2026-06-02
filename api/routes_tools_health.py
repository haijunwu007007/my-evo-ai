"""工具批量健康检查 — 一键检测所有已启动的 Docker 工具"""
import httpx, asyncio
from fastapi import APIRouter

router = APIRouter(tags=["工具健康"])

# 已知已启动的容器端口（docker-compose.tools.yml 中配置的）
KNOWN_PORTS = {
    "Gitea": 3000, "Nextcloud": 8090, "Metabase": 3030,
    "Vaultwarden": 8180, "Home Assistant": 8123,
    "Dify": 8002, "Flowise": 8001, "One-API": 8003,
    "Meilisearch": 7700, "MinIO": 9000, "NocoDB": 8080,
    "IT-Tools": 3170, "Excalidraw": 3080, "Miniflux": 3060,
    "Immich": 2283, "Jellyfin": 3130, "Calibre-Web": 3140,
    "Twenty CRM": 3100, "Invoice Ninja": 3110,
    "Chatwoot": 3120, "osTicket": 3180,
    "Mattermost": 3150, "Focalboard": 3160,
    "Documenso": 3090, "Docmost": 3085,
    "Hoarder": 3070, "Paperless": 3190, "Snipe-IT": 3200,
}

@router.get("/api/v1/tools/health")
async def batch_health():
    """一键检测所有工具（超时 3s）"""
    results = {}
    async def check(name: str, port: int):
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"http://127.0.0.1:{port}")
                results[name] = {"port": port, "alive": True, "status": "running"}
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError):
            results[name] = {"port": port, "alive": False, "status": "stopped"}
    tasks = [check(n, p) for n, p in KNOWN_PORTS.items()]
    await asyncio.gather(*tasks)
    return {"success": True, "total": len(results), "alive": sum(1 for v in results.values() if v["alive"]), "tools": results}
