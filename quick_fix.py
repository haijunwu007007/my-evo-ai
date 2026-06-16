#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c):
    _,o,_=C.exec_command(c,timeout=30,get_pty=True)
    import time;time.sleep(0.3)
    try:return o.read().decode().strip()
    except:return ''
# 先恢复
r("sudo git -C /home/ubuntu/my-evo-ai checkout -- api_server.py")
time.sleep(3)
# 加3行import（分开加，i命令不能识别\\n）
r("sudo sed -i '86ifrom api.routes.routes_hub import router as hub_router' /home/ubuntu/my-evo-ai/api_server.py")
r("sudo sed -i '87ifrom api.routes.hub_static import router as hub_static_router' /home/ubuntu/my-evo-ai/api_server.py")
r("sudo sed -i '88ifrom api.routes.routes_company import router as company_router' /home/ubuntu/my-evo-ai/api_server.py")
time.sleep(2)
print("import:",r("grep -c hub_router /home/ubuntu/my-evo-ai/api_server.py"))
# 加3行include
r("sudo sed -i '165iapp.include_router(hub_router)' /home/ubuntu/my-evo-ai/api_server.py")
r("sudo sed -i '166iapp.include_router(hub_static_router)' /home/ubuntu/my-evo-ai/api_server.py")
r("sudo sed -i '167iapp.include_router(company_router)' /home/ubuntu/my-evo-ai/api_server.py")
print("include:",r("grep -c company_router /home/ubuntu/my-evo-ai/api_server.py"))
# 重启
r("sudo systemctl restart evo.service")
time.sleep(15)
print("状态:",r("sudo systemctl is-active evo.service"))
s=r("sudo systemctl is-active evo.service")
if s=='active':
    print("Hub:",r("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/api/v1/hub/discover"))
    print("Company:",r("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/api/v1/company/status"))
    print("HubPage:",r("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/hub"))
    print("Canvas:",r("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/canvas"))
    print("Fork:",r("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/fork"))
    print("CompanyPage:",r("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/company"))
C.close()
