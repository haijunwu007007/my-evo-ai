"""E2B沙箱"""
import logging,httpx
logger=logging.getLogger("evo.modules.e2b_sandbox")
class E2BSandbox:
 def __init__(s):s._ready=True;s._key=""
 def config(s,key):s._key=key;return{"success":True}
 def run_code(s,code,lang="python"):
  if not s._key:return{"success":False,"error":"未配置"}
  try:r=httpx.post("https://api.e2b.dev/v1/sandbox/code",headers={"Authorization":f"Bearer {s._key}"},json={"language":lang,"code":code},timeout=30);return{"success":r.status_code==200,"result":r.json().get("stdout","")if r.status_code==200 else r.text[:200]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"e2b_sandbox","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("api_key",""))
  if a=="run_code":return s.run_code(p.get("code",""),p.get("lang","python"))
  return s.status()
get_status=lambda:E2BSandbox().status()
register=lambda:{"name":"e2b_sandbox","class":"E2BSandbox","description":"E2B沙箱"}\nmodule_class = E2BSandbox\n