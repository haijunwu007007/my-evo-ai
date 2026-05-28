"""测试 agent_planner — 覆盖 await 未写 bug"""
import sys, os, pytest, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

def test_agent_planner_async_dispatch():
    """bug-3: agent_planner 不能有协程未等待"""
    from modules.agent_planner import AgentPlanner
    p = AgentPlanner()
    from modules._base.planner_types import ExecutionStep
    step = ExecutionStep(step_id=1, module_name="githubtrending", action="trending", params={"language":"python"})
    try:
        import asyncio
        r = asyncio.run(p._call_module_execute(None, step))
    except Exception as e:
        err = str(e).lower()
        assert "coroutine" not in err, f"协程未等待: {e}"
        assert "await" not in err, f"缺少 await: {e}"
