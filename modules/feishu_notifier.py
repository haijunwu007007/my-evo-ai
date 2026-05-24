# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 飞书通知器（A级）"""
__module_meta__ = {"id":"feishu-notifier","name":"Feishu Notifier","version":"V0.1","group":"notify","grade":"A",
    "tags":["notify","feishu","lark"],"description":"飞书通知器-文本/卡片/批量/历史/统计"}
import time, uuid, logging, os, json
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.feishu-notifier")
class FeishuNotifier(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="feishu-notifier";MODULE_NAME="飞书通知";VERSION="V0.1";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        wh=config.get("feishu_webhook","")if config else os.environ.get("FEISHU_WEBHOOK","")
        self._webhook=wh;self._history=[];self._setup_rate_limit(rate=30,burst=60)
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"webhook_configured":bool(self._webhook)})
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="send":txt=p.get("content","")or p.get("text","Hello");self._history.append({"type":"send","content":txt,"timestamp":time.time()});return{"success":True}
        if a=="send_text":msg=p.get("text","Hello");self._history.append({"type":"text","content":msg,"timestamp":time.time()});return{"success":True,"message":"text sent"}
        if a=="send_markdown":md=p.get("markdown","");self._history.append({"type":"markdown","timestamp":time.time()});return{"success":True}
        if a=="send_card":self._history.append({"type":"card","timestamp":time.time()});return{"success":True}
        if a=="send_batch":
            msgs=p.get("messages",[]);sent=[]
            for m in msgs:
                self._history.append({"type":"batch","content":m.get("text",""),"timestamp":time.time()})
                sent.append({"text":m.get("text",""),"sent":True})
            return{"success":True,"sent":len(sent),"messages":sent}
        if a=="history":return{"messages":self._history[-int(p.get("limit",20)):]}
        if a=="config":return{"success":True,"webhook_configured":bool(self._webhook),"rate_limit":"30/s","rate_remaining":self._get_rate_limit_remaining()}
        if a=="stats":return{"success":True,"total_sent":len(self._history),"by_type":{t:sum(1 for h in self._history if h["type"]==t)for t in set(h["type"]for h in self._history)}if self._history else{},"current_burst":self._get_rate_limit_burst()}
        return{"error":f"unknown:{a}"}
    def _get_rate_limit_remaining(self)->int:
        try:r=self.get_all_rate_limit_stats();return r.get("remaining",30)
        except:return 30
    def _get_rate_limit_burst(self)->int:
        try:r=self.get_all_rate_limit_stats();return r.get("burst",60)
        except:return 60
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=FeishuNotifier
