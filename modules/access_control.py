"""访问控制 - IP黑白名单管理"""
import logging, json, os, time
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger = logging.getLogger("evo.modules.access_control")
_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "access_rules.json")
class AccessControl(EnterpriseModule):
    def __init__(self): self._ready = True; self._rules = self._load()
    def _load(self):
        try:
            if os.path.exists(_DATA_FILE): return json.loads(open(_DATA_FILE,"r",encoding="utf-8").read())
        except: pass
        return {"whitelist":[],"blacklist":[]}
    def check(self, ip):
        if ip in self._rules["blacklist"]: return {"allow":False,"reason":"IP被拉黑"}
        return {"allow":True}
    def status(self): return {"name":"access_control","ready":self._ready,"whitelist":len(self._rules["whitelist"]),"blacklist":len(self._rules["blacklist"])}
    def execute(self, a="", p=None):
        if a=="check": return self.check(p.get("ip","") if p else "")
        return self.status()
    def get_status(self): return self.status()
    def register(self): return {"name":"access_control","desc":"访问控制 - IP黑白名单管理"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "access_control", "ready": getattr(self, "_ready", True),
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

get_status = lambda: AccessControl().get_status()
register = lambda: {"name":"access_control","class":"AccessControl","description":"访问控制 - IP黑白名单管理"}
