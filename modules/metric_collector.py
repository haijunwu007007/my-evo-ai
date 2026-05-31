# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 指标收集器（A级）
# Grade: B

真实 psutil/requests + 内存降级"""
__module_meta__ = {"id":"metric-collector","name":"Metric Collector","version":"V0.1","group":"monitoring","grade":"C",
    "tags":["monitoring","metrics","performance","collector"],"description":"System metrics collector - CPU/memory/disk/network"}
import time, logging, json, threading, socket, os
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
from modules._persist import PersistMixin

logger=logging.getLogger("evo.metric-collector")
class MetricCollector(PersistMixin,CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="metric-collector";MODULE_NAME="指标收集器";VERSION="V0.1";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._history=[];self._lock=threading.Lock();self._psutil=None
        self._marked_as_mock=False;self._collect_interval=int((config or {}).get("interval",30))
        self._max_points=int((config or {}).get("max_points",1000));self._hostname=socket.gethostname()
        try:import psutil as ps;self._psutil=ps;logger.info("psutil可用")
        except ImportError:self._marked_as_mock=True;logger.warning("psutil不可用，回退内存模式")
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,
            checks={"history_points":len(self._history),"mode":"mock" if self._marked_as_mock else "real"})
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _collect_real(self):
        metrics={"timestamp":time.time(),"hostname":self._hostname}
        try:
            metrics["cpu_percent"]=self._psutil.cpu_percent(interval=0.1)
            metrics["cpu_count"]=self._psutil.cpu_count()
            mem=self._psutil.virtual_memory();metrics["memory_percent"]=mem.percent
            metrics["memory_used_gb"]=round(mem.used/(1024**3),2);metrics["memory_total_gb"]=round(mem.total/(1024**3),2)
            disk=self._psutil.disk_usage('/');metrics["disk_percent"]=disk.percent
            metrics["disk_used_gb"]=round(disk.used/(1024**3),2);metrics["disk_total_gb"]=round(disk.total/(1024**3),2)
            net=self._psutil.net_io_counters();metrics["net_sent_mb"]=round(net.bytes_sent/(1024**2),2)
            metrics["net_recv_mb"]=round(net.bytes_recv/(1024**2),2)
        except Exception as e:logger.warning("psutil采集部分失败: %s",e)
        return metrics
    def _collect_mock(self):
        import random
        return{"timestamp":time.time(),"hostname":self._hostname,"cpu_percent":round(random.uniform(10,90),1),
            "cpu_count":os.cpu_count()or 4,"memory_percent":round(random.uniform(30,85),1),
            "memory_used_gb":round(random.uniform(4,16),2),"memory_total_gb":16,"disk_percent":round(random.uniform(20,70),1),
            "disk_used_gb":round(random.uniform(50,200),2),"disk_total_gb":256,
            "net_sent_mb":round(random.uniform(0,100),2),"net_recv_mb":round(random.uniform(0,200),2)}
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            return{"success":True,"history_points":len(self._history),"interval":self._collect_interval,
                "hostname":self._hostname,"mode":"mock" if self._marked_as_mock else "real"}
        if a=="collect":
            metrics=self._collect_real() if self._psutil else self._collect_mock()
            with self._lock:self._history.append(metrics);self._history=self._history[-self._max_points:]
            return{"success":True,"metrics":metrics}
        if a=="query":
            limit=int(p.get("limit",100))
            with self._lock:data=self._history[-limit:]
            return{"success":True,"metrics":data,"count":len(data),"mode":"mock" if self._marked_as_mock else "real"}
        if a=="summary":
            with self._lock:data=self._history[-limit:-1] or self._history
            if not data:return{"success":True,"summary":{},"count":0}
            avg_cpu=sum(m.get("cpu_percent",0)for m in data)/len(data)
            avg_mem=sum(m.get("memory_percent",0)for m in data)/len(data)
            avg_disk=sum(m.get("disk_percent",0)for m in data)/len(data)
            return{"success":True,"summary":{"avg_cpu":round(avg_cpu,1),"avg_memory":round(avg_mem,1),
                "avg_disk":round(avg_disk,1),"points":len(data),"hostname":self._hostname}}
        if a=="reset":
            with self._lock:self._history.clear()
            return{"success":True,"cleared":True}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:
        with self._lock:self._history.clear();self.status=ModuleStatus.STOPPED
module_class=MetricCollector
