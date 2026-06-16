#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()

# 上传所有hub文件
sftp=C.open_sftp()
base='/home/ubuntu/my-evo-ai'
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\models.py', f'{base}/api/hub/models.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\discover.py', f'{base}/api/hub/discover.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\discover_cn.py', f'{base}/api/hub/discover_cn.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\integrate.py', f'{base}/api/hub/integrate.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\company.py', f'{base}/api/hub/company.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py', f'{base}/api/routes/routes_hub.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\hub_static.py', f'{base}/api/routes/hub_static.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_company.py', f'{base}/api/routes/routes_company.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\frontend\hub.html', f'{base}/frontend/hub.html')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\frontend\company.html', f'{base}/frontend/company.html')
sftp.close()
print("文件已上传")

# 确认api_server有company路由
r('grep -q "routes_company" /home/ubuntu/my-evo-ai/api_server.py && echo "已注册" || echo "需注册"')
r('sudo sed -i "/routes_hub import/a\\\\nfrom api.routes.routes_company import router as company_router\\napp.include_router(company_router)" /home/ubuntu/my-evo-ai/api_server.py')
r("sudo systemctl restart evo.service")
time.sleep(8)
print("状态:",r("sudo systemctl is-active evo.service"))
print("Company:",r('curl -s -m 5 http://127.0.0.1:8765/api/v1/company/status 2>/dev/null|head -1')[:200])
print("Discover:",r('curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/discover 2>/dev/null|head -1')[:200])
C.close()
