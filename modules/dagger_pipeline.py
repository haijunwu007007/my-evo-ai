"""Dagger CI/CD管线"""
import logging,subprocess
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger=logging.getLogger("evo.modules.dagger_pipeline")
class DaggerPipeline(EnterpriseModule):
 def __init__(s):s._ready=True
 def run(s,module=""):
  try:r=subprocess.run(["dagger","run"]+(["-m",module] if module else[])+["python","-m","pipeline"],capture_output=True,text=True,timeout=300);return{"success":r.returncode==0,"stdout":r.stdout[-500:]}
  except Exception as e:return{"success":False,"error":str(e)}
 def status(s):return{"name":"dagger_pipeline","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="run":return s.run(p.get("module",""))
  return s.status()
get_status=lambda:DaggerPipeline().status()
register=lambda:{"name":"dagger_pipeline","class":"DaggerPipeline","description":"Dagger CI/CD管线"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "dagger_pipeline", "ready": getattr(self, "_ready", True),
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

module_class = DaggerPipeline
