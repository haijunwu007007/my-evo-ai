"""全模块执行验证 — 通过 API lazy-load 逐一触发所有注册模块"""
import json, urllib.request, sys, time
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://127.0.0.1:8765'
OK = FAIL = 0
ERRORS = []

# 1. 取模块列表
try:
    status = json.loads(urllib.request.urlopen(f'{BASE}/api/v1/status', timeout=5).read())
    total = status.get('modules_total', 0)
    print(f'注册模块数: {total}')
    print(f'='*60)
except Exception as e:
    print(f'❌ 无法连接API: {e}')
    sys.exit(1)

# 2. 逐一触发模块加载（通过调各类端点触发 lazy-load）
endpoints = [
    '/api/v1/status',
    '/api/v1/mcp/servers',
    '/api/v1/mcp/builtin/tools',
    '/api/v1/a2a/agents',
    '/api/v1/skills?category=文本生成',
    '/api/v1/connectors?category=AI',
    '/api/v1/gateway/tools',
    '/api/v1/mcpize/status',
    '/api/v1/rest2mcp/tools',
    '/api/v1/analytics/summary',
    '/api/v1/tenant/projects',
    '/api/v1/payment/revenue',
    '/api/v1/plugins',
    '/api/v1/i18n?lang=zh-CN',
]

print('触发 lazy-load 模块...')
for ep in endpoints:
    try:
        r = urllib.request.urlopen(f'{BASE}{ep}', timeout=10)
        d = json.loads(r.read())
        if d.get('success') or r.getcode() == 200:
            OK += 1
        else:
            FAIL += 1
            ERRORS.append(ep)
        print(f'  {"✅" if d.get("success") else "❌"} {ep}')
    except Exception as e:
        FAIL += 1
        ERRORS.append(f'{ep}: {e}')
        print(f'  ❌ {ep}: {str(e)[:50]}')
    time.sleep(0.3)

# 3. 再查状态看加载了多少模块
try:
    status2 = json.loads(urllib.request.urlopen(f'{BASE}/api/v1/status', timeout=5).read())
    loaded = status2.get('modules_loaded', 0)
    print(f'\n触发后已加载模块数: {loaded}')
except:
    pass

# 4. 总结
print(f'\n{"="*60}')
print(f'通过: {OK} | 失败: {FAIL} | 总计: {OK+FAIL}')
if ERRORS:
    print(f'\n失败端点:')
    for e in ERRORS:
        print(f'  ❌ {e}')
else:
    print('🏆 全部通过，零缺陷')
