#!/usr/bin/env python3
import paramiko, time, json
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=30,banner_timeout=60)

def req(method,path,data=None,t=120):
    d=json.dumps(data) if data else ''
    cmd=f'curl -s --max-time {t} -X {method} "http://127.0.0.1:8765{path}" -H "Content-Type: application/json"'
    if d: cmd+=f" -d '{d}'"
    _,o,_=C.exec_command(cmd,timeout=t+15,get_pty=True)
    return o.read().decode(errors='replace')

# 1. Add real project that has docker-compose
print("=== 1. Add Portainer ===")
r1=req('POST','/api/v1/hub/projects',{"id":"portainer","name":"Portainer","source":"docker","repo_url":"","description":"Docker管理面板","category":"infra","tags":["docker","management"]},15)
print(r1[:200])

# 2. Deploy with real docker run
print("\n=== 2. Deploy Portainer ===")
r2=req('POST','/api/v1/hub/projects/portainer/integrate',{"port":9000,"detected":1},60)
print(r2[:500])

# 3. Check running
time.sleep(5)
_2=req('GET','/api/v1/hub/projects/portainer/status',{},15)
print(f"\n=== 3. Status ===")
print(_2[:500])

# 4. Check docker
_,o,_=C.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}'|grep -i portainer",timeout=10,get_pty=True)
print(f"\n=== 4. Container ===")
print(o.read().decode(errors='replace')[:200])

# 5. Port test
_,o2,_=C.exec_command("curl -s -m 5 http://127.0.0.1:9000/ 2>/dev/null|head -c 100",timeout=10,get_pty=True)
print(f"\n=== 5. HTTP access ===")
print(o2.read().decode(errors='replace')[:100])

C.close()
