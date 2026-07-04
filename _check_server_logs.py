"""检查服务器启动日志"""
import urllib.request, json

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# Check if routes_static appears in any log
r = cli("python3", '-c "import os,glob; logs=glob.glob(\'/home/ubuntu/my-evo-ai/logs/*.log\')+glob.glob(\'/tmp/evo*.log\'); print(\\\"NO LOGS\\\" if not logs else \\\"\\n\\\".join([f\\\"{f}: {os.path.getsize(f)}b\\\" for f in logs[:10]]))"')
print("LOGS:", r.get("stdout","")[:500])

# Try importing the module directly and see if there's an error
r = cli("python3", '-c "import sys; sys.path.insert(0,\'/home/ubuntu/my-evo-ai\'); import importlib; m=importlib.import_module(\'api.routes.routes_static\'); print(dir(m.router))"')
print("IMPORT_TEST:", r.get("stdout","")[:500])
print("IMPORT_ERR:", r.get("stderr","")[:500])
