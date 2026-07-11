"""Chatwoot客服"""
import logging,httpx
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger=logging.getLogger("evo.modules.chatwoot_support")
class ChatwootSupport(EnterpriseModule):
 def __init__(s):s._ready=True;s._url="";s._key=""
 def config(s,url,key):s._url=url.rstrip("/");s._key=key;return{"success":True}
 def send(s,inbox,content):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.post(f"{s._url}/api/v1/accounts/1/conversations/{inbox}/messages",headers={"api_access_token":s._key},json={"content":content},timeout=10);return{"success":r.status_code==200}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"chatwoot_support","ready":s._ready,"configured":bool(s._url)}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("key",""))
  if a=="send":return s.send(p.get("inbox_id",""),p.get("content",""))
  return s.status()
get_status=lambda:ChatwootSupport().status()
register=lambda:{"name":"chatwoot_support","class":"ChatwootSupport","description":"Chatwoot客服"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "chatwoot_support", "ready": getattr(self, "_ready", True),
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

module_class = ChatwootSupport
