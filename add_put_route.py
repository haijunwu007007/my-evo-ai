import sys, paramiko, time
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# routes_hub already has PUT route from local file
# Test it
_,o,_=C.exec_command("curl -s -X PUT 'http://127.0.0.1:8765/api/v1/hub/composes/3e274bfe4708' -H 'Content-Type: application/json' -d '{\"name\":\"test-put\",\"nodes\":[\"a\"],\"edges\":[]}'",timeout=10,get_pty=True)
print("PUT:",o.read().decode(errors='replace')[:200])
# Test all
tests=[('Hub','/hub'),('Canvas','/canvas'),('Compose','/api/v1/hub/composes'),('Discover','/api/v1/hub/discover?source=gitee'),('Projects','/api/v1/hub/projects')]
for n,p in tests:
    _,r,_=C.exec_command(f'curl -s --max-time 10 "http://127.0.0.1:8765{p}" 2>/dev/null|head -1',timeout=15,get_pty=True)
    o=r.read().decode(errors='replace').strip()[:60]
    ok=o.startswith('{') or o.startswith('<')
    print(f'{"✅" if ok else "❌"} {n}: {o[:50]}')
C.close()
