"""AUTO-EVO-AI V0.1 — 模型路由"""
VERSION="V0.1"
__module_meta__={"id":"model-router","name":"ModelRouter","version":VERSION,"group":"ai"}
import json,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
class ModelRouter(EnterpriseModule):
    MODULE_ID="model-router";MODULE_NAME="ModelRouter"
    def __init__(self,c=None):
        super().__init__(c);self._routes={};self._url=self.config.get("llm_url","http://127.0.0.1:8765/api/llm/chat")
    def initialize(self):self.status=ModuleStatus.INITIALIZING
    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    def _call(self,model,msg):
        d=json.dumps({"model":model,"messages":[{"role":"user","content":msg}],"max_tokens":1024}).encode()
        try:return json.loads(ur.urlopen(ur.Request(self._url,data=d,headers={"Content-Type":"application/json"},method="POST"),timeout=300).read()).get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception as e:return f"<error: {e}>"
    async def execute(self,a=None,p=None):
        p=p or{}
        if a=="route":
            task=p.get("task","");models=p.get("models",["zhipu:glm-4-flash","zhipu:glm-4-plus"])
            results={}
            for m in models[:3]:
                results[m]=self._call(m,task)
            return {"success":True,"results":results}
        if a=="register":
            self._routes[p["name"]]=p.get("model","zhipu:glm-4-flash")
            return {"success":True,"routes":list(self._routes.keys())}
        return {"success":False,"error":f"unknown: {a}"}
    async def shutdown(self):self._routes.clear();self.status=ModuleStatus.STOPPED
module_class=ModelRouter
