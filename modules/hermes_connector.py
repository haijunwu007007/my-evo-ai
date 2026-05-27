"""AUTO-EVO-AI V0.1 — Hermes消息连接器"""
VERSION="V0.1"
__module_meta__={"id":"hermes-connector","name":"HermesConnector","version":VERSION,"group":"ai"}
import json,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
class HermesConnector(EnterpriseModule):
    MODULE_ID="hermes-connector";MODULE_NAME="HermesConnector"
    def __init__(self,c=None):
        super().__init__(c);self._connections={}
        self._url=self.config.get("llm_url","http://127.0.0.1:8765/api/llm/chat")
    def initialize(self):self.status=ModuleStatus.INITIALIZING
    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    def _call(self,msg):
        d=json.dumps({"model":"zhipu:glm-4-flash","messages":[{"role":"user","content":msg}],"max_tokens":1024}).encode()
        try:return json.loads(ur.urlopen(ur.Request(self._url,data=d,headers={"Content-Type":"application/json"},method="POST"),timeout=30).read()).get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception as e:return f"<error: {e}>"
    async def execute(self,a=None,p=None):
        p=p or{}
        if a=="connect":
            name=p.get("name","");self._connections[name]={"status":"connected","url":p.get("url","")}
            return {"success":True,"connections":list(self._connections.keys())}
        if a=="process":
            msg=p.get("message","")
            return {"success":True,"result":self._call(f"处理消息: {msg}")[:300]}
        return {"success":False,"error":f"unknown: {a}"}
    async def shutdown(self):self._connections.clear();self.status=ModuleStatus.STOPPED
module_class=HermesConnector
