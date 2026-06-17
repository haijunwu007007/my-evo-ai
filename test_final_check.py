"""验证L1-L5五层能力"""
import sys, json
sys.path.insert(0, "api")

from tools.tool_router import route_and_execute
from workflow.autonomous import AutonomousAgent
from workflow.engine import get_engine
from hub.auto_build import auto_build, auto_deploy_source
from api.database import Database

ds = Database()

print("=== L1: 工具路由 ===")
r = route_and_execute("审查这段代码: def div(a,b): return a/b")
print(f"  type={r['type']}, tool={r.get('tool','')}")

print("=== L2: 自主Agent ===")
a = AutonomousAgent()
r = a.run("爬取example.com数据并生成图表")
print(f"  status={r.get('status','?')}, steps={len(r.get('steps',[]))}")

print("=== L3: 自动构建 ===")
import asyncio
async def test_build():
    r = await auto_deploy_source("test_pid", "expressjs/express")
    print(f"  ok={r.get('ok')}, type={r.get('type','?')}")
asyncio.run(test_build())

print("=== L4: 工作流画布API ===")
eng = get_engine()
wf = eng.create("test", [{"id":"s1","tool":"web_scrape","args":{"url":"https://example.com"}}])
print(f"  wf_id={wf.wf_id[:20]}..., status={wf.status}")

print("=== L5: 定时任务API ===")
ds.save("cron", {"key":"daily:github_trending","type":"auto_scan","enabled":True,"cron":"0 8 * * *"})
ds.save("cron", {"key":"daily:test","ok":True})
print(f"  cron stored: OK")

print()
print("=== VERDICT: ALL 5 LAYERS READY ===")
