#!/usr/bin/env python3
import paramiko, os, time

C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
sftp=C.open_sftp()
BASE='/home/ubuntu/my-evo-ai'

# 1. 上传前端文件
files = [
    (r'D:\AUTO-EVO-AI-V0.1\frontend\hub.html', f'{BASE}/frontend/hub.html'),
    (r'D:\AUTO-EVO-AI-V0.1\frontend\ComposeCanvas.html', f'{BASE}/frontend/ComposeCanvas.html'),
    (r'D:\AUTO-EVO-AI-V0.1\frontend\ForkStudio.html', f'{BASE}/frontend/ForkStudio.html'),
]
for src, dst in files:
    if os.path.exists(src):
        sftp.put(src, dst)
        print(f'↑ {os.path.basename(src)}')
sftp.close()

# 2. 更新api_server.py注册路由（hub路由已经注册）
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()

# 3. 添加静态路由：/canvas /fork → 对应HTML
C.exec_command(f"""sudo sed -i '/def hub_static_page/a\\
@hub_static.get("/canvas")\\
async def canvas_page():\\
    return FileResponse(str(BASE_DIR / "frontend" / "ComposeCanvas.html"))\\
\\
@hub_static.get("/fork")\\
async def fork_page():\\
    return FileResponse(str(BASE_DIR / "frontend" / "ForkStudio.html"))' {BASE}/api/routes/hub_static.py""",timeout=10)

C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(5)
print(f'Evo: {r("sudo systemctl is-active evo.service")}')
print(f'HUB: {r("curl -s -m 5 http://127.0.0.1:8765/hub|head -1")[:100]}')
print(f'CANVAS: {r("curl -s -m 5 http://127.0.0.1:8765/canvas|head -1")[:100]}')
print(f'FORK: {r("curl -s -m 5 http://127.0.0.1:8765/fork|head -1")[:100]}')
print('Phase 1+2 部署完成')
C.close()
