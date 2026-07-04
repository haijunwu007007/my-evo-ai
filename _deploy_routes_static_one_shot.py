"""一次性写入routes_static.py到服务器（不分块，避免截断）"""
import urllib.request, json, base64, time

HOST = "https://autoevoai.com"
REMOTE_PATH = "/home/ubuntu/my-evo-ai/api/routes/routes_static.py"
LOCAL_PATH = r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py"

with open(LOCAL_PATH, "rb") as f:
    raw = f.read()
b64 = base64.b64encode(raw).decode()

# 一次性写入（Python脚本从stdin读，但这里走API）
# 改用直接写大块 - 一次写完
payload = json.dumps({
    "cmd": "python3",
    "args": f"-c \"import base64; open('{REMOTE_PATH}','wb').write(base64.b64decode('''{b64}'''))\"",
    "timeout": 30
}).encode()

req = urllib.request.Request(
    f"{HOST}/api/v1/cli/exec",
    data=payload,
    headers={"Content-Type": "application/json"}
)
try:
    r = urllib.request.urlopen(req, timeout=30)
    resp = json.loads(r.read().decode())
    print(f"WRITE: {resp}")
    if not resp.get("success"):
        print("FAILED, trying chunk approach...")
        raise Exception("single write failed")
except Exception as e:
    print(f"Single write failed: {e}")
    # Fallback: delete first, then write
    payload2 = json.dumps({"cmd": "python3", "args": f"-c \"import os; os.remove('{REMOTE_PATH}')\"", "timeout": 5}).encode()
    req2 = urllib.request.Request(f"{HOST}/api/v1/cli/exec", data=payload2, headers={"Content-Type":"application/json"})
    urllib.request.urlopen(req2, timeout=10)
    time.sleep(0.5)
    
    # Now write with chunks
    CHUNK = 300
    total = len(bytes(open(LOCAL_PATH, "rb").read()).hex())
    h = open(LOCAL_PATH, "rb").read().hex()
    for i in range(0, len(h), CHUNK):
        chunk = h[i:i+CHUNK]
        mode = "wb" if i == 0 else "ab"
        p = json.dumps({"cmd": "python3", "args": f"-c \"import binascii; open('{REMOTE_PATH}','{mode}').write(bytes.fromhex('{chunk}'))\"", "timeout": 15}).encode()
        req = urllib.request.Request(f"{HOST}/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req, timeout=15)
        print(f"  [{i//CHUNK+1}/{(len(h)+CHUNK-1)//CHUNK}]")
    
print("Write done, triggering restart...")

# 重启
payload = json.dumps({"cmd": "pkill", "args": "-f api_server", "timeout": 5}).encode()
req = urllib.request.Request(f"{HOST}/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
urllib.request.urlopen(req, timeout=10)

# 验证
for i in range(25):
    try:
        r = urllib.request.urlopen("https://autoevoai.com/agents", timeout=5)
        print(f"[OK] /agents 返回 {r.status}! (第{i+1}秒)")
        break
    except urllib.error.HTTPError as e:
        if i < 12:
            print(f"  [WAIT] 第{i+1}秒: {e.code}")
    except:
        print(f"  [WAIT] 第{i+1}秒")
    time.sleep(1)
else:
    print("[FAIL] /agents 仍不工作")
