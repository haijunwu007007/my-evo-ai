"""潜客捕获"""
import logging,re,httpx
logger=logging.getLogger("evo.modules.lead_catcher")
class LeadCatcher:
 def __init__(s):s._ready=True;s._leads=[]
 def extract(s,url):
  try:r=httpx.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=15);html=r.text;emails=list(set(re.findall(r"[\w.-]+@[\w.-]+\.\w+",html)));phones=list(set(re.findall(r"1[3-9]\d{9}",html)));lead={"url":url,"emails":emails[:10],"phones":phones[:5]};s._leads.append(lead);return{"success":True,"lead":lead}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def list(s):return{"success":True,"total":len(s._leads),"leads":s._leads[-20:]}
 def status(s):return{"name":"lead_catcher","ready":s._ready,"leads":len(s._leads)}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="extract":return s.extract(p.get("url",""))
  if a=="list":return s.list()
  return s.status()
get_status=lambda:LeadCatcher().status()
register=lambda:{"name":"lead_catcher","class":"LeadCatcher","description":"潜客捕获"}
module_class = LeadCatcher
