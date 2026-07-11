"""Perplexica搜索"""
import logging,httpx
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger=logging.getLogger("evo.modules.perplexica_search")
class PerplexicaSearch(EnterpriseModule):
 def __init__(s):s._ready=True;s._url="http://localhost:3001"
 def config(s,url):s._url=url.rstrip("/");return{"success":True}
 def search(s,q):
  try:r=httpx.post(f"{s._url}/api/search",json={"query":q,"focusMode":"webSearch"},timeout=30);return{"success":r.status_code==200,"results":r.json().get("results",[])if r.status_code==200 else[]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"perplexica_search","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""))
  if a=="search":return s.search(p.get("q",""))
  return s.status()
get_status=lambda:PerplexicaSearch().status()
register=lambda:{"name":"perplexica_search","class":"PerplexicaSearch","description":"Perplexica搜索"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "perplexica_search", "ready": getattr(self, "_ready", True),
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

module_class = PerplexicaSearch
