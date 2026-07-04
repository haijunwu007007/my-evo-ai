"""检查服务器上的routes_static.py"""
import urllib.request, json

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# Check for /agent route
r = cli("python3", '-c "c=open(\'/home/ubuntu/my-evo-ai/api/routes/routes_static.py\').read(); print(\'agent:\', \'@router.get(\\\"/agent\\\")\' in c); print(\'agents:\', \'@router.get(\\\"/agents\\\")\' in c); print(\'errors:\', \'@router.get(\\\"/fork\\\")\' in c)"')
print("CHECK:", r.get("stdout",""))
print("ERR:", r.get("stderr","")[:500])

# Check the actual file around the agent section
r = cli("python3", '-c "c=open(\'/home/ubuntu/my-evo-ai/api/routes/routes_static.py\').read(); idx=c.find(\'/agent\'); print(repr(c[max(0,idx-20):idx+300]))"')
print("FILE SNIPPET:", r.get("stdout","")[:500])
