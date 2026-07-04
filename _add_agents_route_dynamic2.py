"""动态添加/agents路由到运行中的FastAPI"""
import urllib.request, json

payload = json.dumps({
    "cmd": "python3",
    "args": "-c \"import sys; sys.path.insert(0,'/home/ubuntu/my-evo-ai'); from api_server import app; from fastapi.responses import FileResponse; from pathlib import Path; p=Path('/home/ubuntu/my-evo-ai/frontend/agents.html'); async def _h(): return FileResponse(str(p)) if p.exists() else JSONResponse({'error':'not found'}); app.add_api_route('/agents',_h); print('OK')\"",
    "timeout": 10
}).encode()

req = urllib.request.Request(
    "https://autoevoai.com/api/v1/cli/exec",
    data=payload,
    headers={"Content-Type": "application/json"}
)
r = urllib.request.urlopen(req, timeout=15)
print(r.read().decode()[:500])
