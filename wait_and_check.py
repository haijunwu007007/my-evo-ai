#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 查看日志
_,o,_=C.exec_command("sudo journalctl -u evo --since '2 min ago' --no-pager 2>&1|tail -20",timeout=15,get_pty=True)
print(o.read().decode()[:1000])
C.close()
