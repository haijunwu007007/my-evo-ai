"""MCP桥接"""
import logging,json,subprocess
logger=logging.getLogger("evo.modules.mcp_bridge")
class MCPBridge:
 def __init__(s):s._ready=True;s._servers={}
 def register(s,name,cmd,args=None):
  s._servers[name]={"cmd":cmd,"args":args or[]};return{"success":True,"server":name}
 def call_tool(s,server,tool,params=None):
  sv=s._servers.get(server)
  if not sv:return{"success":False,"error":"未注册"}
  try:payload=json.dumps({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":tool,"arguments":params or{}}});r=subprocess.run(sv["cmd"]+sv["args"],input=payload,capture_output=True,text=True,timeout=30);return{"success":r.returncode==0,"result":r.stdout[:1000]}
  except Exception as e:return{"success":False,"error":str(e)[:100]}
 def status(s):return{"name":"mcp_bridge","ready":s._ready,"servers":len(s._servers)}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="register":return s.register(p.get("name",""),p.get("cmd",""),p.get("args",[]))
  if a=="call":return s.call_tool(p.get("server",""),p.get("tool",""),p.get("params",{}))
  return s.status()
get_status=lambda:MCPBridge().status()
register=lambda:{"name":"mcp_bridge","class":"MCPBridge","description":"MCP桥接"}
