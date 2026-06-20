"""
AUTO-EVO-AI V0.1 — 日志聚合：收集+搜索+统计
"""
VERSION = "V0.1"
__module_meta__ = {"id": "log-aggr", "name": "LogAggregator", "version": VERSION, "group": "monitor"}

import json, time, re, os
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._persist import PersistMixin

class LogAggregator(PersistMixin, EnterpriseModule):
    MODULE_ID = "log-aggr"; MODULE_NAME = "LogAggregator"
    
    def __init__(self, config=None):
        EnterpriseModule.__init__(self, config or {})
        PersistMixin.__init__(self, "logs")
        self._logs = []
    
    def get_status(self): return {"total_logs": len(self._logs)}
    
    def execute(self, action, **kwargs):
        if action == "ingest":
            entry = {"ts": time.time(), "level": kwargs.get("level","INFO"), "source": kwargs.get("source",""), "msg": kwargs.get("message",""), "id": len(self._logs)}
            self._logs.append(entry)
            self.persist(f"log:{entry['id']}", json.dumps(entry))
            return entry
        if action == "search":
            q = kwargs.get("query", "").lower()
            level = kwargs.get("level", "")
            results = [l for l in self._logs if q in l["msg"].lower() and (not level or l["level"]==level)]
            return {"results": results[-50:], "total": len(results)}
        if action == "stats":
            levels = {}
            for l in self._logs:
                lv = l["level"]; levels[lv] = levels.get(lv,0)+1
            return {"levels": levels, "total": len(self._logs)}
        if action == "recent":
            n = kwargs.get("count", 20)
            return {"logs": self._logs[-n:]}
        return {"error": "unknown: " + str(action)}
