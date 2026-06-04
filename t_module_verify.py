"""
AUTO-EVO-AI 全模块执行验证
逐个加载所有注册模块，调用其核心方法，确认真实可用性
"""
import sys, os, json, time, urllib.request, urllib.error
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://127.0.0.1:8765'
ok, fail, stub = 0, 0, 0
results = []

# 1. 先获取模块列表
try:
    status = json.loads(urllib.request.urlopen(f'{BASE}/api/v1/status', timeout=5).read())
    total = status.get('modules_total', 0)
    print(f'注册模块: {total}')
except Exception as e:
    print(f'无法连接API: {e}')
    sys.exit(1)

# 2. 已知有API端点的模块列表
MODULE_TESTS = [
    ("系统状态", "/api/v1/status", {}),
    ("MCP GitHub", "/api/v1/mcp/builtin/github_trending", {"arguments":{"limit":3}}),
    ("MCP Math", "/api/v1/mcp/builtin/math_calculate", {"arguments":{"expression":"1+1"}}),
    ("MCP System", "/api/v1/mcp/builtin/system_status", {}),
    ("MCP Web Search", "/api/v1/mcp/builtin/web_search", {"arguments":{"query":"AI","count":1}}),
    ("Skills列表", "/api/v1/skills", {}),
    ("Skills搜索", "/api/v1/skills/search?q=翻译", {}),
    ("Gateway工具", "/api/v1/gateway/tools", {}),
    ("Gateway审计", "/api/v1/gateway/audit", {}),
    ("A2A Agents", "/api/v1/a2a/agents", {}),
    ("REST2MCP", "/api/v1/rest2mcp/tools", {}),
    ("MCPize状态", "/api/v1/mcpize/status", {}),
    ("连接器", "/api/v1/connectors", {}),
    ("连接器搜索", "/api/v1/connectors/search?q=ai", {}),
    ("多租户", "/api/v1/tenant/projects", {}),
    ("分析摘要", "/api/v1/analytics/summary", {}),
    ("支付配置", "/api/v1/payment/config", {}),
    ("收益看板", "/api/v1/payment/revenue", {}),
    ("Webhook事件", "/api/v1/webhook/events", {}),
    ("用户登录", "/api/v1/user/login", {"username":"admin","password":""}),
    ("聊天历史", "/api/v1/chat/history?username=admin", {}),
    ("RAG查询", "/api/v1/rag/query", {"query":"AI"}),
    ("i18n中文", "/api/v1/i18n?lang=zh-CN", {}),
    ("公开API Key", "/api/v1/public/key/create", {"name":"test"}),
    ("公开用量", "/api/v1/public/usage", {}),
    ("定时任务", "/api/v1/scheduler/tasks", {}),
    ("插件列表", "/api/v1/plugins", {}),
    ("Agent引擎", "/api/v1/agent/run?task=hi", {}),
]

print(f'\n共 {len(MODULE_TESTS)} 个模块端点测试:\n')

for name, path, body in MODULE_TESTS:
    try:
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            f'{BASE}{path}',
            data=data,
            headers={'Content-Type':'application/json'} if body else {}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        
        if result.get('success', False):
            data_len = len(str(result.get('result', result.get('data', result))))
            print(f'  ✅ {name:20s} → success=true, data={data_len}chars')
            ok += 1
        else:
            print(f'  ⚠️  {name:20s} → success=false, {str(result.get("detail",""))[:60]}')
            fail += 1
    except urllib.error.HTTPError as e:
        print(f'  ❌ {name:20s} → HTTP {e.code}')
        fail += 1
    except Exception as e:
        print(f'  ❌ {name:20s} → {type(e).__name__}: {str(e)[:60]}')
        fail += 1

# 3. 静态文件验证
print('\n=== 静态页面 ===')
pages = ['/', '/admin', '/pricing', '/tutorial', '/public.html', '/manifest.json', '/sw.js', '/workflow', '/scalar']
for p in pages:
    try:
        r = urllib.request.urlopen(f'{BASE}{p}', timeout=5)
        code = r.status
        size = len(r.read())
        print(f'  {"✅" if code==200 else "❌"} {p:20s} → HTTP {code}, {size}B')
        if code == 200: ok += 1
        else: fail += 1
    except Exception as e:
        print(f'  ❌ {p:20s} → {type(e).__name__}')
        fail += 1

print(f'\n{"="*50}')
print(f'  结果: ✅ {ok} | ❌ {fail} | 总计 {ok+fail}')
print(f'  通过率: {ok*100//(ok+fail)}%')
if fail == 0:
    print(f'  等级: 🏆 全部可执行')
else:
    print(f'  等级: ⚠️ 有 {fail} 项异常')
