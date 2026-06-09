"""AUTO-EVO-AI V0.1 - 数据质量引擎（A级）
# Grade: B

数据质量检查：完整性、唯一性、有效性、范围校验"""
__module_meta__ = {"id":"data-quality","name":"Data Quality","version":"V0.1","group":"data","grade":"C",
    "tags":["data","quality","validation","profiling"],"description":"Data quality checks: completeness, uniqueness, validity"}
import time, logging, re
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
from modules._persist import PersistMixin

logger=logging.getLogger("evo.data-quality")
class DataQuality(PersistMixin,CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="data-quality";MODULE_NAME="数据质量引擎";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config)
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":return{"success":True,"checks":["completeness","uniqueness","validity","range","pattern"]}
        if a=="completeness":
            fields=p.get("fields",[])
            if not fields:return{"success":False,"error":"fields_required"}
            total=len(fields);nulls=sum(1 for f in fields if f is None or str(f).strip()=="")
            return{"success":True,"total":total,"nulls":nulls,"completeness":round((total-nulls)/total*100,1)if total else 100}
        if a=="uniqueness":
            values=p.get("values",[])
            if not values:return{"success":False,"error":"values_required"}
            total=len(values);unique=len(set(str(v) for v in values))
            return{"success":True,"total":total,"unique":unique,"duplicates":total-unique,"uniqueness":round(unique/total*100,1)if total else 100}
        if a=="validity":
            rule=p.get("rule","email");values=p.get("values",[])
            patterns={"email":r'^[\w\.-]+@[\w\.-]+\.\w+$',"phone":r'^1[3-9]\d{9}$',"url":r'^https?://','number':r'^-?\d+(\.\d+)?$'}
            pat=patterns.get(rule,"")
            if not pat:return{"success":False,"error":f"unknown_rule:{rule}"}
            valid=sum(1 for v in values if re.match(pat,str(v)))if pat else len(values)
            return{"success":True,"rule":rule,"total":len(values),"valid":valid,"invalid":len(values)-valid,"validity":round(valid/max(1,len(values))*100,1)}
        if a=="profile":
            values=p.get("values",[])
            if not values:return{"success":False,"error":"values_required"}
            nums=[float(v) for v in values if isinstance(v,(int,float)) or str(v).replace('.','',1).replace('-','',1).isdigit()]
            if nums:
                return{"success":True,"count":len(values),"numeric_count":len(nums),"min":min(nums),"max":max(nums),
                    "avg":round(sum(nums)/len(nums),2),"median":sorted(nums)[len(nums)//2]}
            return{"success":True,"count":len(values),"types":list(set(type(v).__name__ for v in values))}
        if a=="schema_detect":
            records=p.get("records",[])
            if not records:return{"success":False,"error":"records_required"}
            schema={}
            for r in records:
                for k,v in (r.items() if isinstance(r,dict) else []):
                    t=type(v).__name__
                    if k not in schema:schema[k]={"types":set(),"non_null":0}
                    schema[k]["types"].add(t)
                    if v is not None and str(v).strip():schema[k]["non_null"]+=1
            return{"success":True,"fields":[{"name":k,"types":list(v["types"]),
                "non_null_rate":round(v["non_null"]/max(1,len(records))*100,1)}for k,v in schema.items()],
                "total_records":len(records),"total_fields":len(schema)}
        if a=="range_check":
            values=p.get("values",[]);min_v=p.get("min",0);max_v=p.get("max",100)
            nums=[float(v) for v in values if isinstance(v,(int,float))]
            out_of_range=[v for v in nums if v<min_v or v>max_v]
            return{"success":True,"total":len(nums),"out_of_range":len(out_of_range),
                "out_of_range_pct":round(len(out_of_range)/max(1,len(nums))*100,1),"min":min_v,"max":max_v}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=DataQuality
