import sys, paramiko, json
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def t(m,p,d=None):
    try:
        c=f'curl -s -o /dev/null -w "%{{http_code}}" -m 5 -X {m} "http://127.0.0.1:8765{p}"'
        if d: c+=f' -H "Content-Type: application/json" -d \'{json.dumps(d)}\''
        _,r,_=C.exec_command(c,timeout=10,get_pty=True)
        code=r.read().decode(errors='replace').strip()
        return '200' if code=='200' else ('404' if code=='404' else (code if code else 'TIMEOUT'))
    except: return 'FAIL'

# 前端页面
pages={'Chat':'/','Hub':'/hub','Canvas':'/canvas','Fork':'/fork','Company':'/company','Tutorial':'/tutorial','Admin':'/admin'}
# 核心API
apis={'Status':'/api/v1/hub/discover?source=gitee','Projects':'/api/v1/hub/projects','Composes':'/api/v1/hub/composes','Templates':'/api/v1/hub/templates','CompanyAPI':'/api/v1/company/status','Health':'/api/v1/health'}
results={}
all_ok=True
print('\n=== 前端页面 ===')
for n,p in pages.items():
    r=t('GET',p); results[n]=r; mark='✅' if r=='200' else '❌'; print(f'{mark} {n}: {r}')
    if r!='200': all_ok=False
print('\n=== 核心API ===')
for n,p in apis.items():
    r=t('GET',p); results[n]=r; mark='✅' if r=='200' else '❌'; print(f'{mark} {n}: {r}')
    if r!='200': all_ok=False
# Post测试
print('\n=== 写入测试 ===')
for n,m,p,d in [('AddProject','POST','/api/v1/hub/projects',{"id":"check","name":"test","category":"web"}),('Compose','POST','/api/v1/hub/composes',{"name":"check-c","nodes":[]}),('Template','POST','/api/v1/hub/templates',{"name":"check-t","category":"ai"})]:
    r=t(m,p,d); results[n]=r
    if r=='200': results[n]='✅'; print(f'✅ {n}: 200')
    else: results[n]=r; print(f'❌ {n}: {r}'); all_ok=False
print(f'\n=== 结果: {"✅ 全部正常" if all_ok else "❌ 有失败"} ===')
# 如有失败明细
if not all_ok:
    for n,r in results.items():
        if r!='200': print(f'  ❌ {n}: {r}')
C.close()
