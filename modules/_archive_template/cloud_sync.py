# -*- coding: utf-8 -*-
# STATUS: TEMPLATE - generated skeleton, minimal real logic
"""AUTO-EVO-AI V0.1 - 云同步引擎（A级）

本地目录同步管理器，支持增量备份和恢复"""
__module_meta__ = {"id":"cloud-sync","name":"Cloud Sync","version":"1.0.0","group":"infrastructure","grade":"A",
    "tags":["infrastructure","sync","backup","cloud"],"description":"Directory sync engine with incremental backup"}
import os, time, hashlib, logging, json, shutil
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.cloud-sync")
class CloudSync(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="cloud-sync";MODULE_NAME="云同步引擎";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._syncs:Dict[str,Dict]={}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"syncs":len(self._syncs)})
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _file_hash(self,path:str)->Optional[str]:
        try:
            with open(path,'rb') as f:return hashlib.md5(f.read()).hexdigest()
        except:return None
    def _scan(self,path:str)->Dict[str,str]:
        result={}
        if not os.path.isdir(path):return result
        for root,dirs,files in os.walk(path):
            for f in files:
                fp=os.path.join(root,f)
                h=self._file_hash(fp)
                if h:result[fp]=h
        return result
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            return{"success":True,"syncs":list(self._syncs.keys()),"count":len(self._syncs)}
        if a=="schedule":
            name=p.get("name","daily_backup");interval=p.get("interval",3600);src=p.get("source","");dst=p.get("dest","")
            self._syncs[name]={"source":src,"dest":dst,"interval":interval,"last_sync":0,"enabled":True,"created":time.time()}
            return{"success":True,"sync_name":name,"interval":interval}
        if a=="sync_now":
            name=p.get("name","")
            cfg=self._syncs.get(name)
            if not cfg:return{"success":False,"error":f"sync_not_found:{name}"}
            src=cfg["source"];dst=cfg["dest"]
            if not os.path.isdir(src):return{"success":False,"error":f"source_not_found:{src}"}
            os.makedirs(dst,exist_ok=True)
            src_hash=self._scan(src);dst_hash=self._scan(dst)
            changed=[];added=[];deleted=[]
            for fp,h in src_hash.items():
                rel=os.path.relpath(fp,src)
                target=os.path.join(dst,rel)
                if h!=dst_hash.get(target):changed.append(rel)
            cfg["last_sync"]=time.time()
            return{"success":True,"sync_name":name,"source":src,"dest":dst,"changed":len(changed)}
        if a=="history":
            name=p.get("name","")
            cfg=self._syncs.get(name)
            return{"success":True,"sync_name":name,"entries":[{"last_sync":cfg.get("last_sync",0),"enabled":cfg.get("enabled",False)}]}if cfg else{"success":False,"error":"not_found"}
        if a=="config":
            name=p.get("name","daily_backup")
            cfg=self._syncs.get(name)
            if not cfg:return{"success":True,"available":list(self._syncs.keys())}
            return{"success":True,"config":cfg}
        if a=="register":
            name=p.get("name","");src=p.get("source","");dst=p.get("destination","")
            if not name or not src or not dst:return{"success":False,"error":"name_source_destination_required"}
            if not os.path.isdir(src):return{"success":False,"error":f"source_not_found:{src}"}
            os.makedirs(dst,exist_ok=True)
            self._syncs[name]={"source":src,"destination":dst,"registered":time.time(),"last_sync":0,"files_synced":0}
            return{"success":True,"sync":name,"source":src,"destination":dst}
        if a=="sync":
            name=p.get("name","");dry_run=p.get("dry_run",False)
            sync=self._syncs.get(name)
            if not sync:return{"success":False,"error":f"unknown_sync:{name}"}
            src,sync["last_sync"]=sync["source"],time.time()
            dst=sync["destination"]
            src_files=self._scan(src);dst_files=self._scan(dst)
            to_copy=[f for f in src_files if f not in dst_files or src_files[f]!=dst_files[f]]
            to_remove=[f for f in dst_files if f.replace(dst,src) not in src_files]
            if dry_run:return{"success":True,"to_copy":len(to_copy),"to_remove":len(to_remove),"files":to_copy[:20]}
            copied=0
            for f in to_copy:
                rel=os.path.relpath(f,src);target=os.path.join(dst,rel)
                os.makedirs(os.path.dirname(target),exist_ok=True)
                try:shutil.copy2(f,target);copied+=1
                except Exception as e:logger.warning("sync_copy_error:%s->%s:%s",f,target,e)
            for f in to_remove:
                try:os.remove(f)
                except:pass
            sync["files_synced"]+=copied
            return{"success":True,"synced":copied,"removed":len(to_remove),"total_synced":sync["files_synced"]}
        if a=="list_files":
            name=p.get("name","")
            sync=self._syncs.get(name)
            if not sync:return{"success":False,"error":f"unknown_sync:{name}"}
            files=list(self._scan(sync["source"]).keys())
            return{"success":True,"files":files[:100],"total":len(files)}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self._syncs.clear();self.status=ModuleStatus.STOPPED
module_class=CloudSync
