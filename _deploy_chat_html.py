"""部署 chat.html → 公网服务器（通过API逐块写入，避免SSH超时和命令行长度限制）"""
import urllib.request, json, base64, time

HOST = "https://autoevoai.com"
REMOTE_PATH = "/home/ubuntu/my-evo-ai/frontend/chat.html"
LOCAL_PATH = "D:/AUTO-EVO-AI-V0.1/frontend/chat.html"

with open(LOCAL_PATH, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")
print(f"[OK] 本地文件 {len(b64)//4*3} bytes")

# 逐块写入: 每块300字符base64（约225字节原始数据）
CHUNK = 300
total = len(b64)
for i in range(0, total, CHUNK):
    chunk = b64[i:i+CHUNK]
    mode = "wb" if i == 0 else "ab"
    # python3 -c从stdin读，这里base64字符串直接嵌入
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
            print(f"  [{i//CHUNK+1}/{(total+CHUNK-1)//CHUNK}] chunk {i}-{i+CHUNK} OK")
        else:
            print(f"  [ERR] {resp}")
    except Exception as e:
        print(f"  [FAIL] chunk {i}: {e}")
        exit(1)

print("[OK] 全部写入完成")

# 重启服务
payload = json.dumps({"cmd": "pkill", "args": "-f api_server", "timeout": 5}).encode()
req = urllib.request.Request(f"{HOST}/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
urllib.request.urlopen(req, timeout=10)
print("[OK] 服务已触发重启")

# 等待恢复
print("\n[WAIT] 等待服务重启...")
for i in range(25):
    try:
        resp = urllib.request.urlopen("https://autoevoai.com/", timeout=5)
        if resp.status == 200:
            html = resp.read().decode("utf-8")
            print(f"[OK] 第{i+1}秒: 已恢复! ({len(html)} bytes)")
            checks = [
                ("voice-bar width:100%", "display:flex" in html and "width:100%" in html.split("voice-bar")[1].split("}")[0] if "voice-bar" in html else False),
                ("input-row border-radius:8px", "border-radius:8px" in html.split(".input-row")[1].split("}")[0] if ".input-row" in html else False),
            ]
            for name, ok in checks:
                print(f"  {'[OK]' if ok else '[FAIL]'} {name}")
            break
    except:
        print(f"  [WAIT] 第{i+1}秒...")
    time.sleep(1)
else:
    print("[FAIL] 服务未恢复")
