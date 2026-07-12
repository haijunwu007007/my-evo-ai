import sys, urllib.request, json, base64, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
URL = "https://autoevoai.com/api/v1/cli/exec"

def exec_py(code):
    data = json.dumps({"cmd": "python3", "args": '-c ' + repr(code)}).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, context=ctx)
    return json.loads(r.read())

# 远程临时文件已有base64数据（上一步写好的）
tmp = "/tmp/_dp_b64.txt"
dest = "/home/ubuntu/my-evo-ai/frontend/chat.html"

# 正确解码
py = (
    "import base64\n"
    f"with open('{tmp}') as f: b64 = f.read()\n"
    f"with open('{dest}','wb') as f: f.write(base64.b64decode(b64))\n"
    f"import os; os.remove('{tmp}')\n"
)

# 用 Base64 包裹多行 Python 代码发送
code_b64 = base64.b64encode(py.encode()).decode()
runner = f"import base64; exec(base64.b64decode('{code_b64}'))"
ret = exec_py(runner)
print(f"Decode: {'OK' if ret.get('success') else 'FAIL'}: {ret.get('stdout','')[:200]} {ret.get('stderr','')[:200]}", flush=True)

# 重启
exec_py("import subprocess; subprocess.run(['pkill','-f','uvicorn'],capture_output=True)")
import time; time.sleep(2)

# 验证
r = urllib.request.urlopen("https://autoevoai.com/chat.html", context=ctx)
d = r.read()
print(f"Verify: HTTP {r.status}, size={len(d)}", flush=True)
if len(d) > 60000:
    print("SUCCESS!", flush=True)
else:
    print("TOO SMALL!", flush=True)
