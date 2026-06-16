#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
_,o,_=C.exec_command('sudo journalctl -u evo --since "30 seconds ago" --no-pager 2>/dev/null|grep -i "hub\\|error\\|traceback"|tail -10',timeout=15,get_pty=True)
print(o.read().decode()[:800])
C.close()
