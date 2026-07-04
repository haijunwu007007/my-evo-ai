"""检查FastAPI所有已注册路由"""
import urllib.request, json

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# Get all routes from the running FastAPI app
r = cli("python3", '-c "import sys; sys.path.insert(0,\'/home/ubuntu/my-evo-ai\'); from api_server import app; [print(f\\\"{r.methods} {r.path}\\n\\\") for r in app.routes if hasattr(r,\\\"path\\\") and \\\"agent\\\" in r.path.lower()]"')
print("=== AGENT ROUTES IN FASTAPI ===")
print(r.get("stdout","")[:1000])
