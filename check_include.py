#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()
print("hub import:",r("grep 'hub_router' /home/ubuntu/my-evo-ai/api_server.py")[:200])
print("company import:",r("grep 'company_router' /home/ubuntu/my-evo-ai/api_server.py")[:200])
print("hub_static:",r("grep 'hub_static' /home/ubuntu/my-evo-ai/api_server.py")[:200])
print("include:",r("grep 'app.include_router(hub' /home/ubuntu/my-evo-ai/api_server.py")[:200])
C.close()
