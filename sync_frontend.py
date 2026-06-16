#!/usr/bin/env python3
import paramiko, time, os
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
src=r'D:\AUTO-EVO-AI-V0.1'
# 同步前端
frontend = [
    'frontend/canvas.html',
    'frontend/fork.html',
    'frontend/hub.html',
    'frontend/chat.html',
]
for f in frontend:
    sftp.put(f'{src}/{f}', f'/home/ubuntu/my-evo-ai/{f}')
    print(f'  {f}')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(8)
_,o,_=C.exec_command('curl -s -o /dev/null -w "%{http_code}" https://autoevoai.com/canvas 2>/dev/null||echo no',timeout=10,get_pty=True)
print(f'Canvas: {o.read().decode().strip()}')
_,o2,_=C.exec_command('curl -s -o /dev/null -w "%{http_code}" https://autoevoai.com/fork 2>/dev/null||echo no',timeout=10,get_pty=True)
print(f'Fork: {o2.read().decode().strip()}')
C.close()
