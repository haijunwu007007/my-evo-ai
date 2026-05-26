# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 地理位置管理器（A级）"""
__module_meta__ = {"id":"geo-manager","name":"Geo Manager","version":"V0.1","group":"infrastructure","grade":"A",
    "tags":["infrastructure","geo","location","replication"],"description":"Geographic manager-index/nearest/distance/regions"}
import time, math, logging, json
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.geo-manager")
class GeoManager(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="geo-manager";MODULE_NAME="地理位置管理器";VERSION="v1.1";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._locations:Dict[str,Dict]={};self._regions:Dict[str,Dict]={}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _haversine(self,lat1:float,lon1:float,lat2:float,lon2:float)->float:
        R=6371;dlat=math.radians(lat2-lat1);dlon=math.radians(lon2-lon1)
        a=math.sin(dlat/2)**2+math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
        return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":return{"success":True,"locations":len(self._locations),"regions":len(self._regions)}
        if a=="index":
            name=p.get("name","");lat=float(p.get("lat",0));lon=float(p.get("lon",0));tags=p.get("tags","")
            if not name:return{"success":False,"error":"name_required"}
            self._locations[name]={"lat":lat,"lon":lon,"tags":tags,"indexed":time.time()};return{"success":True,"indexed":name,"lat":lat,"lon":lon}
        if a=="remove":
            name=p.get("name","");self._locations.pop(name,None);return{"success":True,"removed":name}
        if a=="nearest":
            lat=float(p.get("lat",0));lon=float(p.get("lon",0));limit=int(p.get("limit",5))
            distances=[(name,self._haversine(lat,lon,loc["lat"],loc["lon"]))for name,loc in self._locations.items()]
            distances.sort(key=lambda x:x[1])
            nearest=[{"name":n,"distance_km":round(d,2),"lat":self._locations[n]["lat"],"lon":self._locations[n]["lon"]}for n,d in distances[:limit]]
            return{"success":True,"nearest":nearest}
        if a=="distance":
            frm=p.get("from","");to=p.get("to","")
            if frm not in self._locations or to not in self._locations:return{"success":False,"error":"location_not_found"}
            d=self._haversine(self._locations[frm]["lat"],self._locations[frm]["lon"],self._locations[to]["lat"],self._locations[to]["lon"])
            return{"success":True,"from":frm,"to":to,"distance_km":round(d,2)}
        if a=="register_region":
            name=p.get("name","");zones=p.get("zones","")
            if not name:return{"success":False,"error":"name_required"}
            self._regions[name]={"zones":zones,"registered":time.time()};return{"success":True,"region":name}
        if a=="list_regions":return{"success":True,"regions":[{"name":n,"zones":r.get("zones","")}for n,r in self._regions.items()]}
        if a=="stats":return{"success":True,"locations":len(self._locations),"regions":len(self._regions),"avg_distance_km":round(sum(self._haversine(self._locations[list(self._locations.keys())[0]]["lat"]if self._locations else 0,self._locations[list(self._locations.keys())[0]]["lon"]if self._locations else 0,loc["lat"],loc["lon"])for loc in self._locations.values())/max(1,len(self._locations)),2)if len(self._locations)>1 else 0}
        if a=="search":
            q=p.get("query","").lower()
            matches=[{"name":n,**v}for n,v in self._locations.items()if q in n.lower()or q in v.get("tags","").lower()]
            return{"success":True,"results":matches,"count":len(matches)}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=GeoManager
