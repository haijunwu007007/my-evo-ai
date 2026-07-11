"""发票智能处理"""
import logging,os,time
logger=logging.getLogger("evo.modules.invoice_agent")
class InvoiceAgent:
 def __init__(s):s._ready=True;s._invoices={}
 def scan(s,path):
  if not os.path.exists(path):return{"success":False,"error":"文件不存在"}
  try:
   import subprocess
   r=subprocess.run(["tesseract",path,"stdout","-l","chi_sim+eng"],capture_output=True,text=True,timeout=30)
   text=r.stdout[:500]if r.returncode==0 else""
  except:text=""
  inv={"id":f"inv_{int(time.time())}","file":os.path.basename(path),"text":text,"status":"scanned"}
  s._invoices[inv["id"]]=inv
  return{"success":True,"invoice":inv}
 def list(s):return{"success":True,"total":len(s._invoices),"invoices":list(s._invoices.values())}
 def status(s):return{"name":"invoice_agent","ready":s._ready,"invoices":len(s._invoices)}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="scan":return s.scan(p.get("path",""))
  if a=="list":return s.list()
  return s.status()
get_status=lambda:InvoiceAgent().status()
register=lambda:{"name":"invoice_agent","class":"InvoiceAgent","description":"发票智能处理"}
