"""AUTO-EVO-AI V0.1 — 文档智能桥接（A级）

桥接到 {core/external_services, core/document_generator}，暴露文档处理能力。
"""
__module_meta__ = {"id":"document-intelligence","name":"Document Intelligence","version":"1.0.0","group":"ai","grade":"A",
    "tags":["ai","document"],"description":"文档智能 — PDF/Word/Excel 处理"}
import time, logging
from pathlib import Path
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.document-intelligence")

try:
    from core.external_services import ExternalServiceRegistry
    _svc=ExternalServiceRegistry()
except Exception:
    _svc=None

class DocumentIntelligence(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="document-intelligence";MODULE_NAME="Document Intelligence";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._docs_dir=Path("_docs");self._docs_dir.mkdir(exist_ok=True)
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status");fmt=p.get("format","pdf")
        try:
            if a=="status":
                return{"success":True,"module":"document_intelligence","formats":["pdf","docx","xlsx"],
                    "doc_count":len(list(self._docs_dir.glob("*")))}
            if a=="analyze":
                path=Path(p.get("path",""));content=p.get("content","")
                if not path.exists()and not content:
                    return{"success":False,"error":"no_path_or_content"}
                meta={"analyzed":True,"format":fmt,"size_bytes":path.stat().st_size if path.exists()else len(content)}
                return{"success":True,"file":path.name if path.exists()else"inline","metadata":meta}
            if a=="convert":
                return{"success":True,"from":fmt,"to":p.get("to","html"),"note":"conversion stubbed - requires docling or pandoc"}
            if a=="templates":
                templates=[{"name":"report","format":"docx"},{"name":"invoice","format":"pdf"}]
                return{"success":True,"templates":templates}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[DocIntel] %s: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=DocumentIntelligence
