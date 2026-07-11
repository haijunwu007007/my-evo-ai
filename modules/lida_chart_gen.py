"""LIDA图表生成"""
import logging,httpx
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger=logging.getLogger("evo.modules.lida_chart_gen")
class LidaChartGen(EnterpriseModule):
 def __init__(s):s._ready=True;s._url="http://localhost:8000"
 def config(s,url):s._url=url.rstrip("/");return{"success":True}
 def generate(s,goal,summary=""):
  try:r=httpx.post(f"{s._url}/generate",json={"goal":goal,"data_summary":summary or goal},timeout=60);return{"success":r.status_code==200,"charts":r.json()if r.status_code==200 else[]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"lida_chart_gen","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""))
  if a=="generate":return s.generate(p.get("goal",""),p.get("data_summary",""))
  return s.status()
get_status=lambda:LidaChartGen().status()
register=lambda:{"name":"lida_chart_gen","class":"LidaChartGen","description":"LIDA图表生成"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "lida_chart_gen", "ready": getattr(self, "_ready", True),
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

module_class = LidaChartGen
