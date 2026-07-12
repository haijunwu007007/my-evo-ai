import sys, urllib.request, json, base64, ssl, traceback
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
URL = "https://autoevoai.com/api/v1/cli/exec"

def exec_py(code):
    data = json.dumps({"cmd": "python3", "args": '-c ' + repr(code)}).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, context=ctx)
    return json.loads(r.read())

try:
    ret = exec_py("import sys; print(sys.version)")
    print("Test:", ret, flush=True)
    
    with open(r"D:\AUTO-EVO-AI-V0.1\frontend\chat.html", "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode()
    print(f"File: {len(raw)} bytes, b64={len(b64)} chars", flush=True)
    
    tmp = "/tmp/_dp_b64.txt"
    step = 8000
    
    for i in range(0, len(b64), step):
        chunk = b64[i:i+step]
        mode = "w" if i == 0 else "a"
        py = f"open('{tmp}','{mode}').write({repr(chunk)})"
        ret = exec_py(py)
        if not ret.get("success"):
            print(f"Chunk {i//step} FAIL: {ret}", flush=True)
            sys.exit(1)
        print(f"Chunk {i//step} OK", flush=True)
    
    dest = "/home/ubuntu/my-evo-ai/frontend/chat.html"
    py = f"import base64; base64.b64decode(open('{tmp}').read(), open('{dest}','wb'))"
    ret = exec_py(py)
    print(f"Decode: {ret}", flush=True)
    
    exec_py("import os; os.remove('/tmp/_dp_b64.txt')")
    exec_py("import subprocess; subprocess.run(['pkill','-f','uvicorn'],capture_output=True)")
    
    r = urllib.request.urlopen("https://autoevoai.com/chat.html", context=ctx)
    print(f"Verify: HTTP {r.status}, size={len(r.read())}", flush=True)
    print("DONE", flush=True)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
