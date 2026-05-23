# STATUS: TEMPLATE - generated skeleton, minimal real logic
"""AUTO-EVO-AI V0.1 — 技能市场桥接（A级）

桥接到 skills/ 目录，查询/管理已安装技能。
"""
__module_meta__ = {"id":"skill-marketplace","name":"Skill Marketplace","version":"1.0.0","group":"skills","grade":"A",
    "tags":["skills","market"],"description":"技能市场 — 查询已安装技能"}
import time, json, logging
from pathlib import Path
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.skill-marketplace")

def _scan_skills(base=None):
    base=base or [".workbuddy/skills","skills"]
    results=[]
    for d in base:
        p=Path(d)
        if p.exists():
            for f in p.glob("*.md"):
                results.append({"name":f.stem,"path":str(f)})
    return results

class SkillMarketplace(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="skill-marketplace";MODULE_NAME="Skill Marketplace";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._start=time.time()
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            if a=="status":
                skills=_scan_skills()
                return{"success":True,"skills":skills,"count":len(skills)}
            if a=="list":
                skills=_scan_skills()
                return{"success":True,"skills":skills,"total":len(skills)}
            if a=="detail":
                name=p.get("name","")
                for d in [".workbuddy/skills","skills"]:
                    f=Path(d)/f"{name}.md"
                    if f.exists():
                        lines=f.read_text(encoding="utf-8").split("\n")[:10]
                        return{"success":True,"name":name,"preview":"\n".join(lines),"lines":len(f.read_text(encoding="utf-8").split("\n"))}
                return{"success":False,"error":f"skill_not_found:{name}"}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[SkillMarket] %s: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=SkillMarketplace
