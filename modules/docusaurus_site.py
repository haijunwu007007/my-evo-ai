"""Docusaurus文档站点"""
import logging,subprocess,os
logger=logging.getLogger("evo.modules.docusaurus_site")
class DocusaurusSite:
 def __init__(s):s._ready=True
 def build(s,dir):
  if not os.path.exists(dir):return{"success":False,"error":"目录不存在"}
  try:r=subprocess.run(["npx","docusaurus","build"],cwd=dir,capture_output=True,text=True,timeout=120);return{"success":r.returncode==0,"output":r.stdout[-500:]}
  except Exception as e:return{"success":False,"error":str(e)}
 def start(s,dir,port=3000):
  try:subprocess.Popen(["npx","docusaurus","start","--port",str(port)],cwd=dir);return{"success":True,"url":f"http://localhost:{port}"}
  except:return{"success":False,"error":"启动失败"}
 def status(s):return{"name":"docusaurus_site","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="build":return s.build(p.get("dir",""))
  if a=="start":return s.start(p.get("dir",""),p.get("port",3000))
  return s.status()
get_status=lambda:DocusaurusSite().status()
register=lambda:{"name":"docusaurus_site","class":"DocusaurusSite","description":"Docusaurus文档站点"}
module_class = DocusaurusSite
