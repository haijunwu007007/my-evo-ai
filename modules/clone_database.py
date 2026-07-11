"""数据库克隆"""
import logging,os,subprocess
logger=logging.getLogger("evo.modules.clone_database")
class CloneDatabase:
 def __init__(s):s._ready=True
 def clone_mysql(s,host,user,password,db,target):
  try:r=subprocess.run(["mysqldump","-h",host,"-u",user,f"-p{password}",db,"--no-data"],capture_output=True,text=True,timeout=60);
  except:return{"success":False,"error":"需要mysqldump"}
  if r.returncode!=0:return{"success":False,"error":r.stderr[:200]}
  return{"success":True,"source":db,"target":target}
 def clone_sqlite(s,source,target):
  if not os.path.exists(source):return{"success":False,"error":"源不存在"}
  import shutil;shutil.copy2(source,target);return{"success":True}
 def status(s):return{"name":"clone_database","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="clone_mysql":return s.clone_mysql(p.get("host",""),p.get("user",""),p.get("password",""),p.get("db",""),p.get("target",""))
  if a=="clone_sqlite":return s.clone_sqlite(p.get("source",""),p.get("target",""))
  return s.status()
get_status=lambda:CloneDatabase().status()
register=lambda:{"name":"clone_database","class":"CloneDatabase","description":"数据库克隆"}\nmodule_class = CloneDatabase\n