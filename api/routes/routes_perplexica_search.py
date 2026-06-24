# coding: utf-8
from fastapi import APIRouter
from pydantic import BaseModel
router = APIRouter(prefix="/api/v1/perplexica-search",tags=["perplexica_search"])
try:
    from modules.perplexica_search import module_class
    _m=module_class()
except Exception as e:
    _m=None
class Req(BaseModel): action:str="status"; params:dict={}
@router.get("/status")
def st(): return _m.get_status() if _m else {"success":False,"error":"no mod"}
@router.post("/execute")
def ex(r:Req):
    if not _m: return {"success":False,"error":"no mod"}
    return _m.execute(r.action,r.params)
