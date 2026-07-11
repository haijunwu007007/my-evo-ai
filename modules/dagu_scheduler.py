"""Dagu调度器"""
import logging,json,os,time
logger=logging.getLogger("evo.modules.dagu_scheduler")
_D=os.path.join(os.path.dirname(__file__),"..","data","dags.json")
class DaguScheduler:
 def __init__(s):s._ready=True;s._dags=s._load()
 def _load(s):
  try:
   if os.path.exists(_D):return json.loads(open(_D,"r",encoding="utf-8").read())
  except:pass
  return{}
 def _save(s):
  os.makedirs(os.path.dirname(_D),exist_ok=True);open(_D,"w",encoding="utf-8").write(json.dumps(s._dags,indent=2))
 def create(s,name,steps):
  did=f"dag_{len(s._dags)+1}";s._dags[did]={"id":did,"name":name,"steps":steps,"created":time.time()};s._save()
  return{"success":True,"dag":s._dags[did]}
 def list(s):return{"success":True,"dags":list(s._dags.values())}
 def status(s):return{"name":"dagu_scheduler","ready":s._ready,"dags":len(s._dags)}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="create":return s.create(p.get("name",""),p.get("steps",[]))
  if a=="list":return s.list()
  return s.status()
get_status=lambda:DaguScheduler().status()
register=lambda:{"name":"dagu_scheduler","class":"DaguScheduler","description":"Dagu调度器"}
