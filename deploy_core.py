#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
B='/home/ubuntu/my-evo-ai'
sftp=C.open_sftp()
src=r'D:\AUTO-EVO-AI-V0.1'
sftp.put(f'{src}\\api\\hub\\integrate.py',f'{B}/api/hub/integrate.py')
sftp.put(f'{src}\\api\\hub\\discover.py',f'{B}/api/hub/discover.py')
sftp.put(f'{src}\\api\\routes\\routes_hub.py',f'{B}/api/routes/routes_hub.py')
sftp.put(f'{src}\\frontend\\hub.html',f'{B}/frontend/hub.html')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
print("上传完成，等待加载...")
time.sleep(12)
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=10,get_pty=True)
st=o.read().decode().strip()
print(f'Evo: {st}')
if st!='active':
    _,e,_=C.exec_command('sudo journalctl -u evo -n 10 --no-pager 2>/dev/null|tail -5',timeout=10,get_pty=True)
    print('错误:',e.read().decode()[:500])
else:
    tests={}
    for n,p in [('发现','/api/v1/hub/discover'),('项目','/api/v1/hub/projects'),('组合','/api/v1/hub/composes'),('模板','/api/v1/hub/templates'),('监控','/api/v1/hub/monitor'),('Fork','/api/v1/hub/forks'),('Hub页','/hub'),('画布','/canvas'),('公司','/company'),('引导','/tutorial')]:
        _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
        c=r.read().decode().strip()
        tests[n]=c
        mark='✅' if c in('200','301') else '❌'
        print(f'  {mark} {n}: {c}')
C.close()
