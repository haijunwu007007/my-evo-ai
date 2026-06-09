import requests as r, time, json

BASE = 'http://127.0.0.1:8765'

# 1. 核心端点
endpoints = [
    ('/api/v1/status', 'core status'),
    ('/api/v1/health', 'health'),
    ('/api/v1/version', 'version'),
    ('/api/v1/metrics', 'metrics'),
    ('/api/v1/skills', 'skills'),
    ('/api/v1/agent/catalog', 'agent catalog'),
    ('/api/v1/i18n/langs', 'i18n'),
    ('/api/v1/events', 'events'),
]

oks = 0
fails = 0
for path, name in endpoints:
    t0 = time.time()
    try:
        resp = r.get(BASE+path, timeout=10)
        elapsed = time.time()-t0
        ok = resp.status_code < 400
        if ok:
            oks += 1
            print('OK', name, f'{elapsed*1000:.0f}ms')
        else:
            fails += 1
            print('FAIL', name, resp.status_code)
    except Exception as e:
        fails += 1
        print('FAIL', name, str(e)[:40])

# 2. Agent catalog
c = r.get(BASE+'/api/v1/agent/catalog', timeout=10).json()
skills = c.get('skills', [])
print(f'Agent external skills: {c.get("total",0)}')

# 3. Smart chat routing
for msg in ['帮我用ollama跑模型', '系统怎么样']:
    t0 = time.time()
    resp = r.post(BASE+'/api/v1/smart', json={'message': msg, 'lang': 'zh-CN'}, timeout=30)
    d = resp.json()
    elapsed = time.time()-t0
    mode = d.get('mode', 'core')
    ok = d.get('success', False)
    print('OK' if ok else 'FAIL', mode, msg, f'{elapsed:.1f}s')

# 4. Frontend pages
for p in ['/', '/dashboard', '/workflow']:
    resp = r.get(BASE+p, timeout=10)
    print('OK' if resp.status_code<400 else 'FAIL', p, resp.status_code)

print(f'Result: {oks}/{oks+fails} passed')
