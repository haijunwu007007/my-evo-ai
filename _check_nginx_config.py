"""检查服务器Nginx配置"""
import urllib.request, json

# Check Nginx config
payload = json.dumps({
    "cmd": "python3",
    "args": "-c \"import os; c=os.popen('cat /etc/nginx/sites-enabled/default').read() if os.path.exists('/etc/nginx/sites-enabled/default') else ''; c+=os.popen('cat /etc/nginx/conf.d/*.conf').read() if os.path.exists('/etc/nginx/conf.d') else ''; print(c[:2000])\"",
    "timeout": 10
}).encode()

req = urllib.request.Request(
    "https://autoevoai.com/api/v1/cli/exec",
    data=payload,
    headers={"Content-Type": "application/json"}
)
r = urllib.request.urlopen(req, timeout=15)
import json as j
resp = j.loads(r.read().decode())
print("stdout:", resp.get("stdout", "")[:2000])
print("stderr:", resp.get("stderr", "")[:500])
