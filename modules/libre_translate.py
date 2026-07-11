"""LibreTranslate翻译"""
import logging,httpx
logger=logging.getLogger("evo.modules.libre_translate")
class LibreTranslate:
 def __init__(s):s._ready=True;s._url="http://localhost:5000"
 def config(s,url):s._url=url.rstrip("/");return{"success":True}
 def translate(s,text,source="auto",target="zh"):
  try:r=httpx.post(f"{s._url}/translate",json={"q":text,"source":source,"target":target},timeout=15);return{"success":r.status_code==200,"text":r.json().get("translatedText","")if r.status_code==200 else""}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"libre_translate","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("url",""))
  if a=="translate":return s.translate(p.get("text",""),p.get("source","auto"),p.get("target","zh"))
  return s.status()
get_status=lambda:LibreTranslate().status()
register=lambda:{"name":"libre_translate","class":"LibreTranslate","description":"LibreTranslate翻译"}
