"""JoyAI视觉交互"""
import logging,base64,httpx,os
logger=logging.getLogger("evo.modules.joyai_vl_interaction")
class JoyAIVLInteraction:
 def __init__(s):s._ready=True;s._key=""
 def config(s,key):s._key=key;return{"success":True}
 def ask(s,path,question):
  if not os.path.exists(path):return{"success":False,"error":"文件不存在"}
  try:
   b64=base64.b64encode(open(path,"rb").read()).decode()
   r=httpx.post("https://api.joyai.com/v1/chat/completions",headers={"Authorization":f"Bearer {s._key}"},json={"model":"joy-vl","messages":[{"role":"user","content":[{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}},{"type":"text","text":question}]}]},timeout=30)
   return{"success":r.status_code==200,"answer":r.json().get("choices",[{}])[0].get("message",{}).get("content","")if r.status_code==200 else r.text[:200]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"joyai_vl_interaction","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("api_key",""))
  if a=="ask":return s.ask(p.get("path",""),p.get("question","这是什么？"))
  return s.status()
get_status=lambda:JoyAIVLInteraction().status()
register=lambda:{"name":"joyai_vl_interaction","class":"JoyAIVLInteraction","description":"JoyAI视觉交互"}
