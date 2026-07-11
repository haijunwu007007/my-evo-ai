"""BookStack知识库"""
import logging,httpx
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger=logging.getLogger("evo.modules.bookstack_kb")
class BookstackKB(EnterpriseModule):
 def __init__(s):s._ready=True;s._url="";s._token=""
 def config(s,url,token):s._url=url.rstrip("/");s._token=token;return{"success":True}
 def _api(s,path):
  try:r=httpx.get(f"{s._url}/api{path}",headers={"Authorization":f"Token {s._token}"},timeout=15);return r.json() if r.status_code==200 else {}
  except:return{}
 def search(s,q):return{"success":True,"results":s._api(f"/search?q={q}").get("data",[]) if s._url else []}
 def status(s):return{"name":"bookstack_kb","ready":s._ready,"configured":bool(s._url)}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("token",""))
  if a=="search":return s.search(p.get("q",""))
  return s.status()
get_status=lambda:BookstackKB().status()
register=lambda:{"name":"bookstack_kb","class":"BookstackKB","description":"BookStack知识库"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "bookstack_kb", "ready": getattr(self, "_ready", True),
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

module_class = BookstackKB
