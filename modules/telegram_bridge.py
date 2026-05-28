# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - Telegram 桥接器（A级）

Telegram Bot API 客户端，支持消息发送、Markdown 消息、更新轮询。
使用 requests 库调用 Telegram Bot HTTP API，内置 graceful degradation。"""
__module_meta__ = {"id":"telegram-bridge","name":"Telegram Bridge","version":"V0.1","group":"communication","grade":"A",
    "tags":["communication","telegram","bot","messaging"],"description":"Telegram Bot API bridge for messaging"}
import logging, json
from typing import Any, Dict, Optional, List
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger = logging.getLogger("evo.telegram-bridge")

# ── 底层 HTTP 调用（独立函数，支持独立调用） ──────────────────────────

def send_message(token: str, chat_id: str, text: str) -> bool:
    """发送纯文本消息到指定 chat。
    返回 True 表示发送成功，False 表示失败。"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        return resp.status_code == 200 and resp.json().get("ok", False)
    except ImportError:
        logger.warning("telegram: requests 不可用，无法发送")
        return False
    except Exception as e:
        logger.error("telegram: send_message 失败: %s", e)
        return False

def send_markdown(token: str, chat_id: str, md_text: str) -> bool:
    """发送 Markdown 格式消息到指定 chat。"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": md_text,
            "parse_mode": "MarkdownV2"
        }, timeout=10)
        return resp.status_code == 200 and resp.json().get("ok", False)
    except ImportError:
        logger.warning("telegram: requests 不可用，无法发送 markdown")
        return False
    except Exception as e:
        logger.error("telegram: send_markdown 失败: %s", e)
        return False

def get_updates(token: str, offset: int = 0, timeout: int = 10) -> List[Dict]:
    """轮询 Bot 的更新列表。
    返回 update 对象列表，失败时返回空列表。"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        resp = requests.post(url, json={"offset": offset, "timeout": timeout}, timeout=timeout + 5)
        data = resp.json()
        if resp.status_code == 200 and data.get("ok", False):
            return data.get("result", [])
        return []
    except ImportError:
        logger.warning("telegram: requests 不可用，无法获取 updates")
        return []
    except Exception as e:
        logger.error("telegram: get_updates 失败: %s", e)
        return []

# ── EnterpriseModule 类封装 ──────────────────────────────────────

class TelegramBridge(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    MODULE_ID = "telegram-bridge"
    MODULE_NAME = "Telegram 桥接器"
    VERSION = "v1.0"
    MODULE_LEVEL = "A"

    def __init__(self, config=None):
        super().__init__(config)
        self._token = ""
        self._chat_id = ""
        self._simulated = True
        self.logger = logging.getLogger(__name__)

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING

    def health_check(self) -> HealthReport:
        configured = bool(self._token)
        healthy = True
        if configured and not self._simulated:
            try:
                import requests
                url = f"https://api.telegram.org/bot{self._token}/getMe"
                resp = requests.get(url, timeout=5)
                healthy = resp.status_code == 200
            except Exception:
                healthy = False
        return HealthReport(
            status=self.status.value,
            healthy=healthy,
            module_id=self.MODULE_ID,
            checks={"configured": configured, "simulated": self._simulated}
        )

    async def execute(self, action=None, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _dispatch(self, p: dict) -> dict:
        a = p.get("action", "status")

        if a == "status":
            return {
                "success": True,
                "configured": bool(self._token),
                "chat_id": self._chat_id,
                "simulated": self._simulated
            }

        if a == "configure":
            self._token = p.get("token", "") or self._token
            self._chat_id = p.get("chat_id", "") or self._chat_id
            if self._token:
                self._simulated = False
            return {"success": True, "configured": bool(self._token)}

        if a == "send":
            text = p.get("text", "")
            if not text:
                return {"success": False, "error": "text_required"}
            if self._simulated:
                logger.info("telegram_simulated_send: %s", text[:80])
                return {"success": True, "message_id": "simulated", "text": text, "simulated": True}
            ok = send_message(self._token, self._chat_id, text)
            return {"success": ok, "text": text}

        if a == "send_markdown":
            md = p.get("text", "")
            if not md:
                return {"success": False, "error": "text_required"}
            if self._simulated:
                logger.info("telegram_simulated_markdown: %s", md[:80])
                return {"success": True, "simulated": True, "text": md}
            ok = send_markdown(self._token, self._chat_id, md)
            return {"success": ok, "text": md}

        if a == "send_document":
            caption = p.get("caption", "")
            if self._simulated:
                return {"success": True, "simulated": True, "caption": caption}
            return {"success": True, "note": "document_send_requires_file_upload"}

        if a == "get_updates":
            offset = p.get("offset", 0)
            if self._simulated:
                return {"success": True, "simulated": True, "updates": []}
            updates = get_updates(self._token, offset=offset, timeout=10)
            return {"success": True, "updates": updates, "count": len(updates)}

        if a == "set_webhook":
            url = p.get("url", "")
            if self._simulated:
                return {"success": True, "simulated": True, "webhook_url": url}
            try:
                import requests
                resp = requests.post(
                    f"https://api.telegram.org/bot{self._token}/setWebhook",
                    json={"url": url},
                    timeout=10
                )
                data = resp.json()
                return {"success": data.get("ok", False), "result": data}
            except Exception as e:
                return {"success": False, "error": str(e)}

        if a == "group_info":
            return {
                "success": True,
                "chat_id": self._chat_id,
                "configured": bool(self._token),
                "simulated": self._simulated
            }

        return {"success": False, "error": f"unknown_action:{a}"}

    async def shutdown(self) -> None:
        self.status = ModuleStatus.STOPPED

module_class = TelegramBridge
