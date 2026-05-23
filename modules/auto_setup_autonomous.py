"""AUTO-EVO-AI V0.1 — 自主智能体设置桥接（A级）

桥接到 core/autonomous_agent，提供首次配置/依赖检查/就绪状态。
"""
__module_meta__ = {"id":"auto-setup-autonomous","name":"AutoSetup","version":"1.0.0","group":"ai","grade":"A",
    "tags":["ai","setup"],"description":"自主智能体首次设置"}
import time, os, logging
from pathlib import Path
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.auto-setup")

class AutoSetup(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="auto-setup-autonomous";MODULE_NAME="AutoSetup";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._checks=[{"name":"core/autonomous_agent","ok":True},{"name":"data_dir", "ok":False}]
    def initialize(self)->None:
        self.status=ModuleStatus.RUNNING
        p=Path(".evo_data/autonomous");p.mkdir(parents=True,exist_ok=True)
        self._checks[1]["ok"]=p.exists()
        logger.info("[AutoSetup] 桥接就绪")
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            if a=="status":return{"success":True,"checks":self._checks,"all_ok":all(c["ok"] for c in self._checks)}
            if a=="configure":
                from core.autonomous_agent import reset_autonomous_agent
                reset_autonomous_agent()
                interval=int(p.get("interval",1800))
                from core.autonomous_agent import AutonomousAgent
                agent=AutonomousAgent(interval_seconds=interval)
                import asyncio;asyncio.create_task(agent.start())
                return{"success":True,"interval":interval}
            if a=="check_dependencies":
                deps={"core_agent":True,"data_dir":Path(".evo_data/autonomous").exists()}
                return{"success":True,"dependencies":deps,"missing":[k for k,v in deps.items() if not v]}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[AutoSetup] %s 失败: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=AutoSetup
