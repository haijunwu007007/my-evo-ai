"""重新部署v5 — 正确的 API 参数格式"""
import urllib.request, json, time

HOST = "https://autoevoai.com"

def try_post(ep, body):
    try:
        data = json.dumps(body).encode()
        r = urllib.request.urlopen(f"{HOST}{ep}", data, timeout=60)
        return r.status, r.read().decode(errors="replace")[:500]
    except Exception as e:
        return 0, str(e)[:100]

# ExecRequest: cmd (str), args (str=""), timeout (int=30)
ep = "/api/v1/cli/exec"

# Step 1: 设置ghproxy + fetch + reset
print("1. 拉最新代码...")
status, resp = try_post(ep, {"cmd": "bash", "args": "-c", "timeout": 60,
    "stdin": "cd /home/ubuntu/my-evo-ai && git remote set-url origin https://ghproxy.net/https://github.com/haijunwu007007/my-evo-ai && git fetch origin && git reset --hard origin/master"})
print(f"   {status}: {resp[:300]}")
if status != 200:
    # 尝试只传cmd
    status, resp = try_post(ep, {"cmd": "cd /home/ubuntu/my-evo-ai && git remote set-url origin https://ghproxy.net/https://github.com/haijunwu007007/my-evo-ai && git fetch origin && git reset --hard origin/master && echo DONE", "timeout": 60})
    print(f"   retry: {status}: {resp[:300]}")

# Step 2: 确认版本
print("\n2. 确认版本...")
status, resp = try_post(ep, {"cmd": "cd /home/ubuntu/my-evo-ai && git log --oneline -3 && echo VERSION_DONE", "timeout": 10})
print(f"   {resp[:300]}")

# Step 3: 重启
print("\n3. 重启服务...")
status, resp = try_post(ep, {"cmd": "pkill -f api_server 2>/dev/null; sleep 2; cd /home/ubuntu/my-evo-ai && nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 & echo RESTART_OK", "timeout": 15})
print(f"   {resp[:200]}")

# Step 4: 验证
print("\n4. 验证...")
time.sleep(6)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"   首页: {r.status} toolbar-top={c.count('toolbar-top')} msgs={c.count('messages')}")
r2 = urllib.request.urlopen("https://autoevoai.com/billion-os.html", timeout=10)
print(f"   billion: {r2.status}")
