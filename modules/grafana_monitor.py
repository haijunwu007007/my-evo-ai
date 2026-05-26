"""AUTO-EVO-AI V0.1 — Grafana 监控桥接（A级）

桥接到 Grafana HTTP API，暴露 dashboard/datasource/annotation/alert 查询。
"""
__module_meta__ = {"id":"grafana-monitor","name":"Grafana Monitor","version":"V0.1","group":"monitoring","grade":"A",
    "tags":["monitoring","grafana","observability"],"description":"Grafana 监控 API 桥接"}
import time, json, logging, urllib.request, urllib.error
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.grafana-monitor")

def _grafana_api(path,base_url=None,token=None):
    base=base_url or "http://localhost:3000"
    tk=token or ""
    try:
        req=urllib.request.Request(f"{base}/api{path}",
            headers={"Authorization":f"Bearer {tk}"} if tk else {})
        with urllib.request.urlopen(req,timeout=10) as r:
            return True,json.loads(r.read().decode())
    except Exception as e:return False,{"error":str(e)}

class GrafanaMonitor(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="grafana-monitor";MODULE_NAME="Grafana Monitor";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._base_url="http://localhost:3000"
        self._api_token=""
    def initialize(self)->None:self.status=ModuleStatus.RUNNING;logger.info("[Grafana] 桥接就绪")
    def health_check(self)->HealthReport:
        ok,_=_grafana_api("/health",self._base_url,self._api_token)
        return HealthReport(status=self.status.value,healthy=ok,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        self._base_url=p.get("base_url",self._base_url)
        self._api_token=p.get("api_token",self._api_token)
        try:
            if a=="status":
                ok,data=_grafana_api("/health",self._base_url,self._api_token)
                return{"success":ok,"connected":ok,"version":data.get("version","")if ok else "","error":data.get("error")if not ok else None}
            if a=="dashboards":
                ok,data=_grafana_api("/search?type=dash-db",self._base_url,self._api_token)
                return{"success":ok,"dashboards":data if isinstance(data,list) else [],"count":len(data) if isinstance(data,list)else 0}
            if a=="datasources":
                ok,data=_grafana_api("/datasources",self._base_url,self._api_token)
                if ok and isinstance(data,list):
                    return{"success":True,"datasources":[{"name":d.get("name",""),"type":d.get("type",""),"url":d.get("url","")} for d in data],"count":len(data)}
                return{"success":ok,"datasources":[],"error":data.get("error","")if not ok else "invalid"}
            if a=="annotations":
                ok,data=_grafana_api("/annotations?limit=20",self._base_url,self._api_token)
                return{"success":ok,"annotations":data if isinstance(data,list)else[],"count":len(data)if isinstance(data,list)else 0}
            if a=="alerts":
                ok,data=_grafana_api("/alerts",self._base_url,self._api_token)
                return{"success":ok,"alerts":data if isinstance(data,list)else[],"alert_count":sum(1 for a in(data if isinstance(data,list)else[])if a.get("state")=="alerting")}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[Grafana] %s 失败: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=GrafanaMonitor
