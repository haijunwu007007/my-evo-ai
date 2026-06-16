#!/usr/bin/env python3
import paramiko, os, sys

C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
sftp=C.open_sftp()

def upload(local, remote):
    lpath = os.path.join(r'D:\AUTO-EVO-AI-V0.1', local)
    rpath = f'/home/ubuntu/my-evo-ai/{remote}'
    sftp.put(lpath, rpath)
    print(f'  ↑ {local} → {remote}')

files = [
    ('api/routes/routes_hub.py','api/routes/routes_hub.py'),
    ('api/hub/models.py','api/hub/models.py'),
    ('api/hub/discover.py','api/hub/discover.py'),
    ('api/hub/integrate.py','api/hub/integrate.py'),
    ('api/routes/hub_static.py','api/routes/hub_static.py'),
    ('api_server.py','api_server.py'),
    ('frontend/hub.html','frontend/hub.html'),
    ('frontend/chat.html','frontend/chat.html'),
]

print("上传文件:")
for l,r in files:
    try:
        upload(l,r)
    except Exception as e:
        print(f'  ✗ {l}: {e}')

sftp.close()
print("\n重启服务...")
import time
C.exec_command("sudo systemctl restart evo.service", timeout=10)
time.sleep(5)
_,o,_=C.exec_command("sudo systemctl is-active evo.service", timeout=10, get_pty=True)
print(f"状态: {o.read().decode().strip()}")
_,o2,_=C.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/hub 2>/dev/null||echo no", timeout=10, get_pty=True)
print(f"/hub: {o2.read().decode()[:200]}")
C.close()
print("完成")
