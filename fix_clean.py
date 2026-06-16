#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()
# 恢复原始
r("sudo git -C /home/ubuntu/my-evo-ai checkout -- api_server.py")
time.sleep(2)

# 读原始文件
_,o,_=C.exec_command("cat /home/ubuntu/my-evo-ai/api_server.py",timeout=10,get_pty=True)
content = o.read().decode()

# 手动构建新内容
lines = content.split('\n')
new = []
for line in lines:
    new.append(line)
    if 'from api.routes.routes_github import router as github_router' in line:
        new.append('from api.routes.routes_hub import router as hub_router')
        new.append('from api.routes.hub_static import router as hub_static_router')
        new.append('from api.routes.routes_company import router as company_router')
    if 'app.include_router(github_router)' in line:
        new.append('app.include_router(hub_router)')
        new.append('app.include_router(hub_static_router)')
        new.append('app.include_router(company_router)')

# 写回
with open('/tmp/api_srv.py','w',encoding='utf-8') as f:
    f.write('\n'.join(new))
sftp=C.open_sftp()
sftp.put('/tmp/api_srv.py','/tmp/api_srv.py')
sftp.close()
r("sudo cp /tmp/api_srv.py /home/ubuntu/my-evo-ai/api_server.py")
r("sudo systemctl restart evo.service")
time.sleep(10)
print("状态:",r("sudo systemctl is-active evo.service"))
if r("sudo systemctl is-active evo.service").strip()=='active':
    print("Hub:",r('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/v1/hub/discover'))
    print("Company:",r('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/v1/company/status'))
    print("CompanyData:",r('curl -s http://127.0.0.1:8765/api/v1/company/status 2>/dev/null|head -1')[:200])
print("Canvas:",r('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/canvas'))
print("Fork:",r('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/fork'))
C.close()
