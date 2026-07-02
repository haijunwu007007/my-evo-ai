"""最终部署 — 正确的API参数格式"""
import urllib.request, json, time

HOST = "https://autoevoai.com"

def req(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    r = urllib.request.urlopen(f"{HOST}{path}", data, timeout=60) if data else urllib.request.urlopen(f"{HOST}{path}", timeout=60)
    return r.status, r.read().decode(errors="replace")

def exec_cli(cmd, args_list=None, timeout=60):
    """ExecRequest格式：command (str), args (string[]), timeout (int)"""
    payload = {"command": cmd, "timeout": timeout}
    if args_list:
        payload["args"] = args_list
    data = json.dumps(payload).encode()
    req_obj = urllib.request.Request(f"{HOST}/api/v1/cli/exec",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST")
    try:
        r = urllib.request.urlopen(req_obj, timeout=timeout+10)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        return e.code, {"error": body}
    except Exception as e:
        return 0, {"error": str(e)[:100]}

# Step 1: Fetch + Reset
print("1. 拉取最新代码...")
s, r = exec_cli("git", ["-C", "/home/ubuntu/my-evo-ai", "fetch", "origin"], 30)
print(f"   fetch: {s} {str(r)[:100]}")
s, r = exec_cli("git", ["-C", "/home/ubuntu/my-evo-ai", "reset", "--hard", "origin/master"], 30)
print(f"   reset: {s} {str(r)[:100]}")

# Step 2: 确认版本
s, r = exec_cli("git", ["-C", "/home/ubuntu/my-evo-ai", "log", "--oneline", "-3"], 10)
print(f"\n2. 版本: {str(r)[:200]}")

# Step 3: 重启
print("\n3. 重启服务...")
payload2 = {"command": "pkill", "args": ["-f", "api_server"], "timeout": 10}
data = json.dumps(payload2).encode()
req_obj = urllib.request.Request(f"{HOST}/api/v1/cli/exec",
    data=data, headers={"Content-Type": "application/json"}, method="POST")
try:
    r = urllib.request.urlopen(req_obj, timeout=15)
    print(f"   kill: {r.status}")
except:
    print(f"   kill sent (server restarting)")
time.sleep(3)

# 用bash重启
s, r = exec_cli("bash", ["-c", "cd /home/ubuntu/my-evo-ai && nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 & echo RESTART_OK"], 15)
print(f"   start: {s} {str(r)[:100]}")

# Step 4: 验证
print("\n4. 等待启动...")
time.sleep(8)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"   首页: {r.status} toolbar-top={c.count('toolbar-top')} msgs={c.count('messages')}")
r = urllib.request.urlopen("https://autoevoai.com/billion-os.html", timeout=10)
print(f"   billion: {r.status}")
