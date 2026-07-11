"""Matomo分析"""
import logging,httpx
logger=logging.getLogger("evo.modules.matomo_analytics")
class MatomoAnalytics:
 def __init__(s):s._ready=True;s._url="";s._key=""
 def config(s,url,key):s._url=url.rstrip("/");s._key=key;return{"success":True}
 def get_visits(s,period="day",date="today"):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.get(f"{s._url}/index.php",params={"module":"API","method":"VisitsSummary.getVisits","idSite":1,"period":period,"date":date,"format":"json","token_auth":s._key},timeout=10);return{"success":r.status_code==200,"visits":r.json()if r.status_code==200 else{}}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"matomo_analytics","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("key",""))
  if a=="get_visits":return s.get_visits(p.get("period","day"),p.get("date","today"))
  return s.status()
get_status=lambda:MatomoAnalytics().status()
register=lambda:{"name":"matomo_analytics","class":"MatomoAnalytics","description":"Matomo分析"}\nmodule_class = MatomoAnalytics\n