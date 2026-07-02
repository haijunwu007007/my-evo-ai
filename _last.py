"""最后一次部署 — 直接reset到commit"""
import urllib.request, json, time

H = "https://autoevoai.com"

def cli(c, a="", t=30):
    d = json.dumps({"cmd": c, "args": a, "timeout": t}).encode()
    req = urllib.request.Request(H + "/api/v1/cli/exec", data=d,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=t + 10)
        return r.status, json.loads(r.read())
    except Exception as ex:
        return 0, str(ex)[:100]

s, r = cli("git", "-C /home/ubuntu/my-evo-ai reset --hard b862c3c", 30)
print(f"reset: {s} {str(r)[:200]}")

s, r = cli("git", "-C /home/ubuntu/my-evo-ai log --oneline -3", 10)
print(f"HEAD: {str(r)[:200]}")

cli("pkill", "-f api_server", 5)
time.sleep(3)
py = "import subprocess,os; os.chdir('/home/ubuntu/my-evo-ai'); subprocess.Popen(['nohup','python3','api_server.py','--port','8765'],stdout=open('/tmp/evo_api.log','w'),stderr=2); print('OK')"
s, r = cli("python3", f"-c '{py}'", 15)
print(f"start: {s} {str(r)[:100]}")

time.sleep(8)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"首页: {r.status} tb={c.count('toolbar-top')} msgs={c.count('messages')}")
