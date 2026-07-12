"""
AUTO-EVO-AI V0.1 — 模型路由：LLM路由+故障转移
"""
VERSION = "V0.1"
__module_meta__ = {"id": "model-router", "name": "ModelRouter", "version": VERSION, "group": "ai"}

import json, time, urllib.request
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._persist import PersistMixin

class ModelRouter(PersistMixin, EnterpriseModule):
    MODULE_ID = "model-router"; MODULE_NAME = "ModelRouter"
    
    def __init__(self, config=None):
        EnterpriseModule.__init__(self, config or {})
        PersistMixin.__init__(self, "model_router")
        self._models = [
            {"name": "GLM-4-Flash", "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "weight": 3},
            {"name": "deepseek-chat", "url": "https://api.deepseek.com/v1/chat/completions", "weight": 2},
        ]
        self._failures = {}
    
    def get_status(self): return {"models": len(self._models), "failures": self._failures}
    
    def execute(self, action, **kwargs):
        if action == "route":
            prompt = kwargs.get("prompt", "")
            for m in sorted(self._models, key=lambda x: -x["weight"]):
                if m["name"] in self._failures and self._failures[m["name"]] > time.time() - 60: continue
                try:
                    payload = json.dumps({"model": m["name"], "messages": [{"role":"user","content":prompt}], "max_tokens": 1024}).encode()
                    r = urllib.request.urlopen(urllib.request.Request(m["url"], data=payload, headers={"Authorization":f"Bearer {os.environ.get('ZHIPU_API_KEY','')}","Content-Type":"application/json"}), timeout=15)
                    data = json.loads(r.read())
                    content = data.get("choices",[{}])[0].get("message",{}).get("content","")
                    self.persist(f"route:{time.time()}", json.dumps({"model":m["name"],"prompt":prompt[:50]}))
                    return {"model": m["name"], "response": content}
                except Exception as e:
                    self._failures[m["name"]] = time.time()
            return {"error": "all models failed"}
        if action == "add_model":
            self._models.append({"name": kwargs.get("name",""), "url": kwargs.get("url",""), "weight": kwargs.get("weight",1)})
            self.persist("models", json.dumps(self._models))
            return {"added": kwargs.get("name","")}
        if action == "list_models": return self._models
        return {"error": "unknown: " + str(action)}
