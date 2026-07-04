"""检查agents.html文件是否存在"""
import urllib.request, json

payload = json.dumps({
    "cmd": "python3",
    "args": "-c \"import os; print('agents.html:', os.path.exists('/home/ubuntu/my-evo-ai/frontend/agents.html')); print('agent.html:', os.path.exists('/home/ubuntu/my-evo-ai/frontend/agent.html'))\"",
    "timeout": 10
}).encode()

req = urllib.request.Request(
    "https://autoevoai.com/api/v1/cli/exec",
    data=payload,
    headers={"Content-Type": "application/json"}
)
r = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
print("stdout:", r.get("stdout",""))
print("stderr:", r.get("stderr","")[:200])
