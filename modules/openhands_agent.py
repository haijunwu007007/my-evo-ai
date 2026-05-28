"""AUTO-EVO-AI V0.1 — OpenHands Agent集成"""
VERSION="V0.1"
__module_meta__={"id":"openhands-agent","name":"OpenHandsAgent","version":VERSION,"group":"ai"}
import json,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin
class OpenHandsAgent(EnterpriseModule, CircuitBreakerMixin):
    MODULE_ID="openhands-agent";MODULE_NAME="OpenHandsAgent"
    def __init__(self,c=None):
        super().__init__(c);self._sessions={}
        self._url=self.config.get("llm_url","http://127.0.0.1:8765/api/llm/chat")
    def initialize(self):self.status=ModuleStatus.INITIALIZING
    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    def _call(self,msg,sys_prompt=""):
        msgs=[]
        if sys_prompt:msgs.append({"role":"system","content":sys_prompt})
        msgs.append({"role":"user","content":msg})
        d=json.dumps({"model":"zhipu:glm-4-flash","messages":msgs,"max_tokens":4096}).encode()
        try:return json.loads(ur.urlopen(ur.Request(self._url,data=d,headers={"Content-Type":"application/json"},method="POST"),timeout=60).read()).get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception as e:return f"<error: {e}>"
    async def execute(self,a=None,p=None):
        p=p or{}
        if a=="chat":
            sid=p.get("session_id","default");msg=p.get("message","")
            prompt=p.get("prompt","你是一个AI助手。请回答用户的问题。")
            if sid not in self._sessions:self._sessions[sid]=[]
            self._sessions[sid].append({"role":"user","content":msg})
            reply=self._call(msg,prompt)
            self._sessions[sid].append({"role":"assistant","content":reply})
            return {"success":True,"session_id":sid,"reply":reply}
        if a=="history":
            sid=p.get("session_id","");h=self._sessions.get(sid,[])
            return {"success":True,"messages":h[-10:]}
        return {"success":False,"error":f"unknown: {a}"}
    async def shutdown(self):self._sessions.clear();self.status=ModuleStatus.STOPPED
module_class=OpenHandsAgent
