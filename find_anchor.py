#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
_,o,_=C.exec_command("grep -n 'routes_github\\|routes_services\\|github_router\\|modules_router' /home/ubuntu/my-evo-ai/api_server.py|head -10",timeout=10,get_pty=True)
print(o.read().decode()[:500])
C.close()
