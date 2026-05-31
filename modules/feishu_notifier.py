"""
AUTO-EVO-AI V0.1 — 飞书通知模块 (Lark Notification)
上市公司生产级: 飞书自定义机器人 Webhook 推送
"""
import time, hmac, hashlib, base64, json
from typing import Dict, List, Optional, Any
from datetime import datetime

__module_meta__ = {
    "id": "feishu_notifier",
    "name": "飞书通知",
    "version": "V0.1",
    "group": "notification",
    "tags": ["notification", "feishu", "lark", "enterprise"],
}

CONFIG = {
    "webhooks": {},
    "default_channel": "",
    "retry_count": 3,
    "retry_delay": 1.0,
}

_stats = {"sent": 0, "failed": 0, "history": []}

def health_check() -> dict:
    return {"module": "feishu_notifier", "status": "healthy", "channels": len(CONFIG["webhooks"]), "uptime": time.time()}

def _sign(secret: str, timestamp: int) -> str:
    s = f"{timestamp}\n{secret}"
    return base64.b64encode(hmac.new(s.encode(), digestmod=hashlib.sha256).digest()).decode()

def _send_webhook(name: str, payload: dict, secret: str = "") -> dict:
    import urllib.request, urllib.error
    url = CONFIG["webhooks"].get(name, name)
    if secret:
        ts = int(time.time())
        url = url + f"×tamp={ts}&sign={_sign(secret, ts)}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    for attempt in range(CONFIG["retry_count"]):
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            body = resp.read().decode()
            result = json.loads(body)
            if result.get("StatusCode") == 0 or result.get("code") == 0:
                _stats["sent"] += 1
                _stats["history"].append({"channel": name, "status": "ok", "ts": datetime.now().isoformat()})
                return {"success": True, "channel": name}
            return {"success": False, "error": result}
        except Exception as e:
            if attempt < CONFIG["retry_count"] - 1:
                time.sleep(CONFIG["retry_delay"])
    _stats["failed"] += 1
    _stats["history"].append({"channel": name, "status": "fail", "ts": datetime.now().isoformat()})
    return {"success": False, "error": str(e)}

def execute(action: str = "send", params: dict = None) -> dict:
    p = params or {}
    if action == "health":
        return health_check()
    elif action == "config":
        if "webhooks" in p: CONFIG["webhooks"].update(p["webhooks"])
        if "default_channel" in p: CONFIG["default_channel"] = p["default_channel"]
        return {"success": True, "config": {k: ("***" if k == "webhooks" else v) for k, v in CONFIG.items()}}
    elif action == "test":
        channel = p.get("channel", CONFIG["default_channel"])
        return _send_webhook(channel, {"msg_type": "text", "content": {"text": f"[TEST] 飞书通知测试 {datetime.now().isoformat()}"}}, p.get("secret", ""))
    elif action == "stats":
        return {"success": True, **_stats}
    elif action == "send":
        channel = p.get("channel", CONFIG["default_channel"])
        msg_type = p.get("msg_type", "text")
        content = p.get("content", "")
        title = p.get("title", "")
        secret = p.get("secret", "")
        if msg_type == "text":
            payload = {"msg_type": "text", "content": {"text": content}}
        elif msg_type == "markdown":
            payload = {"msg_type": "interactive", "card": {"header": {"title": {"tag": "plain_text", "content": title}, "template": p.get("template", "blue")}, "elements": [{"tag": "markdown", "content": content}]}}
        elif msg_type == "link":
            payload = {"msg_type": "interactive", "card": {"header": {"title": {"tag": "plain_text", "content": title}}, "elements": [{"tag": "markdown", "content": f"[{content}]({p.get('url','')})"}]}}
        else:
            payload = {"msg_type": "text", "content": {"text": content}}
        return _send_webhook(channel, payload, secret)
    return {"success": False, "error": f"unknown action: {action}"}
