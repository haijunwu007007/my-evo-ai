# -*- coding: utf-8 -*-
"""AUTO-EVO-AI v7.0 - 首次运行设置（A级）"""
__module_meta__ = {"id":"first-run-setup","name":"First Run Setup","version":"1.0.0","group":"system","grade":"A","tags":["system","setup","init"],"description":"首次运行设置"}
import time, uuid, logging
from typing import Any, Dict, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin, Result)
logger=logging.getLogger("evo.first-run")
class FirstRunSetup(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="first-run-setup";MODULE_NAME="首次运行设置";VERSION="v7.0";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._items=[{"name":"API Key","done":True},{"name":"Webhook","done":True},{"name":"Cron Jobs","done":False}]
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="checklist":return{"items":self._items,"progress":f"{sum(1 for i in self._items if i['done'])}/{len(self._items)}"}
        if a=="mark_done":n=p.get("name","");next((i for i in self._items if i['name']==n),{}).update({"done":True});return{"success":True}
        if a=="auto_configure":return{"success":True,"cfg":["env","db","webhook"],"skipped":["llm_key"]}
        return{"error":f"unknown:{a}"}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=FirstRunSetup
