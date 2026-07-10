import logging
logger = logging.getLogger("evo.modules.docling_processor")
class DoclingProcessor:
    def __init__(self): self._ready = True
    def status(self): return {"name": "docling_processor", "ready": self._ready}
    def execute(self, action="", params=None):
        if action == "status": return self.status()
        return {"success": False, "error": "unsupported"}
def get_status(): return DoclingProcessor().status()
def register(): return {"name": "docling_processor", "description": "Docling文档分析", "class": "DoclingProcessor"}
