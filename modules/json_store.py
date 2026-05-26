# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - JSON 持久化存储（A级）"""
__module_meta__ = {"id":"json-store","name":"JSON Store","version":"V0.1","group":"storage","grade":"A","tags":["storage","json","persistence"],"description":"JSON 持久化存储"}
import time,uuid,logging,json,os,shutil
from typing import Any,Dict
from modules._base.enterprise_module import (EnterpriseModule,ModuleStatus,HealthReport,CircuitBreakerMixin,RateLimiterMixin)
logger=logging.getLogger("evo.json-store")
class JsonStore(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="json-store";MODULE_NAME="JSON存储";VERSION = "V0.1";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._data={};self._store_path=self.config.get("path","data/json_store.json");self._backup_path=self._store_path+".bak"
    def initialize(self)->None:
        try:
            if os.path.exists(self._store_path):
                with open(self._store_path,'r',encoding='utf-8')as f:self._data=json.load(f)
        except:pass
        self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"keys":len(self._data)})
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status");key=p.get("key","")
        if a=="save":key=key or uuid.uuid4().hex[:8];self._data[key]=p.get("value",{});self._flush();return{"success":True,"key":key}
        if a=="load":return{"success":True,"value":self._data.get(key,None)}
        if a=="delete":self._data.pop(key,None);self._flush();return{"success":True}
        if a=="list":return{"keys":list(self._data.keys()),"count":len(self._data)}
        if a=="flush":self._flush();return{"success":True}
        if a=="stats":return{"success":True,"total_keys":len(self._data),"store_path":self._store_path,"exists":os.path.exists(self._store_path),"size_bytes":os.path.getsize(self._store_path)if os.path.exists(self._store_path)else 0}
        if a=="backup":
            shutil.copy2(self._store_path,self._backup_path)if os.path.exists(self._store_path)else None
            return{"success":True,"backup_path":self._backup_path,"restored":os.path.exists(self._backup_path)}
        if a=="restore":
            if os.path.exists(self._backup_path):
                with open(self._backup_path,'r',encoding='utf-8')as f:self._data=json.load(f)
                self._flush();return{"success":True,"restored":len(self._data)}
            return{"success":False,"error":"backup_not_found"}
        if a=="clear":n=len(self._data);self._data.clear();self._flush();return{"success":True,"cleared":n}
        if a=="search_keys":
            q=p.get("query","").lower()
            matches=[k for k in self._data if q in k.lower() or q in str(self._data[k]).lower()]
            return{"success":True,"query":q,"matches":matches,"count":len(matches)}
        return{"error":f"unknown:{a}"}
    def _flush(self):
        try:
            os.makedirs(os.path.dirname(self._store_path)or'.',exist_ok=True)
            with open(self._store_path,'w',encoding='utf-8')as f:json.dump(self._data,f,ensure_ascii=False,default=str)
        except:pass
    async def shutdown(self)->None:self._flush();self.status=ModuleStatus.STOPPED
module_class=JsonStore
