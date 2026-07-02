"""部署 — FETCH_HEAD方式"""
import urllib.request, json, time

H = "https://autoevoai.com"
GP = "https://ghproxy.net/https://github.com/haijunwu007007/my-evo-ai"

def cli(c, a="", t=30):
    d = json.dumps({"cmd": c, "args": a, "timeout": t}).encode()
    req = urllib.request.Request(H + "/api/v1/cli/exec", data=d,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=t + 10)
        return r.status, json.loads(r.read())
    except Exception as ex:
        return 0, str(ex)[:100]

# 1. Fetch from ghproxy
print("1. fetch from ghproxy...")
s, r = cli("git", f"-C /home/ubuntu/my-evo-ai fetch {GP} master", 60)
print(f"   {s}: {str(r)[:200]}")

# 2. Reset to FETCH_HEAD
print("2. reset to FETCH_HEAD...")
s, r = cli("git", "-C /home/ubuntu/my-evo-ai reset --hard FETCH_HEAD", 30)
print(f"   {s}: {str(r)[:200]}")

# 3. Version
print("3. version...")
s, r = cli("git", "-C /home/ubuntu/my-evo-ai log --oneline -3", 10)
print(f"   {str(r)[:200]}")

# 4. Restart
print("4. restart...")
cli("pkill", "-f api_server", 5)
time.sleep(3)
pycode = 'import subprocess,os; os.chdir("/home/ubuntu/my-evo-ai"); subprocess.Popen(["nohup","python3","api_server.py","--port","8765"],stdout=open("/tmp/evo_api.log","w"),stderr=2); print("OK")'
s, r = cli("python3", f"-c \"{pycode}\"", 15)
print(f"   {s}: {str(r)[:100]}")

# 5. Verify
print("5. wait...")
time.sleep(8)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"   首页: {r.status} tb={c.count('toolbar-top')} msgs={c.count('messages')}")
