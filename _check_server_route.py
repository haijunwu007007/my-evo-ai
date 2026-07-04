"""检查服务器上routes_static.py是否包含/agents"""
import urllib.request, json

payload = json.dumps({
    "cmd": "python3",
    "args": "-c \"import re; c=open('/home/ubuntu/my-evo-ai/api/routes/routes_static.py').read(); print('/agents count:', len(re.findall(r'/agents', c)))\"",
    "timeout": 10
}).encode()

req = urllib.request.Request(
    "https://autoevoai.com/api/v1/cli/exec",
    data=payload,
    headers={"Content-Type": "application/json"}
)
r = urllib.request.urlopen(req, timeout=15)
print(r.read().decode())
