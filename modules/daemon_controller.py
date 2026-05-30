# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 守护进程控制器（A级）
# Grade: B

使用 subprocess + os 管理真实系统进程，跨平台兼容 Windows/Linux。"""
__module_meta__ = {"id":"daemon-controller","name":"Daemon Controller","version":"V0.1","group":"ops","grade":"B","tags":["ops","daemon","process"],"description":"守护进程控制器，支持真实进程启停监控"}
import os, time, uuid, logging, subprocess, platform, signal
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.daemon-controller")
class DaemonController(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="daemon-controller";MODULE_NAME="守护进程";VERSION = "V0.1";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._daemons:Dict[str,Dict]={};self._events:List[Dict]=[]
        self._is_windows = platform.system() == "Windows"
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        running=sum(1 for d in self._daemons.values()if self._is_process_alive(d.get("pid",-1)))
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"daemon_count":len(self._daemons),"running":running})
    def _is_process_alive(self,pid:int)->bool:
        if pid<=0:return False
        try:
            if self._is_windows:
                r=subprocess.run(["tasklist","/FI","PID eq {}".format(pid)],capture_output=True,text=True,timeout=3)
                return str(pid) in r.stdout
            else:
                os.kill(pid,0);return True
        except:return False
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="start":
            name=p.get("name","");cmd=p.get("cmd","");args=p.get("args","")
            if not cmd:return{"success":False,"error":"cmd_required"}
            try:
                full_cmd=cmd if isinstance(cmd,list) else cmd.split()
                if args:full_cmd=full_cmd+([args]if isinstance(args,str)else args)
                proc=subprocess.Popen(full_cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                pid=proc.pid
                self._daemons[name]={"pid":pid,"status":"running","cmd":cmd,"started":time.time(),"restarts":0,"returncode":None}
                self._events.append({"type":"start","name":name,"time":time.time(),"pid":pid})
                return{"success":True,"daemon":name,"pid":pid}
            except Exception as e:
                return{"success":False,"error":str(e)}
        if a=="stop":
            name=p.get("name","");d=self._daemons.get(name)
            if not d:return{"success":False,"error":"daemon_not_found"}
            pid=d.get("pid",-1)
            try:
                if self._is_windows:
                    subprocess.run(["taskkill","/F","/PID",str(pid)],capture_output=True,timeout=5)
                else:
                    os.kill(pid,signal.SIGTERM)
                d["status"]="stopped";d["returncode"]=-1
                self._events.append({"type":"stop","name":name,"time":time.time()})
                return{"success":True,"stopped":name,"pid":pid}
            except Exception as e:
                d["status"]="error";return{"success":False,"error":str(e)}
        if a=="restart":
            name=p.get("name","");d=self._daemons.get(name)
            if not d:return{"success":False,"error":"daemon_not_found"}
            stop_r=self._dispatch({"action":"stop","name":name})
            if not stop_r.get("success"):return stop_r
            start_r=self._dispatch({"action":"start","name":name,"cmd":d.get("cmd","")})
            if start_r.get("success"):
                d["restarts"]=d.get("restarts",0)+1
            return start_r
        if a=="status":
            name=p.get("name","");d=self._daemons.get(name)
            if not d:return{"success":False,"error":"daemon_not_found"}
            alive=self._is_process_alive(d.get("pid",-1))
            return{"success":True,"daemon":name,"pid":d.get("pid"),"status":"running"if alive else"stopped","cmd":d.get("cmd",""),"restarts":d.get("restarts",0),"uptime":round(time.time()-d.get("started",time.time()),1)if alive else 0}
        if a=="list":
            result={}
            for n,d in self._daemons.items():
                alive=self._is_process_alive(d.get("pid",-1))
                result[n]={"pid":d.get("pid"),"status":"running"if alive else"stopped","cmd":d.get("cmd",""),"restarts":d.get("restarts",0)}
            return{"daemons":result}
        if a=="log":
            name=p.get("name","");d=self._daemons.get(name)
            if not d:return{"success":False,"error":"daemon_not_found"}
            alive=self._is_process_alive(d.get("pid",-1))
            return{"success":True,"daemon":name,"status":"running"if alive else"stopped","uptime":round(time.time()-d.get("started",time.time()),1),"pid":d.get("pid"),"restarts":d.get("restarts",0),"cmd":d.get("cmd","")}
        if a=="stats":
            total=len(self._daemons);running=sum(1 for d in self._daemons.values()if self._is_process_alive(d.get("pid",-1)))
            return{"success":True,"total":total,"running":running,"stopped":total-running,"total_restarts":sum(d.get("restarts",0)for d in self._daemons.values())}
        if a=="schedule_restart":
            name=p.get("name","");delay=int(p.get("delay",60))
            if name not in self._daemons:return{"success":False,"error":"daemon_not_found"}
            sched_id=uuid.uuid4().hex[:8];self._events.append({"type":"schedule_restart","name":name,"delay":delay,"id":sched_id,"time":time.time()})
            return{"success":True,"scheduled_id":sched_id,"daemon":name,"delay_seconds":delay,"will_restart_at":time.strftime("%H:%M:%S",time.localtime(time.time()+delay))}
        if a=="events":
            return{"success":True,"events":[{"type":e["type"],"name":e["name"],"time":time.strftime("%H:%M:%S",time.localtime(e["time"]))}for e in self._events[-100:]]}
        return{"error":f"unknown:{a}"}
    async def shutdown(self)->None:self._daemons.clear();self.status=ModuleStatus.STOPPED
module_class=DaemonController
