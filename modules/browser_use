"""
AUTO-EVO-AI V0.1 — 浏览器操作：curl抓取+截图
"""
VERSION = "V0.1"
__module_meta__ = {"id": "browser-use", "name": "BrowserUse", "version": VERSION, "group": "tools"}

import json, subprocess, time, tempfile, os
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

class BrowserUse(EnterpriseModule):
    MODULE_ID = "browser-use"; MODULE_NAME = "BrowserUse"
    
    def __init__(self, config=None): EnterpriseModule.__init__(self, config or {})
    
    def get_status(self): return {"ready": True}
    
    def execute(self, action, **kwargs):
        if action == "fetch_page":
            url = kwargs.get("url", "")
            if not url: return {"error": "url required"}
            try:
                r = subprocess.run(["curl", "-skL", "--max-time", "15", url], capture_output=True, text=True, timeout=20)
                return {"status": r.returncode, "content": r.stdout[:5000], "stderr": r.stderr[:200]}
            except Exception as e: return {"error": str(e)}
        if action == "screenshot":
            return {"error": "screenshot requires headless browser, not available"}
        if action == "status": return {"curl_available": True}
        return {"error": "unknown: " + str(action)}
