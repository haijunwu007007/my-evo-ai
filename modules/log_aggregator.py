# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 日志聚合器（A级）

日志收集、查询、导出引擎，支持多级别过滤"""
__module_meta__ = {"id":"log-aggregator","name":"Log Aggregator","version":"1.0.0","group":"monitoring","grade":"A",
    "tags":["monitoring","logging","aggregation","query"],"description":"Log aggregation and query engine"}
import time, uuid, logging, json, threading
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.log-aggregator")
class LogAggregator(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="log-aggregator";MODULE_NAME="日志聚合器";VERSION="v1.0";MODULE_LEVEL="A"
    _MAX_ENTRIES=10000
    def __init__(self,config=None):
        super().__init__(config);self._entries:List[Dict]=[];self._lock=threading.Lock()
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"entries":len(self._entries)})
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            return{"success":True,"entries":len(self._entries),"max":self._MAX_ENTRIES,
                "levels":list(set(e.get("level","info") for e in self._entries))}
        if a=="ingest":
            level=p.get("level","info");source=p.get("source","");msg=p.get("message","")
            entry={"id":str(uuid.uuid4())[:8],"timestamp":time.time(),"level":level,"source":source,"message":msg}
            with self._lock:
                self._entries.append(entry)
                if len(self._entries)>self._MAX_ENTRIES:self._entries=self._entries[-self._MAX_ENTRIES:]
            return{"success":True,"log_id":entry["id"]}
        if a=="query":
            level=p.get("level","");source=p.get("source","");limit=int(p.get("limit",100))
            since=float(p.get("since",0))
            results=self._entries
            if level:results=[e for e in results if e["level"]==level]
            if source:results=[e for e in results if e["source"]==source]
            if since:results=[e for e in results if e["timestamp"]>since]
            results=results[-limit:]
            return{"success":True,"entries":[{"id":e["id"],"timestamp":e["timestamp"],"level":e["level"],
                "source":e["source"],"message":e["message"]} for e in results],"count":len(results)}
        if a=="export":
            f=p.get("format","json")
            if f=="json":return{"success":True,"format":"json","data":json.dumps(self._entries[-500:])}
            if f=="text":return{"success":True,"format":"text","data":"\n".join(
                f"[{e['level'].upper()}][{e['source']}] {e['message']}" for e in self._entries[-500:])}
            return{"success":False,"error":f"unsupported_format:{f}"}
        if a=="clear":
            n=len(self._entries)
            with self._lock:self._entries.clear()
            return{"success":True,"cleared":n}
        if a=="level_counts":
            counts={}
            for e in self._entries:
                counts[e["level"]]=counts.get(e["level"],0)+1
            return{"success":True,"level_counts":counts,"total":len(self._entries)}
        if a=="search":
            keyword=p.get("keyword","")
            if not keyword:return{"success":True,"entries":[],"count":0,"keyword":keyword}
            kwl=keyword.lower()
            hits=[e for e in self._entries if kwl in e.get("message","").lower()or kwl in e.get("source","").lower()]
            limit=int(p.get("limit",100))
            return{"success":True,"entries":hits[-limit:],"count":len(hits),"keyword":keyword}
        if a=="purge":
            older_than=float(p.get("older_than",86400))
            cutoff=time.time()-older_than
            with self._lock:
                before=len(self._entries)
                self._entries=[e for e in self._entries if e["timestamp"]>=cutoff]
                purged=before-len(self._entries)
            return{"success":True,"purged":purged,"remaining":len(self._entries),"older_than_hours":round(older_than/3600,1)}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self._entries.clear();self.status=ModuleStatus.STOPPED
module_class=LogAggregator
