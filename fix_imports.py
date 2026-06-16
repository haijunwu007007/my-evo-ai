#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()
# 在 routes_github import 行前插入hub imports
r("sudo sed -i '/from api.routes.routes_github import/a\\nfrom api.routes.routes_hub import router as hub_router\\nfrom api.routes.hub_static import router as hub_static_router' /home/ubuntu/my-evo-ai/api_server.py")
# 在 routes_company import 行前插入
r("sudo sed -i '/hub_static_router/a\\nfrom api.routes.routes_company import router as company_router' /home/ubuntu/my-evo-ai/api_server.py")
# 在 modules_router 后插入include
r("sudo sed -i '/app.include_router(skills_market_router)/a\\napp.include_router(hub_router)\\napp.include_router(hub_static_router)\\napp.include_router(company_router)' /home/ubuntu/my-evo-ai/api_server.py")
print("已修改，检查:",r("grep -c 'hub_router\\|company_router' /home/ubuntu/my-evo-ai/api_server.py"))
r("sudo systemctl restart evo.service")
time.sleep(8)
print("状态:",r("sudo systemctl is-active evo.service"))
if r("sudo systemctl is-active evo.service").strip()=='active':
    print("Hub:",r('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/v1/hub/discover'))
    print("Company:",r('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/v1/company/status'))
    print("CompanyAPI:",r('curl -s http://127.0.0.1:8765/api/v1/company/status 2>/dev/null|head -1')[:200])
C.close()
