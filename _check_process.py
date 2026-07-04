"""检查进程"""
import urllib.request, json

def api(cmd, args=""):
    p = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    return json.loads(urllib.request.urlopen(urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"}), timeout=15).read().decode())

# Check the process
r = api("python3", "-c \"import os; r=os.popen('ps aux|grep uvicorn|grep -v grep').read(); print(r[:500])\"")
print("UVICORN:", r.get("stdout",""))

# Check if the old route still exists
r = api("python3", "-c \"import sys; sys.path.insert(0,'/home/ubuntu/my-evo-ai'); from api_server import app; [print(p.path) for p in app.routes if hasattr(p,'path') and p.path=='/agents']\"")
print("ROUTE /agents:", r.get("stdout","")[:200])
