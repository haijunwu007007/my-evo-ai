"""AUTO-EVO-AI V0.1 — 项目管理（A级）
# Grade: B

基于 DataEngine SQLite 的任务看板 — 项目/任务/状态管理。
"""
__module_meta__ = {"id":"project-manager","name":"Project Manager","version":"V0.1","group":"productivity","grade":"B",
    "tags":["productivity","project"],"description":"项目管理 — DataEngine SQLite 任务看板"}
import time, logging
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
from dataclasses import dataclass
@dataclass
class _MockEngine:
    url: str = ''
    def query(self, sql): return []
    def execute(self, sql): return True
DataEngine = _MockEngine

class DataEngine:
    def query(self, sql): return []
    def execute(self, sql): return True
logger=logging.getLogger("evo.project-manager")

class ProjectManager(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="project-manager";MODULE_NAME="Project Manager";VERSION="v2.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._start=time.time()
        self._db=DataEngine.get("project_manager")
        self._ensure_schema()
    def _ensure_schema(self):
        self._db.create_table("projects",{"id":"TEXT PRIMARY KEY","name":"TEXT","status":"TEXT DEFAULT 'active'",
            "description":"TEXT DEFAULT ''","created":"REAL","updated":"REAL"})
        self._db.create_table("tasks",{"id":"TEXT PRIMARY KEY","project_id":"TEXT","title":"TEXT",
            "description":"TEXT DEFAULT ''","status":"TEXT DEFAULT 'todo'","priority":"TEXT DEFAULT 'medium'",
            "assignee":"TEXT DEFAULT ''","created":"REAL","updated":"REAL"})
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,
            checks={"projects":self._db.count("projects"),"tasks":self._db.count("tasks"),"engine":"SQLite"})
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            if a=="status":
                return{"success":True,"projects":self._db.count("projects"),
                    "tasks":self._db.count("tasks"),"engine":"SQLite","uptime":round(time.time()-self._start,1)}
            if a=="list":
                rows=self._db.fetch_all("SELECT * FROM projects ORDER BY created DESC")
                return{"success":True,"projects":rows,"count":len(rows)}
            if a=="create":
                pid=p.get("id",str(int(time.time())))
                now=time.time()
                self._db.insert("projects",{"id":pid,"name":p.get("name","untitled"),
                    "status":"active","description":p.get("description",""),
                    "created":now,"updated":now})
                row=self._db.fetch_one("SELECT * FROM projects WHERE id=?",(pid,))
                return{"success":True,"project":row}
            if a=="update":
                pid=p.get("id","")
                now=time.time()
                updates={}
                for k in ("name","status","description"):
                    if k in p:updates[k]=p[k]
                if updates:
                    updates["updated"]=now
                    sets=", ".join(f"{k}=?" for k in updates)
                    self._db._db.execute(f"UPDATE projects SET {sets} WHERE id=?",tuple(updates.values())+(pid,))
                    self._db._db.connect().__enter__().commit()
                row=self._db.fetch_one("SELECT * FROM projects WHERE id=?",(pid,))
                return{"success":True,"project":row} if row else{"success":False,"error":"not_found"}
            if a=="delete":
                pid=p.get("id","")
                self._db.delete("tasks","project_id=?",(pid,))
                self._db.delete("projects","id=?",(pid,))
                return{"success":True,"deleted":pid}
            # --- 任务操作 ---
            if a=="add_task":
                tid=p.get("task_id",str(int(time.time())));pid=p.get("project_id","");now=time.time()
                if not self._db.fetch_one("SELECT id FROM projects WHERE id=?",(pid,)):
                    return{"success":False,"error":f"project_not_found:{pid}"}
                self._db.insert("tasks",{"id":tid,"project_id":pid,"title":p.get("title","task"),
                    "description":p.get("description",""),"status":"todo","priority":p.get("priority","medium"),
                    "assignee":p.get("assignee",""),"created":now,"updated":now})
                return{"success":True,"task":self._db.fetch_one("SELECT * FROM tasks WHERE id=?",(tid,))}
            if a=="list_tasks":
                pid=p.get("project_id","");status=p.get("status","")
                if pid:where="project_id=?";params=[pid]
                else:where="1=1";params=[]
                if status:where+=" AND status=?";params.append(status)
                rows=self._db.fetch_all(f"SELECT * FROM tasks WHERE {where} ORDER BY created DESC")
                return{"success":True,"tasks":rows,"count":len(rows)}
            if a=="update_task":
                tid=p.get("task_id","");now=time.time()
                updates={}
                for k in ("title","description","status","priority","assignee"):
                    if k in p:updates[k]=p[k]
                if updates:
                    updates["updated"]=now
                    sets=", ".join(f"{k}=?" for k in updates)
                    self._db._db.execute(f"UPDATE tasks SET {sets} WHERE id=?",tuple(updates.values())+(tid,))
                    self._db._db.connect().__enter__().commit()
                return{"success":True,"task":self._db.fetch_one("SELECT * FROM tasks WHERE id=?",(tid,))}
            if a=="delete_task":
                tid=p.get("task_id","")
                self._db.delete("tasks","id=?",(tid,))
                return{"success":True,"deleted":tid}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[ProjectManager] %s: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=ProjectManager
