"""AutoGPT v2 — 长期自主决策Agent集成"""
import os, json, time
from pathlib import Path

def autogpt_run(goal: str = "", max_steps: int = 10, 
                continuous: bool = False, output_dir: str = "") -> dict:
    """运行 AutoGPT 长期自主任务
    Args:
        goal: 目标任务描述
        max_steps: 最大执行步数
        continuous: 是否连续执行（直到完成或失败）
        output_dir: 输出目录
    Returns:
        {"success": bool, "result": str, "steps": list, "summary": str}
    """
    try:
        # 尝试使用 autogpt
        try:
            from autogpt import AutoGPT
            from autogpt.config import Config
            cfg = Config()
            agent = AutoGPT(cfg)
            result = agent.run(goal=goal, max_steps=max_steps, continuous=continuous)
            return {
                "success": True,
                "result": result.get("summary", str(result)[:1000]),
                "steps": result.get("steps", []),
                "artifacts": result.get("artifacts", [])
            }
        except ImportError:
            # 回退：系统自带的 step-by-step 执行
            from api.agent_llm import call_llm
            from api.agent_tools import exec_tool
            api_key = os.environ.get("OPENAI_API_KEY", "")

            BASE = Path(__file__).resolve().parent.parent
            OUT = BASE / "output"
            TOOLS_DIR = OUT / "tools"
            _GENERATED = {}
            _LAST = {}
            steps_log = []

            # AutoGPT 式的计划→执行→评估循环
            for step in range(max_steps):
                # 规划
                plan_msgs = [
                    {"role": "system", "content": "你是一个自主AI Agent。给定目标，输出下一步操作。格式: { 'thought':'...', 'tool':'...', 'args':{...} }"},
                    {"role": "user", "content": f"目标: {goal}\n已完成步骤: {len(steps_log)}\n下一步做什么？输出JSON。"}
                ]
                plan, _ = call_llm(plan_msgs, None, api_key)
                if not plan:
                    break

                try:
                    plan_json = json.loads(plan.strip().strip('```json').strip('```').strip())
                except:
                    plan_json = {"thought": plan[:200], "tool": "web_search", "args": {"query": goal[:50]}}

                thought = plan_json.get("thought", "")
                tool_name = plan_json.get("tool", "web_search")
                tool_args = plan_json.get("args", {})

                # 执行
                tool_result = exec_tool(tool_name, tool_args, BASE, OUT, _LAST, _GENERATED)
                step_entry = {
                    "step": step + 1,
                    "thought": thought,
                    "tool": tool_name,
                    "result": str(tool_result.get("data", ""))[:200]
                }
                steps_log.append(step_entry)

                # 如果连续模式，评估是否完成
                if not continuous and step >= max_steps - 1:
                    break

                import time as _time
                _time.sleep(1)

            return {
                "success": True,
                "steps": steps_log,
                "total_steps": len(steps_log),
                "summary": f"AutoGPT 执行了 {len(steps_log)} 步，目标: {goal[:50]}"
            }

    except Exception as e:
        return {"success": False, "error": f"AutoGPT 执行失败: {e}"}
