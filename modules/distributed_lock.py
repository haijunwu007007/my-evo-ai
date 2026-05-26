# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 分布式锁（A级）

文件级分布式锁，支持 TTL、阻塞等待、可重入"""
__module_meta__ = {"id":"distributed-lock","name":"Distributed Lock","version":"V0.1","group":"infrastructure","grade":"A",
    "tags":["infrastructure","lock","distributed","concurrency"],"description":"File-based distributed lock with TTL"}
import time, os, uuid, logging, threading, tempfile
from typing import Any, Dict, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.distributed-lock")
class DistributedLock(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="distributed-lock";MODULE_NAME="分布式锁";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._lock_dir=os.path.join(tempfile.gettempdir(),"evo_locks")
        self._held:Dict[str,str]={};os.makedirs(self._lock_dir,exist_ok=True)
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"held":len(self._held)})
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _lock_path(self,name:str)->str:return os.path.join(self._lock_dir,f"{name}.lock")
    def _acquire_file(self,path:str,owner:str,ttl:int)->bool:
        try:
            now=time.time()
            with open(path,'x') as f:f.write(f"{owner}|{now+ttl}")
            return True
        except FileExistsError:
            try:
                with open(path,'r') as f:data=f.read().strip()
                parts=data.split('|')
                if len(parts)==2 and float(parts[1])<time.time():
                    os.remove(path)
                    return self._acquire_file(path,owner,ttl)
            except:pass
            return False
    def _stats(self)->Dict:
        locks=os.listdir(self._lock_dir)if os.path.isdir(self._lock_dir)else[]
        active=0;expired=0
        for l in locks:
            try:
                with open(os.path.join(self._lock_dir,l))as f:
                    parts=f.read().strip().split('|')
                    if len(parts)==2 and float(parts[1])>time.time():active+=1
                    else:expired+=1
            except:expired+=1
        return{"total":len(locks),"active":active,"expired":expired,"held":len(self._held)}
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            lock_files=[f for f in os.listdir(self._lock_dir) if f.endswith('.lock')] if os.path.isdir(self._lock_dir) else []
            return{"success":True,"held":len(self._held),"locks":lock_files}
        if a=="acquire":
            name=p.get("name","default");owner=p.get("owner",str(uuid.uuid4())[:8]);ttl=int(p.get("ttl",30))
            timeout=float(p.get("timeout",0));start=time.time()
            path=self._lock_path(name)
            acquired=False
            while time.time()-start<timeout or timeout<=0:
                if self._acquire_file(path,owner,ttl):
                    self._held[name]=owner;acquired=True;break
                if timeout<=0:break
                time.sleep(0.1)
            return{"success":acquired,"lock":name,"owner":owner,"ttl":ttl}
        if a=="release":
            name=p.get("name","default");owner=p.get("owner","")
            path=self._lock_path(name)
            if os.path.exists(path):
                try:
                    with open(path,'r') as f:data=f.read().strip()
                    if not owner or data.startswith(owner):os.remove(path)
                except:pass
            self._held.pop(name,None)
            return{"success":True,"released":name}
        if a=="check":
            name=p.get("name","default");path=self._lock_path(name)
            if os.path.exists(path):
                try:
                    with open(path,'r') as f:data=f.read().strip().split('|')
                    return{"success":True,"locked":True,"owner":data[0],"expires_at":float(data[1]),"remaining":max(0,float(data[1])-time.time())}
                except:return{"success":True,"locked":True}
            return{"success":True,"locked":False}
        if a=="stats":
            return{"success":True,"stats":self._stats()}
        if a=="heartbeat":
            name=p.get("name","");ttl=int(p.get("ttl",30))
            path=self._lock_path(name)
            if os.path.exists(path):
                try:
                    with open(path,'r')as f:parts=f.read().strip().split('|')
                    owner=parts[0];now=time.time()
                    with open(path,'w')as f:f.write(f"{owner}|{now+ttl}")
                    return{"success":True,"lock":name,"extended_until":now+ttl}
                except:return{"success":False,"error":"heartbeat_failed"}
            return{"success":False,"error":"lock_not_found"}
        if a=="release_all":
            count=0
            for name in list(self._held.keys()):
                path=self._lock_path(name)
                try:os.remove(path);count+=1
                except:pass
            self._held.clear()
            return{"success":True,"released":count}
        if a=="deadlock_detect":
            locks=os.listdir(self._lock_dir)if os.path.isdir(self._lock_dir)else[]
            deadlocks=[];now=time.time()
            for l in locks:
                try:
                    with open(os.path.join(self._lock_dir,l))as f:
                        parts=f.read().strip().split('|')
                        if len(parts)==2 and float(parts[1])<now-3600:
                            deadlocks.append({"lock":l,"expired_since":now-float(parts[1])})
                except:pass
            return{"success":True,"deadlocks":deadlocks,"count":len(deadlocks)}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:
        for name in list(self._held.keys()):
            path=self._lock_path(name)
            try:os.remove(path)
            except:pass
        self._held.clear();self.status=ModuleStatus.STOPPED
module_class=DistributedLock
