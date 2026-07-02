"""重启 — pkill杀完后用python3重启"""
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

# 用python3执行shell命令
sc = (
    "import subprocess,os,time;"
    "os.chdir('/home/ubuntu/my-evo-ai');"
    "p=subprocess.Popen(['nohup','python3','api_server.py','--port','8765'],"
    "stdout=open('/tmp/evo_api.log','w'),stderr=subprocess.STDOUT);"
    "print('OK pid='+str(p.pid))"
)
s, r = cli("python3", f"-c '{sc}'", 15)
print(f"start: {s} {str(r)[:100]}")

time.sleep(8)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"首页: {r.status} tb={c.count('toolbar-top')} msg={c.count('messages')}")
