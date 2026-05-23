# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 快捷键管理器（A级）

合并 hot_key_detection + hotkey_events → 统一快捷键管理
支持热键注册、事件分发、冲突检测"""
__module_meta__ = {"id":"hotkey-manager","name":"Hotkey Manager","version":"1.0.0","group":"system","grade":"A",
    "tags":["system","hotkey","shortcut"],"description":"Hotkey manager with event dispatch"}
import time, logging
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.hotkey-manager")
class HotkeyManager(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="hotkey-manager";MODULE_NAME="快捷键管理器";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._shortcuts:Dict[str,Dict]={}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":return{"success":True,"shortcuts":len(self._shortcuts),"keys":list(self._shortcuts.keys())}
        if a=="register":
            key=p.get("key","");handler=p.get("handler","");desc=p.get("description","")
            if not key or not handler:return{"success":False,"error":"key_and_handler_required"}
            if key in self._shortcuts:return{"success":False,"error":f"conflict:{key}_already_registered"}
            self._shortcuts[key]={"handler":handler,"description":desc,"registered_at":time.time()}
            return{"success":True,"registered":key}
        if a=="unregister":
            key=p.get("key","")
            self._shortcuts.pop(key,None)
            return{"success":True,"unregistered":key}
        if a=="trigger":
            key=p.get("key","")
            sc=self._shortcuts.get(key)
            if not sc:return{"success":False,"error":f"unknown_shortcut:{key}"}
            logger.info("hotkey_triggered:%s->%s",key,sc["handler"])
            return{"success":True,"key":key,"handler":sc["handler"],"description":sc["description"]}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=HotkeyManager
