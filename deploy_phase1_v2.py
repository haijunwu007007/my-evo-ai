#!/usr/bin/env python3
import paramiko, os, time, base64

C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
sftp=C.open_sftp()
BASE='/home/ubuntu/my-evo-ai'

def put(src, dst):
    if os.path.exists(src):
        sftp.put(src, dst)
        print(f'↑ {os.path.basename(src)}')

# 1. 上传前端
for f in ['hub.html','ComposeCanvas.html','ForkStudio.html']:
    src = os.path.join(r'D:\AUTO-EVO-AI-V0.1\frontend', f)
    put(src, f'{BASE}/frontend/{f}')

# 2. 上传hub_static.py（含/canvas /fork路由）
static_path = f'{BASE}/api/routes/hub_static.py'
existing = sftp.file(static_path,'r').read().decode() if sftp.exists else ''
new_static = existing.replace(
    'from fastapi.responses import FileResponse, JSONResponse',
    'from fastapi.responses import FileResponse, JSONResponse, HTMLResponse'
)
if '/canvas' not in new_static:
    new_static += '''
@hub_static.get("/canvas")
async def canvas_page():
    p = BASE_DIR / "frontend" / "ComposeCanvas.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<h3>Canvas not found</h3>")

@hub_static.get("/fork")
async def fork_page():
    p = BASE_DIR / "frontend" / "ForkStudio.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<h3>ForkStudio not found</h3>")
'''
with sftp.open(static_path, 'w') as f: f.write(new_static)
sftp.close()
print('hub_static.py updated')

# 3. 重启
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(5)
_,o,_=C.exec_command("sudo systemctl is-active evo.service",timeout=10,get_pty=True)
print(f'Evo: {o.read().decode().strip()}')
_,o2,_=C.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/canvas 2>/dev/null",timeout=10,get_pty=True)
print(f'/canvas: {o2.read().decode().strip()}')
_,o3,_=C.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/fork 2>/dev/null",timeout=10,get_pty=True)
print(f'/fork: {o3.read().decode().strip()}')
C.close()
