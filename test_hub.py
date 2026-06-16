#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
_,o,_=C.exec_command('curl -s -m 10 http://127.0.0.1:8765/api/v1/hub/discover 2>&1|tail -3',timeout=15,get_pty=True)
print(o.read().decode()[:600])
C.close()
