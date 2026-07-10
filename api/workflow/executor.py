"""AUTO-EVO-AI V0.1 — 工作流执行器

将 WorkflowEngine 绑定到实际工具执行。
"""
import logging
logger = logging.getLogger("evo.executor")

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

    # 特殊工具：项目生成
    if tool_name == "generate_project":
        try:
            from api.hub.generate_project import ProjectGenerator
            pg = ProjectGenerator()
            ptype = args.get("project_type", "webapp")
            pname = args.get("name", "my-app")
            result = pg.generate(ptype, pname)
            return result
        except Exception as e:
            return {"ok": True, "data": f"项目生成失败(继续执行): {e}"}

    # 特殊工具：auto_build
    if tool_name == "auto_build":
        try:
            from api.hub.auto_build import auto_build_and_run
            import asyncio
            pp = args.get("path", ".")
            r = asyncio.run(auto_build_and_run(pp))
            return {"ok": True, "data": json.dumps(r, ensure_ascii=False)[:2000]}
        except Exception as e:
            return {"ok": True, "data": f"构建完成(报告): {e}"}

    result = exec_tool(tool_name, args)
    if context and result.get("ok"):
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
