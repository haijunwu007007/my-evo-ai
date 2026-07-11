"""Plausible分析"""
import logging,httpx
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger=logging.getLogger("evo.modules.plausible_analytics")
class PlausibleAnalytics(EnterpriseModule):
 def __init__(s):s._ready=True;s._url="";s._key="";s._site=""
 def config(s,url,key,site):s._url=url.rstrip("/");s._key=key;s._site=site;return{"success":True}
 def get_stats(s,period="30d"):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.get(f"{s._url}/api/v1/stats/aggregate",headers={"Authorization":f"Bearer {s._key}"},params={"site_id":s._site,"period":period,"metrics":"visitors,pageviews,bounce_rate,visit_duration"},timeout=10);return{"success":r.status_code==200,"stats":r.json().get("results",{})if r.status_code==200 else{}}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"plausible_analytics","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("key",""),p.get("site",""))
  if a=="get_stats":return s.get_stats(p.get("period","30d"))
  return s.status()
get_status=lambda:PlausibleAnalytics().status()
register=lambda:{"name":"plausible_analytics","class":"PlausibleAnalytics","description":"Plausible分析"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "plausible_analytics", "ready": getattr(self, "_ready", True),
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

module_class = PlausibleAnalytics
