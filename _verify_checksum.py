"""验证服务器和本地routes_static.py完全一致"""
import urllib.request, json, hashlib

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# Check MD5 on server
r = cli("python3", "-c \"import hashlib; print(hashlib.md5(open('/home/ubuntu/my-evo-ai/api/routes/routes_static.py','rb').read()).hexdigest())\"")
server_md5 = r.get("stdout","").strip()
print(f"Server MD5: {server_md5}")

# Local MD5
local_md5 = hashlib.md5(open(r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py", "rb").read()).hexdigest()
print(f"Local MD5:  {local_md5}")

print(f"Match: {server_md5 == local_md5}")

# Also check if there's a .pyc cache that needs clearing
r = cli("python3", "-c \"import os, glob; caches = glob.glob('/home/ubuntu/my-evo-ai/**/__pycache__/routes_static*', recursive=True); [print(c) for c in caches]\"")
print(f"Cache files: {r.get('stdout','')[:200]}")
