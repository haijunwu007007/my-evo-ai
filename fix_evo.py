#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()
print("日志:",r("sudo journalctl -u evo --no-pager -n 30 2>/dev/null")[:1000])
# 恢复api_server
r("sudo git -C /home/ubuntu/my-evo-ai checkout -- api_server.py 2>&1")
import time;time.sleep(2)
# 手动加路由
r("sudo sed -i '/routes_hub import/a\\nfrom api.routes.routes_company import router as company_router\\napp.include_router(company_router, prefix=\"/api/v1/company\")' /home/ubuntu/my-evo-ai/api_server.py")
r("sudo systemctl restart evo.service")
time.sleep(8)
print("状态:",r("sudo systemctl is-active evo.service"))
print("测试:",r("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/api/v1/company/status"))
C.close()
