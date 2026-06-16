#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
sftp=C.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py', '/home/ubuntu/my-evo-ai/api/routes/routes_hub.py')
print("routes_hub.py 已上传")
# 删除调试端点
C.exec_command("sudo sed -i '/# ─── 调试/d' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py",timeout=5)
C.exec_command("sudo systemctl restart evo.service",timeout=10)
time.sleep(5)
_,o,_=C.exec_command("sudo systemctl is-active evo.service",timeout=10,get_pty=True)
print(f"Evo: {o.read().decode().strip()}")
_,o2,_=C.exec_command("curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/discover 2>/dev/null|head -1",timeout=10,get_pty=True)
res=o2.read().decode()[:200]
print(f"Discover: {res}")
C.close()
