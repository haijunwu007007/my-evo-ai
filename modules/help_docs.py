# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 帮助文档引擎（A级）

文档索引、搜索、分类管理"""
__module_meta__ = {"id":"help-docs","name":"Help Docs","version":"V0.1","group":"system","grade":"A",
    "tags":["system","help","docs","search","knowledge"],"description":"Help documentation index and search engine"}
import time, uuid, logging, re
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.help-docs")
class HelpDocs(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="help-docs";MODULE_NAME="帮助文档";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._articles:Dict[str,Dict]={};self._categories:Dict[str,List[str]]={}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            return{"success":True,"articles":len(self._articles),"categories":list(self._categories.keys())}
        if a=="add":
            title=p.get("title","");content=p.get("content","");category=p.get("category","general");tags=p.get("tags","")
            if not title:return{"success":False,"error":"title_required"}
            aid=str(uuid.uuid4())[:8]
            self._articles[aid]={"id":aid,"title":title,"content":content,"category":category,"tags":tags,"added":time.time()}
            self._categories.setdefault(category,[]).append(aid)
            return{"success":True,"article_id":aid,"title":title}
        if a=="get":
            aid=p.get("article_id","")
            art=self._articles.get(aid)
            if not art:return{"success":False,"error":f"unknown_article:{aid}"}
            return{"success":True,"article":art}
        if a=="search":
            q=p.get("query","").lower()
            if not q:return{"success":True,"results":[],"count":0}
            results=[]
            for art in self._articles.values():
                if q in art["title"].lower() or q in art.get("content","").lower() or q in art.get("tags","").lower():
                    results.append({"id":art["id"],"title":art["title"],"category":art.get("category",""),"snippet":art.get("content","")[:150]})
            return{"success":True,"results":results,"count":len(results)}
        if a=="by_category":
            cat=p.get("category","");aids=self._categories.get(cat,[])
            return{"success":True,"category":cat,"articles":[self._articles[a] for a in aids if a in self._articles],"count":len(aids)}
        if a=="remove":
            aid=p.get("article_id","")
            art=self._articles.pop(aid,None)
            if art:
                cat=art.get("category","general")
                if cat in self._categories:self._categories[cat]=[a for a in self._categories[cat] if a!=aid]
            return{"success":True,"removed":bool(art)}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self._articles.clear();self.status=ModuleStatus.STOPPED
module_class=HelpDocs
