"""Docusaurus文档站点"""
import logging,subprocess,os
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger=logging.getLogger("evo.modules.docusaurus_site")
class DocusaurusSite(EnterpriseModule):
 def __init__(s):s._ready=True
 def build(s,dir):
  if not os.path.exists(dir):return{"success":False,"error":"目录不存在"}
  try:r=subprocess.run(["npx","docusaurus","build"],cwd=dir,capture_output=True,text=True,timeout=120);return{"success":r.returncode==0,"output":r.stdout[-500:]}
  except Exception as e:return{"success":False,"error":str(e)}
 def start(s,dir,port=3000):
  try:subprocess.Popen(["npx","docusaurus","start","--port",str(port)],cwd=dir);return{"success":True,"url":f"http://localhost:{port}"}
  except:return{"success":False,"error":"启动失败"}
 def status(s):return{"name":"docusaurus_site","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="build":return s.build(p.get("dir",""))
  if a=="start":return s.start(p.get("dir",""),p.get("port",3000))
  return s.status()
get_status=lambda:DocusaurusSite().status()
register=lambda:{"name":"docusaurus_site","class":"DocusaurusSite","description":"Docusaurus文档站点"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "docusaurus_site", "ready": getattr(self, "_ready", True),
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

module_class = DocusaurusSite
