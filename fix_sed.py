#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()

# 恢复
r("sudo git -C /home/ubuntu/my-evo-ai checkout -- api_server.py")
time.sleep(2)

# 直接bash脚本修改
script = """#!/bin/bash
cd /home/ubuntu/my-evo-ai
# 在 modules import 后加hub
sed -i '/from api.routes.routes_services import/a\\\\nfrom api.routes.routes_hub import router as hub_router\\nfrom api.routes.hub_static import router as hub_static_router\\nfrom api.routes.routes_company import router as company_router' api_server.py
# 在 modules include 后加注册
sed -i '/app.include_router(modules_router)/a\\\\napp.include_router(hub_router)\\napp.include_router(hub_static_router)\\napp.include_router(company_router)' api_server.py
"""
sftp=C.open_sftp()
with sftp.open('/tmp/fix.sh','w') as f: f.write(script)
sftp.close()
r("chmod +x /tmp/fix.sh")
r("sudo bash /tmp/fix.sh")
print("hub:",r("grep -c 'hub_router' /home/ubuntu/my-evo-ai/api_server.py"))
print("company:",r("grep -c 'company_router' /home/ubuntu/my-evo-ai/api_server.py"))
r("sudo systemctl restart evo.service")
time.sleep(10)
print("状态:",r("sudo systemctl is-active evo.service"))
if r("sudo systemctl is-active evo.service").strip()=='active':
    print("Hub:",r('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/v1/hub/discover'))
    print("Company:",r('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/v1/company/status'))
C.close()
