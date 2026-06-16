import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# routes_hub.py 修复版
content = open(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py', 'rb').read()
sftp=C.open_sftp()
with sftp.open('/tmp/routes_hub_fixed.py','wb') as f: f.write(content)
sftp.close()
C.exec_command('sudo cp /tmp/routes_hub_fixed.py /home/ubuntu/my-evo-ai/api/routes/routes_hub.py',timeout=10)
print('routes_hub.py 恢复')
# 恢复company路由
C.exec_command('sudo cp /home/ubuntu/my-evo-ai/api/routes/routes_company.py /home/ubuntu/my-evo-ai/api/routes/routes_company.py.bak',timeout=5)
C.exec_command('sudo sed -i /@router.get/d /home/ubuntu/my-evo-ai/api/routes/routes_company.py',timeout=5)
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(10)
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=10,get_pty=True)
print('Evo:',o.read().decode().strip())
# 验证
tests={'HUB':'/hub','API':'/api/v1/hub/discover'}
for n,p in tests.items():
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
    print(f'  {"✅" if r.read().decode().strip()=="200" else "❌"} {n}')
C.close()
open(r'D:\AUTO-EVO-AI-V0.1\sync_fixed.txt','w').write('done')
