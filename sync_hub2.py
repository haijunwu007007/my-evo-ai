#!/usr/bin/env python3
import paramiko, os, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)

# 创建目录
_,o,_=C.exec_command("mkdir -p /home/ubuntu/my-evo-ai/api/hub", timeout=10, get_pty=True)
sftp=C.open_sftp()

def put(local, remote):
    lpath = os.path.join(r'D:\AUTO-EVO-AI-V0.1', local)
    rpath = f'/home/ubuntu/my-evo-ai/{remote}'
    sftp.put(lpath, rpath)
    print(f'  ✓ {local}')

files = [
    ('api/hub/models.py','api/hub/models.py'),
    ('api/hub/discover.py','api/hub/discover.py'),
    ('api/hub/integrate.py','api/hub/integrate.py'),
]
print("上传hub引擎:")
for l,r in files:
    try: put(l,r)
    except Exception as e: print(f'  ✗ {l}: {e}')

sftp.close()
C.exec_command("sudo systemctl restart evo.service", timeout=10)
time.sleep(5)
_,o,_=C.exec_command("sudo systemctl is-active evo.service", timeout=10, get_pty=True)
print(f"Evo: {o.read().decode().strip()}")
_,o2,_=C.exec_command("curl -s -m 5 http://127.0.0.1:8765/hub 2>/dev/null|head -3", timeout=10, get_pty=True)
print(f"Hub页: {o2.read().decode()[:200]}")
C.close()
