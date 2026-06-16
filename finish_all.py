import sys, paramiko, time
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
# 上传全部文件
files = [
    r'D:\AUTO-EVO-AI-V0.1\api\hub\compose_deploy.py',
    r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py',
    r'D:\AUTO-EVO-AI-V0.1\frontend\hub.html',
]
for f in files:
    dest = f.replace(r'D:\AUTO-EVO-AI-V0.1', '/home/ubuntu/my-evo-ai').replace('\\','/')
    sftp.put(f, dest)
    print(f'  {dest}')
sftp.close()
C.exec_command("sudo systemctl restart evo.service",timeout=10)
time.sleep(10)
# 全面验证
tests = {
    'Hub页': '/hub','画布':'/canvas','开发':'/fork',
    '公司':'/company','引导':'/tutorial','管理':'/admin',
    '发现':'/api/v1/hub/discover','项目':'/api/v1/hub/projects',
    '组合':'/api/v1/hub/composes','模板':'/api/v1/hub/templates',
    '公司API':'/api/v1/company/status','搜索':'/api/v1/hub/search?q=ollama',
    '部署':'/api/v1/hub/projects/portainer/start',
}
for n,p in tests.items():
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 8 "http://127.0.0.1:8765{p}"',timeout=12,get_pty=True)
    c=r.read().decode(errors='replace').strip()
    m='✅' if c in ('200','301') else '❌'
    print(f'{m} {n}: {c}')
C.close()
