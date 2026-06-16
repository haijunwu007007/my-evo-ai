#!/usr/bin/env python3
import sys, paramiko, time, json
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=30,banner_timeout=60)
def req(method,path,data=None,t=15):
    d=json.dumps(data) if data else ''
    cmd=f'curl -s -m {t} -X {method} "http://127.0.0.1:8765{path}" -H "Content-Type: application/json"'
    if d: cmd+=f" -d '{d}'"
    _,o,_=C.exec_command(cmd,timeout=t+10,get_pty=True)
    return o.read().decode(errors='replace')

# Add portainer project
r=req('POST','/api/v1/hub/projects',{"id":"pt","name":"Portainer","source":"docker","category":"infra","config":"{\"port\":9010}"},10)
print(f"Add: {r[:80]}")
# Deploy on port 9010 (MinIO uses 9000)
r=req('POST','/api/v1/hub/projects/pt/integrate',{"port":9010,"image":"portainer/portainer-ce","detected":1},120)
print(f"Deploy: {r[:200]}")
time.sleep(5)
# Check
_,o,_=C.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}'|grep -i portainer",timeout=10,get_pty=True)
print(f"Docker: {o.read().decode(errors='replace')[:100]}")
_,o2,_=C.exec_command("curl -s -m 5 http://127.0.0.1:9010/ 2>/dev/null|head -c 80",timeout=10,get_pty=True)
print(f"Port 9010: {o2.read().decode(errors='replace')[:80]}")
C.close()
