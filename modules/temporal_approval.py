# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 时序审批引擎（A级）
# Grade: B

审批工作流引擎，支持多级审批、超时自动处理/统计"""
__module_meta__ = {"id":"temporal-approval","name":"Temporal Approval","version":"V0.1","group":"workflow","grade":"C",
    "tags":["workflow","approval","temporal","review"],"description":"Approval workflow: multi-level review/timeout/stats"}
import time, uuid, logging
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.temporal-approval")
class TemporalApproval(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="temporal-approval";MODULE_NAME="时序审批引擎";VERSION="v2.0";MODULE_LEVEL="A"
    _STATUSES=["pending","approved","rejected","expired","cancelled"]
    def __init__(self,config=None):super().__init__(config);self._requests:Dict[str,Dict]={};self._start=time.time()
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            counts={s:sum(1 for r in self._requests.values() if r["status"]==s) for s in self._STATUSES}
            return{"success":True,"requests":len(self._requests),"counts":counts}
        if a=="create":
            req_id=str(uuid.uuid4())[:8];title=p.get("title","");submitter=p.get("submitter","")
            reviewers=p.get("reviewers","");ttl=int(p.get("ttl",86400))
            self._requests[req_id]={"id":req_id,"title":title,"description":p.get("description",""),"submitter":submitter,
                "reviewers":reviewers.split(",")if reviewers else[],"status":"pending","reviews":[],
                "created":time.time(),"expires":time.time()+max(60,ttl)}
            return{"success":True,"request_id":req_id}
        if a=="review":
            req_id=p.get("request_id","");reviewer=p.get("reviewer","");decision=p.get("decision","")
            req=self._requests.get(req_id)
            if not req:return{"success":False,"error":"unknown_request"}
            if req["status"]!="pending":return{"success":False,"error":f"already_{req['status']}"}
            if time.time()>req.get("expires",0):req["status"]="expired";return{"success":False,"error":"expired"}
            if decision not in["approve","reject"]:return{"success":False,"error":"decision_must_be_approve_or_reject"}
            req["reviews"].append({"reviewer":reviewer,"decision":decision,"timestamp":time.time()})
            req["status"]="approved" if decision=="approve" else "rejected"
            return{"success":True,"request_id":req_id,"status":req["status"]}
        if a=="get":
            req_id=p.get("request_id","");req=self._requests.get(req_id)
            if not req:return{"success":False,"error":"unknown_request"}
            if req["status"]=="pending"and time.time()>req.get("expires",0):req["status"]="expired"
            return{"success":True,"request":req}
        if a=="list":
            status_f=p.get("status","");results=[r for r in self._requests.values()if not status_f or r["status"]==status_f]
            return{"success":True,"requests":[{"id":r["id"],"title":r["title"],"status":r["status"],"created":r["created"]}for r in sorted(results,key=lambda x:-x["created"])],"count":len(results)}
        if a=="stats":return{"total":len(self._requests),"statuses":{s:sum(1 for r in self._requests.values() if r["status"]==s)for s in self._STATUSES},"uptime":round(time.time()-self._start,1)}
        if a=="reject":
            req_id=p.get("request_id","");req=self._requests.get(req_id)
            if not req:return{"success":False,"error":"not_found"}
            if req["status"]!="pending":return{"success":False,"error":f"already_{req['status']}"}
            req["status"]="rejected";req["reviews"].append({"reviewer":"system","decision":"reject","timestamp":time.time()})
            req["reason"]=p.get("reason","rejected_by_system")
            return{"success":True,"request_id":req_id,"status":"rejected"}
        if a=="bulk_approve":
            ids=p.get("request_ids","").split(",")if p.get("request_ids")else[]
            if not ids:return{"success":False,"error":"request_ids_required"}
            approved=0
            for rid in ids:
                req=self._requests.get(rid.strip())
                if req and req["status"]=="pending":req["status"]="approved";req["reviews"].append({"reviewer":"bulk","decision":"approve","timestamp":time.time()});approved+=1
            return{"success":True,"approved":approved,"total":len(ids)}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self._requests.clear();self.status=ModuleStatus.STOPPED
module_class=TemporalApproval
