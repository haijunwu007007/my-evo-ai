#!/usr/bin/env python3
import paramiko, time, json
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=30,banner_timeout=60)

def req(method,path,data=None,t=30):
    d=json.dumps(data) if data else ''
    cmd=f'curl -s --max-time {t} -X {method} "http://127.0.0.1:8765{path}" -H "Content-Type: application/json"'
    if d: cmd+=f" -d '{d}'"
    _,o,_=C.exec_command(cmd,timeout=t+10,get_pty=True)
    return o.read().decode(errors='replace')

# 1. Create compose with portainer + test projects
print("Create compose...")
r1=req('POST','/api/v1/hub/composes',{"name":"管理面板","description":"Portainer+Dashboard","nodes":["portainer"],"edges":[],"config":{"unified_port":9000}},15)
print(f"  {r1[:200]}")

# 2. Deploy compose as group
print("Deploy compose...")
r2=req('POST','/api/v1/hub/composes/deploy',{"name":"管理面板","nodes":["portainer"],"settings":{"unified_port":9000}},60)
print(f"  {r2[:500]}")

# 3. Check docker-compose
_,o,_=C.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}'|head -10",timeout=10,get_pty=True)
print(f"\nDocker:\n{o.read().decode(errors='replace')[:300]}")

# 4. Final all-endpoint check
_,o2,_=C.exec_command("curl -s -m 5 http://127.0.0.1:9000/ 2>/dev/null|head -c 80",timeout=10,get_pty=True)
print(f"Port 9000: {o2.read().decode(errors='replace')[:80]}")

C.close()
