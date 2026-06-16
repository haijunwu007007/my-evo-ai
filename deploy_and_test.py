#!/usr/bin/env python3
import sys, paramiko, time, json, os
sys.stdout.reconfigure(encoding='utf-8')

C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=30,banner_timeout=60)

src=r'D:\AUTO-EVO-AI-V0.1'
sftp=C.open_sftp()

# Upload all hub engine files
hub_files = ['api/hub/integrate.py','api/hub/models.py','api/hub/discover_cn.py','api/hub/compose_deploy.py','api/routes/routes_hub.py']
for f in hub_files:
    local=f'{src}/{f}'
    remote=f'/home/ubuntu/my-evo-ai/{f}'
    if os.path.isfile(local):
        sftp.put(local,remote)
        print(f'  + {f}')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(15)

# Verify
_,o,_=C.exec_command('systemctl is-active evo.service',timeout=10,get_pty=True)
e=o.read().decode(errors='replace').strip()
print(f'\nEvo: {e}')
if e!='active':
    _,o2,_=C.exec_command("sudo journalctl -u evo -n 10 --no-pager|grep -i error|tail -3",timeout=10,get_pty=True)
    print(f'Error:\n  {o2.read().decode(errors="replace")[:300]}')
    C.close()
    sys.exit(1)

# Test ALL endpoints
print()
tests=[
    ('/',True),('/hub',True),('/canvas',True),('/fork',True),('/company',True),
    ('/tutorial',True),('/admin',True),
    ('/api/v1/hub/discover?source=gitee',False),
    ('/api/v1/hub/projects',False),('/api/v1/hub/composes',False),
    ('/api/v1/hub/templates',False),('/api/v1/company/status',False),
    ('/api/v1/hub/monitor',False),
]
ok=0
for p,is_html in tests:
    _,r,_=C.exec_command(f'curl -s -m 10 "http://127.0.0.1:8765{p}" 2>/dev/null|head -c 80',timeout=15,get_pty=True)
    out=r.read().decode(errors='replace').strip()
    if out:
        print(f'  ✅ {p}')
        ok+=1
    else:
        print(f'  ❌ {p}')
print(f'\n{ok}/{len(tests)} 通过')

# Deploy nginx
print('\n=== 部署 nginx ===')
_,d1,_=C.exec_command("""curl -s --max-time 10 -X POST 'http://127.0.0.1:8765/api/v1/hub/projects' -H 'Content-Type: application/json' -d '{"id":"nginx","name":"nginx","source":"docker","category":"web"}' """,timeout=15,get_pty=True)
print('  Add:',d1.read().decode(errors='replace')[:100])
time.sleep(2)
_,d2,_=C.exec_command("""curl -s --max-time 60 -X POST 'http://127.0.0.1:8765/api/v1/hub/projects/nginx/integrate' -H 'Content-Type: application/json' -d '{"port":8080,"internal_port":80}' """,timeout=70,get_pty=True)
print('  Deploy:',d2.read().decode(errors='replace')[:200])
time.sleep(8)
_,d3,_=C.exec_command("curl -s -m 10 'http://127.0.0.1:8765/api/v1/hub/projects/nginx/status'|head -c 200",timeout=15,get_pty=True)
print('  Status:',d3.read().decode(errors='replace')[:200])
_,d4,_=C.exec_command("docker ps --filter name=evo-nginx --format '{{.Names}} {{.Status}}'",timeout=10,get_pty=True)
print('  Docker:',d4.read().decode(errors='replace')[:150])
_,d5,_=C.exec_command("curl -s -m 5 http://127.0.0.1:8080/ 2>/dev/null|head -c 80",timeout=10,get_pty=True)
print('  HTTP:',d5.read().decode(errors='replace')[:80])

C.close()
