#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
base='/home/ubuntu/my-evo-ai'
files={
    r'D:\AUTO-EVO-AI-V0.1\api\hub\discover_cn.py': f'{base}/api/hub/discover_cn.py',
    r'D:\AUTO-EVO-AI-V0.1\api\hub\company.py': f'{base}/api/hub/company.py',
    r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_company.py': f'{base}/api/routes/routes_company.py',
    r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py': f'{base}/api/routes/routes_hub.py',
    r'D:\AUTO-EVO-AI-V0.1\frontend\hub.html': f'{base}/frontend/hub.html',
    r'D:\AUTO-EVO-AI-V0.1\frontend\chat.html': f'{base}/frontend/chat.html',
    r'D:\AUTO-EVO-AI-V0.1\frontend\company.html': f'{base}/frontend/company.html',
}
for src,dst in files.items():
    sftp.put(src,dst)
sftp.close()
# 注册company路由
C.exec_command("sudo sed -i '/routes_hub import/a\\\\nfrom api.routes.routes_company import router as company_router\\napp.include_router(company_router)' /home/ubuntu/my-evo-ai/api_server.py",timeout=10)
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(8)
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=10,get_pty=True)
print(f"Evo: {o.read().decode().strip()}")
tests = {'Hub':'/hub','Canvas':'/canvas','Fork':'/fork','Company':'/company','Discover':'/api/v1/hub/discover','CompanyAPI':'/api/v1/company/status'}
for n,p in tests.items():
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
    print(f'  {"✅" if r.read().decode().strip() in ("200","301") else "❌"} {n}')
C.close()
