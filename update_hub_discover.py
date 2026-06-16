#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py', '/home/ubuntu/my-evo-ai/api/routes/routes_hub.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api_server.py', '/home/ubuntu/my-evo-ai/api_server.py')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(8)
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=10,get_pty=True)
r1=o.read().decode().strip()
# 验证路由
tests = [
    ('discover', '/api/v1/hub/discover'),
    ('search', '/api/v1/hub/search?q=ollama'),
    ('composes', '/api/v1/hub/composes'),
    ('projects', '/api/v1/hub/projects'),
    ('monitor', '/api/v1/hub/monitor'),
]
for name, path in tests:
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1:8765{path}',timeout=10,get_pty=True)
    code=r.read().decode().strip()
    print(f'  {name}: {code}')
_,o2,_=C.exec_command("curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/discover|python3 -c 'import sys,json;d=json.load(sys.stdin);print(f\"项目数: {len(d.get(chr(112)+chr(114)+chr(111)+chr(106)+chr(101)+chr(99)+chr(116)+chr(115),[]))}\")'",timeout=10,get_pty=True)
print(o2.read().decode()[:200])
C.close()
