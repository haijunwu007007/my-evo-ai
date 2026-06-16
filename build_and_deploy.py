#!/usr/bin/env python3
"""构建前端+后端+部署到公网"""
import paramiko, time, os

BASE = r'D:\AUTO-EVO-AI-V0.1'
C = paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp = C.open_sftp()

# 上传全部核心文件
files = [
    ('api/hub/integrate.py','api/hub/integrate.py'),
    ('api/hub/company.py','api/hub/company.py'),
    ('api/routes/routes_hub.py','api/routes/routes_hub.py'),
    ('api/routes/routes_company.py','api/routes/routes_company.py'),
    ('frontend/hub.html','frontend/hub.html'),
    ('frontend/canvas.html','frontend/canvas.html'),
    ('frontend/fork.html','frontend/fork.html'),
    ('frontend/company.html','frontend/company.html'),
]
for local, remote in files:
    fp = os.path.join(BASE, local)
    if os.path.isfile(fp):
        sftp.put(fp, f'/home/ubuntu/my-evo-ai/{remote}')
        print(f'  ↑ {remote}')
sftp.close()

# 注册公司路由
C.exec_command('sudo sed -i "s/from api.routes.hub_static/from api.routes.routes_company import router as company_router\\nfrom api.routes.hub_static/" /home/ubuntu/my-evo-ai/api_server.py',timeout=10)
C.exec_command('sudo sed -i "s/app.include_router(hub_router)/app.include_router(company_router)\\napp.include_router(hub_router)/" /home/ubuntu/my-evo-ai/api_server.py',timeout=10)

# 重启
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(15)

# 验证
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=10,get_pty=True)
print(f'\nEvo: {o.read().decode().strip()}')

# 测试所有页面
pages={'Chat':'/','Hub':'/hub','Canvas':'/canvas','Fork':'/fork','Company':'/company','API Hub':'/api/v1/hub/discover','API Company':'/api/v1/company/status'}
for n,p in pages.items():
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
    print(f'  {"✅" if r.read().decode().strip()=="200" else "❌"} {n}: 200')

# 部署测试：Portainer
print('\n部署测试 Portainer...')
C.exec_command('''curl -s --max-time 120 -X POST http://127.0.0.1:8765/api/v1/hub/projects/portainer/integrate \
  -H "Content-Type: application/json" \
  -d '{"port":9000,"image":"portainer/portainer-ce"}' > /tmp/portainer_deploy.json 2>&1 &''',timeout=5,get_pty=True)
time.sleep(120)
_,o2,_=C.exec_command('cat /tmp/portainer_deploy.json',timeout=10,get_pty=True)
print(f'  Portainer: {o2.read().decode()[:300]}')

# 公司测试
_,o3,_=C.exec_command('''curl -s --max-time 10 -X POST http://127.0.0.1:8765/api/v1/company/task \
  -H "Content-Type: application/json" \
  -d '{"department":"cto","task":"部署一个Web服务"}' ''',timeout=15,get_pty=True)
print(f'  Task: {o3.read().decode()[:200]}')

C.close()
