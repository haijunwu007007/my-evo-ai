#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
# 检查服务器版本
_,o,_=C.exec_command('head -30 /home/ubuntu/my-evo-ai/api/hub/discover.py',timeout=10,get_pty=True)
print("服务器:",o.read().decode()[:300])
_,o2,_=C.exec_command('python3 -c "from datetime import datetime, timedelta;print(\'OK:\',(datetime.today()-timedelta(days=1)).isoformat()[:10])"',timeout=10,get_pty=True)
print("日期:",o2.read().decode()[:200])
C.close()
