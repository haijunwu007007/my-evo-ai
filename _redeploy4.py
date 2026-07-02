"""重新部署v4 — 尝试各种请求格式"""
import urllib.request, json, time

HOST = "https://autoevoai.com"
CMDS = [
    "cd /home/ubuntu/my-evo-ai && git remote set-url origin https://ghproxy.net/https://github.com/haijunwu007007/my-evo-ai && git fetch origin && git reset --hard origin/master && echo OK",
    "pkill -f api_server 2>/dev/null; sleep 2; cd /home/ubuntu/my-evo-ai && nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 & echo DONE"
]

def try_post(url, body):
    try:
        data = json.dumps(body).encode()
        r = urllib.request.urlopen(f"{HOST}{url}", data, timeout=30)
        return r.status, json.loads(r.read())
    except Exception as e:
        return 0, str(e)[:100]

# 尝试各种payload格式
payloads = [
    {"cmd":"bash","args":"-c","stdin":CMDS[0]},
    {"cmd":CMDS[0]},
    {"command":CMDS[0]},
    {"action":"exec","params":{"cmd":CMDS[0]}},
    {"message":CMDS[0]},
    {"prompt":CMDS[0]},
]

for ep in ["/api/v1/cli/exec", "/api/v1/hk/exec"]:
    for p in payloads:
        s, r = try_post(ep, p)
        if s == 200:
            print(f"[WORKED] {ep}: {str(p)[:80]}")
            print(f"  result: {str(r)[:200]}")
            break
    else:
        print(f"[FAIL] {ep}: none worked")
