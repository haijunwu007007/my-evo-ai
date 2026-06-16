import sys, paramiko, time, json
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def req(method,path,data=None,t=15):
    payload=json.dumps(data) if data else ''
    cmd=f'curl -s -m {t} -X {method} "http://127.0.0.1:8765{path}" -H "Content-Type: application/json"'
    if payload: cmd+=f" -d '{payload}'"
    _,o,_=C.exec_command(cmd,timeout=t+5,get_pty=True)
    return o.read().decode(errors='replace')[:600]
# 1. 发现
print("1.Discover:",req('GET','/api/v1/hub/discover')[:100])
# 2. 加项目
print("2.Add:",req('POST','/api/v1/hub/projects',{"id":"p-ollama","name":"Ollama","source":"github","category":"ai"})[:100])
# 3. 列出
print("3.List:",req('GET','/api/v1/hub/projects')[:100])
# 4. 创建组合
print("4.Compose:",req('POST','/api/v1/hub/composes',{"name":"Test-Comp","nodes":["p1","p2"]})[:100])
# 5. 列出组合
print("5.Composes:",req('GET','/api/v1/hub/composes')[:100])
# 6. 创建模板
print("6.Template:",req('POST','/api/v1/hub/templates',{"name":"AI平台","category":"ai"})[:100])
# 7. 列出模板
print("7.Templates:",req('GET','/api/v1/hub/templates')[:100])
# 8. 监控
print("8.Monitor:",req('GET','/api/v1/hub/monitor')[:100])
# 9. 公司
print("9.Company:",req('GET','/api/v1/company/status')[:100])
# 10. 项目状态
print("10.Status:",req('GET','/api/v1/hub/projects/p-ollama/status')[:100])
C.close()
