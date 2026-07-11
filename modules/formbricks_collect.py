"""Formbricks表单收集"""
import logging,httpx
logger=logging.getLogger("evo.modules.formbricks_collect")
class FormbricksCollect:
 def __init__(s):s._ready=True;s._url="";s._key=""
 def config(s,url,key):s._url=url.rstrip("/");s._key=key;return{"success":True}
 def list_surveys(s):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.get(f"{s._url}/api/v1/surveys",headers={"x-api-key":s._key},timeout=10);return{"success":r.status_code==200,"surveys":r.json().get("data",[])if r.status_code==200 else[]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"formbricks_collect","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("key",""))
  if a=="list_surveys":return s.list_surveys()
  return s.status()
get_status=lambda:FormbricksCollect().status()
register=lambda:{"name":"formbricks_collect","class":"FormbricksCollect","description":"Formbricks表单收集"}
module_class = FormbricksCollect
