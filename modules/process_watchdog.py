# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 进程看门狗（A级）"""
__module_meta__ = {"id":"process-watchdog","name":"Process Watchdog","version":"V0.1","group":"ops","grade":"A","tags":["ops","watchdog","monitor"],"description":"进程看门狗"}
import time, uuid, logging
from typing import Any, Dict, List
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.process-watchdog")
class ProcessWatchdog(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="process-watchdog";MODULE_NAME="进程看门狗";VERSION = "V0.1";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._targets={};self._alerts=[];self._history=[]
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="watch":
            name=p.get("name","");interval=int(p.get("interval",30));self._targets[name]={"pid":p.get("pid",""),"interval":interval,"healthy":True,"last_heartbeat":time.time()};return{"success":True,"watched":name}
        if a=="unwatch":self._targets.pop(p.get("name",""),None);return{"success":True}
        if a=="heartbeat":
            name=p.get("name","");t=self._targets.get(name);t and t.update({"last_heartbeat":time.time(),"healthy":True});return{"success":True,"acknowledged":True}
        if a=="check":
            name=p.get("name","");t=self._targets.get(name);now=time.time();healthy=t and(now-t.get("last_heartbeat",0))<t.get("interval",30)*2
            if t:t["healthy"]=healthy
            if not healthy:self._alerts.append({"target":name,"at":now,"type":"missed_heartbeat"});self._history.append({"target":name,"action":"alert","time":now})
            return{"success":True,"target":name,"healthy":healthy,"last_heartbeat":t.get("last_heartbeat",0)if t else None}
        if a=="alerts":return{"alerts":self._alerts[-int(p.get("limit",50)):]}
        if a=="targets":return{"success":True,"targets":{k:{"interval":v["interval"],"healthy":v["healthy"],"last_heartbeat":time.strftime("%H:%M:%S",time.localtime(v["last_heartbeat"]))}for k,v in self._targets.items()}}
        if a=="restart":
            name=p.get("name","");t=self._targets.get(name)
            if not t:return{"success":False,"error":"target_not_found"}
            t["last_heartbeat"]=time.time();t["healthy"]=True;t["restarts"]=t.get("restarts",0)+1
            self._history.append({"target":name,"action":"restart","time":time.time()})
            return{"success":True,"restarted":name,"restart_count":t["restarts"]}
        if a=="history":return{"success":True,"history":[{"target":h["target"],"action":h["action"],"time":time.strftime("%H:%M:%S",time.localtime(h["time"]))}for h in self._history[-100:]]}
        if a=="bulk_check":results={n:self._check_target(n,t)for n,t in self._targets.items()};return{"success":True,"results":results,"healthy":sum(1 for r in results.values()if r),"total":len(results)}
        if a=="stats":return{"success":True,"watched":len(self._targets),"alerts":len(self._alerts),"restarts":sum(t.get("restarts",0)for t in self._targets.values()),"healthy":sum(1 for t in self._targets.values()if t["healthy"])}
        return{"error":f"unknown:{a}"}
    def _check_target(self,name,t):now=time.time();return t and(now-t.get("last_heartbeat",0))<t.get("interval",30)*2
    async def shutdown(self)->None:self._targets.clear();self.status=ModuleStatus.STOPPED
module_class=ProcessWatchdog
