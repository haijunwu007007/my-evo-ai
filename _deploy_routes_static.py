"""部署 routes_static.py 到公网服务器"""
import urllib.request, json, base64, time

HOST = "https://autoevoai.com"
REMOTE_PATH = "/home/ubuntu/my-evo-ai/api/routes/routes_static.py"
LOCAL_PATH = r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py"

with open(LOCAL_PATH, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")
print(f"[OK] 本地文件 {len(b64)//4*3} bytes")

CHUNK = 300
total = len(b64)
for i in range(0, total, CHUNK):
    chunk = b64[i:i+CHUNK]
    mode = "wb" if i == 0 else "ab"
    payload = json.dumps({
        "cmd": "python3",
        "args": f"-c \"import base64; open('{REMOTE_PATH}','{mode}').write(base64.b64decode('{chunk}'))\"",
        "timeout": 15
    }).encode()
    req = urllib.request.Request(
        f"{HOST}/api/v1/cli/exec",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        resp = json.loads(r.read().decode())
        if resp.get("success"):
            print(f"  [{i//CHUNK+1}/{(total+CHUNK-1)//CHUNK}] OK")
        else:
            print(f"  [ERR] {resp}")
    except Exception as e:
        print(f"  [FAIL] chunk {i}: {e}")
        exit(1)

print("[OK] 全部写入完成")

# 重启API服务
payload = json.dumps({"cmd": "pkill", "args": "-f api_server", "timeout": 5}).encode()
req = urllib.request.Request(f"{HOST}/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
urllib.request.urlopen(req, timeout=10)
print("[OK] API服务已触发重启")

# 验证
for i in range(15):
    try:
        resp = urllib.request.urlopen("https://autoevoai.com/agents", timeout=5)
        if resp.status == 200:
            print(f"[OK] /agents 返回 200! (第{i+1}秒)")
            break
    except urllib.error.HTTPError as e:
        if e.code == 200:
            print(f"[OK] /agents 返回 200!")
            break
        print(f"  [WAIT] 第{i+1}秒: HTTP {e.code}")
    except Exception as e:
        print(f"  [WAIT] 第{i+1}秒")
    time.sleep(1)
else:
    print("[FAIL] /agents 仍返回404")
