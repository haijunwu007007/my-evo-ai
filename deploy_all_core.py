#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()

# 1) 上传重写的canvas.html（拖拽+连线+保存）
sftp.put(r'D:\AUTO-EVO-AI-V0.1\frontend\canvas.html','/home/ubuntu/my-evo-ai/frontend/canvas.html')
# 2) 上传重写的fork.html（编辑器+提交）
sftp.put(r'D:\AUTO-EVO-AI-V0.1\frontend\fork.html','/home/ubuntu/my-evo-ai/frontend/fork.html')
# 3) 上传重写的company.html（部门活跃）
sftp.put(r'D:\AUTO-EVO-AI-V0.1\frontend\company.html','/home/ubuntu/my-evo-ai/frontend/company.html')
# 4) 上传更新的hub.html（部署按钮+状态轮询）
sftp.put(r'D:\AUTO-EVO-AI-V0.1\frontend\hub.html','/home/ubuntu/my-evo-ai/frontend/hub.html')
# 5) 上传后端集成引擎（git clone + docker）
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\integrate.py','/home/ubuntu/my-evo-ai/api/hub/integrate.py')
# 6) 上传公司引擎（真正干活）
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\company.py','/home/ubuntu/my-evo-ai/api/hub/company.py')
# 7) 上传路由
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py','/home/ubuntu/my-evo-ai/api/routes/routes_hub.py')
sftp.close()

C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(10)
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=10,get_pty=True)
print(f'Evo: {o.read().decode().strip()}')

# 测试核心端点
tests={'Hub':'/hub','Canvas':'/canvas','Fork':'/fork','Company':'/company','Tutorial':'/tutorial',
       'Discover':'/api/v1/hub/discover','CompanyStatus':'/api/v1/company/status',
       'Integrate':'/api/v1/hub/projects','Composes':'/api/v1/hub/composes'}
for n,p in tests.items():
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
    c=r.read().decode().strip()
    print(f'  {"✅" if c=="200" else "❌"} {n}: {c}')

# 测试部署一个项目
C.exec_command('''curl -s -X POST http://127.0.0.1:8765/api/v1/hub/projects/portainer/integrate \
  -H "Content-Type: application/json" \
  -d '{"port":9000}' --max-time 120 > /tmp/deploy_test.log 2>&1 &''',timeout=5,get_pty=True)
print('部署测试已启动（后台120s）...')
time.sleep(15)
_,o2,_=C.exec_command('tail -3 /tmp/deploy_test.log 2>/dev/null',timeout=10,get_pty=True)
res=o2.read().decode().strip()[:200]
print(f'部署结果: {res if res else "运行中..."}')

C.close()
