"""访问控制 - IP黑白名单管理"""
import logging, json, os, time
logger = logging.getLogger("evo.modules.access_control")
_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "access_rules.json")
class AccessControl:
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
get_status = lambda: AccessControl().get_status()
register = lambda: {"name":"access_control","class":"AccessControl","description":"访问控制 - IP黑白名单管理"}
