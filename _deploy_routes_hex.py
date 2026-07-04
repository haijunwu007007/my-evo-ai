"""用hex编码一次性写入routes_static.py（无特殊字符）"""
import urllib.request, json, time

HOST = "https://autoevoai.com"
REMOTE_PATH = "/home/ubuntu/my-evo-ai/api/routes/routes_static.py"
LOCAL_PATH = r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py"

with open(LOCAL_PATH, "rb") as f:
    hex_data = f.read().hex()

print(f"Local: {len(bytes.fromhex(hex_data))} bytes, hex: {len(hex_data)} chars")

# hex字符只有[0-9a-f]，无特殊字符，最安全
# Delete existing file first
payload = json.dumps({"cmd": "python3", "args": "-c \"import os; os.remove('/home/ubuntu/my-evo-ai/api/routes/routes_static.py')\"", "timeout": 5}).encode()
req = urllib.request.Request(f"{HOST}/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
try: urllib.request.urlopen(req, timeout=10)
except: pass
time.sleep(0.5)

CHUNK = 300  # 300 hex chars = 150 bytes per chunk
total_chunks = (len(hex_data) + CHUNK - 1) // CHUNK

for i in range(0, len(hex_data), CHUNK):
    chunk = hex_data[i:i+CHUNK]
    mode = "wb" if i == 0 else "ab"
    p = json.dumps({
        "cmd": "python3", 
        "args": f"-c \"import binascii; open('{REMOTE_PATH}','{mode}').write(binascii.unhexlify('{chunk}'))\"",
        "timeout": 15
    }).encode()
    try:
        req = urllib.request.Request(f"{HOST}/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        if not resp.get("success"):
            print(f"  [{i//CHUNK+1}/{total_chunks}] FAIL: {resp.get('stderr','')[:50]}")
            exit(1)
    except Exception as e:
        print(f"  [{i//CHUNK+1}/{total_chunks}] ERR: {e}")
        exit(1)
    if i % 1500 == 0:
        print(f"  [{i//CHUNK+1}/{total_chunks}] OK")
print("[OK] 全部写入完成")

# 验证文件尺寸
payload = json.dumps({"cmd": "python3", "args": f"-c \"import os; print(os.path.getsize('{REMOTE_PATH}'))\"", "timeout": 5}).encode()
req = urllib.request.Request(f"{HOST}/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
r = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
print(f"Server filesize: {r.get('stdout','')}")

# 重启
payload = json.dumps({"cmd": "pkill", "args": "-f \"api_server\"", "timeout": 5}).encode()
req = urllib.request.Request(f"{HOST}/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
urllib.request.urlopen(req, timeout=10)
print("[OK] 服务已重启")

# 验证/agents
for i in range(30):
    try:
        r = urllib.request.urlopen("https://autoevoai.com/agents", timeout=5)
        print(f"[OK] /agents -> {r.status} ({i+1}s)")
        break
    except urllib.error.HTTPError as e:
        if e.code == 404 and i < 28:
            time.sleep(1)
        else:
            print(f"[FAIL] /agents -> {e.code}")
            break
    except Exception as e:
        if i < 28:
            time.sleep(1)
        else:
            print(f"[FAIL] {e}")
            break
