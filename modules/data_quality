"""
AUTO-EVO-AI V0.1 — 数据质量检测
"""
VERSION = "V0.1"
__module_meta__ = {"id": "data-quality", "name": "DataQuality", "version": VERSION, "group": "data"}

import json, statistics
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

class DataQuality(EnterpriseModule):
    MODULE_ID = "data-quality"; MODULE_NAME = "DataQuality"
    
    def __init__(self, config=None): EnterpriseModule.__init__(self, config or {})
    
    def get_status(self): return {"ready": True}
    
    def execute(self, action, **kwargs):
        if action == "check_null":
            data = kwargs.get("data", [])
            nulls = sum(1 for x in data if x is None or x == "" or x == "null")
            return {"total": len(data), "nulls": nulls, "null_rate": round(nulls/len(data)*100,2) if data else 0}
        if action == "check_duplicates":
            data = kwargs.get("data", [])
            seen = set(); dups = set()
            for x in data: (dups if x in seen else seen).add(x)
            return {"total": len(data), "duplicates": list(dups), "dup_count": len(dups)}
        if action == "detect_outliers":
            values = [float(x) for x in kwargs.get("data",[]) if isinstance(x,(int,float)) or str(x).replace(".","").replace("-","").isdigit()]
            if len(values) < 3: return {"error": "need at least 3 values"}
            m = statistics.mean(values); s = statistics.stdev(values) if len(values)>1 else 0
            outliers = [v for v in values if abs(v-m) > 2*s]
            return {"mean": round(m,2), "std": round(s,2), "outliers": outliers, "outlier_count": len(outliers)}
        return {"error": "unknown: " + str(action)}
