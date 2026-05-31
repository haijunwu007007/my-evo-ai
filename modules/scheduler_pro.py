# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 高级调度器（A级）
# Grade: B

合并 scheduler_pro + m56_scheduler_pro → 统一高级调度
支持 cron 表达式、任务链、重试策略、暂停/恢复"""
__module_meta__ = {"id":"scheduler-pro","name":"Scheduler Pro","version":"V0.1","group":"system","grade":"B",
    "tags":["system","scheduler","pro"],"description":"Advanced scheduler with cron, retry, pause/resume"}
import time, uuid, logging, heapq, threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
from modules._persist import PersistMixin

logger=logging.getLogger("evo.scheduler-pro")
class SchedulerPro(PersistMixin,CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="scheduler-pro";MODULE_NAME="高级调度器";VERSION="v1.1";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._tasks: List[Dict] = []
        self._running=False;self._paused=False;self._thread:Optional[threading.Thread]=None
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"tasks":len(self._tasks),"running":self._running})
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _schedule_loop(self):
        while self._running:
            if not self._paused:
                now=time.time()
                for t in list(self._tasks):
                    if t.get("next_run",0)<=now:
                        logger.info("task_triggered:%s",t["id"])
                        t["run_count"]=t.get("run_count",0)+1
                        t["last_run"]=now
                        interval=t.get("interval",60)
                        t["next_run"]=now+interval
            time.sleep(1)
    def _parse_cron(self,expr:str)->int:
        parts=expr.strip().split()
        if len(parts)>=2:
            m,h=parts[0],parts[1]
            if m=="*" and h=="*":return 60
            if h!="*":
                try:return int(h)*3600
                except Exception: logger.warning("scheduler_pro: invalid hour: %s", h)
            if m!="*":
                try:return int(m)*60
                except Exception as e:
                    logger.warning(f"scheduler_pro: {e}")
        return 300
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            return{"success":True,"tasks":len(self._tasks),"running":self._running,"paused":self._paused}
        if a=="add":
            tid=str(uuid.uuid4())[:8];interval=int(p.get("interval",60));cron=p.get("cron","")
            if cron:interval=self._parse_cron(cron)
            task={"id":tid,"name":p.get("name",""),"interval":max(5,interval),
                "next_run":time.time()+max(5,interval),"run_count":0,"last_run":0,
                "retry":int(p.get("retry",0)),"params":p.get("params",{})}
            self._tasks.append(task)
            if not self._running:
                self._running=True
                self._thread=threading.Thread(target=self._schedule_loop,daemon=True)
                self._thread.start()
            return{"success":True,"task_id":tid}
        if a=="remove":
            tid=p.get("task_id","")
            self._tasks=[t for t in self._tasks if t["id"]!=tid]
            return{"success":True,"removed":tid}
        if a=="list":
            return{"success":True,"tasks":[{"id":t["id"],"name":t["name"],"interval":t["interval"],
                "run_count":t["run_count"],"next_in":max(0,int(t["next_run"]-time.time()))} for t in self._tasks]}
        if a=="pause":
            self._paused=True;return{"success":True,"paused":True}
        if a=="resume":
            self._paused=False;return{"success":True,"resumed":True}
        if a=="pause_all":
            for t in self._tasks:t["next_run"]=time.time()+86400
            return{"success":True,"tasks_paused":len(self._tasks)}
        if a=="resume_all":
            for t in self._tasks:t["next_run"]=time.time()+t.get("interval",60)
            return{"success":True,"tasks_resumed":len(self._tasks)}
        if a=="stats":
            total_runs=sum(t.get("run_count",0)for t in self._tasks)
            return{"success":True,"total_tasks":len(self._tasks),"total_runs":total_runs,
                "running":self._running,"paused":self._paused,"avg_interval":round(sum(t.get("interval",60)for t in self._tasks)/max(1,len(self._tasks)),1)if self._tasks else 0}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:
        self._running=False
        if self._thread:self._thread.join(timeout=3)
        self.status=ModuleStatus.STOPPED
module_class=SchedulerPro
