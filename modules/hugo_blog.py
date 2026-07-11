"""Hugo博客"""
import logging,subprocess,os
logger=logging.getLogger("evo.modules.hugo_blog")
class HugoBlog:
 def __init__(s):s._ready=True
 def build(s,dir):
  if not os.path.exists(dir):return{"success":False,"error":"目录不存在"}
  try:r=subprocess.run(["hugo"],cwd=dir,capture_output=True,text=True,timeout=120);return{"success":r.returncode==0,"output":r.stdout[-500:]}
  except Exception as e:return{"success":False,"error":str(e)}
 def status(s):return{"name":"hugo_blog","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="build":return s.build(p.get("dir",""))
  return s.status()
get_status=lambda:HugoBlog().status()
register=lambda:{"name":"hugo_blog","class":"HugoBlog","description":"Hugo博客"}\nmodule_class = HugoBlog\n