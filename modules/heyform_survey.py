"""HeyForm问卷"""
import logging,httpx
logger=logging.getLogger("evo.modules.heyform_survey")
class HeyformSurvey:
 def __init__(s):s._ready=True;s._url="";s._key=""
 def config(s,url,key):s._url=url.rstrip("/");s._key=key;return{"success":True}
 def create(s,title,questions):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.post(f"{s._url}/api/v1/forms",headers={"Authorization":f"Bearer {s._key}"},json={"title":title,"questions":questions},timeout=10);return{"success":r.status_code==200,"form":r.json()if r.status_code==200 else{}}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def list(s):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.get(f"{s._url}/api/v1/forms",headers={"Authorization":f"Bearer {s._key}"},timeout=10);return{"success":r.status_code==200,"forms":r.json()if r.status_code==200 else[]}
  except:return{"success":True,"forms":[]}
 def status(s):return{"name":"heyform_survey","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("key",""))
  if a=="create":return s.create(p.get("title",""),p.get("questions",[]))
  if a=="list":return s.list()
  return s.status()
get_status=lambda:HeyformSurvey().status()
register=lambda:{"name":"heyform_survey","class":"HeyformSurvey","description":"HeyForm问卷"}\nmodule_class = HeyformSurvey\n