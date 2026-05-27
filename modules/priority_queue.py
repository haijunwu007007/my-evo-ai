# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 优先级队列（A级）

基于堆的优先级任务队列，支持优先级分级和延迟消费"""
__module_meta__ = {"id":"priority-queue","name":"Priority Queue","version":"V0.1","group":"infrastructure","grade":"A",
    "tags":["infrastructure","queue","priority","scheduling"],"description":"Priority queue with heap-based scheduling"}
import time, uuid, logging, heapq
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.priority-queue")
class PriorityQueue(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="priority-queue";MODULE_NAME="优先级队列";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._heap=[];self._counter=0;self._items:Dict[str,Dict]={}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"size":len(self._heap)})
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            return{"success":True,"size":len(self._heap),"items":len(self._items)}
        if a=="push":
            item_id=str(uuid.uuid4())[:8];data=p.get("data",{});priority=int(p.get("priority",5))
            delay=float(p.get("delay",0))
            scheduled=time.time()+max(0,delay)
            entry=(priority,scheduled,self._counter,item_id,data)
            heapq.heappush(self._heap,entry);self._counter+=1
            self._items[item_id]={"priority":priority,"scheduled":scheduled,"data":data,"pushed":time.time()}
            return{"success":True,"item_id":item_id,"position":len(self._heap)}
        if a=="pop":
            while self._heap:
                priority,scheduled,counter,item_id,data=self._heap[0]
                if scheduled<=time.time():
                    heapq.heappop(self._heap);self._items.pop(item_id,None)
                    return{"success":True,"item_id":item_id,"data":data,"priority":priority}
                break
            return{"success":True,"item_id":None,"note":"queue_empty_or_not_yet_ready"}
        if a=="peek":
            if not self._heap:return{"success":True,"item_id":None,"note":"queue_empty"}
            priority,scheduled,counter,item_id,data=self._heap[0]
            return{"success":True,"item_id":item_id,"priority":priority,"scheduled_in":max(0,round(scheduled-time.time(),1))}
        if a=="size":
            return{"success":True,"size":len(self._heap),"waiting":len([e for e in self._heap if e[1]<=time.time()])}
        if a=="clear":
            n=len(self._heap);self._heap.clear();self._items.clear();self._counter=0
            return{"success":True,"cleared":n}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self._heap.clear();self._items.clear();self.status=ModuleStatus.STOPPED
module_class=PriorityQueue
