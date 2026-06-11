import httpx
base = 'https://122.51.144.227'
paths = {
    '对话': '/',
    '仪表盘': '/dashboard',
    '仪表盘(v2)': '/index.html',
    '企业管理': '/app/login',
    '管理后台': '/admin.html',
}
for name, path in paths.items():
    try:
        r = httpx.get(base+path, verify=False, timeout=10, follow_redirects=True)
        print(f'{name:15s} {r.status_code} {len(r.text):>6}b  {path}')
    except Exception as e:
        print(f'{name:15s} ERR {str(e)[:40]}  {path}')
