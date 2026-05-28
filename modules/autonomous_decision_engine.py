"""AUTO-EVO-AI V0.1 — 自主决策引擎"""
VERSION = "V0.1"
__module_meta__ = {"id": "auto-decision", "name": "DecisionEngine", "version": VERSION, "group": "ai"}
import json, uuid, urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin

class DecisionEngine(EnterpriseModule, CircuitBreakerMixin):
    MODULE_ID = "auto-decision"; MODULE_NAME = "DecisionEngine"
    def __init__(self, c=None):
        super().__init__(c); self._decisions = {}
        self._llm_url = self.config.get("llm_url", "http://127.0.0.1:8765/api/llm/chat")
    def initialize(self): self.status = ModuleStatus.INITIALIZING
    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value, healthy=True, module_id=self.MODULE_ID)
    def _call_llm(self, prompt):
        d = json.dumps({"model":"zhipu:glm-4-flash","messages":[{"role":"user","content":prompt}],"max_tokens":1024}).encode()
        try:
            return json.loads(ur.urlopen(ur.Request(self._llm_url,data=d,headers={"Content-Type":"application/json"},method="POST"),timeout=30).read()).get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception as e: return f"<error: {e}>"
    async def execute(self, action=None, params=None):
        p = params or {}
        if action == "decide":
            ctx = p.get("context",""); opts = p.get("options",["yes","no"])
            prompt = f"上下文: {ctx}\n选项: {', '.join(opts)}\n请选择一个最佳选项并解释原因。"
            result = self._call_llm(prompt)
            aid = uuid.uuid4().hex[:8]
            self._decisions[aid] = {"context":ctx,"options":opts,"result":result}
            return {"success":True,"decision_id":aid,"result":result[:200]}
        elif action == "history":
            return {"success":True,"decisions":[{k:{"result":v["result"][:100],"options":v["options"]} for k,v in self._decisions.items()}]}
        return {"success":False,"error":f"unknown: {action}"}
    async def shutdown(self): self._decisions.clear(); self.status = ModuleStatus.STOPPED
module_class = DecisionEngine
