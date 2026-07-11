"""Semgrep扫描 — 静态代码安全扫描"""
import logging, subprocess, json, os
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger = logging.getLogger('evo.modules.semgrep_scanner')
class SemgrepScanner(EnterpriseModule):
    def __init__(self): self._ready=True
    def scan(self, path, config='auto'):
        if not os.path.exists(path): return {'success':False,'error':'路径不存在'}
        try:
            r=subprocess.run(['semgrep','--config',config,'--json',path],capture_output=True,text=True,timeout=120)
            if r.returncode in (0,1):
                data=json.loads(r.stdout) if r.stdout else {}
                return {'success':True,'results':data.get('results',[]),'count':len(data.get('results',[])),'errors':data.get('errors',[])}
            return {'success':False,'error':r.stderr[:200]}
        except Exception as e: return {'success':False,'error':str(e)}
    def status(self): return {'name':'semgrep_scanner','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='scan': return self.scan(p.get('path',''),p.get('config','auto'))
        return self.status()
get_status=lambda:SemgrepScanner().status()
register=lambda:{'name':'semgrep_scanner','class':'SemgrepScanner','description':'Semgrep安全扫描'}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "semgrep_scanner", "ready": getattr(self, "_ready", True),
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

module_class = SemgrepScanner
