"""重启 — 写py脚本到服务器再执行"""
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

# 写restart.py到服务器
pycode = (
    "import subprocess,os\n"
    "os.chdir('/home/ubuntu/my-evo-ai')\n"
    "p=subprocess.Popen(['nohup','python3','api_server.py','--port','8765'],\n"
    "stdout=open('/tmp/evo_api.log','w'),stderr=2)\n"
    "print('OK pid='+str(p.pid))\n"
)
b64 = pycode.encode().hex()
s, r = cli("python3", f"-c \"open('/tmp/restart.py','w').write(bytes.fromhex('{b64}').decode()); print('wrote')\"", 10)
print(f"write: {s} {str(r)[:100]}")

# 执行
s, r = cli("python3", "/tmp/restart.py", 15)
import sys; sys.stdout.reconfigure(encoding='utf-8', errors='replace')
print(f"run: {s} {str(r)[:200]}")

time.sleep(8)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"首页: {r.status} tb={c.count('toolbar-top')} msg={c.count('messages')}")
