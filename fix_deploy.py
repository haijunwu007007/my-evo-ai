#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(10)
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=10,get_pty=True)
print(f'Evo: {o.read().decode().strip()}')
_,o2,_=C.exec_command("curl -s -o /dev/null -w '%{http_code}' -m 5 http://127.0.0.1:8765/api/v1/hub/discover",timeout=10,get_pty=True)
print(f'API: {o2.read().decode().strip()}')
_,o3,_=C.exec_command("curl -s -o /dev/null -w '%{http_code}' -m 5 http://127.0.0.1:8765/api/v1/company/status",timeout=10,get_pty=True)
print(f'Company API: {o3.read().decode().strip()}')
C.close()
