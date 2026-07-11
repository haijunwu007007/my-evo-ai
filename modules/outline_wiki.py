"""Outline知识库"""
import logging,httpx
logger=logging.getLogger("evo.modules.outline_wiki")
class OutlineWiki:
 def __init__(s):s._ready=True;s._url="";s._key=""
 def config(s,url,key):s._url=url.rstrip("/");s._key=key;return{"success":True}
 def search(s,q):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.post(f"{s._url}/api/documents.search",headers={"Authorization":f"Bearer {s._key}"},json={"query":q},timeout=10);return{"success":r.status_code==200,"results":r.json().get("data",[])if r.status_code==200 else[]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"outline_wiki","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("key",""))
  if a=="search":return s.search(p.get("q",""))
  return s.status()
get_status=lambda:OutlineWiki().status()
register=lambda:{"name":"outline_wiki","class":"OutlineWiki","description":"Outline知识库"}\nmodule_class = OutlineWiki\n