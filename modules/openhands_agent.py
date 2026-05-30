"""AUTO-EVO-AI V0.1 — OpenHands Agent集成"""
# Grade: B
VERSION="V0.1"
__module_meta__={"id":"openhands-agent","name":"OpenHandsAgent","version":VERSION,"group":"ai"}
import json,time,uuid,logging,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin

logger=logging.getLogger(__name__)

class OpenHandsAgent(EnterpriseModule, CircuitBreakerMixin):
    MODULE_ID="openhands-agent";MODULE_NAME="OpenHandsAgent"
    def __init__(self,c=None):
        super().__init__(c)
        self._thoughts=[]
        self._actions=[]
        self._sessions={}
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
        try:
            if a=="think":
                task=p.get("task","");context=p.get("context","")
                prompt=f"请针对以下任务进行深度思考分析:\n任务: {task}\n"
                if context:prompt+=f"上下文: {context}\n"
                prompt+="请输出: 1)问题分析 2)可能的解决方案 3)推荐方案及理由"
                thought=self._call(prompt,"你是一个深度思考型AI助手，擅长分析和推理。")
                thought_id=uuid.uuid4().hex[:8]
                self._thoughts.append({"id":thought_id,"task":task[:100],"thought":thought[:200],"timestamp":time.time()})
                return {"success":True,"thought_id":thought_id,"thought":thought}
            if a=="act":
                plan=p.get("plan","");task=p.get("task","")
                prompt=f"请根据以下计划执行具体行动:\n任务: {task}\n计划: {plan}\n请给出具体的执行步骤和操作结果。"
                result=self._call(prompt,"你是一个行动型AI助手，擅长执行计划和产生具体成果。")
                act_id=uuid.uuid4().hex[:8]
                self._actions.append({"id":act_id,"task":task[:100],"result":result[:200],"timestamp":time.time()})
                return {"success":True,"action_id":act_id,"result":result}
            if a=="chat":
                sid=p.get("session_id","default");msg=p.get("message","")
                sys_prompt=p.get("prompt","你是一个AI助手。请回答用户的问题。")
                if sid not in self._sessions:self._sessions[sid]=[]
                self._sessions[sid].append({"role":"user","content":msg})
                reply=self._call(msg,sys_prompt)
                self._sessions[sid].append({"role":"assistant","content":reply})
                return {"success":True,"session_id":sid,"reply":reply}
            if a=="status":
                return {"success":True,"thoughts_count":len(self._thoughts),"actions_count":len(self._actions),"sessions_count":len(self._sessions),"recent_thoughts":self._thoughts[-3:] if self._thoughts else [],"recent_actions":self._actions[-3:] if self._actions else []}
            return {"success":False,"error":f"unknown: {a}"}
        except Exception as e:
            logger.error("OpenHandsAgent.execute error: %s",e)
            return {"success":False,"error":str(e)}
    async def shutdown(self):
        self._thoughts.clear();self._actions.clear();self._sessions.clear()
        self.status=ModuleStatus.STOPPED
module_class=OpenHandsAgent
