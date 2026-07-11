"""Grafana监控"""
import logging,httpx
logger=logging.getLogger("evo.modules.grafana_monitor")
class GrafanaMonitor:
 def __init__(s):s._ready=True;s._url="";s._key=""
 def config(s,url,key):s._url=url.rstrip("/");s._key=key;return{"success":True}
 def list_dashboards(s):
  if not s._url:return{"success":False,"error":"未配置"}
  try:r=httpx.get(f"{s._url}/api/search",headers={"Authorization":f"Bearer {s._key}"},timeout=10);return{"success":r.status_code==200,"dashboards":r.json()if r.status_code==200 else[]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"grafana_monitor","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""),p.get("key",""))
  if a=="list_dashboards":return s.list_dashboards()
  return s.status()
get_status=lambda:GrafanaMonitor().status()
register=lambda:{"name":"grafana_monitor","class":"GrafanaMonitor","description":"Grafana监控"}
