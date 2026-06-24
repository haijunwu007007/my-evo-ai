"""AUTO-EVO-AI V0.1 — Loop Library API"""
from fastapi import APIRouter; import time, uuid
router = APIRouter(prefix="/api/v1/loop-library", tags=["loop-library"])
_patterns = {"deploy_verify":{"name":"部署验证循环","category":"工程","steps":[{"name":"build","desc":"编译"},{"name":"deploy","desc":"部署"},{"name":"test","desc":"测试"},{"name":"verify","desc":"验证"},{"name":"release","desc":"发布"}],"tags":["cicd"]},"research_write":{"name":"调研写作循环","category":"内容","steps":[{"name":"collect","desc":"收集"},{"name":"analyze","desc":"分析"},{"name":"draft","desc":"撰稿"},{"name":"review","desc":"审阅"},{"name":"publish","desc":"发布"}],"tags":["research"]},"code_review":{"name":"代码审查循环","category":"工程","steps":[{"name":"checkout","desc":"检出"},{"name":"lint","desc":"静态分析"},{"name":"review","desc":"审查"},{"name":"fix","desc":"修复"},{"name":"verify","desc":"验证"}],"tags":["code"]}}
@router.get("/status")
def status(): cats=list(set(v["category"] for v in _patterns.values())); return {"success":True,"available":True,"patterns":len(_patterns),"categories":cats}
@router.get("/patterns")
def list_patterns(category:str=""): items=[{"name":k,**v} for k,v in _patterns.items() if not category or v.get("category")==category]; return {"success":True,"patterns":items,"total":len(items)}
@router.get("/patterns/{name}")
def get_pattern(name:str): p=_patterns.get(name); return {"success":bool(p),"pattern":({"name":name,**p} if p else None)}
@router.post("/execute")
def execute(name:str="", context:str=""): p=_patterns.get(name); return {"success":bool(p),"execution":(p if p else {"error":"not found"})}
