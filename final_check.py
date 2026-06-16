#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
time.sleep(15)
def r(c):
    _,o,_=C.exec_command(c,timeout=15,get_pty=True)
    time.sleep(0.5)
    try:return o.read().decode().strip()
    except:return ''
s=r("sudo systemctl is-active evo.service")
print(f"状态: {s}")
if s=='active':
    for n,p in [('Discover','/api/v1/hub/discover'),('Company','/api/v1/company/status'),('HubPage','/hub'),('Canvas','/canvas'),('Fork','/fork'),('CompanyPage','/company')]:
        c=r(f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:8765{p}")
        print(f"  {n}: {c}")
else:
    print(r("sudo journalctl -u evo --no-pager -n 5 2>/dev/null|tail -5"))
C.close()
