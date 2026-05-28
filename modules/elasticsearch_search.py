# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - Elasticsearch 搜索（A级）

真实 ES REST API + 内存降级"""
__module_meta__ = {"id":"elasticsearch-search","name":"ES Search","version":"V0.1","group":"network","grade":"A",
    "tags":["network","search","elasticsearch"],"description":"Elasticsearch 搜索 - 索引/文档/搜索/管理"}
import time, uuid, logging
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.es-search")
class ElasticsearchSearch(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="elasticsearch-search";MODULE_NAME="ES搜索";VERSION="V0.1";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._indices:Dict[str,list]={};self._start=time.time()
        self._requests=None;self._marked_as_mock=False
        self._host=(config or {}).get("es_host","http://localhost:9200")
        try:
            import requests as r;self._requests=r
        except ImportError:
            self._marked_as_mock=True
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        if self._requests and not self._marked_as_mock:
            try:
                r=self._requests.get(f"{self._host}/_cluster/health",timeout=3)
                if r.ok:data=r.json();return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,
                    checks={"cluster":data.get("status","unknown"),"nodes":data.get("number_of_nodes",0),"mode":"real"})
            except Exception as e:logger.warning("ES health真实调用失败: %s",e)
        return HealthReport(status=self.status.value,healthy=not self._marked_as_mock,module_id=self.MODULE_ID,
            checks={"indices":len(self._indices),"mode":"mock"})
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _es_request(self,method,path,json_data=None):
        if not self._requests or self._marked_as_mock:return None
        try:
            url=f"{self._host}/{path}"
            r=self._requests.request(method,url,json=json_data,timeout=5)
            return r.json() if r.ok else {"error":r.status_code,"text":r.text}
        except Exception as e:logger.debug("ES %s %s failed: %s",method,path,e);return None
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="create_index":
            idx=p.get("index","default").lower();shards=int(p.get("shards",1));replicas=int(p.get("replicas",0))
            resp=self._es_request("PUT",idx,{"settings":{"index":{"number_of_shards":shards,"number_of_replicas":replicas}}})
            self._indices.setdefault(idx,[]);mode="real" if resp else "mock"
            return{"success":True,"index":idx,"shards":shards,"replicas":replicas,"mode":mode}
        if a=="index_doc":
            idx=p.get("index","default");did=p.get("id",f"doc_{uuid.uuid4().hex[:8]}");body=p.get("body",{})
            resp=self._es_request("POST",f"{idx}/_doc/{did}",body)
            self._indices.setdefault(idx,[]).append({"id":did,"body":body,"timestamp":time.time()})
            mode="real" if resp else "mock"
            return{"success":True,"index":idx,"id":did,"result":(resp or {}).get("result","created"),"mode":mode}
        if a=="search":
            idx=p.get("index","default");q=p.get("query","").lower();size=int(p.get("size",10))
            resp=self._es_request("POST",f"{idx}/_search",{"query":{"query_string":{"query":q}},"size":size})
            if resp:
                hits=resp.get("hits",{});results=[{"id":h.get("_id"),"score":h.get("_score"),"body":h.get("_source",{})} for h in hits.get("hits",[])]
                return{"success":True,"results":results,"total":hits.get("total",{}).get("value",len(results)),"took_ms":resp.get("took",0),"mode":"real"}
            docs=self._indices.get(idx,[]);results=[d for d in docs if any(q in str(v).lower()for v in d["body"].values())]
            return{"success":True,"results":results[:size],"total":len(results),"took_ms":3,"mode":"mock"}
        if a=="delete_index":
            idx=p.get("index","");self._es_request("DELETE",idx)
            self._indices.pop(idx,None);return{"success":True}
        if a=="indices":
            resp=self._es_request("GET","_cat/indices?format=json")
            if resp:
                items={item["index"]:{"docs":int(item.get("docs.count",0)),"status":item.get("status","")} for item in resp}
                return{"success":True,"indices":items,"count":len(items),"mode":"real"}
            return{"success":True,"indices":{k:{"docs":len(v)}for k,v in self._indices.items()},"count":len(self._indices),"mode":"mock"}
        if a=="stats":
            resp=self._es_request("GET","_stats")
            if resp:
                total_docs=sum(s.get("primaries",{}).get("docs",{}).get("count",0) for s in resp.get("indices",{}).values())
                return{"success":True,"indices":len(resp.get("indices",{})),"total_docs":total_docs,"uptime":round(time.time()-self._start,1),"mode":"real"}
            return{"success":True,"indices":len(self._indices),"total_docs":sum(len(v)for v in self._indices.values()),"uptime":round(time.time()-self._start,1),"mode":"mock"}
        if a=="delete_doc":
            idx=p.get("index","");did=p.get("id","");self._es_request("DELETE",f"{idx}/_doc/{did}")
            docs=self._indices.get(idx,[]);self._indices[idx]=[d for d in docs if d["id"]!=did]
            return{"success":True,"deleted":did,"index":idx}
        return{"error":f"unknown:{a}"}
    async def shutdown(self)->None:self._indices.clear();self.status=ModuleStatus.STOPPED
module_class=ElasticsearchSearch
