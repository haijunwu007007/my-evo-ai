#!/usr/bin/env python3
import paramiko, os, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
sftp=C.open_sftp()
BASE='/home/ubuntu/my-evo-ai'

# 1. 前端文件
for f in ['hub.html','ComposeCanvas.html','ForkStudio.html']:
    src = os.path.join(r'D:\AUTO-EVO-AI-V0.1\frontend', f)
    if os.path.exists(src):
        sftp.put(src, f'{BASE}/frontend/{f}')
        print(f'↑ {f}')

# 2. 用命令行直接在服务器上加路由
C.exec_command(f"""cat >> {BASE}/api/routes/hub_static.py << 'PYEOF'

@hub_static.get("/canvas")
async def canvas_page():
    p = __import__('pathlib').Path(__file__).resolve().parent.parent.parent / "frontend" / "ComposeCanvas.html"
    from fastapi.responses import FileResponse, HTMLResponse
    return FileResponse(str(p)) if p.exists() else HTMLResponse("Not found")

@hub_static.get("/fork")
async def fork_page():
    p = __import__('pathlib').Path(__file__).resolve().parent.parent.parent / "frontend" / "ForkStudio.html"
    from fastapi.responses import FileResponse, HTMLResponse
    return FileResponse(str(p)) if p.exists() else HTMLResponse("Not found")
PYEOF""",timeout=10)

C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(5)
def g(c): _,o,_=C.exec_command(c,timeout=10,get_pty=True);return o.read().decode().strip()
print(f'Evo: {g("sudo systemctl is-active evo.service")}')
print(f'/canvas: {g("curl -s -o /dev/null -w \'%{http_code}\' http://127.0.0.1:8765/canvas")}')
print(f'/fork: {g("curl -s -o /dev/null -w \'%{http_code}\' http://127.0.0.1:8765/fork")}')
print(f'/hub: {g("curl -s -o /dev/null -w \'%{http_code}\' http://127.0.0.1:8765/hub")}')
sftp.close();C.close()
