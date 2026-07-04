"""两步部署：1)写极小脚本到服务器 2)执行"""
import urllib.request, json, base64

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 15}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# 极小脚本：直接追加到routes_static.py
script = 'import sys; sys.path.insert(0,"/home/ubuntu/my-evo-ai"); from api_server import app; from fastapi.responses import FileResponse; from pathlib import Path; p=Path("frontend/agents.html"); app.add_api_route("/agents",lambda req:FileResponse(str(p))); print("OK")'

b64 = base64.b64encode(script.encode()).decode()
print(f"Script: {len(script)} chars, b64: {len(b64)} chars")

# Step 1: 写入脚本
r = cli("python3", f"-c \"import base64; base64.b64decode('{b64}').decode()\"")
print("DECODE test:", r.get("stdout","")[:100])

# Use even shorter: just write the script via base64
r = cli("python3", f"-c \"import base64; open('/tmp/a.py','w').write(base64.b64decode('{b64}').decode())\"")
print("WRITE:", r.get("stdout","")[:100], r.get("stderr","")[:100])

# Step 2: 执行
r = cli("python3", "/tmp/a.py")
print("EXEC:", r.get("stdout","")[:200], r.get("stderr","")[:100])

# Step 3: 验证
import urllib.error
try:
    r2 = urllib.request.urlopen("https://autoevoai.com/agents", timeout=10)
    print(f"OK! /agents -> {r2.status}")
except urllib.error.HTTPError as e:
    print(f"FAIL: /agents -> {e.code}")
