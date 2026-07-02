"""重启服务 — 用写入脚本方式"""
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

# 1. Kill all pythons
print("1. kill...")
cli("pkill", "-9 -f python", 5)
time.sleep(3)

# 2. Write restart script
script = "#!/bin/bash\ncd /home/ubuntu/my-evo-ai\nnohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 &\n"
b64 = script.encode().hex()
cmd = f"-c \"open('/tmp/restart.sh','w').write(bytes.fromhex('{b64}').decode()); print('done')\""
s, r = cli("python3", cmd, 10)
print(f"write: {s} {str(r)[:100]}")

# 3. Exec
s, r = cli("bash", "/tmp/restart.sh", 15)
print(f"run: {s} {str(r)[:100]}")

# 4. Wait & verify
time.sleep(8)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"首页: {r.status} tb={c.count('toolbar-top')} msg={c.count('messages')}")
