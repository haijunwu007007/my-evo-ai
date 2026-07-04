"""检查名称冲突"""
import urllib.request, json

def cli(cmd, args=""):
    p = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())

# Search for agents_page in ALL python files
r = cli("python3", '-c "import os; root=\'/home/ubuntu/my-evo-ai\'; [print(os.path.join(dirpath,f),\':\',line_no) for dirpath,dirnames,filenames in os.walk(root) for f in filenames if f.endswith(\'.py\') for line_no,line in enumerate(open(os.path.join(dirpath,f),errors=\'ignore\'),1) if \'agents_page\' in line]"')
print("FOUND agents_page in:")
print(r.get("stdout",""))

# Try to trigger the real /agents via a direct request to localhost:8765
r = cli("python3", '-c "import http.client; c=http.client.HTTPConnection(\'127.0.0.1\',8765,timeout=5); c.request(\'GET\',\'/agents\'); r=c.getresponse(); print(r.status, r.read().decode()[:200])"')
print("LOCAL /agents:", r.get("stdout","")[:300])
