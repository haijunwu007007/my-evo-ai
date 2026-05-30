# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - MongoDB NoSQL 存储（A级）
# Grade: B

真实 MongoDB (pymongo) + 内存降级"""
__module_meta__ = {"id":"mongodb-nosql","name":"MongoDB NoSQL","version":"V0.1","group":"infrastructure","grade":"B",
    "tags":["infrastructure","database","nosql","mongodb","document"],"description":"MongoDB-style document store engine"}
import time, uuid, logging, json, copy
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.mongodb-nosql")
class MongoDBNoSQL(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="mongodb-nosql";MODULE_NAME="MongoDB 文档存储";VERSION="V0.1";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._collections:Dict[str,List[Dict]]={}
        self._mongo=None;self._db=None;self._marked_as_mock=False
        self._uri=(config or {}).get("mongo_uri","mongodb://localhost:27017")
        self._db_name=(config or {}).get("mongo_db","evo_ai")
        try:
            import pymongo as pm;self._mongo=pm
            self._client=pm.MongoClient(self._uri,serverSelectionTimeoutMS=2000)
            self._client.admin.command('ping')
            self._db=self._client[self._db_name];logger.info("MongoDB连接成功: %s/%s",self._uri,self._db_name)
        except ImportError:logger.warning("pymongo不可用，回退内存模式");self._marked_as_mock=True
        except Exception as e:logger.warning("MongoDB连接失败(%s)，回退内存模式",e);self._marked_as_mock=True
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        if not self._marked_as_mock:
            try:
                self._client.admin.command('ping');return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"collections":len(self._db.list_collection_names()),"mode":"real"})
            except:pass
        return HealthReport(status=self.status.value,healthy=not self._marked_as_mock,module_id=self.MODULE_ID,checks={"collections":len(self._collections),"mode":"mock"})
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status");col=p.get("collection","default")
        if a=="status":
            if not self._marked_as_mock:
                try:names=self._db.list_collection_names();return{"success":True,"collections":names,"docs":sum(self._db[c].count_documents({})for c in names),"mode":"real"}
                except:pass
            return{"success":True,"collections":list(self._collections.keys()),"docs":sum(len(docs)for docs in self._collections.values()),"mode":"mock"}
        if a=="insert":
            doc=p.get("document",{})
            if not self._marked_as_mock:
                try:r=self._db[col].insert_one(doc);return{"success":True,"_id":str(r.inserted_id),"collection":col,"mode":"real"}
                except Exception as e:logger.warning("Mongo insert失败: %s",e)
            if "_id" not in doc:doc["_id"]=str(uuid.uuid4())[:8]
            doc["_created"]=time.time()
            if col not in self._collections:self._collections[col]=[]
            self._collections[col].append(copy.deepcopy(doc));return{"success":True,"_id":doc["_id"],"collection":col,"mode":"mock"}
        if a=="find":
            query=p.get("query",{});limit=int(p.get("limit",100))
            if not self._marked_as_mock:
                try:docs=list(self._db[col].find(query).limit(limit));return{"success":True,"documents":[dict(d)for d in docs],"count":len(docs),"mode":"real"}
                except:pass
            docs=self._collections.get(col,[]);results=copy.deepcopy([d for d in docs if all(d.get(k)==v for k,v in query.items())][:limit])
            return{"success":True,"documents":results,"count":len(results),"mode":"mock"}
        if a=="update":
            query=p.get("query",{});update=p.get("update",{});upsert=p.get("upsert",False)
            if not self._marked_as_mock:
                try:r=self._db[col].update_many(query,{"$set":update});return{"success":True,"updated":r.modified_count,"collection":col,"mode":"real"}
                except:pass
            docs=self._collections.get(col,[]);updated=0
            for d in docs:
                if all(d.get(k)==v for k,v in query.items()):d.update(update);d["_updated"]=time.time();updated+=1
            return{"success":True,"updated":updated,"collection":col,"mode":"mock"}
        if a=="delete":
            query=p.get("query",{})
            if not self._marked_as_mock:
                try:r=self._db[col].delete_many(query);return{"success":True,"deleted":r.deleted_count,"mode":"real"}
                except:pass
            docs=self._collections.get(col,[]);before=len(docs)
            self._collections[col]=[d for d in docs if not all(d.get(k)==v for k,v in query.items())]
            return{"success":True,"deleted":before-len(self._collections[col]),"mode":"mock"}
        if a=="count":
            if not self._marked_as_mock:
                try:return{"success":True,"count":self._db[col].count_documents({}),"collection":col,"mode":"real"}
                except:pass
            return{"success":True,"count":len(self._collections.get(col,[])),"collection":col,"mode":"mock"}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:
        if not self._marked_as_mock:
            try:self._client.close()
            except:pass
        self._collections.clear();self.status=ModuleStatus.STOPPED
module_class=MongoDBNoSQL
