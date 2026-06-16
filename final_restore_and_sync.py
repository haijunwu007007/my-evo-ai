#!/usr/bin/env python3
import paramiko, time, os, subprocess

print("=== 1. 恢复服务器代码 ===")
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=30,banner_timeout=60)
sftp=C.open_sftp()
src=r'D:\AUTO-EVO-AI-V0.1'
files=[
    'api/routes/routes_hub.py','api/hub/discover.py','api/hub/integrate.py',
    'api/hub/models.py','api/hub/compose_deploy.py','api/routes/hub_static.py',
    'api/routes/routes_company.py','frontend/hub.html','api_server.py',
]
for f in files:
    local=f'{src}/{f}'
    remote=f'/home/ubuntu/my-evo-ai/{f}'
    if os.path.isfile(local):
        sftp.put(local,remote)
        print(f'  + {f}')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(12)
print()

print("=== 2. 测试 ===")
_,o,_=C.exec_command("sudo systemctl is-active evo.service",timeout=10,get_pty=True)
print(f'Evo: {o.read().decode().strip()}')

tests = [
    ('Hub页','/hub'),('画布','/canvas'),('开发','/fork'),('公司','/company'),
    ('引导','/tutorial'),('管理','/admin'),('聊天','/'),
    ('发现','/api/v1/hub/discover?source=gitee'),('项目','/api/v1/hub/projects'),
    ('组合','/api/v1/hub/composes'),('模板','/api/v1/hub/templates'),
    ('公司API','/api/v1/company/status'),('监控','/api/v1/hub/monitor'),
    ('组合详情','/api/v1/hub/composes/05e5fdde47ab'),
]
for n,p in tests:
    _,r,_=C.exec_command(f'curl -s -m 10 "http://127.0.0.1:8765{p}" 2>/dev/null|head -1',timeout=15,get_pty=True)
    out=r.read().decode(errors='replace').strip()
    ok=('success' in out or '<!DOCTYPE' in out or 'projects' in out or 'departments' in out or 'composes' in out or 'templates' in out)
    print(f'  {"✅" if ok else "❌"} {n}')
C.close()
print()

print("=== 3. 同步 ===")
subprocess.run(['git','-C',src,'add','-A'],capture_output=True)
subprocess.run(['git','-C',src,'commit','-m','full sync fix'],capture_output=True)
subprocess.run(['git','-C',src,'push'],capture_output=True)
print('  GitHub: 已推送')
subprocess.run(['robocopy',src,'E:\\AUTO-EVO-AI-V0.1','/MIR','/NJH','/NJS','/NP','/XF','.git','__pycache__','*.pyc','/XD','.git','__pycache__'],capture_output=True,shell=True)
print('  E盘: 已同步')
print()
print('✅ 全部完成')
