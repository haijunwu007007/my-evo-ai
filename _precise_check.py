"""精确检查服务器上的/agents路由"""
import urllib.request, json

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# Exact line with @router.get("/agents")
r = cli("python3", '-c "c=open(\'/home/ubuntu/my-evo-ai/api/routes/routes_static.py\').read(); idx=c.find(\'@router.get(\\\"/agents\\\")\'); print(repr(c[idx:idx+200]))"')
print("AGENTS DEF:", r.get("stdout","")[:300])

# Check if routes_agents.py has a @router.get("/agents") too
r = cli("python3", '-c "c=open(\'/home/ubuntu/my-evo-ai/api/routes/routes_agents.py\').read(); idx=c.find(\'@router.get\') if c else -1; print(repr(c[max(0,idx):idx+200]) if idx>=0 else \\\"NO ROUTES_IN agents.py\\\")"')
print("AGENTS_API:", r.get("stdout","")[:300])
