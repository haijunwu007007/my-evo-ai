"""AUTO-EVO-AI V0.1 — 工作流执行器

将 WorkflowEngine 绑定到实际工具执行。
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.agent_tools import exec_tool
from api.workflow.engine import WorkflowEngine, get_engine

def tool_executor(tool_name: str, args: dict, context: dict = None) -> dict:
    """执行工具，支持上下文变量注入"""
    if context:
        resolved = {}
        for k, v in args.items():
            if isinstance(v, str) and v.startswith("$"):
                var_name = v[1:]
                resolved[k] = context.get(var_name, v)
            else:
                resolved[k] = v
        args = resolved
    result = exec_tool(tool_name, args)
    if context and result.get("ok"):
        # 自动注入结果到上下文
        context[f"_{tool_name}_result"] = result.get("data", "")
    return result

def create_and_run(goal: str, planner_result: dict) -> dict:
    """从规划结果创建工作流并执行"""
    from api.workflow.engine import WorkflowStep
    engine = get_engine()
    engine._tool_executor = tool_executor

    steps = planner_result.get("steps", [])
    wf = engine.create(
        name=goal[:50],
        steps=steps,
        description=goal,
    )
    return engine.execute(wf.wf_id)

def run_from_goal(goal: str, steps: list) -> dict:
    """直接根据步骤列表执行"""
    engine = get_engine()
    engine._tool_executor = tool_executor
    wf = engine.create(name=goal[:50], steps=steps, description=goal)
    return engine.execute(wf.wf_id)
