#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()

# 读当前api_server
_,o,_=C.exec_command("cat /home/ubuntu/my-evo-ai/api_server.py", timeout=10, get_pty=True)
content = o.read().decode()

# 在 routes_hub import 前插入
insert = """from api.routes.routes_hub import router as hub_router
from api.routes.routes_company import router as company_router
from api.routes.hub_static import router as hub_static_router

"""
# 找到"from api.routes.routes_env import"这行的位置，在它之前插入
lines = content.split('\n')
new_lines = []
for i, line in enumerate(lines):
    if line.strip() == 'from api.routes.routes_github import router as github_router':
        new_lines.append(insert)
    new_lines.append(line)

# 在 include_router 前插入注册
new_content = '\n'.join(new_lines)
insert2 = "app.include_router(hub_router)\napp.include_router(company_router)\napp.include_router(hub_static_router)\n\n"
new_content = new_content.replace("app.include_router(modules_router)\n", "app.include_router(modules_router)\n" + insert2)

sftp = C.open_sftp()
with sftp.open('/tmp/api_server.py', 'w') as f:
    f.write(new_content)
sftp.close()

r("sudo cp /tmp/api_server.py /home/ubuntu/my-evo-ai/api_server.py")

r("sudo systemctl restart evo.service")
time.sleep(8)
print("状态:",r("sudo systemctl is-active evo.service"))
print("Hub:",r("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/api/v1/hub/discover"))
print("Company:",r("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/api/v1/company/status"))
print("HubPage:",r("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/hub"))
C.close()
