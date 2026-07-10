from modules._base.enterprise_module import EnterpriseModule
#!/usr/bin/env python3
"""
AUTO-EVO-AI V0.1 — Enterprise Notifier (企业通知网关)
======================================================
生产级多通道通知模块：企业微信 / 钉钉

功能特性:
- 多通道统一接口: wecom | dingtalk
- 消息类型支持: text | markdown | link
- HMAC 签名验证 (钉钉安全)
- 发送历史追踪 / 统计
- 测试通道连通性

级别: A (生产级)
"""
from __future__ import annotations
import os, sys, json, time, hashlib, hmac, logging, asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from urllib.parse import urlencode
from base64 import b64encode, b64decode
import urllib.request, urllib.error, urllib.parse

# ── 模块元信息 ──
MODULE_ID = "enterprise_notifier"
MODULE_NAME = "Enterprise Notifier (企业通知)"
VERSION = "V0.1"
MODULE_LEVEL = "A"

logger = logging.getLogger(f"evo.{MODULE_ID}")

# ── 默认配置 ──
_CONFIG: dict[str, Any] = {
    "wecom_webhook_url": "",
    "dingtalk_webhook_url": "",
    "dingtalk_secret": "",
    "max_retries": 3,
    "timeout_sec": 10,
}

# ── 发送历史 ──
_history: list[dict] = []
_stats: dict[str, Any] = {"sent": 0, "failed": 0, "last_send": None}

# ═══════════════════════════════════════════════════════
# 核心函数
# ═══════════════════════════════════════════════════════

async def execute(action: str, **kwargs) -> dict:
    """模块执行入口"""
    if action == "send":
        return _send(
            channel=kwargs.get("channel", "wecom"),
            msg_type=kwargs.get("msg_type", "text"),
            title=kwargs.get("title", ""),
            content=kwargs.get("content", ""),
            url=kwargs.get("url", ""),
        )
    elif action == "status":
        return {"success": True, "channels": _active_channels(), "stats": dict(_stats)}
    elif action == "history":
        limit = kwargs.get("limit", 20)
        return {"success": True, "history": _history[-limit:]}
    elif action == "test":
        return _test_channel(kwargs.get("channel", "wecom"))
    else:
        return {"success": False, "error": f"Unknown action: {action}"}

def health_check() -> dict:
    return {"status": "healthy", "module": MODULE_ID, "version": VERSION,
            "channels": _active_channels(), "sent": _stats["sent"], "failed": _stats["failed"]}

# ═══════════════════════════════════════════════════════
# 发送逻辑
# ═══════════════════════════════════════════════════════

def _send(channel: str, msg_type: str = "text", title: str = "",
          content: str = "", url: str = "") -> dict:
    """统一发送"""
    t0 = time.time()
    senders = {"wecom": _send_wecom, "dingtalk": _send_dingtalk}
    sender = senders.get(channel)
    if not sender:
        return {"success": False, "error": f"Unsupported channel: {channel}"}

    result = sender(msg_type, content, title, url)
    elapsed = round((time.time() - t0) * 1000, 1)
    result["duration_ms"] = elapsed

    _history.append({"channel": channel, "msg_type": msg_type, "success": result["success"],
                     "time": datetime.now(timezone.utc).isoformat()})
    if result["success"]:
        _stats["sent"] += 1
        _stats["last_send"] = datetime.now(timezone.utc).isoformat()
    else:
        _stats["failed"] += 1
    return result

# ═══════════════════════════════════════════════════════
# 企业微信
# ═══════════════════════════════════════════════════════

def _send_wecom(msg_type: str, content: str, title: str = "", url: str = "") -> dict:
    webhook = _CONFIG.get("wecom_webhook_url", "")
    if not webhook:
        return {"success": False, "error": "未配置 wecom_webhook_url"}

    if msg_type == "markdown":
        payload = {"msgtype": "markdown", "markdown": {"content": content[:4096]}}
    elif msg_type == "link":
        payload = {"msgtype": "news", "news": {"articles": [{
            "title": title[:128], "description": content[:512], "url": url[:2048]
        }]}}
    else:
        payload = {"msgtype": "text", "text": {"content": content[:2048]}}
    return _http_post("wecom", webhook, payload)

# ═══════════════════════════════════════════════════════
# 钉钉
# ═══════════════════════════════════════════════════════

