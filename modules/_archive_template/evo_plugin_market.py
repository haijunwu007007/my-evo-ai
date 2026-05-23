# STATUS: TEMPLATE - generated skeleton, minimal real logic
"""AUTO-EVO-AI V0.1 — 插件市场桥接（A级）

桥接到 plugins/ 注册中心和已安装插件列表。
"""
__module_meta__ = {"id":"evo-plugin-market","name":"Evo Plugin Market","version":"1.0.0","group":"plugins","grade":"A",
    "tags":["plugins","market"],"description":"插件市场 — 已安装插件列表与注册"}
import time, json, logging
from pathlib import Path
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.evo-plugin-market")

PLUGINS_DIR=Path("plugins/installed")

def _scan_plugins():
    if not PLUGINS_DIR.exists():
        return []
    plugins=[]
    for p in PLUGINS_DIR.iterdir():
        if p.is_dir():
            mf=p/"plugin.json"
            if mf.exists():
                try:
                    data=json.loads(mf.read_text(encoding="utf-8"))
                    plugins.append({"id":p.name,"name":data.get("name",p.name),"version":data.get("version","0.0.0")})
                except Exception:
                    plugins.append({"id":p.name,"name":p.name,"version":"?"})
    return plugins

class EvoPluginMarket(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="evo-plugin-market";MODULE_NAME="Evo Plugin Market";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._start=time.time()
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            if a=="status":
                plugins=_scan_plugins()
                return{"success":True,"plugins":plugins,"count":len(plugins)}
            if a=="list":
                plugins=_scan_plugins()
                return{"success":True,"plugins":plugins,"total":len(plugins)}
            if a=="detail":
                pid=p.get("id","")
                mf=PLUGINS_DIR/pid/"plugin.json"
                if mf.exists():
                    data=json.loads(mf.read_text(encoding="utf-8"))
                    return{"success":True,"plugin":data}
                return{"success":False,"error":f"plugin_not_found:{pid}"}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[PluginMarket] %s: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=EvoPluginMarket
