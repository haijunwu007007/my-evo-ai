# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 防火墙规则引擎（A级）

访问控制规则引擎，支持 IP、路径、方法级别 ACL"""
__module_meta__ = {"id":"firewall-rules","name":"Firewall Rules","version":"1.0.0","group":"security","grade":"A",
    "tags":["security","firewall","acl","access-control"],"description":"Access control rules engine with IP and path ACL"}
import time, uuid, logging, re
from typing import Any, Dict, List
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.firewall-rules")
class FirewallRules(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="firewall-rules";MODULE_NAME="防火墙规则引擎";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._rules:List[Dict]=[];self._whitelist:List[str]=[];self._blacklist:List[str]=[];self._audit_log=[]
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"rules":len(self._rules),"whitelist":len(self._whitelist),"blacklist":len(self._blacklist)})
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _match_ip(self,ip:str,pattern:str)->bool:
        if pattern==ip:return True
        if '*'in pattern:
            pat=re.escape(pattern).replace(r'\*','.*')
            return bool(re.match(f"^{pat}$",ip))
        return False
    def _dispatch(self,p):
        a=p.get("action","status");ts=time.time()
        if a=="status":return{"success":True,"rules":len(self._rules),"whitelist":len(self._whitelist),"blacklist":len(self._blacklist),"audit_entries":len(self._audit_log)}
        if a=="add_rule":
            rid=str(uuid.uuid4())[:8];pattern=p.get("pattern","");action=p.get("action","allow");priority=int(p.get("priority",50))
            if not pattern:return{"success":False,"error":"pattern_required"}
            if action not in["allow","deny"]:return{"success":False,"error":"action_must_be_allow_or_deny"}
            self._rules.append({"id":rid,"pattern":pattern,"action":action,"priority":priority,"created":ts})
            self._rules.sort(key=lambda r:(-r["priority"],r["created"]))
            return{"success":True,"rule_id":rid,"pattern":pattern,"action":action}
        if a=="check":
            ip=p.get("ip","");path=p.get("path","");method=p.get("method","GET")
            for ipb in self._blacklist:
                if self._match_ip(ip,ipb):
                    self._audit_log.append({"ip":ip,"path":path,"action":"deny","reason":"blacklist","time":ts})
                    return{"success":True,"allowed":False,"reason":f"blacklisted:{ipb}","ip":ip,"path":path}
            for ipw in self._whitelist:
                if self._match_ip(ip,ipw):
                    self._audit_log.append({"ip":ip,"path":path,"action":"allow","reason":"whitelist","time":ts})
                    return{"success":True,"allowed":True,"reason":"whitelisted","ip":ip,"path":path}
            for rule in self._rules:
                if re.match(rule["pattern"],path):
                    allowed=rule["action"]=="allow"
                    self._audit_log.append({"ip":ip,"path":path,"action":rule["action"],"reason":"rule_match","rule_id":rule["id"],"time":ts})
                    return{"success":True,"allowed":allowed,"reason":f"rule:{rule['action']}","rule_id":rule["id"]}
            return{"success":True,"allowed":True,"reason":"default_allow"}
        if a=="add_to_list":
            lst=p.get("list","whitelist");ip=p.get("ip","")
            if lst=="whitelist"and ip not in self._whitelist:self._whitelist.append(ip)
            elif lst=="blacklist"and ip not in self._blacklist:self._blacklist.append(ip)
            else:return{"success":False,"error":f"unknown_list:{lst}"}
            return{"success":True,"list":lst,"ip":ip}
        if a=="remove_rule":
            rid=p.get("rule_id","");before=len(self._rules)
            self._rules=[r for r in self._rules if r["id"]!=rid]
            return{"success":True,"removed":len(self._rules)<before}
        if a=="list_rules":return{"success":True,"rules":self._rules}
        if a=="stats":return{"success":True,"total_rules":len(self._rules),"whitelist_count":len(self._whitelist),"blacklist_count":len(self._blacklist),"audit_count":len(self._audit_log),"recent_audit":self._audit_log[-10:]}
        if a=="test_rule":
            ip=p.get("ip","127.0.0.1");path=p.get("path","/")
            r=self._dispatch({"action":"check","ip":ip,"path":path})
            return{"success":True,"test_result":r,"ip":ip,"path":path}
        if a=="batch_import":
            rules=p.get("rules",[])
            if not isinstance(rules,list):return{"success":False,"error":"rules_must_be_list"}
            imported=0
            for rl in rules:
                self._rules.append({"id":str(uuid.uuid4())[:8],"pattern":rl.get("pattern",""),"action":rl.get("action","allow"),"priority":int(rl.get("priority",50)),"created":ts});imported+=1
            return{"success":True,"imported":imported,"total_rules":len(self._rules)}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self._rules.clear();self.status=ModuleStatus.STOPPED
module_class=FirewallRules
