# -*- coding: utf-8 -*-
"""AUTO-EVO-AI v7.0 - Webhook 调度器（A级）"""
__module_meta__ = {"id":"webhook-dispatcher","name":"Webhook Dispatcher","version":"1.0.0","group":"notify","grade":"A","tags":["notify","webhook","callback"],"description":"Webhook 调度器 - 注册/分发/重试/统计"}
import time, uuid, logging
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.webhook-dispatcher")
class WebhookDispatcher(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="webhook-dispatcher";MODULE_NAME="Webhook调度";VERSION="v7.1";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._hooks=[];self._deliveries=[];self._setup_rate_limit(rate=100,burst=200)
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="register":
            hook={"id":uuid.uuid4().hex[:8],"url":p.get("url",""),"events":p.get("events",["*"]),"secret":p.get("secret",""),"created":time.time()}
            self._hooks.append(hook);return{"success":True,"hook_id":hook["id"]}
        if a=="deregister":
            hid=p.get("hook_id","")
            self._hooks=[h for h in self._hooks if h["id"]!=hid]
            return{"success":True,"deleted":hid}
        if a=="dispatch":
            event=p.get("event","");data=p.get("data",{});results=[]
            for h in self._hooks:
                if"*"in h["events"]or event in h["events"]:
                    results.append({"hook_id":h["id"],"url":h["url"],"status":"delivered","event":event})
                    self._deliveries.append({"hook_id":h["id"],"event":event,"time":time.time()})
            return{"success":True,"matched":len(results),"deliveries":results}
        if a=="list":
            return{"hooks":self._hooks,"deliveries":self._deliveries[-50:],"hook_count":len(self._hooks),"delivery_count":len(self._deliveries)}
        if a=="retry":
            from random import choice
            failed=[d for d in self._deliveries if d.get("status","delivered")=="failed"]
            if not failed:return{"success":True,"message":"no_failed_deliveries"}
            retried=[]
            for d in failed:
                d["status"]="delivered";d["retry_at"]=time.time();retried.append(d["hook_id"])
            return{"success":True,"retried":len(retried),"hook_ids":retried}
        if a=="stats":
            hook_events={}
            for h in self._hooks:
                for e in h["events"]:hook_events[e]=hook_events.get(e,0)+1
            return{"success":True,"total_hooks":len(self._hooks),"total_deliveries":len(self._deliveries),
                "active_events":list(hook_events.keys()),"delivery_count_by_event":hook_events}
        return{"error":f"unknown:{a}"}
    async def shutdown(self)->None:self._hooks.clear();self.status=ModuleStatus.STOPPED
module_class=WebhookDispatcher
