"""Postiz社交媒体"""
import logging,httpx
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger=logging.getLogger("evo.modules.postiz_social")
class PostizSocial(EnterpriseModule):
 def __init__(s):s._ready=True;s._url="";s._key=""
 def config(s,url,key):s._url=url.rstrip("/");s._key=key;return{"success":True}
 def post(s,content,platforms=None):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.post(f"{s._url}/api/v1/posts",headers={"Authorization":f"Bearer {s._key}"},json={"content":content,"platforms":platforms or["twitter"]},timeout=10);return{"success":r.status_code==200,"post":r.json()if r.status_code==200 else{}}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"postiz_social","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("key",""))
  if a=="post":return s.post(p.get("content",""),p.get("platforms",None))
  return s.status()
get_status=lambda:PostizSocial().status()
register=lambda:{"name":"postiz_social","class":"PostizSocial","description":"Postiz社交媒体"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "postiz_social", "ready": getattr(self, "_ready", True),
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

module_class = PostizSocial
