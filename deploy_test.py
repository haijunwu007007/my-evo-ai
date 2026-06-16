import sys, paramiko, time, json
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 1. Add project
pid="test-nginx"
data=json.dumps({"id":pid,"name":"nginx-proxy","source":"docker","repo_url":"https://github.com/nginx/nginx","description":"nginx web server (test)","category":"infra"})
_,o,_=C.exec_command(f'curl -s -X POST http://127.0.0.1:8765/api/v1/hub/projects -H "Content-Type: application/json" -d \'{data}\'',timeout=10,get_pty=True)
print("ADD:",o.read().decode(errors='replace')[:200])
# 2. Deploy
_,o2,_=C.exec_command(f'curl -s --max-time 60 -X POST http://127.0.0.1:8765/api/v1/hub/projects/{pid}/integrate -H "Content-Type: application/json" -d \'{{"port":8888}}\'',timeout=70,get_pty=True)
print("DEPLOY:",o2.read().decode(errors='replace')[:500])
# 3. Status
time.sleep(3)
_,o3,_=C.exec_command(f'curl -s http://127.0.0.1:8765/api/v1/hub/projects/{pid}/status -m 5',timeout=10,get_pty=True)
print("STATUS:",o3.read().decode(errors='replace')[:300])
C.close()
