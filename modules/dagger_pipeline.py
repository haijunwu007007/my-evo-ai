"""Dagger CI/CD管线"""
import logging,subprocess
logger=logging.getLogger("evo.modules.dagger_pipeline")
class DaggerPipeline:
 def __init__(s):s._ready=True
 def run(s,module=""):
  try:r=subprocess.run(["dagger","run"]+(["-m",module] if module else[])+["python","-m","pipeline"],capture_output=True,text=True,timeout=300);return{"success":r.returncode==0,"stdout":r.stdout[-500:]}
  except Exception as e:return{"success":False,"error":str(e)}
 def status(s):return{"name":"dagger_pipeline","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="run":return s.run(p.get("module",""))
  return s.status()
get_status=lambda:DaggerPipeline().status()
register=lambda:{"name":"dagger_pipeline","class":"DaggerPipeline","description":"Dagger CI/CD管线"}\nmodule_class = DaggerPipeline\n