# -*- coding: utf-8 -*-
"""AUTO-EVO-AI v7.0 - 通用限流器（A级）"""
__module_meta__ = {"id":"rate-limiter-mod","name":"Rate Limiter","version":"1.0.0","group":"system","grade":"A","tags":["system","rate-limit","throttle"],"description":"通用限流器（多策略:令牌桶/滑动窗口/配置管理）"}
import time, uuid, logging, threading
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.rate-limiter-mod")
class RateLimiter(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="rate-limiter-mod";MODULE_NAME="通用限流器";VERSION="v7.1";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._buckets:Dict[str,float]={};self._windows:Dict[str,list]={};self._lock=threading.Lock();self._configs:Dict[str,dict]={}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="token_bucket":
            key=p.get("key","default");rate=float(p.get("rate",10));burst=int(p.get("burst",20))
            with self._lock:
                now=time.time();last=self._buckets.get(f"{key}_last",now);tokens=self._buckets.get(f"{key}_tokens",burst)
                tokens=min(burst,tokens+(now-last)*rate);allowed=tokens>=1
                if allowed:self._buckets[f"{key}_tokens"]=tokens-1;self._buckets[f"{key}_last"]=now
            return{"success":True,"key":key,"allowed":allowed,"tokens_remaining":round(tokens-1 if allowed else tokens,2)}
        if a=="sliding_window":
            key=p.get("key","default");limit=int(p.get("limit",100));window=int(p.get("window",60))
            with self._lock:
                now=time.time();self._windows.setdefault(key,[]);self._windows[key]=[t for t in self._windows[key]if now-t<window]
                if len(self._windows[key])<limit:self._windows[key].append(now);return{"success":True,"key":key,"allowed":True,"remaining":limit-len(self._windows[key])}
            return{"success":True,"key":key,"allowed":False,"remaining":0}
        if a=="config":
            key=p.get("key","default");r=float(p.get("rate",10));b=int(p.get("burst",20));w=int(p.get("window",60));l=int(p.get("limit",100))
            self._configs[key]={"rate":r,"burst":b,"window":w,"limit":l,"method":p.get("method","token_bucket")};return{"success":True,"key":key,"config":self._configs[key]}
        if a=="config_list":return{"success":True,"configs":self._configs}
        if a=="clear":
            key=p.get("key","")
            with self._lock:
                if key:self._buckets={k:v for k,v in self._buckets.items() if not k.startswith(f"{key}_")};self._windows.pop(key,None)
                else:self._buckets.clear();self._windows.clear()
            return{"success":True,"cleared":True}
        if a=="blocklist":
            return{"success":True,"keys":list(set(k.rsplit("_",1)[0] for k in self._buckets if k.endswith("_last"))), "total_buckets":len(self._buckets)//2,"windows":sum(len(v)for v in self._windows.values())}
        if a=="stats":return{"buckets":len(self._buckets)//2,"windows":{k:len(v)for k,v in self._windows.items()},
            "configs":len(self._configs),"methods":["token_bucket","sliding_window"]}
        return{"error":f"unknown:{a}"}
    async def shutdown(self)->None:self._buckets.clear();self._windows.clear();self.status=ModuleStatus.STOPPED
module_class=RateLimiter
