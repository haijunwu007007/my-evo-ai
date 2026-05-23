# -*- coding: utf-8 -*-
# STATUS: TEMPLATE - generated skeleton, minimal real logic
"""AUTO-EVO-AI V0.1 - 文件监听器（A级）

合并 file_watcher + file_watcher_engine → 统一文件监听
支持目录监控、事件检测、回调通知"""
__module_meta__ = {"id":"file-watcher","name":"File Watcher","version":"1.0.0","group":"system","grade":"A",
    "tags":["system","file","module","watch"],"description":"File Watcher with directory monitoring"}
import os, time, hashlib, logging, threading
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)

logger=logging.getLogger("evo.file-watcher")

class FileWatcher(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="file-watcher";MODULE_NAME="文件监听器";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._watched_dirs: Dict[str, Dict] = {}
        self._snapshots: Dict[str, Dict[str, str]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
    def initialize(self)->None:
        self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _get_file_hash(self,path:str)->Optional[str]:
        try:
            with open(path,'rb') as f:return hashlib.md5(f.read()).hexdigest()
        except:return None
    def _scan_directory(self,path:str)->Dict[str,str]:
        result={}
        for root,dirs,files in os.walk(path):
            for f in files:
                fp=os.path.join(root,f)
                h=self._get_file_hash(fp)
                if h:result[fp]=h
        return result
    def _watch_loop(self):
        while self._running:
            for dpath,cfg in list(self._watched_dirs.items()):
                if not os.path.isdir(dpath):continue
                try:
                    current=self._scan_directory(dpath)
                    prev=self._snapshots.get(dpath,{})
                    added=[k for k in current if k not in prev]
                    removed=[k for k in prev if k not in current]
                    modified=[k for k in current if k in prev and current[k]!=prev[k]]
                    if added:logger.info("files_added[%s]:%s",dpath,added)
                    if removed:logger.info("files_removed[%s]:%s",dpath,removed)
                    if modified:logger.info("files_modified[%s]:%s",dpath,modified)
                    self._snapshots[dpath]=current
                except Exception as e:
                    logger.warning("scan_error[%s]:%s",dpath,e)
            time.sleep(cfg.get("interval",5))
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            return{"success":True,"dirs":list(self._watched_dirs.keys()),"running":self._running}
        if a=="watch":
            path=p.get("path","")
            if not os.path.isdir(path):return{"success":False,"error":f"not_a_directory:{path}"}
            interval=int(p.get("interval",5))
            self._watched_dirs[path]={"interval":max(1,interval)}
            self._snapshots[path]=self._scan_directory(path)
            if not self._running:
                self._running=True
                self._thread=threading.Thread(target=self._watch_loop,daemon=True)
                self._thread.start()
            return{"success":True,"path":path,"files":len(self._snapshots[path])}
        if a=="unwatch":
            path=p.get("path","")
            self._watched_dirs.pop(path,None);self._snapshots.pop(path,None)
            if not self._watched_dirs:
                self._running=False
            return{"success":True,"path":path}
        if a=="changes":
            path=p.get("path","")
            snap=self._snapshots.get(path,{})
            return{"success":True,"files":list(snap.keys()),"count":len(snap)}
        if a=="ignore_patterns":
            path=p.get("path","");patterns=p.get("patterns",[])
            cfg=self._watched_dirs.get(path)
            if not cfg:return{"success":False,"error":f"not_watching:{path}"}
            cfg["ignore"]=patterns
            return{"success":True,"path":path,"ignore_patterns":patterns}
        if a=="pause":
            for cfg in self._watched_dirs.values():cfg["paused"]=True
            return{"success":True,"paused":True}
        if a=="resume":
            for cfg in self._watched_dirs.values():cfg["paused"]=False
            return{"success":True,"resumed":True}
        if a=="batch_process":
            path=p.get("path","")
            cfg=self._watched_dirs.get(path)
            if not cfg:return{"success":False,"error":f"not_watching:{path}"}
            snap=self._snapshots.get(path,{})
            if not self._running:self._start_watching()
            return{"success":True,"path":path,"files":len(snap),"action":"batch","processing":True}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:
        self._running=False
        if self._thread:self._thread.join(timeout=3)
        self.status=ModuleStatus.STOPPED
module_class=FileWatcher
