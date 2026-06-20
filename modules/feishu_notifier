"""
AUTO-EVO-AI V0.1 — 飞书通知：Webhook推送
"""
VERSION = "V0.1"
__module_meta__ = {"id": "feishu", "name": "FeishuNotifier", "version": VERSION, "group": "notify"}

import json, urllib.request, time
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

class FeishuNotifier(EnterpriseModule):
    MODULE_ID = "feishu"; MODULE_NAME = "FeishuNotifier"
    
    def __init__(self, config=None): EnterpriseModule.__init__(self, config or {})
    
    def get_status(self): return {"ready": True}
    
    def execute(self, action, **kwargs):
        if action == "send":
            webhook = kwargs.get("webhook", "")
            msg = kwargs.get("message", "Hello")
            title = kwargs.get("title", "通知")
            if not webhook: return {"error": "webhook required"}
            try:
                payload = json.dumps({"msg_type": "interactive", "card": {"header": {"title": {"tag": "plain_text", "content": title}}, "elements": [{"tag": "markdown", "content": msg}]}}).encode()
                r = urllib.request.urlopen(urllib.request.Request(webhook, data=payload, headers={"Content-Type":"application/json"}), timeout=10)
                return {"status": r.status}
            except Exception as e: return {"error": str(e)}
        if action == "send_text":
            webhook = kwargs.get("webhook", "")
            msg = kwargs.get("message", "")
            if not webhook: return {"error": "webhook required"}
            try:
                payload = json.dumps({"msg_type": "text", "content": {"text": msg}}).encode()
                r = urllib.request.urlopen(urllib.request.Request(webhook, data=payload, headers={"Content-Type":"application/json"}), timeout=10)
                return {"status": r.status}
            except Exception as e: return {"error": str(e)}
        return {"error": "unknown: " + str(action)}
