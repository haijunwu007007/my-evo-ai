#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()
# 检查问题
print("api_server line count:",r("wc -l /home/ubuntu/my-evo-ai/api_server.py"))
print("routes_hub存在:",r("ls -la /home/ubuntu/my-evo-ai/api/routes/routes_hub.py"))
print("hub_static存在:",r("ls -la /home/ubuntu/my-evo-ai/api/routes/hub_static.py"))
print("grep hub:",r("grep 'routes_hub\\|hub_static' /home/ubuntu/my-evo-ai/api_server.py 2>/dev/null"))
print("错误日志:",r("sudo journalctl -u evo --no-pager -n 10 2>/dev/null|grep -i error|tail -5"))
C.close()
