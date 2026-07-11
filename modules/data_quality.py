"""数据质量检查"""
import logging
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger = logging.getLogger('evo.modules.data_quality')
class DataQuality(EnterpriseModule):
    def __init__(self): self._ready=True
    def check_null(self, data, fields):
        if not data: return {'success':False,'error':'无数据'}
        results=[]
        for f in fields:
            nc=sum(1 for row in (data if isinstance(data,list) else [data]) if row.get(f) is None or row.get(f)=='')
            t=len(data) if isinstance(data,list) else 1
            results.append({'field':f,'nulls':nc,'total':t,'rate':round(nc/t*100,1) if t else 0})
        return {'success':True,'checks':results}
    def status(self): return {'name':'data_quality','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='check_null': return self.check_null(p.get('data',[]),p.get('fields',[]))
        return self.status()
get_status=lambda:DataQuality().status()
register=lambda:{'name':'data_quality','class':'DataQuality','description':'数据质量 - 完整性检查'}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "data_quality", "ready": getattr(self, "_ready", True),
         "status": self.status.value if hasattr(self, "status") else "running"}

def health_check(self):
 return HealthReport(status=self.status.value if hasattr(self, "status") else "running",
                    healthy=getattr(self, "_ready", True), module_id=self.MODULE_ID)

def initialize(self):
 self.status = ModuleStatus.RUNNING
 return {"success": True}

def shutdown(self):
 self.status = ModuleStatus.STOPPED
 return {"success": True}

module_class = DataQuality
