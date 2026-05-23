"""AUTO-EVO-AI V0.1 — 指南管理器桥接（A级）

桥接到 modules/help_docs 和 frontend 内置指南，提供模块搜索/分类导航。
"""
__module_meta__ = {"id":"guide-manager","name":"Guide Manager","version":"1.0.0","group":"system","grade":"A",
    "tags":["system","guide","help"],"description":"指南管理器 — 用户指南与帮助导航"}
import time, logging, json
from pathlib import Path
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.guide-manager")

FRONTEND_DIR=Path(__file__).parent.parent/"frontend"
DASHBOARD_DIR=FRONTEND_DIR/"dashboard"

class GuideManager(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="guide-manager";MODULE_NAME="Guide Manager";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config)
        self._guides=[{"id":"getting_started","name":"快速开始","path":"/guide/start"},
                       {"id":"modules","name":"模块使用","path":"/guide/modules"},
                       {"id":"api","name":"API 文档","path":"/docs"}]
    def initialize(self)->None:self.status=ModuleStatus.RUNNING;logger.info("[GuideManager] 桥接就绪")
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            if a=="status":
                return{"success":True,"guides":len(self._guides),"module":"guide_manager","status":"running"}
            if a=="list_guides":
                return{"success":True,"guides":self._guides,"count":len(self._guides)}
            if a=="search_guides":
                q=p.get("query","").lower()
                if not q:return{"success":True,"results":[],"query":q}
                results=[g for g in self._guides if q in g["name"].lower()or q in g["id"].lower()]
                return{"success":True,"results":results,"count":len(results),"query":q}
            if a=="get_help":
                topic=p.get("topic","")
                from modules.help_docs import HelpDocs
                h=HelpDocs();loop=None
                try:
                    import asyncio
                    loop=asyncio.new_event_loop()
                    r=loop.run_until_complete(h.execute("get_help",{"topic":topic}))
                    return{"success":True,"topic":topic,"content":r.data if hasattr(r,"data")else str(r)}
                except ImportError:
                    return{"success":False,"error":"help_docs_unavailable"}
                finally:
                    if loop:loop.close()
            if a=="dashboard_path":
                d=DASHBOARD_DIR
                has_index=(d/"index.html").exists() if d.exists() else False
                return{"success":True,"dashboard_path":str(d)if d.exists()else "N/A","has_index":has_index}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[GuideManager] %s 失败: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=GuideManager
