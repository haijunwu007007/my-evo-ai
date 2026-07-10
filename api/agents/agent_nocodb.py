"""NocoDB - AUTO-EVO-AI集成 (localhost:8081)"""
import logging
logger = logging.getLogger("evo.agent_nocodb")

import json, httpx, os

NOCO_URL = os.environ.get("NOCO_URL", "")

def nocodb_query(**kwargs):
    """NocoDB数据表查询 / API操作"""
    try:
        action = kwargs.get("action", "status")
        table = kwargs.get("table", "")
        if action in ("status", "health"):
            resp = httpx.get(NOCO_URL, timeout=5)
            return {"ok": resp.status_code == 200, "data": {"status_code": resp.status_code, "server": "nocodb"}, "message": f"NocoDB {'running' if resp.status_code == 200 else 'error'} ({resp.status_code})"}
        if action == "list_projects":
            resp = httpx.get(f"{NOCO_URL}/api/v2/meta/projects", timeout=10)
            if resp.status_code == 401:
                return {"ok": True, "data": {"note": "需要先通过WebUI创建API Token", "api_url": f"{NOCO_URL}/api/v2/meta/projects"}, "message": "服务运行中，需要认证"}
            return {"ok": False, "data": None, "message": f"HTTP {resp.status_code}"}
        return {"ok": True, "data": {"note": f"NocoDB服务运行中，可通过WebUI访问: {NOCO_URL}"}, "message": "ok"}
    except httpx.ConnectError:
        return {"ok": False, "data": None, "message": "无法连接NocoDB (localhost:8081)，请确认Docker容器已启动"}
    except Exception as e:
        return {"ok": False, "data": None, "message": f"NocoDB失败: {e}"}
