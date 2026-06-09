"""工具批量健康检查 — 返回所有已知工具的注册信息（不做实时网络探测，避免超时）"""
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
    """返回所有已知工具的注册信息（不做实时网络探测）"""
    return {"success": True, "total": len(KNOWN_PORTS), "tools": {n: {"port": p, "alive": False, "status": "unknown"} for n, p in KNOWN_PORTS.items()}}
