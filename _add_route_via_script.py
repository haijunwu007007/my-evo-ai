"""创建脚本文件到服务器然后执行"""
import urllib.request, json, base64

REMOTE = "https://autoevoai.com"

def api(cmd, args=""):
    p = json.dumps({"cmd": cmd, "args": args, "timeout": 15}).encode()
    req = urllib.request.Request(f"{REMOTE}/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())

# Write a really short script to /tmp using hex
script = open(r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py", "rb").read().hex()
print(f"Hex length: {len(script)}")

CHUNK = 200
for i in range(0, len(script), CHUNK):
    chunk = script[i:i+CHUNK]
    mode = "wb" if i == 0 else "ab"
    r = api("python3", f"-c \"import binascii; open('/home/ubuntu/my-evo-ai/api/routes/routes_static.py','{mode}').write(binascii.unhexlify('{chunk}'))\"")
    if not r.get("success"):
        print(f"CHUNK {i} FAIL: {r.get('stderr','')}")
        exit(1)
    if i % 2000 == 0:
        print(f"  [{i//CHUNK+1}/{(len(script)+CHUNK-1)//CHUNK}]")

# Verify
r = api("python3", "-c \"import os; print(os.path.getsize('/home/ubuntu/my-evo-ai/api/routes/routes_static.py'))\"")
print(f"Server filesize: {r.get('stdout','')}")

# Check /agent route first
r = api("python3", "-c \"import sys; sys.path.insert(0,'/home/ubuntu/my-evo-ai'); from api_server import app; [print(r.path) for r in app.routes if hasattr(r,'path') and 'agent' in r.path.lower()]\"")
print("REGISTERED agent ROUTES:")
print(r.get("stdout",""))
print("ERR:", r.get("stderr","")[:200])

# Direct test
import urllib.error
try:
    r2 = urllib.request.urlopen(f"{REMOTE}/agent", timeout=10)
    print(f"/agent: {r2.status}")
except Exception as e:
    print(f"/agent: {e}")

try:
    r2 = urllib.request.urlopen(f"{REMOTE}/agents", timeout=10)
    print(f"/agents: {r2.status}")
except urllib.error.HTTPError as e:
    print(f"/agents: HTTP {e.code} - {e.read().decode()[:100]}")
