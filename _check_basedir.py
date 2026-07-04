"""检查BASE_DIR和文件路径"""
import urllib.request, json

def cli(cmd, args=""):
    p = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())

# Check BASE_DIR from the running app
r = cli("python3", "-c \"import sys; sys.path.insert(0,'/home/ubuntu/my-evo-ai'); from api.infra import BASE_DIR; print('BASE_DIR:', str(BASE_DIR)); print('exists:', (BASE_DIR / 'frontend' / 'agents.html').exists())\"")
print("BASE_DIR:", r.get("stdout",""))
print("ERR:", r.get("stderr","")[:200])

# Also try a direct check from the route handler
# The route uses: p = BASE_DIR / "frontend" / "agents.html"
# But routes_static.py imports BASE_DIR from api.infra
# Let me check api.infra's BASE_DIR
r = cli("python3", "-c \"import sys; sys.path.insert(0,'/home/ubuntu/my-evo-ai'); from api._paths import BASE_DIR; print('_paths BASE_DIR:', str(BASE_DIR)); print('infra BASE_DIR:', str(type(BASE_DIR)))\"")
print("", r.get("stdout",""))
