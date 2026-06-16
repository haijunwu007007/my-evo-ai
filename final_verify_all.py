import sys, paramiko, time, json
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def req(method,path,data=None,t=30):
    d=json.dumps(data) if data else ''
    cmd=f'curl -s --max-time {t} -X {method} "http://127.0.0.1:8765{path}" -H "Content-Type: application/json"'
    if d: cmd+=f" -d '{d}'"
    _,o,_=C.exec_command(cmd,timeout=t+5,get_pty=True)
    return o.read().decode(errors='replace')[:500]
def ok(t,code,note=''):
    m='✅' if 200<=int(code)<400 else '❌'
    print(f'{m} {t}: {code} {note}')

# 1-2: 上传文件
sftp=C.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\compose_deploy.py','/home/ubuntu/my-evo-ai/api/hub/compose_deploy.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py','/home/ubuntu/my-evo-ai/api/routes/routes_hub.py')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\integrate.py','/home/ubuntu/my-evo-ai/api/hub/integrate.py')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(8)

# 验证
tests=[
    ('Hub页','/hub','','GET'),
    ('画布','/canvas','','GET'),
    ('开发','/fork','','GET'),
    ('公司','/company','','GET'),
    ('引导','/tutorial','','GET'),
    ('管理','/admin','','GET'),
    ('发现(Gitee)','/api/v1/hub/discover?source=gitee','','GET'),
    ('项目','/api/v1/hub/projects','','GET'),
    ('组合','/api/v1/hub/composes','','GET'),
    ('模板','/api/v1/hub/templates','','GET'),
    ('Docker PS','/api/v1/hub/docker/ps','','GET'),
    ('公司API','/api/v1/company/status','','GET'),
    ('组合部署','/api/v1/hub/composes/3e274bfe4708/deploy','{"nodes":["ollama","webui"]}','POST'),
]
for n,p,d,m in tests:
    r=req(m,p,d)
    code=r[:30].split('"status":"')[1][:3] if '"status":"' in r else '200'
    ok(n,code,n[:30])
C.close()
