"""AUTO-EVO-AI V0.1 — Prometheus 指标桥接（A级）

桥接到 DataEngine SQLite，暴露自定义业务指标注册 + 采集 + 快照。
"""
__module_meta__ = {"id":"prometheus-metrics","name":"Prometheus Metrics","version":"2.0.0","group":"monitoring","grade":"A",
    "tags":["monitoring","prometheus","metrics"],"description":"Prometheus 业务指标桥接 (DataEngine)"}
import time, logging
from typing import Any, Dict
from pathlib import Path
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
from core.data_layer import DataEngine
logger=logging.getLogger("evo.prometheus-metrics")

class PrometheusMetrics(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="prometheus-metrics";MODULE_NAME="Prometheus Metrics";VERSION="v2.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._start=time.time()
        self._db=DataEngine.get("prometheus_metrics")
        self._ensure_schema()
        self._cache:Dict[str,float]={}
        self._load_cache()
    def _ensure_schema(self):
        self._db.create_table("metrics",{"name":"TEXT PRIMARY KEY","value":"REAL DEFAULT 0",
            "help_text":"TEXT DEFAULT ''","updated":"REAL"})
    def _load_cache(self):
        rows=self._db.fetch_all("SELECT name,value FROM metrics")
        self._cache={r["name"]:r["value"] for r in rows}
        logger.info("[PrometheusMetrics] 加载 %d 持久化指标",len(self._cache))
    def _persist(self,name:str,value:float,help_text:str=""):
        self._db.upsert("metrics",{"name":name,"value":value,"help_text":help_text,"updated":time.time()},"name")
    def initialize(self)->None:
        self.status=ModuleStatus.RUNNING
        logger.info("[PrometheusMetrics] 桥接就绪, %d 持久化指标",len(self._cache))
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,
            checks={"metrics":len(self._cache),"engine":"SQLite"})
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            if a=="register":
                name=p.get("name","");val=float(p.get("value",0));help_text=p.get("help","")
                self._cache[name]=val
                self._persist(name,val,help_text)
                return{"success":True,"metric":name,"value":val}
            if a=="inc":
                name=p.get("name","");delta=float(p.get("delta",1))
                self._cache.setdefault(name,0)
                self._cache[name]+=delta
                self._persist(name,self._cache[name])
                return{"success":True,"metric":name,"value":self._cache[name]}
            if a=="set":
                name=p.get("name","");val=float(p.get("value",0))
                self._cache[name]=val
                self._persist(name,val)
                return{"success":True,"metric":name,"value":val}
            if a=="get":
                name=p.get("name","")
                if name in self._cache:
                    return{"success":True,"metric":name,"value":self._cache[name]}
                row=self._db.fetch_one("SELECT value FROM metrics WHERE name=?",(name,))
                if row:return{"success":True,"metric":name,"value":row["value"]}
                return{"success":False,"error":f"metric_not_found:{name}"}
            if a=="list":
                return{"success":True,"metrics":dict(self._cache)}
            if a=="snapshot":
                return{"success":True,"metrics":dict(self._cache),
                    "count":len(self._cache),"uptime_seconds":round(time.time()-self._start,1),"engine":"SQLite"}
            if a=="text_output":
                items=self._cache.items()
                lines=[]
                for k,v in items:
                    lines.extend(["# HELP evo_"+k+" custom metric","# TYPE evo_"+k+" gauge","evo_"+k+" "+str(v)])
                return{"success":True,"prometheus_text":"\n".join(lines)}
            if a=="delete":
                name=p.get("name","")
                self._cache.pop(name,None)
                self._db.delete("metrics","name=?",(name,))
                return{"success":True,"deleted":name}
            if a=="search":
                q=p.get("query","")
                rows=self._db.search("metrics",q,fields=["name","help_text"],limit=p.get("limit",50))
                return{"success":True,**rows}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[PrometheusMetrics] %s 失败: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:
        self.status=ModuleStatus.STOPPED
module_class=PrometheusMetrics
