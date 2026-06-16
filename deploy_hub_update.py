import sys, paramiko, time
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py','/home/ubuntu/my-evo-ai/api/routes/routes_hub.py')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(8)
for t in ['/api/v1/hub/composes','/api/v1/hub/composes/nonexist','/api/v1/hub/composes/nonexist']:
    _,o,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://127.0.0.1:8765{t}',timeout=10,get_pty=True)
    print(f'{t}: {o.read().decode(errors="replace").strip()}')
C.close()
