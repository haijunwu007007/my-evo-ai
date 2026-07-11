"""Perplexica搜索"""
import logging,httpx
logger=logging.getLogger("evo.modules.perplexica_search")
class PerplexicaSearch:
 def __init__(s):s._ready=True;s._url="http://localhost:3001"
 def config(s,url):s._url=url.rstrip("/");return{"success":True}
 def search(s,q):
  try:r=httpx.post(f"{s._url}/api/search",json={"query":q,"focusMode":"webSearch"},timeout=30);return{"success":r.status_code==200,"results":r.json().get("results",[])if r.status_code==200 else[]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"perplexica_search","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""))
  if a=="search":return s.search(p.get("q",""))
  return s.status()
get_status=lambda:PerplexicaSearch().status()
register=lambda:{"name":"perplexica_search","class":"PerplexicaSearch","description":"Perplexica搜索"}\nmodule_class = PerplexicaSearch\n