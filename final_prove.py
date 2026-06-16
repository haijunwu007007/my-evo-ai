import sys, paramiko, time
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# Test git clone + docker-compose with n8n (lightweight, has docker-compose)
pid='test-n8n'
data='{"id":"'+pid+'","name":"n8n","source":"github","repo_url":"https://github.com/n8n-io/n8n","description":"Workflow automation","category":"devtools","config":{"strategy":"docker"}}'
# Add
C.exec_command(f'curl -s -X POST http://127.0.0.1:8765/api/v1/hub/projects -H "Content-Type: application/json" -d \'{data}\'',timeout=10,get_pty=True)
# Deploy (git clone + docker-compose)
_,r,_=C.exec_command(f'curl -s --max-time 600 -X POST http://127.0.0.1:8765/api/v1/hub/projects/{pid}/integrate -H "Content-Type: application/json" -d \'{{"strategy":"docker","port":5678}}\'',timeout=610,get_pty=True)
out=r.read().decode(errors='replace')[:800]
print('Deploy:',out)
time.sleep(5)
# Status
_,r2,_=C.exec_command(f'curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/projects/{pid}/status',timeout=10,get_pty=True)
print('Status:',r2.read().decode(errors='replace')[:400])
# docker ps
_,r3,_=C.exec_command("docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'|head -5",timeout=10,get_pty=True)
print('\nRunning containers:')
print(r3.read().decode(errors='replace')[:300])
# Compose deploy test
comp_data='{"name":"测试组合","nodes":["p1","p2"],"strategy":"docker-compose"}'
_,r4,_=C.exec_command(f'curl -s --max-time 30 -X POST http://127.0.0.1:8765/api/v1/hub/composes -H "Content-Type: application/json" -d \'{comp_data}\'',timeout=35,get_pty=True)
print('\nCompose:',r4.read().decode(errors='replace')[:200])
C.close()
