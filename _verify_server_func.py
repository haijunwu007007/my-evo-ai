"""验证服务器上/agents路由函数"""
import urllib.request, json

def api(cmd, args=""):
    p = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    return json.loads(urllib.request.urlopen(urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"}), timeout=15).read().decode())

# Check the agents route definition
r = api("python3", "-c \"c=open('/home/ubuntu/my-evo-ai/api/routes/routes_static.py').read(); i=c.find('@router.get(\\\"/agents\\\")'); print(c[i:i+300])\"")
print("AGENTS FUNC:", r.get("stdout","")[:400])

# Check the server log for errors
r = api("python3", "-c \"import os; f='/home/ubuntu/my-evo-ai/logs/evo.log'; print(os.popen('tail -50 '+f+'|grep -i error').read()[:500])\"")
print("LOGS:", r.get("stdout","")[:500])
