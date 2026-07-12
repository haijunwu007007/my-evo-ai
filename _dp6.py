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

# 1) 检查远程临时文件
ret = exec_py("import os; print(os.path.getsize('/tmp/_dp_b64.txt') if os.path.exists('/tmp/_dp_b64.txt') else 'NOT_FOUND')")
print(f"1) Temp file: {ret}", flush=True)

# 2) 解码写入 - 正确的单行写法
py_code = "import base64; open('/home/ubuntu/my-evo-ai/frontend/chat.html','wb').write(base64.b64decode(open('/tmp/_dp_b64.txt').read()))"
ret = exec_py(py_code)
print(f"2) Decode: {ret}", flush=True)

# 3) 清理
exec_py("import os; os.remove('/tmp/_dp_b64.txt')")

# 4) 重启
print("3) Restarting...", flush=True)
exec_py("import subprocess; subprocess.run(['pkill','-f','uvicorn'],capture_output=True)")

# 5) 等服务恢复
print("4) Waiting for service...", flush=True)
for i in range(30):
    time.sleep(2)
    try:
        r = urllib.request.urlopen("https://autoevoai.com/chat.html", context=ctx)
        d = r.read()
        print(f"   attempt {i+1}: HTTP {r.status}, size={len(d)}", flush=True)
        if r.status == 200 and len(d) > 65000:
            print(f"5) SUCCESS! chat.html = {len(d)} bytes", flush=True)
            break
    except Exception as e:
        print(f"   attempt {i+1}: {type(e).__name__}", flush=True)

print("DONE", flush=True)
