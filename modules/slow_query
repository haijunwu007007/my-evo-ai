"""
AUTO-EVO-AI V0.1 — 慢查询分析：SQL性能分析
"""
VERSION = "V0.1"
__module_meta__ = {"id": "slow-query", "name": "SlowQuery", "version": VERSION, "group": "database"}

import json, time, re
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._persist import PersistMixin

class SlowQuery(PersistMixin, EnterpriseModule):
    MODULE_ID = "slow-query"; MODULE_NAME = "SlowQuery"
    
    def __init__(self, config=None):
        EnterpriseModule.__init__(self, config or {})
        PersistMixin.__init__(self, "slow_query")
        self._queries = []
    
    def get_status(self): return {"recorded": len(self._queries)}
    
    def execute(self, action, **kwargs):
        if action == "analyze":
            sql = kwargs.get("sql", "")
            duration = float(kwargs.get("duration", 0))
            # Basic analysis
            issues = []
            if not sql.lower().startswith(("select","insert","update","delete")): issues.append("非标准SQL")
            if "select *" in sql.lower(): issues.append("SELECT * 建议改为具体字段")
            if "like '%" in sql.lower(): issues.append("LIKE前缀通配符无法走索引")
            if "not in" in sql.lower(): issues.append("NOT IN 可优化为 NOT EXISTS")
            if "or" in sql.lower() and "index" not in sql.lower(): issues.append("OR 条件建议用 UNION")
            result = {"sql": sql[:100], "duration": duration, "issues": issues, "suggestions": len(issues)}
            entry = {"ts": time.time(), "duration": duration, "issues": issues, "sql": sql[:100]}
            self._queries.append(entry)
            self.persist(f"q:{time.time()}", json.dumps(entry))
            return result
        if action == "list":
            threshold = kwargs.get("threshold", 0.1)
            slow = [q for q in self._queries if q["duration"] > threshold]
            return {"slow_queries": slow[-20:], "total": len(slow)}
        if action == "stats":
            if not self._queries: return {"avg": 0, "max": 0, "total": 0}
            durs = [q["duration"] for q in self._queries]
            return {"avg": round(sum(durs)/len(durs),3), "max": round(max(durs),3), "total": len(self._queries)}
        return {"error": "unknown: " + str(action)}
