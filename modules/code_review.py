"""代码审查 - 静态分析检查"""
import logging, re, os
logger = logging.getLogger("evo.modules.code_review")
class CodeReview:
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
get_status = lambda: CodeReview().status()
register = lambda: {"name":"code_review","class":"CodeReview","description":"代码审查"}
