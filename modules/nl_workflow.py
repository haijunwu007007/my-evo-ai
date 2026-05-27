"""AUTO-EVO-AI V0.1 — 自然语言工作流"""
VERSION="V0.1"
__module_meta__={"id":"nl-workflow","name":"NLWorkflow","version":VERSION,"group":"ai"}
import json,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
class NLWorkflow(EnterpriseModule):
    MODULE_ID="nl-workflow";MODULE_NAME="NLWorkflow"
    def __init__(self,c=None):
        super().__init__(c);self._workflows={}
        self._url=self.config.get("llm_url","http://127.0.0.1:8765/api/llm/chat")
    def initialize(self):self.status=ModuleStatus.INITIALIZING
    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    def _call(self,msg):
        d=json.dumps({"model":"zhipu:glm-4-flash","messages":[{"role":"user","content":msg}],"max_tokens":2048}).encode()
        try:return json.loads(ur.urlopen(ur.Request(self._url,data=d,headers={"Content-Type":"application/json"},method="POST"),timeout=30).read()).get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception as e:return f"<error: {e}>"
    async def execute(self,a=None,p=None):
        p=p or{}
        if a=="create":
            desc=p.get("description","")
            steps=self._call(f"将以下需求拆分为3-5个执行步骤:\n{desc}")
            wid=f"wf_{len(self._workflows)}";self._workflows[wid]={"desc":desc,"steps":steps}
            return {"success":True,"workflow_id":wid,"steps":steps}
        if a=="run":
            w=self._workflows.get(p.get("workflow_id",""))
            if not w:return {"success":False,"error":"not found"}
            results=[]
            for i,s in enumerate(w["steps"].split(chr(10))[:5]):
                if s.strip():results.append({"step":i+1,"result":self._call(f"执行: {s}")[:200]})
            return {"success":True,"results":results}
        if a=="list":
            return {"success":True,"workflows":{k:{"desc":v["desc"][:60]} for k,v in self._workflows.items()}}
        return {"success":False,"error":f"unknown: {a}"}
    async def shutdown(self):self._workflows.clear();self.status=ModuleStatus.STOPPED
module_class=NLWorkflow
