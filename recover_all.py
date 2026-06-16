#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=15):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()
# 复原
r("sudo git -C /home/ubuntu/my-evo-ai checkout -- api_server.py")
time.sleep(3)
# 用python写文件
_,o,_=C.exec_command("cat /home/ubuntu/my-evo-ai/api_server.py",timeout=10,get_pty=True)
lines=o.read().decode(errors='replace').split('\n')
nl=[]
for l in lines:
    nl.append(l)
    if 'from api.routes.routes_services import' in l:
        nl.append('from api.routes.routes_hub import router as hub_router')
        nl.append('from api.routes.hub_static import router as hub_static_router')
        nl.append('from api.routes.routes_company import router as company_router')
    if 'app.include_router(modules_router)' in l:
        nl.append('app.include_router(hub_router)')
        nl.append('app.include_router(hub_static_router)')
        nl.append('app.include_router(company_router)')
r("cat > /tmp/as.py << 'EOF'\n"+'\n'.join(nl)+"\nEOF")
r("sudo cp /tmp/as.py /home/ubuntu/my-evo-ai/api_server.py")
time.sleep(2)
r("sudo systemctl restart evo.service")
time.sleep(10)
print("状态:",r("sudo systemctl is-active evo.service"))
s=r("sudo systemctl is-active evo.service").strip()
if s=='active':
    for p in ['/api/v1/hub/discover','/api/v1/hub/projects','/api/v1/company/status','/hub','/company','/canvas','/fork']:
        _,o2,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
        print(f"  {p}: {o2.read().decode().strip()}")
else:
    print("日志:",r("sudo journalctl -u evo --no-pager -n 10 2>/dev/null|tail -10"))
C.close()
