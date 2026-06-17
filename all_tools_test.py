"""逐个测试所有87个工具是否正常导入和执行"""
import sys, json, time
sys.path.insert(0, "api")
from agent_tools import list_tools, exec_tool, _tools

tools = list_tools()
ok, fail = 0, 0
results = []

for t in tools:
    name = t["name"]
    cat = t["category"]
    try:
        r = exec_tool(name, {"test": True, "url": "https://example.com", "query": "test", "topic": "AI", "message": "Hello"})
        if r.get("ok") is not False:
            ok += 1
            status = "✅"
        else:
            fail += 1
            status = "❌"
        results.append(f"{status} {name:25s} | {cat:10s} | {r.get('data','')[:60]}")
    except Exception as e:
        fail += 1
        results.append(f"❌ {name:25s} | {cat:10s} | 崩溃: {str(e)[:60]}")

print(f"\n{'='*60}")
print(f"  工具测试结果: {len(tools)} 总 / {ok} 通过 / {fail} 失败")
print(f"{'='*60}")
for r in results:
    print(r)
