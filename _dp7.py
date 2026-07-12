"""完整部署脚本：上传+解码+验证"""
import sys, urllib.request, json, base64, ssl, time
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
URL = "https://autoevoai.com/api/v1/cli/exec"

def exec_py(code):
    data = json.dumps({"cmd": "python3", "args": '-c ' + repr(code)}).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, context=ctx)
    return json.loads(r.read())

with open(r"D:\AUTO-EVO-AI-V0.1\frontend\chat.html", "rb") as f:
    raw = f.read()
b64 = base64.b64encode(raw).decode()
print(f"Source: {len(raw)} bytes", flush=True)

# 分块写入
tmp = "/tmp/_dp_b64.txt"
for i in range(0, len(b64), 8000):
    chunk = b64[i:i+8000]
    mode = "w" if i == 0 else "a"
    ret = exec_py(f"open('{tmp}','{mode}').write({repr(chunk)})")
    if not ret.get("success"):
        print(f"Chunk {i//8000} FAIL: {ret}", flush=True)
        sys.exit(1)
    print(f"Chunk {i//8000} OK", flush=True)

# 解码
ret = exec_py("import base64; open('/home/ubuntu/my-evo-ai/frontend/chat.html','wb').write(base64.b64decode(open('/tmp/_dp_b64.txt').read()))")
print(f"Decode: {ret}", flush=True)

# 清理
exec_py("import os; os.remove('/tmp/_dp_b64.txt')")

# 重启
exec_py("import subprocess; subprocess.run(['pkill','-f','uvicorn'],capture_output=True)")
time.sleep(3)

# 验证
for i in range(20):
    try:
        r = urllib.request.urlopen("https://autoevoai.com/chat.html", ctx=ctx)
        d = r.read()
        if len(d) > 65000:
            print(f"VERIFIED: HTTP {r.status}, {len(d)} bytes!", flush=True)
            break
        print(f"  attempt {i+1}: {len(d)} bytes (too small)", flush=True)
    except Exception as e:
        print(f"  attempt {i+1}: {type(e).__name__}", flush=True)
    time.sleep(2)

print("DONE", flush=True)
