"""AUTO-EVO-AI V0.1 — MCP协议桥接器"""
VERSION="V0.1"
__module_meta__={"id":"mcp-bridge","name":"MCPBridge","version":VERSION,"group":"ai"}
import json,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin
class MCPBridge(EnterpriseModule, CircuitBreakerMixin):
    MODULE_ID="mcp-bridge";MODULE_NAME="MCPBridge"
    def __init__(self,c=None):
        super().__init__(c);self._tools={}
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
        if a=="register_tool":
            name=p.get("name","");desc=p.get("description","")
            self._tools[name]={"desc":desc,"params":p.get("params",{})}
            return {"success":True,"tools":list(self._tools.keys())}
        if a=="call_tool":
            tool=self._tools.get(p.get("tool",""))
            if not tool:return {"success":False,"error":"tool not found"}
            prompt=f"工具: {tool['desc']}\n参数: {json.dumps(p.get('args',{}),ensure_ascii=False)}\n执行结果:"
            return {"success":True,"result":self._call(prompt)}
        return {"success":False,"error":f"unknown: {a}"}
    async def shutdown(self):self._tools.clear();self.status=ModuleStatus.STOPPED
module_class=MCPBridge
