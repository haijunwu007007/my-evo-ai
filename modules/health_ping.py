# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 健康探测（A级）
# Grade: B

TCP/HTTP 端点健康检查器，支持自定义探测策略/统计/历史"""
__module_meta__ = {"id":"health-ping","name":"Health Ping","version":"V0.1","group":"monitoring","grade":"C",
    "tags":["monitoring","health","ping","tcp","http"],"description":"TCP/HTTP health checker with custom probes, stats, history"}
import time, socket, urllib.request, urllib.parse, logging, json
from typing import Any, Dict, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.health-ping")
class HealthPing(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="health-ping";MODULE_NAME="健康探测";VERSION="v1.1";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._targets:Dict[str,Dict]={};self._history=[]
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _tcp_ping(self,host:str,port:int,timeout:int=5)->dict:
        start=time.time()
        try:
            s=socket.create_connection((host,port),timeout=timeout);s.close()
            return{"success":True,"latency_ms":round((time.time()-start)*1000,1)}
        except Exception as e:return{"success":False,"error":str(e)}
    def _http_ping(self,url:str,timeout:int=10)->dict:
        start=time.time()
        try:
            req=urllib.request.Request(url,method="GET")
            with urllib.request.urlopen(req,timeout=timeout)as resp:
                return{"success":True,"status":resp.status,"latency_ms":round((time.time()-start)*1000,1)}
        except urllib.error.HTTPError as e:
            return{"success":True,"status":e.code,"latency_ms":round((time.time()-start)*1000,1)}
        except Exception as e:return{"success":False,"error":str(e)}
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            return{"success":True,"targets":len(self._targets),"list":[{"name":n,"type":t.get("type",""),"healthy":t.get("last_result",{}).get("success",False) if t.get("last_result") else None} for n,t in self._targets.items()]}
        if a=="ping":
            target=p.get("target","");ping_type=p.get("type","http");timeout=int(p.get("timeout",10))
            r={"http":self._http_ping,"tcp":lambda: self._tcp_ping(*(target.split(":")[:2]+[80]) if ":" in target else (target,80))}[ping_type]()
            self._history.append({"target":target,"type":ping_type,"result":r,"time":time.time()})
            return r
        if a=="register":
            name=p.get("name","");target=p.get("target","");ping_type=p.get("type","http");interval=int(p.get("interval",60))
            if not name or not target:return{"success":False,"error":"name_and_target_required"}
            self._targets[name]={"target":target,"type":ping_type,"interval":max(10,interval),"registered":time.time(),"last_result":None}
            return{"success":True,"registered":name}
        if a=="deregister":
            name=p.get("name","");self._targets.pop(name,None);return{"success":True,"deregistered":name}
        if a=="check_all":
            results=[]
            for name,cfg in self._targets.items():
                if cfg["type"]=="tcp":
                    parts=cfg["target"].split(":");host=parts[0];port=int(parts[1])if len(parts)>1 else 80
                    r=self._tcp_ping(host,port)
                else:r=self._http_ping(cfg["target"])
                cfg["last_result"]=r;results.append({"name":name,"result":r});self._history.append({"target":name,"result":r,"time":time.time()})
            return{"success":True,"results":results,"total":len(results),"healthy":sum(1 for r in results if r["result"].get("success",False))}
        if a=="stats":
            total=len(self._history);healthy=sum(1 for h in self._history if h["result"].get("success",False))
            return{"success":True,"total_pings":total,"healthy_pct":round(healthy/max(1,total)*100,1)if total else "N/A","targets":len(self._targets),"history_size":len(self._history)}
        if a=="history":
            limit=int(p.get("limit",20))
            return{"success":True,"history":[{"target":h["target"],"success":h["result"].get("success",False),"time":h["time"]}for h in self._history[-limit:]],"total":len(self._history)}
        if a=="config":
            name=p.get("name","");interval=p.get("interval",None)
            if name in self._targets and interval:self._targets[name]["interval"]=int(interval)
            return{"success":True}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self._targets.clear();self.status=ModuleStatus.STOPPED
module_class=HealthPing
