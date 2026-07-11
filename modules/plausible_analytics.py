"""Plausible分析"""
import logging,httpx
logger=logging.getLogger("evo.modules.plausible_analytics")
class PlausibleAnalytics:
 def __init__(s):s._ready=True;s._url="";s._key="";s._site=""
 def config(s,url,key,site):s._url=url.rstrip("/");s._key=key;s._site=site;return{"success":True}
 def get_stats(s,period="30d"):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.get(f"{s._url}/api/v1/stats/aggregate",headers={"Authorization":f"Bearer {s._key}"},params={"site_id":s._site,"period":period,"metrics":"visitors,pageviews,bounce_rate,visit_duration"},timeout=10);return{"success":r.status_code==200,"stats":r.json().get("results",{})if r.status_code==200 else{}}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"plausible_analytics","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("key",""),p.get("site",""))
  if a=="get_stats":return s.get_stats(p.get("period","30d"))
  return s.status()
get_status=lambda:PlausibleAnalytics().status()
register=lambda:{"name":"plausible_analytics","class":"PlausibleAnalytics","description":"Plausible分析"}
module_class = PlausibleAnalytics
