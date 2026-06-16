import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 删除开头的错误字符n
C.exec_command("sudo sed -i '1s/^n//' /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10)
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(20)
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=15,get_pty=True)
e=o.read().decode().strip()
print(f'Evo: {e}')
if e=='active':
    for n,p in [('Hub','/hub'),('Canvas','/canvas'),('Fork','/fork'),('Company','/company'),('API','/api/v1/hub/discover')]:
        _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
        c=r.read().decode().strip()
        print(f'  {c} {n}')
C.close()
