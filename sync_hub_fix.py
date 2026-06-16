#!/usr/bin/env python3
import paramiko, time, os
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
src=r'D:\AUTO-EVO-AI-V0.1'
# 同步关键文件
files = [
    'api_server.py',
    'api/routes/routes_hub.py',
    'api/hub/models.py',
    'api/hub/discover.py',
    'api/hub/integrate.py',
]
for f in files:
    sftp.put(f'{src}/{f}', f'/home/ubuntu/my-evo-ai/{f}')
    print(f'  {f}')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(8)
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=10,get_pty=True)
r1=o.read().decode().strip()
print(f'Evo: {r1}')
_,o2,_=C.exec_command("curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/composes|head -1",timeout=10,get_pty=True)
print(f'Composes: {o2.read().decode()[:100]}')
_,o3,_=C.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/api/v1/hub/discover",timeout=10,get_pty=True)
print(f'Discover: {o3.read().decode().strip()}')
C.close()
print('部署完成')
