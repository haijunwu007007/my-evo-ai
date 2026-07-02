"""重新部署v3 — 尝试各种API端点"""
import urllib.request, json, time

HOST = "https://autoevoai.com"

def try_api(method, url, body=None):
    try:
        data = json.dumps(body).encode() if body else None
        r = urllib.request.urlopen(f"{HOST}{url}", data, timeout=15)
        return r.status, json.loads(r.read())
    except Exception as e:
        return 0, str(e)[:80]

# 尝试各种端点
for ep in ["/api/v1/cli/exec", "/api/v1/cli", "/api/v1/execute", 
           "/api/v1/tool/exec", "/api/v1/tools/exec",
           "/api/v1/hk/exec", "/api/v1/agent/exec"]:
    status, resp = try_api("POST", ep, {"cmd":"id","args":"-c","stdin":"echo test"})
    print(f"  {ep}: {status} {str(resp)[:60]}")
