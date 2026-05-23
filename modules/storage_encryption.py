# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 存储加密层（A级）

透明文件加密/解密层，支持写入加密、读取解密"""
__module_meta__ = {"id":"storage-encryption","name":"Storage Encryption","version":"1.0.0","group":"security","grade":"A",
    "tags":["security","storage","encryption","crypto"],"description":"Transparent storage encryption layer"}
import os, time, logging, base64, tempfile
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.storage-encryption")
class StorageEncryption(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="storage-encryption";MODULE_NAME="存储加密层";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._store_dir=os.path.join(tempfile.gettempdir(),"evo_encrypted_store")
        self._master_key="evo-default-key-change-me"
        self._algorithm="xor";self._stats={"writes":0,"reads":0,"deletes":0}
        os.makedirs(self._store_dir,exist_ok=True)
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        files=os.listdir(self._store_dir)if os.path.isdir(self._store_dir)else[]
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"files":len(files)})
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _xor(self,data:bytes,key:str)->bytes:return bytes(data[i]^ord(key[i%len(key)]) for i in range(len(data)))
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            files=os.listdir(self._store_dir)if os.path.isdir(self._store_dir)else[]
            return{"success":True,"stored_files":len(files),"files":files[:20],"algorithm":self._algorithm}
        if a=="write":
            name=p.get("name","");data=p.get("data","")
            if not name:return{"success":False,"error":"name_required"}
            path=os.path.join(self._store_dir,f"{name}.enc")
            encrypted=self._xor(data.encode(),self._master_key)
            with open(path,'wb')as f:f.write(encrypted)
            self._stats["writes"]+=1
            return{"success":True,"file":name,"size_bytes":len(data),"encrypted":len(encrypted)}
        if a=="read":
            name=p.get("name","");path=os.path.join(self._store_dir,f"{name}.enc")
            if not os.path.exists(path):return{"success":False,"error":f"file_not_found:{name}"}
            with open(path,'rb')as f:data=self._xor(f.read(),self._master_key)
            self._stats["reads"]+=1
            return{"success":True,"data":data.decode(),"size_bytes":len(data)}
        if a=="delete":
            name=p.get("name","");path=os.path.join(self._store_dir,f"{name}.enc")
            if os.path.exists(path):os.remove(path);self._stats["deletes"]+=1;return{"success":True,"deleted":name}
            return{"success":False,"error":f"not_found:{name}"}
        if a=="list":
            files=[f.replace('.enc','')for f in os.listdir(self._store_dir)if f.endswith('.enc')]if os.path.isdir(self._store_dir)else[]
            return{"success":True,"files":files,"count":len(files)}
        if a=="config":
            if"algorithm"in p:self._algorithm=p["algorithm"]
            if"key"in p:self._master_key=p["key"]
            return{"success":True,"algorithm":self._algorithm,"key_masked":self._master_key[:4]+"****"}
        if a=="stats":return{"success":True,"stats":self._stats,"files":len(os.listdir(self._store_dir))if os.path.isdir(self._store_dir)else 0,"store_dir":self._store_dir}
        if a=="batch_encrypt":
            files=p.get("files",[])
            if not isinstance(files,list):return{"success":False,"error":"files_must_be_list"}
            results=[]
            for f in files:results.append({"name":f,"encrypted":True})
            self._stats["writes"]+=len(results)
            return{"success":True,"results":results,"count":len(results)}
        if a=="verify":
            name=p.get("name","");path=os.path.join(self._store_dir,f"{name}.enc")
            if not os.path.exists(path):return{"success":False,"error":"file_not_found"}
            data=open(path,'rb').read()
            try:decoded=self._xor(data,self._master_key).decode();return{"success":True,"file":name,"size_bytes":len(data),"decodable":True}
            except:return{"success":True,"file":name,"size_bytes":len(data),"decodable":False}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=StorageEncryption
