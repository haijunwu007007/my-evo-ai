"""飞书通知"""
import logging,httpx,json
logger=logging.getLogger("evo.modules.feishu_notifier")
class FeishuNotifier:
 def __init__(s):s._ready=True;s._webhook=""
 def config(s,url):s._webhook=url;return{"success":True}
 def send(s,msg,title="通知"):
  if not s._webhook:return{"success":False,"error":"未配置"}
  try:r=httpx.post(s._webhook,json={"msg_type":"post","content":json.dumps({"zh_cn":{"title":title,"content":[[{"tag":"text","text":msg}]]}})},timeout=10);return{"success":r.status_code==200}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"feishu_notifier","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("webhook",""))
  if a=="send":return s.send(p.get("msg",""),p.get("title","通知"))
  return s.status()
get_status=lambda:FeishuNotifier().status()
register=lambda:{"name":"feishu_notifier","class":"FeishuNotifier","description":"飞书通知"}
