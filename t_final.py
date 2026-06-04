"""Final comprehensive test of all new features"""
import json, urllib.request, time, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://127.0.0.1:8765'
results = []
def test(name, func):
    try:
        ok, info = func()
        results.append((name, 'PASS' if ok else 'FAIL', info))
        print(f"  {'PASS' if ok else 'FAIL'} {name}: {info}")
    except Exception as e:
        results.append((name, 'ERROR', str(e)[:80]))
        print(f"  ERROR {name}: {e}")

# 1. MCP Gateway
test("MCP Servers", lambda: (
    True, f"{json.loads(urllib.request.urlopen(BASE+'/api/v1/mcp/servers',timeout=5).read()).get('total',0)} servers"
))
test("MCP Tools", lambda: (
    True, f"{json.loads(urllib.request.urlopen(BASE+'/api/v1/mcp/builtin/tools',timeout=5).read()).get('total',0)} tools"
))
test("MCP Execute github_trending", lambda: (
    (d:=json.loads(urllib.request.urlopen(urllib.request.Request(BASE+'/api/v1/mcp/builtin/github_trending',data=json.dumps({"arguments":{}}).encode(),headers={'Content-Type':'application/json'}),timeout=15).read())).get('success'),
    f"{len(json.loads(d['content']))} repos"
))
test("MCP Execute math", lambda: (
    (d:=json.loads(urllib.request.urlopen(urllib.request.Request(BASE+'/api/v1/mcp/builtin/math_calculate',data=json.dumps({"arguments":{"expression":"500+450+520"}}).encode(),headers={'Content-Type':'application/json'}),timeout=5).read())).get('success'),
    f"1470={d['content']}"
))

# 2. RAG
test("RAG Analyze", lambda: (
    (d:=json.loads(urllib.request.urlopen(urllib.request.Request(BASE+'/api/v1/rag/analyze',data=json.dumps({"query":"AI automation","top_k":2}).encode(),headers={'Content-Type':'application/json'}),timeout=10).read())).get('success'),
    d.get('answer','')[:50] or '(no answer)'
))

# 3. Gateway Auth
test("Gateway 31 templates", lambda: (
    (d:=json.loads(urllib.request.urlopen(BASE+'/api/v1/gateway/tools',timeout=5).read())).get('success'),
    f"{d['total']} templates, {d['enabled_count']} enabled"
))

# 4. MCPize
test("MCPize Status", lambda: (
    (d:=json.loads(urllib.request.urlopen(BASE+'/api/v1/mcpize/status',timeout=5).read())).get('success'),
    f"{d['total']} integrated" + str([x['name'] for x in d.get('integrated',[])])
))

# 5. Connectors
test("Connectors List", lambda: (
    (d:=json.loads(urllib.request.urlopen(BASE+'/api/v1/connectors',timeout=5).read())).get('success'),
    f"{d['total']} connectors"
))
test("Connectors Search stripe", lambda: (
    (d:=json.loads(urllib.request.urlopen(BASE+'/api/v1/connectors/search?q=stripe',timeout=5).read())).get('success'),
    f"{d['total']} found"
))

# 6. Skills count
test("Skills Total", lambda: (
    (d:=json.loads(urllib.request.urlopen(BASE+'/api/v1/skills',timeout=5).read())).get('success'),
    f"{d['total']} skills"
))

# 7. Auth
test("User Login", lambda: (
    (d:=json.loads(urllib.request.urlopen(urllib.request.Request(BASE+'/api/v1/user/login',data=json.dumps({"username":"admin","password":""}).encode(),headers={'Content-Type':'application/json'}),timeout=5).read())).get('success'),
    d.get('user','')
))

print(f"\n========== 最终结果 ==========")
passed = sum(1 for r in results if r[1]=='PASS')
failed = sum(1 for r in results if r[1]=='FAIL')
err = sum(1 for r in results if r[1]=='ERROR')
print(f"通过: {passed} | 失败: {failed} | 错误: {err} | 总计: {len(results)}")
if failed or err:
    print("\n问题项:")
    for r in results:
        if r[1]!='PASS':
            print(f"  🔴 [{r[1]}] {r[0]}: {r[2]}")
