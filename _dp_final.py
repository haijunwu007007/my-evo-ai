#!/usr/bin/env python3
"""部署 chat.html 到公网服务器"""
import urllib.request, json, base64, sys, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

SRC = r"D:\AUTO-EVO-AI-V0.1\frontend\chat.html"
URL = "https://autoevoai.com/api/v1/cli/exec"

def exec_py(py_code):
    data = json.dumps({"cmd": "python3", "args": f"-c '{py_code}'"}).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, context=ctx)
    return json.loads(r.read())

with open(SRC, "rb") as f:
    raw = f.read()
b64 = base64.b64encode(raw).decode()
print(f"chat.html: {len(raw)} bytes, b64={len(b64)} chars")

tmp = "/tmp/_dp_b64.txt"
step = 8000

for i in range(0, len(b64), step):
    chunk = b64[i : i + step]
    mode = "w" if i == 0 else "a"
    # 用 repr() 保护字符串
    es = repr(chunk)
    py = f"open('{tmp}','{mode}').write({es})"
    ret = exec_py(py)
    if not ret.get("success"):
        print(f"  chunk {i//step}: FAIL - {ret.get('stderr','')[:100]}")
        sys.exit(1)
    print(f"  chunk {i//step}: OK")

# 解码写入
dest = "/home/ubuntu/my-evo-ai/frontend/chat.html"
py = f"import base64; open('{dest}','wb').write(base64.b64decode(open('{tmp}').read()))"
ret = exec_py(py)
print(f"  decode+write: {'OK' if ret.get('success') else 'FAIL'}: {ret.get('stdout','')[:100]}")

# 清理
exec_py(f"import os; os.remove('{tmp}')")

# 重启
exec_py("import subprocess; subprocess.run(['pkill','-f','uvicorn'],capture_output=True)")

# 验证
r = urllib.request.urlopen("https://autoevoai.com/chat.html", context=ctx)
print(f"  verify: HTTP {r.status}, size={len(r.read())}")

print("\nDONE")
