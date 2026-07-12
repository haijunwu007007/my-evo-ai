#!/usr/bin/env python3
"""部署 chat.html 到公网服务器 v3"""
import urllib.request, json, base64, sys, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

SRC = r"D:\AUTO-EVO-AI-V0.1\frontend\chat.html"
URL = "https://autoevoai.com/api/v1/cli/exec"

with open(SRC, "rb") as f:
    raw = f.read()
b64 = base64.b64encode(raw).decode()
print(f"chat.html: {len(raw)} bytes, b64={len(b64)} chars")

# 分块写入远程临时文件
tmp = "/tmp/_dp_b64.txt"
step = 8000

# 清空临时文件
data = json.dumps({"cmd": "python3", "args": f"-c 'open(\"{tmp}\",\"w\").write(\"\")'"}).encode()
urllib.request.urlopen(urllib.request.Request(URL, data=data, headers={"Content-Type":"application/json"}), context=ctx)

for i in range(0, len(b64), step):
    chunk = b64[i : i + step]
    # base64 不含单引号，用单引号安全
    py_code = f"import pathlib; pathlib.Path('{tmp}').write_text(pathlib.Path('{tmp}').read_text() + '''{chunk}''')"
    args = f"-c '{py_code}'"
    data = json.dumps({"cmd": "python3", "args": args}).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, context=ctx)
        ret = json.loads(r.read())
        if not ret.get("success"):
            print(f"  chunk {i//step}: FAIL - {ret.get('stderr','')[:100]}")
            sys.exit(1)
        print(f"  chunk {i//step}: OK")
    except Exception as e:
        print(f"  chunk {i//step}: ERROR {e}")
        sys.exit(1)

# 解码写入目标
dest = "/home/ubuntu/my-evo-ai/frontend/chat.html"
py = f"import base64; dest='{dest}'; open(dest,'wb').write(base64.b64decode(open('{tmp}','r').read()))"
data = json.dumps({"cmd": "python3", "args": f"-c '{py}'"}).encode()
req = urllib.request.Request(URL, data=data, headers={"Content-Type":"application/json"})
r = urllib.request.urlopen(req, context=ctx)
ret = json.loads(r.read())
print(f"  decode+write: {'OK' if ret.get('success') else 'FAIL'}: {ret.get('stdout','')[:100]}")

# 清理临时文件
data2 = json.dumps({"cmd": "python3", "args": "-c 'import os; os.remove(\"/tmp/_dp_b64.txt\")'"}).encode()
try:
    urllib.request.urlopen(urllib.request.Request(URL, data=data2, headers={"Content-Type":"application/json"}), context=ctx)
except:
    pass

# 重启
data3 = json.dumps({"cmd": "python3", "args": "-c 'import subprocess,sys; subprocess.run([\"pkill\",\"-f\",\"uvicorn\"],capture_output=True)'"}).encode()
try:
    urllib.request.urlopen(urllib.request.Request(URL, data=data3, headers={"Content-Type":"application/json"}), context=ctx)
except:
    pass
print("  restart: sent")

print("\nDONE")
