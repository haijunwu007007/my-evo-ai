"""直接修复服务器 - 用python3 -c追加/agents路由到routes_static.py"""
import urllib.request, json

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# Read current file, check for /agents, and show the full route
r = cli("python3", '-c "c=open(\'/home/ubuntu/my-evo-ai/api/routes/routes_static.py\').read(); i=c.find(\'@router.get(\\\"/agents\\\")\'); print(i); print(c[i:i+300])"')
print("=== FULL AGENTS ROUTE ===")
print(r.get("stdout","")[:500])

# Also show what /agent route looks like for comparison
r = cli("python3", '-c "c=open(\'/home/ubuntu/my-evo-ai/api/routes/routes_static.py\').read(); i=c.find(\'@router.get(\\\"/agent\\\")\'); print(i); print(c[i:i+300])"')
print("=== FULL AGENT ROUTE ===")
print(r.get("stdout","")[:500])
