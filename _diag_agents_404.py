"""诊断/agents 404问题"""
import urllib.request, json

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# 1. Check what's listening on port 8765
r = cli("python3", '-c "import os; print(os.popen(\'ss -tlnp|grep 8765\').read()[:500])"')
print("LISTEN 8765:", r.get("stdout",""))

# 2. Check routes_static.py for the exact agents route
r = cli("python3", '-c "c=open(\'/home/ubuntu/my-evo-ai/api/routes/routes_static.py\').read(); i=c.find(\'@router.get\'); [print(c[i:i+80]) for i in range(len(c)) if c[i:i+18]==\'@router.get(\\\"/agents\\\")\' ]"')
print("AGENTS ROUTE:", r.get("stdout",""))

# 3. Check if the route is actually reachable
import urllib.error
try:
    r2 = urllib.request.urlopen("https://autoevoai.com/agents", timeout=10)
    print(f"DIRECT: {r2.status} {len(r2.read())}b")
except urllib.error.HTTPError as e:
    print(f"DIRECT: HTTP {e.code}")
    resp_text = e.read().decode()[:300]
    print(f"  BODY: {resp_text}")

# 4. Check internal 8765
try:
    import socket
    r2 = urllib.request.urlopen("http://127.0.0.1:8765/agents", timeout=5)
    print(f"LOCAL: {r2.status} {len(r2.read())}b")
except Exception as e:
    print(f"LOCAL: {e}")

# 5. Check if uvicorn is alive
r = cli("python3", '-c "import os; print(os.popen(\'pgrep -af uvicorn 2>/dev/null; pgrep -af api_server 2>/dev/null\').read()[:500])"')
print("PROCESSES:", r.get("stdout",""))
