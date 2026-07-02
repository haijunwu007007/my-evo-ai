"""重新部署v2 — 通过香港Worker执行命令"""
import urllib.request, json, time, base64

HK = "http://43.129.75.222:8766"
REPO = "https://ghproxy.net/https://github.com/haijunwu007007/my-evo-ai"

def hk_run(cmd):
    body = json.dumps({"cmd": base64.b64encode(cmd.encode()).decode()}).encode()
    try:
        r = urllib.request.urlopen(f"{HK}/api/v1/hk/exec", body, timeout=120)
        return json.loads(r.read())
    except Exception as e:
        # 尝试直接格式
        body2 = json.dumps({"command": cmd}).encode()
        r = urllib.request.urlopen(f"{HK}/exec", body2, timeout=120)
        return json.loads(r.read())

print("1. 设置ghproxy + fetch...")
r = hk_run(f"cd /home/ubuntu/my-evo-ai && git remote set-url origin {REPO} && git fetch origin 2>&1")
print(f"   result: {str(r)[:200]}")

print("2. 重置到最新...")
r = hk_run("cd /home/ubuntu/my-evo-ai && git reset --hard origin/master 2>&1")
print(f"   {str(r)[:200]}")

print("3. 确认版本...")
r = hk_run("cd /home/ubuntu/my-evo-ai && git log --oneline -3 2>&1")
print(f"   {str(r)[:200]}")

print("4. 重启...")
r = hk_run("pkill -f api_server 2>/dev/null; sleep 2; cd /home/ubuntu/my-evo-ai && nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 & echo RESTART_OK")
print(f"   {str(r)[:100]}")

print("5. 验证...")
time.sleep(6)
for ep, name in [("/","首页"),("/billion-os.html","billion"),("/api/v1/evo/status","自进化")]:
    r = urllib.request.urlopen(f"https://autoevoai.com{ep}", timeout=10)
    c = r.read().decode(errors="replace")
    print(f"   {name}: {r.status} toolbar-top={c.count('toolbar-top')} msgs={c.count('class=\"messages\"')}")
