"""AUTO-EVO-AI V0.1 — 模型路由"""
# Grade: B
VERSION="V0.1"
__module_meta__={"id":"model-router","name":"ModelRouter","version":VERSION,"group":"ai"}
import json,time,uuid,random,logging,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin
from modules._persist import PersistMixin


logger=logging.getLogger(__name__)

class ModelRouter(PersistMixin,EnterpriseModule, CircuitBreakerMixin):
    MODULE_ID="model-router";MODULE_NAME="ModelRouter"
    def __init__(self,c=None):
        super().__init__(c)
        self._models={}
        self._usage_counter={}
        self._url=self.config.get("llm_url","http://127.0.0.1:8765/api/llm/chat")
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
        try:
            if a=="register_model":
                name=p.get("name","");model=p.get("model","zhipu:glm-4-flash");capabilities=p.get("capabilities",[])
                self._models[name]={"model":model,"capabilities":capabilities,"registered_at":time.time()}
                self._usage_counter[name]=0
                return {"success":True,"name":name,"model":model}
            if a=="route":
                task=p.get("task","");model_key=p.get("model_key","")
                if model_key and model_key in self._models:
                    target=self._models[model_key]["model"]
                elif self._models:
                    target=random.choice(list(self._models.values()))["model"]
                else:
                    target="zhipu:glm-4-flash"
                result=self._call(target,task)
                key=model_key or target
                self._usage_counter[key]=self._usage_counter.get(key,0)+1
                return {"success":True,"routed_to":target,"result":result[:500]}
            if a=="load_balance":
                task=p.get("task","")
                if not self._models:
                    return {"success":False,"error":"no models registered"}
                min_used=min(self._usage_counter.values()) if self._usage_counter else 0
                candidates=[k for k,v in self._usage_counter.items() if v==min_used]
                chosen=random.choice(candidates)
                target=self._models[chosen]["model"]
                result=self._call(target,task)
                self._usage_counter[chosen]+=1
                return {"success":True,"chosen":chosen,"model":target,"result":result[:500]}
            if a=="status":
                return {"success":True,"models_count":len(self._models),"models":{k:v["model"] for k,v in self._models.items()},"usage":dict(self._usage_counter)}
            return {"success":False,"error":f"unknown: {a}"}
        except Exception as e:
            logger.error("ModelRouter.execute error: %s",e)
            return {"success":False,"error":str(e)}
    async def shutdown(self):self._models.clear();self._usage_counter.clear();self.status=ModuleStatus.STOPPED
module_class=ModelRouter
