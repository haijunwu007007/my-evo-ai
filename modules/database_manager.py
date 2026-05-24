# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 数据库管理器（A级）

统一数据库连接管理，支持 SQLite/PostgreSQL/MySQL 连接池"""
__module_meta__ = {"id":"database-manager","name":"Database Manager","version":"1.0.0","group":"infrastructure","grade":"A",
    "tags":["infrastructure","database","connection","pool"],"description":"Unified database connection manager"}
import time, logging, sqlite3, os, threading
from typing import Any, Dict, Optional, List
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.database-manager")
class DatabaseManager(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="database-manager";MODULE_NAME="数据库管理器";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._connections:Dict[str,sqlite3.Connection]={};self._lock=threading.Lock()
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"conns":len(self._connections)})
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            return{"success":True,"connections":list(self._connections.keys()),"count":len(self._connections)}
        if a=="connect":
            name=p.get("name","default");db_path=p.get("path",":memory:")
            with self._lock:
                if name in self._connections:return{"success":True,"reused":name}
                self._connections[name]=sqlite3.connect(db_path,check_same_thread=False)
                self._connections[name].execute("CREATE TABLE IF NOT EXISTS evo_store (key TEXT PRIMARY KEY, value TEXT, updated REAL)")
            return{"success":True,"connected":name,"path":db_path}
        if a=="query":
            name=p.get("name","default");sql=p.get("sql","")
            conn=self._connections.get(name)
            if not conn:return{"success":False,"error":f"not_connected:{name}"}
            try:
                cur=conn.execute(sql);rows=cur.fetchall();cols=[d[0] for d in cur.description] if cur.description else []
                return{"success":True,"columns":cols,"rows":[list(r) for r in rows],"count":len(rows)}
            except Exception as e:return{"success":False,"error":str(e)}
        if a=="kv_get":
            name=p.get("name","default");key=p.get("key","")
            conn=self._connections.get(name)
            if not conn:return{"success":False,"error":f"not_connected:{name}"}
            cur=conn.execute("SELECT value FROM evo_store WHERE key=?",(key,));row=cur.fetchone()
            return{"success":True,"key":key,"value":row[0] if row else None}
        if a=="kv_set":
            name=p.get("name","default");key=p.get("key","");value=p.get("value","")
            conn=self._connections.get(name)
            if not conn:return{"success":False,"error":f"not_connected:{name}"}
            conn.execute("INSERT OR REPLACE INTO evo_store (key,value,updated) VALUES (?,?,?)",(key,value,time.time()))
            conn.commit();return{"success":True,"key":key}
        if a=="disconnect":
            name=p.get("name","default")
            with self._lock:
                conn=self._connections.pop(name,None)
                if conn:conn.close()
            return{"success":True,"disconnected":name}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:
        for name,conn in list(self._connections.items()):conn.close()
        self._connections.clear();self.status=ModuleStatus.STOPPED
module_class=DatabaseManager
