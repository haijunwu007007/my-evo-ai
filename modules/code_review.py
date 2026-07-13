"""代码审查 - 静态分析检查"""
import logging, re, os
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger = logging.getLogger("evo.modules.code_review")
class CodeReview(EnterpriseModule):
    def __init__(self): self._ready = True
    def review(self, path):
        if not os.path.exists(path): return {"success":False,"error":"文件不存在"}
        text = open(path,"r",encoding="utf-8",errors="replace").read()
        issues = []
        if re.search(r"except\s*:", text): issues.append({"severity":"error","msg":"裸except"})
        if "print(" in text: issues.append({"severity":"warn","msg":"print语句"})
        if "TODO" in text: issues.append({"severity":"info","msg":"TODO标记"})
        return {"success":True,"file":os.path.basename(path),"issues":issues,"count":len(issues)}
    def status(self): return {"name":"code_review","ready":self._ready}
    def execute(self,a="",p=None):
        if a=="review": return self.review(p.get("path","") if p else "")
        return self.status()

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "code_review", "ready": getattr(self, "_ready", True),
         "status": self.status.value if hasattr(self, "status") else "running"}

def health_check(self):
 return HealthReport(status=self.status.value if hasattr(self, "status") else "running",
                    healthy=getattr(self, "_ready", True), module_id=self.MODULE_ID)

def initialize(self):
 self.status = ModuleStatus.RUNNING
 return {"success": True}

def shutdown(self):
 self.status = ModuleStatus.STOPPED
 return {"success": True}

get_status = lambda: CodeReview().status()
register = lambda: {"name":"code_review","class":"CodeReview","description":"代码审查"}

# ── 兼容性导出 — routes_code_review.py 和 slash_commands.py 需要 ──

class _ReviewerStub:
    """代码审查器桩实现"""
    def __init__(self):
        self._ready = True
    def review_commit(self, hash_val="", compare=""):
        return {"success": True, "target": "commit", "hash": hash_val, "compare": compare,
                "issues": [], "summary": "桩实现 — 代码审查引擎未完整加载"}
    def review_branch(self, base="master", head=""):
        return {"success": True, "target": "branch", "base": base, "head": head,
                "issues": [], "summary": "桩实现 — 代码审查引擎未完整加载"}
    def review_working_tree(self, staged=False):
        return {"success": True, "target": "working", "staged": staged,
                "issues": [], "summary": "桩实现 — 代码审查引擎未完整加载"}
    def get_history(self, limit=20): return []
    def get_commit_log(self, limit=20): return []
    def get_diff(self, target="", compare=""): return ""

_reviewer_instance = None
def get_reviewer():
    global _reviewer_instance
    if _reviewer_instance is None:
        _reviewer_instance = _ReviewerStub()
    return _reviewer_instance
