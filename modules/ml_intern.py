"""AUTO-EVO-AI V0.1 — ML Intern工具链"""
VERSION="V0.1"
__module_meta__={"id":"ml-intern","name":"MLIntern","version":VERSION,"group":"ai"}
import json,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
class MLIntern(EnterpriseModule):
    MODULE_ID="ml-intern";MODULE_NAME="MLIntern"
    def __init__(self,c=None):
        super().__init__(c);self._url=self.config.get("llm_url","http://127.0.0.1:8765/api/llm/chat")
    def initialize(self):self.status=ModuleStatus.INITIALIZING
    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    def _call(self,msg):
        d=json.dumps({"model":"zhipu:glm-4-flash","messages":[{"role":"user","content":msg}],"max_tokens":2048}).encode()
        try:return json.loads(ur.urlopen(ur.Request(self._url,data=d,headers={"Content-Type":"application/json"},method="POST"),timeout=30).read()).get("choices",[{}])[0].get("message",{}).get("content","")[:500]
        except Exception as e:return f"<error: {e}>"
    async def execute(self,a=None,p=None):
        p=p or{}
        if a=="analyze":
            return {"success":True,"analysis":self._call(f"分析数据:\n{p.get('data','')}")}
        if a=="report":
            return {"success":True,"report":self._call(f"生成报告:\n{p.get('topic','')}")}
        if a=="code":
            return {"success":True,"code":self._call(f"写代码:\n{p.get('task','')}")}
        return {"success":False,"error":f"unknown: {a}"}
    async def shutdown(self):self.status=ModuleStatus.STOPPED
module_class=MLIntern
