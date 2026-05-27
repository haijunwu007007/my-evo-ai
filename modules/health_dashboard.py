"""AUTO-EVO-AI V0.1 — 健康仪表盘桥接（A级）

聚合系统健康状态：模块健康/API状态/资源用量/告警摘要。
桥接到 modules/health_checker 和 modules/health_monitor。
"""
__module_meta__ = {"id":"health-dashboard","name":"Health Dashboard","version":"V0.1","group":"ops","grade":"A",
    "tags":["ops","health","dashboard"],"description":"健康仪表盘 — 聚合系统健康数据"}
import time, logging
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.health-dashboard")

class HealthDashboard(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="health-dashboard";MODULE_NAME="Health Dashboard";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._start_time=time.time()
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            if a=="status":
                uptime=time.time()-self._start_time
                return{"success":True,"uptime_seconds":round(uptime,1),"module":"health_dashboard","status":"running"}
            if a=="system_health":
                from api.infra import registry
                r=registry.get_registry() if hasattr(registry,"get_registry")else registry
                h=r.get_all_health() if hasattr(r,"get_all_health")else {}
                total=len(h);active=sum(1 for v in h.values()if v.get("status")=="active");
                err=sum(1 for v in h.values()if v.get("status")in("error","lazy_error"))
                return{"success":True,"total_modules":total,"active":active,"errors":err,
                    "health_rate":round(active/total*100,1)if total else 0}
            if a=="module_health":
                mod=p.get("module","")
                from api.infra import registry
                r=registry.get_registry() if hasattr(registry,"get_registry")else registry
                return{"success":True,"health":r.get_all_health().get(mod,{})}
            if a=="recent_issues":
                return{"success":True,"issues":[],"note":"health_dashboard: 无持久化指标"}
            if a=="summary":
                uptime=time.time()-self._start_time
                return{"success":True,"uptime":f"{uptime/86400:.1f}d","status":"running","module":"health_dashboard"}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[HealthDashboard] %s 失败: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=HealthDashboard
