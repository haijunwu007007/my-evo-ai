"""Workflow综合测试"""
import sys
sys.path.insert(0, "api")

from workflow.autonomous import AutonomousAgent, get_agent
from workflow.engine import WorkflowEngine, get_engine, Workflow
from workflow.executor import tool_executor, create_and_run, run_from_goal
from workflow.planner import create_planner_prompt, parse_steps

agent = get_agent()
engine = get_engine()

# 1. Planner: 任务分解
print("[1] Planner 任务分解:")
steps = agent.plan("爬取example.com数据并生成图表")
if steps.get("ok"):
    for s in steps["steps"]:
        print(f"  Step {s['id']}: {s['tool']}({s.get('args',{})})")
else:
    print(f"  (降级): {steps.get('error','')}")

# 2. Engine: 创建和执行工作流
print("\n[2] Engine 工作流:")
try:
    from workflow.engine import WorkflowStep
    wf = engine.create(name="test", steps=[{"id":"s1","tool":"chart_create","args":{"data":"[1,2,3]"},"label":"test"}])
    result = engine.execute(wf.wf_id)
    print(f"  Workflow ID: {wf.wf_id}")
    print(f"  Status: {result.get('status','?')}")
except Exception as e:
    print(f"  Error: {e}")

# 3. Executor: 工具执行
print("\n[3] Executor 工具执行:")
r = tool_executor("web_scrape", {"url": "https://example.com"})
print(f"  web_scrape: {r['ok']} ({len(r.get('data',''))} chars)")
r2 = tool_executor("chart_create", {"data": "[1,2,3]"})
print(f"  chart_create: {r2['ok']} ({len(r2.get('data',''))} chars)")

# 4. Autonomous Agent
print("\n[4] Autonomous Agent (多步):")
result = agent.run("爬取https://example.com数据并生成图表")
print(f"  Status: {result.get('status')}")
print(f"  Steps: {result.get('steps_executed',0)}/{result.get('steps_planned',0)}")
for s in result.get("plan", []):
    print(f"    {s.get('tool','?')}")

# 5. Single step
print("\n[5] Autonomous Agent (单步-降级匹配):")
result2 = agent.run("帮我审查这段代码: def div(a,b): return a/b")
print(f"  Status: {result2.get('status')}")
if result2.get("results"):
    print(f"  Result: {result2['results'][0][:100]}")

# 6. Chat fallback
print("\n[6] Autonomous Agent (纯聊天):")
result3 = agent.run("你好")
print(f"  Status: {result3.get('status')}")
print(f"  Result: {result3.get('result','')[:50]}")

print("\n=== DONE ===")
