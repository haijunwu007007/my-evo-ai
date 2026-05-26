# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 发布订阅（A级）"""
__module_meta__ = {"id":"pub-sub","name":"Pub/Sub","version":"V0.1","group":"notify","grade":"A","tags":["notify","pubsub","messaging"],"description":"发布订阅"}
import time,uuid,logging
from typing import Any,Dict,List
from modules._base.enterprise_module import (EnterpriseModule,ModuleStatus,HealthReport,CircuitBreakerMixin,RateLimiterMixin)
logger=logging.getLogger("evo.pub-sub")
class PubSub(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="pub-sub";MODULE_NAME="发布订阅";VERSION = "V0.1";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._topics:Dict[str,List[Dict]]={};self._messages=[];self._stats={"published":0,"subscribed":0,"unsubscribed":0}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"topics":len(self._topics),"messages":len(self._messages)})
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="create_topic":t=p.get("topic","default");self._topics.setdefault(t,[]);return{"success":True,"topic":t}
        if a=="publish":
            t=p.get("topic","default");msg={"id":uuid.uuid4().hex[:8],"data":p.get("data",{}),"timestamp":time.time()};self._topics.setdefault(t,[]);self._messages.append(msg);self._stats["published"]+=1
            for sub in self._topics.get(t,[]):
                try:cb=sub.get("callback");cb and cb(msg)
                except:pass
            return{"success":True,"topic":t,"message_id":msg["id"]}
        if a=="subscribe":
            t=p.get("topic","");sid=uuid.uuid4().hex[:8];self._topics.setdefault(t,[]).append({"id":sid,"callback":p.get("callback",""),"created":time.time()});self._stats["subscribed"]+=1;return{"success":True,"subscription_id":sid}
        if a=="unsubscribe":
            t=p.get("topic","");sid=p.get("subscription_id","");self._topics[t]=[s for s in self._topics.get(t,[])if s["id"]!=sid];self._stats["unsubscribed"]+=1;return{"success":True}
        if a=="list":return{"topics":{t:len(subs)for t,subs in self._topics.items()},"total_messages":len(self._messages)}
        if a=="stats":return{"success":True,"stats":self._stats,"topics":len(self._topics),"active_subscriptions":sum(len(s)for s in self._topics.values()),"messages_total":len(self._messages)}
        if a=="publish_batch":
            t=p.get("topic","default");events=p.get("events",[])
            if not isinstance(events,list):return{"success":False,"error":"events_must_be_list"}
            ids=[]
            for ev in events:
                msg={"id":uuid.uuid4().hex[:8],"data":ev,"timestamp":time.time()}
                self._messages.append(msg);ids.append(msg["id"]);self._stats["published"]+=1
            return{"success":True,"topic":t,"published":len(ids),"message_ids":ids}
        if a=="unsub_all":
            t=p.get("topic","")
            if t:self._topics.pop(t,None)
            else:self._topics.clear()
            return{"success":True,"cleared":True}
        return{"error":f"unknown:{a}"}
    async def shutdown(self)->None:self._topics.clear();self._messages.clear();self.status=ModuleStatus.STOPPED
module_class=PubSub
