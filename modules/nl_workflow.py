"""AUTO-EVO-AI V0.1 — 自然语言工作流"""
# Grade: B
VERSION="V0.1"
__module_meta__={"id":"nl-workflow","name":"NLWorkflow","version":VERSION,"group":"ai"}
import json,time,uuid,logging,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

logger=logging.getLogger(__name__)

class NLWorkflow(EnterpriseModule):
    MODULE_ID="nl-workflow";MODULE_NAME="NLWorkflow"
    def __init__(self,c=None):
        super().__init__(c)
        self._templates={}
        self._history=[]
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
        try:
            if a=="parse":
                text=p.get("text","");intent=p.get("intent","")
                prompt=f"解析以下自然语言指令:\n{text}\n"
                if intent:prompt+=f"意图: {intent}\n"
                prompt+="请输出: 1)意图识别 2)参数提取(JSON) 3)建议执行的步骤"
                result=self._call(prompt)
                parse_id=uuid.uuid4().hex[:8]
                self._history.append({"action":"parse","parse_id":parse_id,"input":text[:100],"timestamp":time.time()})
                return {"success":True,"parse_id":parse_id,"parsed":result}
            if a=="execute":
                workflow_id=p.get("workflow_id","");params=p.get("params",{})
                tmpl=self._templates.get(workflow_id)
                if not tmpl:return {"success":False,"error":f"template '{workflow_id}' not found"}
                steps=tmpl.get("steps",[])
                results=[]
                for i,step in enumerate(steps):
                    step_prompt=f"执行工作流步骤 {i+1}/{len(steps)}: {step}\n参数: {json.dumps(params,ensure_ascii=False)}"
                    step_result=self._call(step_prompt)
                    results.append({"step":i+1,"name":step,"result":step_result[:200]})
                exec_id=uuid.uuid4().hex[:8]
                self._history.append({"action":"execute","execution_id":exec_id,"workflow_id":workflow_id,"steps":len(steps),"timestamp":time.time()})
                return {"success":True,"execution_id":exec_id,"results":results}
            if a=="add_template":
                name=p.get("name","");steps=p.get("steps",[]);desc=p.get("description","")
                if not steps:return {"success":False,"error":"steps required"}
                tid=uuid.uuid4().hex[:8]
                self._templates[tid]={"name":name,"steps":steps,"description":desc,"created_at":time.time()}
                return {"success":True,"template_id":tid,"name":name,"step_count":len(steps)}
            if a=="status":
                return {"success":True,"templates_count":len(self._templates),"templates":{k:v["name"] for k,v in self._templates.items()},"history_count":len(self._history)}
            return {"success":False,"error":f"unknown: {a}"}
        except Exception as e:
            logger.error("NLWorkflow.execute error: %s",e)
            return {"success":False,"error":str(e)}
    async def shutdown(self):self._templates.clear();self._history.clear();self.status=ModuleStatus.STOPPED
module_class=NLWorkflow
