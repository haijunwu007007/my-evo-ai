"""直接测试路由处理函数"""
import urllib.request, json

def cli(cmd, args=""):
    p = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())

# Test: call the agents_page function directly
r = cli("python3", "-c \"import sys; sys.path.insert(0,'/home/ubuntu/my-evo-ai'); import asyncio; from api.routes.routes_static import agents_page; result = asyncio.run(agents_page()); print(type(result), result.status_code)\"")
print("DIRECT CALL:", r.get("stdout","")[:200])
print("ERR:", r.get("stderr","")[:200])
