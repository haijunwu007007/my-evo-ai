#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
src=r'D:\AUTO-EVO-AI-V0.1'
# 前端文件：本地名→服务器名
pairs = [
    ('frontend/ComposeCanvas.html', 'frontend/canvas.html'),
    ('frontend/ForkStudio.html', 'frontend/fork.html'),
    ('frontend/hub.html', 'frontend/hub.html'),
    ('frontend/chat.html', 'frontend/chat.html'),
]
for local, remote in pairs:
    sftp.put(f'{src}/{local}', f'/home/ubuntu/my-evo-ai/{remote}')
    print(f'  {local} → {remote}')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(8)
_,o,_=C.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/canvas',timeout=10,get_pty=True)
r1=o.read().decode().strip()
_,o2,_=C.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/fork',timeout=10,get_pty=True)
r2=o2.read().decode().strip()
print(f'Canvas: {r1}  Fork: {r2}')
_,o3,_=C.exec_command("curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/composes|head -1",timeout=10,get_pty=True)
print(f'Composes: {o3.read().decode()[:120]}')
C.close()
