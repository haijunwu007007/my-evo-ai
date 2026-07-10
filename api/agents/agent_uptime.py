"""Uptime Kuma - AUTO-EVO-AI集成 (localhost:3001)"""
import json, httpx, os

KUMA_URL = os.environ.get("KUMA_URL", "")

def uptime_kuma(**kwargs):
    """Uptime Kuma站点监控"""
    try:
        action = kwargs.get("action", "status")
        url = f"{KUMA_URL}/api/{action}" if action != "status" else f"{KUMA_URL}"

        # Kuma不需要认证头（首次需Web UI设置用户）
        resp = httpx.get(url, timeout=10)
        return {"ok": resp.status_code < 500, "data": {"status_code": resp.status_code, "action": action}, "message": f"HTTP {resp.status_code}"}
    except httpx.ConnectError:
        return {"ok": False, "data": None, "message": "无法连接Uptime Kuma (localhost:3001)，请确认Docker容器已启动"}
    except Exception as e:
        return {"ok": False, "data": None, "message": f"Uptime Kuma失败: {e}"}
