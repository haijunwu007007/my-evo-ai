#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\discover.py','/home/ubuntu/my-evo-ai/api/hub/discover.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py','/home/ubuntu/my-evo-ai/api/routes/routes_hub.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\frontend\hub.html','/home/ubuntu/my-evo-ai/frontend/hub.html')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(8)
_,o,_=C.exec_command("sudo systemctl is-active evo.service",timeout=10,get_pty=True)
print(f'Evo: {o.read().decode().strip()}')
tests={'Hub':'/hub','Canvas':'/canvas','Fork':'/fork','Tutorial':'/tutorial','Chat':'/','Admin':'/admin'}
for n,p in tests.items():
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
    print(f'  {"✅" if r.read().decode().strip() in ("200","301") else "❌"} {n}')
C.close()
