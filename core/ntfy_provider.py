"""
Ntfy 推送通知提供者 — 30k⭐
与系统通知通道集成，支持手机/桌面推送
"""

import json, urllib.request, os
from core.logging_config import get_logger

logger = get_logger("evo.ntfy_provider")

NTFY_BASE = os.environ.get("NTFY_BASE", "http://localhost:8086")
NTFY_DEFAULT_TOPIC = os.environ.get("NTFY_TOPIC", "evo-alerts")


class NtfyProvider:
    """Ntfy 推送通知封装"""

    def __init__(self, base_url: str = NTFY_BASE, topic: str = NTFY_DEFAULT_TOPIC):
        self.base_url = base_url.rstrip("/")
        self.topic = topic

    def send(self, message: str, title: str = "EVO System",
             priority: int = 3, tags: list[str] | None = None) -> dict:
        """发送推送通知"""
        body = {
            "topic": self.topic,
            "message": message,
            "title": title,
            "priority": priority,
        }
        if tags:
            body["tags"] = tags
        try:
            data = json.dumps(body).encode()
            req = urllib.request.Request(
                f"{self.base_url}/{self.topic}",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                success = r.status == 200
                if success:
                    logger.info(f"[Ntfy] 推送成功: {title}")
                return {"success": success, "topic": self.topic}
        except Exception as e:
            logger.warning(f"[Ntfy] 推送失败: {e}")
            return {"success": False, "error": str(e)}

    def health(self) -> bool:
        """检查 Ntfy 服务状态"""
        try:
            r = urllib.request.urlopen(f"{self.base_url}/v1/health", timeout=2)
            return r.status == 200
        except Exception:
            return False


# 全局实例
ntfy = NtfyProvider()
