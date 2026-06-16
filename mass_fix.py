#!/usr/bin/env python3
"""批量修复所有缺陷"""
import paramiko, time, json
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()

files = [
    (r'D:\AUTO-EVO-AI-V0.1\api\hub\compose_deploy.py','api/hub/compose_deploy.py'),
    (r'D:\AUTO-EVO-AI-V0.1\api\hub\integrate.py','api/hub/integrate.py'),
    (r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py','api/routes/routes_hub.py'),
    (r'D:\AUTO-EVO-AI-V0.1\api\routes\hub_static.py','api/routes/hub_static.py'),
    (r'D:\AUTO-EVO-AI-V0.1\frontend\hub.html','frontend/hub.html'),
]
for local,remote in files:
    sftp.put(local,f'/home/ubuntu/my-evo-ai/{remote}')
    print(f'  {remote}')
sftp.close()

# 修复api_server.py
C.exec_command("sudo sed -i 's/^nfrom/from/' /home/ubuntu/my-evo-ai/api_server.py",timeout=5)
C.exec_command("sudo systemctl daemon-reload && sudo systemctl restart evo.service",timeout=10)
time.sleep(8)
_,o,_=C.exec_command("sudo systemctl is-active evo.service",timeout=10,get_pty=True)
print(f'Evo: {o.read().decode().strip()}')

def test(path,t=10,silent=False):
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m {t} "http://127.0.0.1:8765{path}"',timeout=t+5,get_pty=True)
    c=r.read().decode().strip()
    return c

tests=[('/', '首页'),('/hub','开源中心'),('/canvas','画布'),('/admin','管理'),('/company','公司'),('/tutorial','引导'),('/api/v1/hub/discover?source=gitee','发现-Gitee'),('/api/v1/hub/projects','项目列表'),('/api/v1/hub/composes','组合列表'),('/api/v1/hub/templates','模板列表'),('/api/v1/company/status','公司API')]
ok=fail=0
for path,name in tests:
    c=test(path)
    m='✅' if c in('200','301') else '❌'
    if m=='✅': ok+=1
    else: fail+=1
    print(f'  {m} {name}: {c}')
print(f'\n总计: {ok}✅ {fail}❌')
C.close()
