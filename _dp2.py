#!/usr/bin/env python3
"""部署 chat.html 到公网服务器"""
import urllib.request, json, base64, sys, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

SRC = r"D:\AUTO-EVO-AI-V0.1\frontend\chat.html"
HOST = "https://autoevoai.com"
URL = HOST + "/api/v1/cli/exec"

# 读取文件
with open(SRC, "rb") as f:
    raw = f.read()
b64 = base64.b64encode(raw).decode()
print(f"chat.html: {len(raw)} bytes, b64={len(b64)} chars")

# 分块写入
tmp = "/tmp/_dp_b64.txt"
step = 8000

for i in range(0, len(b64), step):
    chunk = b64[i : i + step]
    # 转义单引号: ' -> '\'' 
    safe = chunk.replace("'", "'\\''")
    mode = ">" if i == 0 else ">>"
    cmd_body = f"echo '{safe}' {mode} {tmp}"
    data = json.dumps({"cmd": "python3", "args": f"-c '{cmd_body}'"}).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, context=ctx)
        ret = json.loads(r.read())
        if not ret.get("success"):
            print(f"FAIL chunk {i//step}: {ret.get('stderr','')[:80]}")
            sys.exit(1)
        print(f"  chunk {i//step}: OK")
    except Exception as e:
        print(f"  chunk {i//step}: ERROR {e}")
        sys.exit(1)

# 解码写入目标文件
dest = "/home/ubuntu/my-evo-ai/frontend/chat.html"
cmd = f"base64 -d {tmp} > {dest} && rm -f {tmp} && wc -c {dest}"
data = json.dumps({"cmd": "python3", "args": f"-c '{cmd}'"}).encode()
req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
r = urllib.request.urlopen(req, context=ctx)
ret = json.loads(r.read())
print(f"  decode+write: {'OK' if ret.get('success') else 'FAIL'}: {ret.get('stdout','')[:100]}")

# 重启
cmd2 = "pkill -f uvicorn 2>/dev/null; echo restart_sent"
data2 = json.dumps({"cmd": "python3", "args": f"-c '{cmd2}'"}).encode()
try:
    urllib.request.urlopen(urllib.request.Request(URL, data=data2, headers={"Content-Type": "application/json"}), context=ctx)
except:
    pass
print("  restart: sent")

print("\nDONE")
