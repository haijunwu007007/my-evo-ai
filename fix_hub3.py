#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
# 用简单版本替换discover函数
C.exec_command('''sudo sed -i 's/async def hub_discover/async def _hub_discover_old/' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py && sudo sed -i 's/@router.get("\\/api\\/v1\\/hub\\/discover")/async def hub_discover/' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py''', timeout=10)
# 写新函数
_,o,_=C.exec_command("tail -5 /home/ubuntu/my-evo-ai/api/routes/routes_hub.py", timeout=10,get_pty=True)
print(o.read().decode()[:200])
C.close()
