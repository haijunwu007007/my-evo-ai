"""在服务器代码中搜索404错误生成处"""
import urllib.request, json

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# Check Nginx conf
r = cli("python3", '-c "import os; c=open(\'/etc/nginx/sites-available/evo.conf\').read() if os.path.exists(\'/etc/nginx/sites-available/evo.conf\') else open(\'/etc/nginx/sites-available/autoevoai.com\').read(); print(c)"')
print("NGINX CONF:", r.get("stdout","")[:500])

# Test /agents via localhost curl
r = cli("python3", '-c "import urllib.request; r=urllib.request.urlopen(\'http://127.0.0.1:8765/agents\',timeout=5); print(r.status, r.read().decode()[:200])"')
print("LOCAL /agents:", r.get("stdout","")[:300])
print("LOCAL ERR:", r.get("stderr","")[:200])
