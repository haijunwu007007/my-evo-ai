"""代码审查 - 静态分析检查"""
import logging, re, os
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger = logging.getLogger("evo.modules.code_review")
class CodeReview(EnterpriseModule):
    def __init__(self): self._ready = True
    def review(self, path):
        if not os.path.exists(path): return {"success":False,"error":"文件不存在"}
        text = open(path,"r",encoding="utf-8",errors="replace").read()
        issues = []
        if re.search(r"except\s*:", text): issues.append({"severity":"error","msg":"裸except"})
        if "print(" in text: issues.append({"severity":"warn","msg":"print语句"})
        if "TODO" in text: issues.append({"severity":"info","msg":"TODO标记"})
        return {"success":True,"file":os.path.basename(path),"issues":issues,"count":len(issues)}
    def status(self): return {"name":"code_review","ready":self._ready}
    def execute(self,a="",p=None):
        if a=="review": return self.review(p.get("path","") if p else "")
        return self.status()

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "code_review", "ready": getattr(self, "_ready", True),
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

get_status = lambda: CodeReview().status()
register = lambda: {"name":"code_review","class":"CodeReview","description":"代码审查"}
