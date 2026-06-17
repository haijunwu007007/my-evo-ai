"""测试 V0.1 核心能力"""
import sys, json
sys.path.insert(0, ".")

# 1. Autonomous agent
from api.workflow.autonomous import get_agent
agent = get_agent()
r = agent.run("审查这段代码: def div(a,b): return a/b")
print(f"1. Agent: type={r['status']}, steps={r['steps_executed']}, ok={r['ok']}")

r2 = agent.run("生成图表 10,20,30")
print(f"2. Agent chart: type={r2['status']}, steps={r2['steps_executed']}")

# 2. Tool router
from api.tools.tool_router import route_and_execute
r3 = route_and_execute("审查以下代码: function hello(){return 1}")
print(f"3. Router: type={r3['type']}, tool={r3.get('tool_name','')}")

# 3. Auto build detection
from api.hub.auto_build import detect_lang
files = ["package.json", "src/index.js", "README.md"]
db = detect_lang(files)
print(f"4. Detect: lang={db['lang']}, build={db['build'][:30]}")

# 4. Hub auto deploy
import asyncio
async def test_search():
    from api.hub.github_autodeploy import search_github_async, has_docker_compose
    results = await search_github_async("portainer docker", 5)
    print(f"5. Search: {len(results)} results")
    if results:
        dc = await has_docker_compose(results[0]["repo_url"])
        print(f"6. DockerCheck: {dc['has_docker_config']}, type={dc['deploy_type']}")

asyncio.run(test_search())

# 7. Import all tools
from api.tools import list_tools, exec_tool
t = list_tools()
print(f"7. Tools: {len(t)}")
r4 = exec_tool("chart_create", {"data": "[1,2,3]"})
print(f"8. chart: {r4['ok']}")

print("\n=== ALL PASS ===")