def _send_dingtalk(msg_type: str, content: str, title: str = "", url: str = "") -> dict:
    webhook = _CONFIG.get("dingtalk_webhook_url", "")
    if not webhook:
        return {"success": False, "error": "未配置 dingtalk_webhook_url"}

    # 签名 (安全方式)
    secret = _CONFIG.get("dingtalk_secret", "")
    if secret:
        ts = str(round(time.time() * 1000))
        sign_str = f"{ts}\n{secret}"
        sign = b64encode(hmac.new(secret.encode(), sign_str.encode(), hashlib.sha256).digest()).decode()
        webhook += f"?timestamp={ts}&sign={urllib.parse.quote(sign)}"

    if msg_type == "markdown":
        payload = {"msgtype": "markdown", "markdown": {"title": title[:64], "text": content[:5000]}}
    elif msg_type == "link":
        payload = {"msgtype": "link", "link": {
            "title": title[:128], "text": content[:512], "messageUrl": url[:2048]
        }}
    else:
        payload = {"msgtype": "text", "text": {"content": content[:2048]}}
    return _http_post("dingtalk", webhook, payload)

# ═══════════════════════════════════════════════════════
# HTTP 发送 (同步 + 重试)
# ═══════════════════════════════════════════════════════

def _http_post(channel: str, url: str, payload: dict) -> dict:
    """HTTP POST with retry"""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    max_retries = _CONFIG.get("max_retries", 3)
    last_err = ""

    for attempt in range(1 + max_retries):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=_CONFIG.get("timeout_sec", 10)) as resp:
                body = resp.read().decode("utf-8")
                r = json.loads(body)
                errcode = r.get("errcode", 0)
                if errcode == 0:
                    return {"success": True, "channel": channel, "message_id": r.get("msgid", r.get("processMsgKey", ""))}
                last_err = r.get("errmsg", body[:200])
        except Exception as e:
            last_err = str(e)[:200]

        if attempt < max_retries:
            delay = 1.0 * (2 ** attempt)
            logger.warning(f"[{channel}] retry {attempt+1}/{max_retries}: {last_err}")
            time.sleep(delay)

    return {"success": False, "channel": channel, "error": last_err}

# ═══════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════

def _active_channels() -> list[str]:
    return [k.replace("_webhook_url","") for k in ["wecom_webhook_url","dingtalk_webhook_url"] if _CONFIG.get(k)]

def _test_channel(channel: str) -> dict:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return _send(channel=channel, msg_type="text",
                 content=f"Enterprise Notifier 测试消息\n时间: {ts}\n状态: 通道正常")

def get_config() -> dict:
    safe = dict(_CONFIG)
    for k in ["dingtalk_secret"]:
        safe[k] = "***" if safe.get(k) else ""
    return {"success": True, "config": safe}

def update_config(**kwargs) -> dict:
    for k, v in kwargs.items():
        if k in _CONFIG:
            _CONFIG[k] = v if v != "***" else _CONFIG.get(k, "")
    logger.info(f"Config updated: {list(kwargs.keys())}")
    return {"success": True}

# ═══════════════════════════════════════════════════════
# 模块导出
# ═══════════════════════════════════════════════════════

module_class = type("EnterpriseNotifierModule", (), {
    "MODULE_ID": MODULE_ID,
    "MODULE_NAME": MODULE_NAME,
    "VERSION": VERSION,
    "MODULE_LEVEL": MODULE_LEVEL,
    "execute": execute,
    "health_check": health_check,
})

__all__ = ["execute", "health_check", "get_config", "update_config", "_send", "module_class"]

# ═══════════════════════════════════════════════════════
# 自带测试
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    async def test():
        r = await execute("status")
        logger.info("Status:", json.dumps(r, ensure_ascii=False, indent=2)))
        h = health_check()
        logger.info("Health:", json.dumps(h, ensure_ascii=False, indent=2)))
    asyncio.run(test())


class EnterpriseNotifier(EnterpriseModule):
    MODULE_ID = "enterprise_notifier"
    MODULE_NAME = "EnterpriseNotifier"

    async def initialize(self):
        self.info(f"EnterpriseNotifier initialized")

    async def execute(self, action, params=None):
        return await super().execute(action, params)

    def health_check(self):
        return super().health_check()

module_class = EnterpriseNotifier
