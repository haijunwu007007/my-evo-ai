# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 慢查询分析（A级）"""
# Grade: B
__module_meta__ = {"id":"slow-query","name":"Slow Query","version":"V0.1","group":"data","grade":"C",
    "tags":["data","sql","performance"],"description":"慢查询分析 - 分析/日志/报告/导出/配置"}
import time, uuid, logging, re
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.slow-query")
class SlowQuery(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="slow-query";MODULE_NAME="慢查询分析";VERSION="V0.1";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._queries=[];self._threshold_ms=1000
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="analyze":
            sql=p.get("sql","SELECT * FROM users WHERE id=1");dur=float(p.get("duration_ms",1500))
            issues=[];suggestions=[]
            if "SELECT *"in sql.upper():issues.append("SELECT * used, consider explicit columns");suggestions.append("Replace SELECT * with specific column names")
            if"WHERE"not in sql.upper():issues.append("No WHERE clause - full table scan possible");suggestions.append("Add WHERE condition to filter rows")
            if"LIKE '%"in sql.upper():issues.append("Leading wildcard LIKE prevents index use");suggestions.append("Avoid leading % in LIKE, use full-text search instead")
            if"JOIN"in sql.upper()and"ON"not in sql.upper():issues.append("JOIN without ON clause");suggestions.append("Add explicit ON condition")
            if dur>1000:issues.append(f"Query took {dur}ms - exceeds 1s threshold");suggestions.append("Add appropriate indexes, consider query optimization")
            score=max(0,100-(len(issues)*20)-dur//100)
            self._queries.append({"sql":sql[:200],"duration":dur,"issues":len(issues),"score":score,"timestamp":time.time()})
            return{"success":True,"sql":sql,"duration_ms":dur,"issues":issues,"suggestions":suggestions,"health_score":score}
        if a=="log":
            self._queries.append({"sql":p.get("sql",""),"duration":float(p.get("duration_ms",0)),"timestamp":time.time()});return{"success":True}
        if a=="report":
            slow=[q for q in self._queries if q["duration"]>self._threshold_ms]
            return{"success":True,"total_queries":len(self._queries),"slow_queries":len(slow),
                "slow_rate":f"{len(slow)*100//max(len(self._queries),1)}%","threshold_ms":self._threshold_ms,
                "top_slow":sorted(slow,key=lambda x:x["duration"],reverse=True)[:10]}
        if a=="export":
            f=p.get("format","json");limit=int(p.get("limit",500))
            if f=="json":return{"success":True,"data":self._queries[-limit:],"count":min(len(self._queries),limit)}
            if f=="text":lines=[f"[{q['duration']}ms][score:{q['score']}] {q['sql'][:80]}" for q in self._queries[-limit:]]
            return{"success":True,"format":"text","data":"\n".join(lines)}
        if a=="stats":
            by_status={};avg_dur=0
            if self._queries:avg_dur=sum(q["duration"]for q in self._queries)/len(self._queries)
            return{"success":True,"total_queries":len(self._queries),"avg_duration_ms":round(avg_dur,1),
                "threshold_ms":self._threshold_ms,"slow_count":sum(1 for q in self._queries if q["duration"]>self._threshold_ms)}
        if a=="config":
            if"threshold_ms"in p:self._threshold_ms=int(p.get("threshold_ms",1000))
            return{"success":True,"threshold_ms":self._threshold_ms}
        if a=="clear":
            self._queries.clear();return{"success":True,"cleared":True}
        return{"error":f"unknown:{a}"}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=SlowQuery
