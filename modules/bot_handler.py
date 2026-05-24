"""AUTO-EVO-AI V0.1 — 机器人处理桥接（A级）

桥接到通知通道系统，提供统一的通道状态/send/health 入口。
"""
__module_meta__ = {"id":"bot-handler","name":"Bot Handler","version":"1.0.0","group":"notification","grade":"A",
    "tags":["notification","bot"],"description":"机器人处理 — 桥接到通知通道"}
import time, logging
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.bot-handler")

class BotHandler(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="bot-handler";MODULE_NAME="Bot Handler";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._handlers={"zhipu":"glm-4-flash","dingtalk":"webhook","feishu":"webhook"}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            if a=="status":
                return{"success":True,"handlers":list(self._handlers.keys()),"active":len(self._handlers),"module":"bot_handler"}
            if a=="route":
                handler=p.get("handler","");msg=p.get("message","")
                if handler in self._handlers:
                    return{"success":True,"routed":True,"handler":handler,"target":self._handlers[handler],"message_len":len(msg)}
                return{"success":False,"error":f"unknown_handler:{handler}","available":list(self._handlers.keys())}
            if a=="channels":
                return{"success":True,"channels":self._handlers}
            if a=="register":
                name=p.get("name","");target=p.get("target","")
                if name:self._handlers[name]=target
                return{"success":True,"handler":name,"target":target}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[BotHandler] %s: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=BotHandler
