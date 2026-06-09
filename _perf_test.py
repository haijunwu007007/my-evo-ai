import requests, time, sys

BASE = 'http://127.0.0.1:8765'

endpoints = [
    '/', '/api/v1/status', '/api/v1/health', '/api/v1/metrics',
    '/api/v1/version', '/api/v1/skills', '/api/v1/skills/search?q=chat',
    '/api/v1/i18n?lang=zh-CN', '/api/v1/i18n/langs',
    '/api/v1/mcp/servers', '/api/v1/mcp/search?q=chat',
    '/api/v1/connectors', '/api/v1/gateway/templates',
    '/api/v1/mcpize/status', '/api/v1/a2a/agents',
    '/api/v1/rag/kb', '/api/v1/rag/documents',
    '/api/v1/public/usage',
    '/api/v1/config/items', '/api/v1/scheduler/status', '/api/v1/scheduler/tasks',
    '/api/v1/events', '/api/v1/diagnosis/health',
    '/api/v1/rest2mcp/tools', '/api/v1/insights/evolution',
    '/dashboard', '/workflow', '/scalar', '/sw.js', '/manifest.json',
]

ok, fail, slow = 0, 0, 0
times = []
for path in endpoints:
    t0 = time.time()
    try:
        r = requests.get(BASE + path, timeout=5)
        elapsed = time.time() - t0
        times.append(elapsed)
        if r.status_code < 400:
            ok += 1
            if elapsed > 0.5: slow += 1
            tag = 'OK'
        else:
            fail += 1
            tag = 'HTTP%d' % r.status_code
        print('%s %s %.0fms' % (path.ljust(35), tag.rjust(8), elapsed*1000))
    except Exception as e:
        elapsed = time.time() - t0
        fail += 1
        print('%s %s %.0fms %s' % (path.ljust(35), 'ERR'.rjust(8), elapsed*1000, str(e)[:40]))

print('')
print('PASS=%d FAIL=%d SLOW(>500ms)=%d' % (ok, fail, slow))
if times:
    print('AVG=%.0fms MIN=%.0fms MAX=%.0fms' % (sum(times)/len(times)*1000, min(times)*1000, max(times)*1000))
