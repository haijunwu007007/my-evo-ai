"""AUTO-EVO-AI V0.1 — MCP协议桥接器"""
# Grade: B
VERSION="V0.1"
__module_meta__={"id":"mcp-bridge","name":"MCPBridge","version":VERSION,"group":"ai"}
import json,time,uuid,logging,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin

logger=logging.getLogger(__name__)

class MCPBridge(EnterpriseModule, CircuitBreakerMixin):
    MODULE_ID="mcp-bridge";MODULE_NAME="MCPBridge"
    def __init__(self,c=None):
        super().__init__(c)
        self._services={}
        self._call_history=[]
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
            if a=="register_service":
                name=p.get("name","");desc=p.get("description","");version=p.get("version","1.0")
                schema=p.get("schema",{})
                sid=uuid.uuid4().hex[:8]
                self._services[name]={"id":sid,"name":name,"description":desc,"version":version,"schema":schema,"registered_at":time.time()}
                return {"success":True,"service_id":sid,"service_name":name}
            if a=="discover":
                query=p.get("query","")
                if query:
                    matches={k:v for k,v in self._services.items() if query.lower() in k.lower() or query.lower() in v.get("description","").lower()}
                else:
                    matches=dict(self._services)
                return {"success":True,"services":{k:{"description":v.get("description",""),"version":v.get("version","")} for k,v in matches.items()},"count":len(matches)}
            if a=="call":
                service=p.get("service","");args=p.get("args",{})
                svc=self._services.get(service)
                if not svc:return {"success":False,"error":f"service '{service}' not found"}
                prompt=f"调用MCP服务: {svc['description']}\n参数: {json.dumps(args,ensure_ascii=False)}\n请执行并返回结果。"
                result=self._call(prompt)
                call_id=uuid.uuid4().hex[:8]
                self._call_history.append({"call_id":call_id,"service":service,"args":args,"result":result[:200],"timestamp":time.time()})
                return {"success":True,"call_id":call_id,"result":result}
            if a=="status":
                svc_count=len(self._services)
                recent_calls=self._call_history[-10:] if self._call_history else []
                return {"success":True,"services_count":svc_count,"services":list(self._services.keys()),"recent_calls":recent_calls,"total_calls":len(self._call_history)}
            return {"success":False,"error":f"unknown: {a}"}
        except Exception as e:
            logger.error("MCPBridge.execute error: %s",e)
            return {"success":False,"error":str(e)}
    async def shutdown(self):
        self._services.clear();self._call_history.clear()
        self.status=ModuleStatus.STOPPED
module_class=MCPBridge
