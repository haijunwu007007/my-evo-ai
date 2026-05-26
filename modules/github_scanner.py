# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - GitHub 扫描器（A级）

GitHub Trending 扫描、仓库分析、Stars/Forks 追踪"""
__module_meta__ = {"id":"github-scanner","name":"GitHub Scanner","version":"V0.1","group":"devops","grade":"A",
    "tags":["devops","github","scanner","trending"],"description":"GitHub trending scanner and repository analyzer"}
import time, logging, json, urllib.request, re
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.github-scanner")
class GithubScanner(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="github-scanner";MODULE_NAME="GitHub 扫描器";VERSION="v1.0";MODULE_LEVEL="A"
    _CACHE={};_CACHE_TTL=300
    def __init__(self,config=None):super().__init__(config)
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _fetch_trending(self,language:str="python",since:str="daily")->List[Dict]:
        cache_key=f"{language}_{since}"
        if cache_key in self._CACHE and time.time()-self._CACHE[cache_key]["time"]<self._CACHE_TTL:
            logger.info("trending_cache_hit:%s",cache_key)
            return self._CACHE[cache_key]["data"]
        url="https://github.com/trending"
        if language:url+=f"/{language}"
        url+=f"?since={since}"
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"text/html"})
            with urllib.request.urlopen(req,timeout=30)as resp:
                html=resp.read().decode('utf-8',errors='replace')
        except Exception as e:
            logger.warning("trending_fetch_failed:%s",e)
            return[] if cache_key not in self._CACHE else self._CACHE[cache_key]["data"]
        repos=[]
        for match in re.finditer(r'<h2[^>]*>.*?href="/([^/"]+)/([^/"]+)"[^>]*>.*?</h2>',html,re.DOTALL):
            owner,name=match.group(1),match.group(2)
            desc_match=re.search(r'<p[^>]*class="col-9[^"]*"[^>]*>(.*?)</p>',html[match.end():match.end()+500],re.DOTALL)
            desc=desc_match.group(1).strip()if desc_match else""
            desc=re.sub(r'<[^>]+>','',desc)
            repos.append({"owner":owner,"name":name,"description":desc[:200],"language":language,"since":since})
            if len(repos)>=15:break
        self._CACHE[cache_key]={"data":repos,"time":time.time()}
        return repos
    def _fetch_repo_info(self,owner:str,name:str)->Dict:
        api_url=f"https://api.github.com/repos/{owner}/{name}"
        try:
            req=urllib.request.Request(api_url,headers={"User-Agent":"EvoScanner","Accept":"application/vnd.github.v3+json"})
            with urllib.request.urlopen(req,timeout=15)as resp:
                data=json.loads(resp.read())
                return{"owner":owner,"name":name,"stars":data.get("stargazers_count",0),"forks":data.get("forks_count",0),
                    "description":data.get("description",""),"language":data.get("language",""),"topics":data.get("topics",[]),
                    "updated":data.get("updated_at","")}
        except Exception as e:
            logger.warning("repo_api_failed:%s/%s:%s",owner,name,e)
            return{"owner":owner,"name":name,"error":str(e)}
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":
            return{"success":True,"cached":len(self._CACHE),"fields":["trending","repo_info","search","stars","forks"]}
        if a=="trending":
            language=p.get("language","python");since=p.get("since","daily")
            repos=self._fetch_trending(language,since)
            return{"success":True,"repositories":repos,"count":len(repos),"language":language,"since":since}
        if a=="repo_info":
            owner=p.get("owner","");name=p.get("name","")
            if not owner or not name:return{"success":False,"error":"owner_and_name_required"}
            info=self._fetch_repo_info(owner,name)
            return{"success":True,"repository":info}
        if a=="search":
            query=p.get("query","")
            if not query:return{"success":False,"error":"query_required"}
            api_url=f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&per_page=10"
            try:
                req=urllib.request.Request(api_url,headers={"User-Agent":"EvoScanner","Accept":"application/vnd.github.v3+json"})
                with urllib.request.urlopen(req,timeout=15)as resp:
                    data=json.loads(resp.read())
                    repos=[{"owner":item["owner"]["login"],"name":item["name"],"stars":item.get("stargazers_count",0),
                        "description":item.get("description","")} for item in data.get("items",[])]
                    return{"success":True,"repositories":repos,"total":data.get("total_count",0)}
            except Exception as e:return{"success":False,"error":str(e)}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self._CACHE.clear();self.status=ModuleStatus.STOPPED
module_class=GithubScanner
