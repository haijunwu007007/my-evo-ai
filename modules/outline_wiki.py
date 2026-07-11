"""Outline知识库"""
import logging,httpx
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger=logging.getLogger("evo.modules.outline_wiki")
class OutlineWiki(EnterpriseModule):
 def __init__(s):s._ready=True;s._url="";s._key=""
 def config(s,url,key):s._url=url.rstrip("/");s._key=key;return{"success":True}
 def search(s,q):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.post(f"{s._url}/api/documents.search",headers={"Authorization":f"Bearer {s._key}"},json={"query":q},timeout=10);return{"success":r.status_code==200,"results":r.json().get("data",[])if r.status_code==200 else[]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"outline_wiki","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("key",""))
  if a=="search":return s.search(p.get("q",""))
  return s.status()
get_status=lambda:OutlineWiki().status()
register=lambda:{"name":"outline_wiki","class":"OutlineWiki","description":"Outline知识库"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "outline_wiki", "ready": getattr(self, "_ready", True),
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

module_class = OutlineWiki
