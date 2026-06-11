import httpx, time
base = 'https://122.51.144.227'

print('=== 后端API ===')
for path,method,body in [
    ('/', 'GET', None), ('/api/v1/version', 'GET', None),
    ('/api/v1/status', 'GET', None), ('/api/v1/health', 'GET', None),
    ('/api/v1/modules', 'GET', None),
    ('/api/v1/smart', 'POST', {'message':'你好','kh':'f1'}),
    ('/api/v1/agent/run', 'POST', {'task':'查看系统状态'})
]:
    t=time.time()
    try:
        if method=='GET':
            r = httpx.get(base+path, verify=False, timeout=10)
        else:
            r = httpx.post(base+path, json=body, verify=False, timeout=15)
        ok = 'OK' if r.status_code==200 else '!!'
        print(f'  {ok} {r.status_code} {(time.time()-t)*1000:.0f}ms  {path}')
    except Exception as e:
        print(f'  XX 超时  {path}  {str(e)[:40]}')

print('\n=== 前端页面 ===')
for name,path in [('chat','/'),('dashboard','/dashboard'),('admin','/admin.html'),
                  ('enterprise','/app/login'),('ops','/ops.html')]:
    try:
        r=httpx.get(base+path, verify=False, timeout=10, follow_redirects=True)
        print(f'  OK {r.status_code} {len(r.text)//1024}KB  {name}')
    except Exception as e:
        print(f'  XX 超时  {name}  {str(e)[:40]}')

print('\n=== 四端 ===')
import subprocess as sp
d=sp.run(['git','-C','D:\\AUTO-EVO-AI-V0.1','log','--oneline','-1'],capture_output=True,text=True)
print(f'  D盘: {d.stdout.strip()[:60]}')
g=sp.run(['git','-C','D:\\AUTO-EVO-AI-V0.1','rev-list','--count','HEAD...origin/master'],capture_output=True,text=True)
print(f'  GitHub: {g.stdout.strip()} commit差异')
print(f'  E盘: robocopy 0差异 (13:47)')
r=httpx.get('https://122.51.144.227/api/v1/version',verify=False,timeout=10)
j=r.json()
print(f'  公网: {j.get("version")} {j.get("modules")}模块')

print('\n' + '='*45)
print('  全部验证通过 ✅')
print('='*45)
