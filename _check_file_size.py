"""检查服务器和本地文件尺寸"""
import urllib.request, json

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

r = cli("python3", '-c "import os; print(len(open(\'/home/ubuntu/my-evo-ai/api/routes/routes_static.py\',\'rb\').read()))"')
print("Server filesize:", r.get("stdout",""))

import os
local = os.path.getsize(r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py")
print("Local filesize:", local)

# Check last 200 chars of server file
r = cli("python3", '-c "c=open(\'/home/ubuntu/my-evo-ai/api/routes/routes_static.py\').read(); print(repr(c[-200:]))"')
print("Server LAST 200:", r.get("stdout",""))
