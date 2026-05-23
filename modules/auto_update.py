"""AUTO-EVO-AI V0.1 — 自动更新桥接（A级）

系统版本检查和更新管理，使用 git 查看版本和拉取更新。
"""
__module_meta__ = {"id":"auto-update","name":"Auto Update","version":"1.0.0","group":"system","grade":"A",
    "tags":["system","update"],"description":"自动更新检查与管理"}
import time, subprocess, logging
from pathlib import Path
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.auto-update")

def _git(*args):
    try:
        r=subprocess.run(["git"]+list(args),capture_output=True,text=True,timeout=30,cwd=Path(__file__).parent.parent)
        return r.returncode==0,r.stdout.strip() if r.stdout else r.stderr.strip()
    except Exception as e:return False,str(e)

class AutoUpdate(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="auto-update";MODULE_NAME="Auto Update";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._last_check=None
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            if a=="status":
                ok,ver=_git("log","-1","--format=%h %s %ci")
                return{"success":True,"version":ver if ok else "N/A","last_check":self._last_check}
            if a=="check_version":
                ok,ver=_git("describe","--tags","--always")
                branch_ok,branch=_git("rev-parse","--abbrev-ref","HEAD")
                return{"success":True,"version":ver if ok else "unknown","branch":branch if branch_ok else "unknown"}
            if a=="check_update":
                ok1,_=_git("fetch","--quiet")
                ok2,behind=_git("rev-list","--count","HEAD..origin/HEAD")
                return{"success":ok1,"has_update":int(behind)>0 if behind.isdigit() else False,"behind":behind}
            if a=="do_update":
                ok1,_=_git("stash")
                ok2,out=_git("pull","--ff-only")
                return{"success":ok2,"output":out,"stash_applied":ok1}
            if a=="last_update":
                self._last_check=time.time()
                return{"success":True,"timestamp":self._last_check}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[AutoUpdate] %s 失败: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=AutoUpdate
