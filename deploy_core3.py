#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\discover.py','/home/ubuntu/my-evo-ai/api/hub/discover.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\integrate.py','/home/ubuntu/my-evo-ai/api/hub/integrate.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py','/home/ubuntu/my-evo-ai/api/routes/routes_hub.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\frontend\hub.html','/home/ubuntu/my-evo-ai/frontend/hub.html')
sftp.close()
# 修复 api_server.py
C.exec_command("grep -q 'routes_hub' /home/ubuntu/my-evo-ai/api_server.py && echo IMPORT_OK || echo MISSING",timeout=10)
import time
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(15)
_,o,_=C.exec_command("sudo systemctl is-active evo.service",timeout=10,get_pty=True)
print(f'Evo: {o.read().decode().strip()}')
time.sleep(5)
# 测试发现（多平台）
_,o2,_=C.exec_command("curl -s -m 10 http://127.0.0.1:8765/api/v1/hub/discover 2>/dev/null|python3 -c \"import sys,json;d=json.load(sys.stdin);print(f'发现: {len(d.get(\\\"projects\\\",[]))}个项目')\"",timeout=15,get_pty=True)
print('测试:',o2.read().decode(errors='replace')[:100])
# 测试部署
_,o3,_=C.exec_command("curl -s -X POST http://127.0.0.1:8765/api/v1/hub/projects -H 'Content-Type: application/json' -d '{\"name\":\"test-portainer\",\"source\":\"docker\"}' 2>/dev/null",timeout=10,get_pty=True)
print('加入:',o3.read().decode(errors='replace')[:200])
C.close()
