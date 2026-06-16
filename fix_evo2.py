#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()
# 恢复原始
r("sudo git -C /home/ubuntu/my-evo-ai checkout -- api_server.py 2>&1")
# 加import
r("sudo sed -i '/routes_hub import/a\\nfrom api.routes.routes_company import router as company_router\\napp.include_router(company_router)' /home/ubuntu/my-evo-ai/api_server.py")
r("sudo systemctl restart evo.service")
time.sleep(8)
print("状态:",r("sudo systemctl is-active evo.service"))
print("Company:",r('curl -s http://127.0.0.1:8765/api/v1/company/status 2>/dev/null|head -1')[:200])
print("Hub:",r('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/v1/hub/discover'))
C.close()
