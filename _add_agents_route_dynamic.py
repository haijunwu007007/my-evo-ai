"""动态添加/agents路由到运行中的FastAPI应用 - 无需修改文件"""
import urllib.request, json

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# 动态添加路由 - 使用FastAPI app实例
r = cli("python3", '-c "import sys; sys.path.insert(0,\'/home/ubuntu/my-evo-ai\'); from api_server import app; from fastapi.responses import FileResponse; from pathlib import Path; p=Path(\'/home/ubuntu/my-evo-ai/frontend/agents.html\'); @app.get(\'/agents\') async def _a(): return FileResponse(str(p)) if p.exists() else JSONResponse({}); print(\'OK\')"')
print("DYNAMIC_ADD:", r.get("stdout","")[:200])
print("DYNAMIC_ERR:", r.get("stderr","")[:200])
