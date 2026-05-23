"""AUTO-EVO-AI V0.1 — 自主智能体桥接模块（A级）

桥接到 core/autonomous_agent.AutonomousAgent，
暴露核心引擎的 state/start/stop/stats/decisions 控制面。
"""
__module_meta__ = {"id":"autonomous-agent","name":"AutoAgent","version":"1.0.0","group":"ai","grade":"A",
    "tags":["ai","agent","autonomous"],"description":"自主智能体桥接 — 代理 core/autonomous_agent"}
import time, logging
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.autonomous-agent")

# 延迟导入，避免循环依赖
_agent_cache = None
def _get_agent():
    global _agent_cache
    if _agent_cache is None:
        from core.autonomous_agent import get_autonomous_agent
        _agent_cache = get_autonomous_agent()
    return _agent_cache

class AutoAgent(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="autonomous-agent";MODULE_NAME="AutoAgent";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._initialized=False
    def initialize(self)->None:
        self.status=ModuleStatus.RUNNING
        self._initialized=True
        logger.info("[AutoAgent] 桥接就绪")
    def health_check(self)->HealthReport:
        agent=_get_agent()
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,
            checks={"agent_running":agent.is_running if agent else False})
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            agent=_get_agent()
            if a=="status":
                stats=agent.get_stats() if agent else {}
                return{"success":True,"running":agent.is_running if agent else False,
                    "cycle_count":stats.get("cycle_count",0),
                    "interval":stats.get("interval_seconds",1800),
                    "decisions":stats.get("decisions_stats",{})}
            if a=="start":
                import asyncio
                asyncio.create_task(agent.start());
                return{"success":True,"status":"starting"}
            if a=="stop":
                import asyncio
                asyncio.create_task(agent.stop());
                return{"success":True,"status":"stopping"}
            if a=="stats":return{"success":True,**agent.get_stats()}
            if a=="decisions":return{"success":True,"decisions":agent.get_recent_decisions(int(p.get("limit",20)))}
            if a=="cycles":return{"success":True,"cycles":agent.get_recent_cycles(int(p.get("limit",10)))}
            if a=="data_flow_links":return{"success":True,"links":agent.get_data_flow_links()}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[AutoAgent] %s 失败: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:
        self._initialized=False
        self.status=ModuleStatus.STOPPED
module_class=AutoAgent
