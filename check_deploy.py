#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 检查evo状态
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=10,get_pty=True)
print('Evo:',o.read().decode().strip())
# 逐个测试
for n,p in [('发现','/api/v1/hub/discover'),('项目','/api/v1/hub/projects'),('组合','/api/v1/hub/composes'),('模板','/api/v1/hub/templates'),('Hub页','/hub')]:
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
    c=r.read().decode().strip()
    print(f'  {"✅" if c in("200","301") else "❌"} {n}: {c}')
C.close()
