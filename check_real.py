import sys, paramiko
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 真实测试
for n,c,p in [('发现-GET','curl -s -m 10','/api/v1/hub/discover?source=gitee'),('部署-POST','curl -s -m 10 -X POST','/api/v1/hub/projects/portainer/start')]:
    _,r,_=C.exec_command(f'{c} "http://127.0.0.1:8765{p}" 2>/dev/null|head -1',timeout=15,get_pty=True)
    out=r.read().decode(errors='replace').strip()[:80]
    ok='✅' if out and not out.startswith('000') else '❌'
    print(f'{ok} {n}: {out}')
C.close()
