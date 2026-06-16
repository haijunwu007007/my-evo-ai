import sys, paramiko, time, json
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def req(method,path,data=None):
    d=json.dumps(data) if data else ''
    c=f'curl -s -m 10 -X {method} "http://127.0.0.1:8765{path}" -H "Content-Type: application/json"'
    if d: c+=f" -d '{d}'"
    _,o,_=C.exec_command(c,timeout=15,get_pty=True)
    return o.read().decode(errors='replace')[:500]
# Test compose create
cid="test-comp-1"
r=req('POST','/api/v1/hub/composes',{"id":cid,"name":"AI测试组合","nodes":["ollama","webui"],"edges":[{"from":"ollama","to":"webui"}]})
print("Create:",r[:200])
r2=req('GET','/api/v1/hub/composes')
print("List:",r2[:300])
r3=req('GET',f'/api/v1/hub/composes/{cid}')
print("Get:",r3[:200])
r4=req('DELETE',f'/api/v1/hub/composes/{cid}')
print("Delete:",r4[:200])
C.close()
