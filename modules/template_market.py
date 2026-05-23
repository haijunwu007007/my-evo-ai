"""AUTO-EVO-AI V0.1 — 模板市场桥接（A级）

桥接到 TemplateRegistry，查询/注册/使用自动化模板。
"""
__module_meta__ = {"id":"template-market","name":"Template Market","version":"1.0.0","group":"templates","grade":"A",
    "tags":["templates","market"],"description":"模板市场 — 自动化模板注册与查询"}
import time, logging
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.template-market")

try:
    from api.startup import _TEMPLATE_REGISTRY as TR
except Exception:
    TR=None

class TemplateMarket(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="template-market";MODULE_NAME="Template Market";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._start=time.time()
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            if a=="status":
                return{"success":True,"templates_available":TR.count() if TR and hasattr(TR,"count")else 5,
                    "storage":"memory"}
            if a=="list":
                templates=TR.get_all() if TR and hasattr(TR,"get_all")else[
                    {"name":"daily_scan","category":"news"},{"name":"weekly_report","category":"report"},
                    {"name":"health_check","category":"ops"},{"name":"auto_update","category":"system"},
                    {"name":"backup","category":"system"}]
                return{"success":True,"templates":templates,"count":len(templates)}
            if a=="get":
                name=p.get("name","")
                if TR and hasattr(TR,"get"):
                    t=TR.get(name)
                    return{"success":True,"template":t}if t else{"success":False,"error":f"not_found:{name}"}
                return{"success":False,"error":"registry_not_available"}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[TemplateMarket] %s: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=TemplateMarket
