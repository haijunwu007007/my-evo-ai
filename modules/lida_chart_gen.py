"""LIDA图表生成"""
import logging,httpx
logger=logging.getLogger("evo.modules.lida_chart_gen")
class LidaChartGen:
 def __init__(s):s._ready=True;s._url="http://localhost:8000"
 def config(s,url):s._url=url.rstrip("/");return{"success":True}
 def generate(s,goal,summary=""):
  try:r=httpx.post(f"{s._url}/generate",json={"goal":goal,"data_summary":summary or goal},timeout=60);return{"success":r.status_code==200,"charts":r.json()if r.status_code==200 else[]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"lida_chart_gen","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""))
  if a=="generate":return s.generate(p.get("goal",""),p.get("data_summary",""))
  return s.status()
get_status=lambda:LidaChartGen().status()
register=lambda:{"name":"lida_chart_gen","class":"LidaChartGen","description":"LIDA图表生成"}\nmodule_class = LidaChartGen\n