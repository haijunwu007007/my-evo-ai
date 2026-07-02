"""重新部署：指定ghproxy URL确保拉到最新"""
import urllib.request, json, time

HOST = "https://autoevoai.com"
REPO = "https://ghproxy.net/https://github.com/haijunwu007007/my-evo-ai"

# 通过香港worker执行命令
def hk_exec(cmd):
    body = json.dumps({"cmd":"bash","args":"-c","stdin":cmd}).encode()
    r = urllib.request.urlopen(f"{HOST}/api/v1/cli/exec", body, timeout=60)
    return json.loads(r.read())

# 1. 设置ghproxy并fetch
print("1. 重新fetch (ghproxy)...")
r = hk_exec(f"cd /home/ubuntu/my-evo-ai && git remote set-url origin {REPO} && git fetch origin 2>&1")
print(f"   {json.dumps(r)[:200]}")

# 2. 重置到最新
print("2. reset到最新...")
r = hk_exec("cd /home/ubuntu/my-evo-ai && git reset --hard origin/master 2>&1")
print(f"   {json.dumps(r)[:200]}")

# 3. 确认版本
r = hk_exec("cd /home/ubuntu/my-evo-ai && git log --oneline -3 2>&1")
print(f"3. 当前版本:\n   {r.get('stdout','')[:200]}")

# 4. 重启
print("4. 重启服务...")
r = hk_exec("pkill -f api_server 2>/dev/null; sleep 2; cd /home/ubuntu/my-evo-ai && nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 & echo RESTART_OK")
print(f"   {json.dumps(r)[:100]}")

# 5. 验证
time.sleep(5)
for ep, name in [("/","首页"),("/billion-os.html","billion"),("/api/v1/evo/status","自进化")]:
    r = urllib.request.urlopen(f"https://autoevoai.com{ep}", timeout=10)
    c = r.read().decode(errors="replace")
    tb = c.count("toolbar-top")
    msg = c.count("class=\"messages\"")
    print(f"   {name}: {r.status} toolbar-top={tb} messages={msg}")
