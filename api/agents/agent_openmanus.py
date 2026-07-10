"""OpenManus — 通用Agent框架桥接"""
import logging
logger = logging.getLogger("evo.agent_openmanus")

import os, json
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def openmanus_run(task: str = "", mode: str = "auto", tools: list = None) -> dict:
    """运行 OpenManus 通用Agent任务
    Args:
        task: 任务描述
        mode: 执行模式 (auto/interactive/plan)
        tools: 可用工具列表
    Returns:
        {"success": bool, "result": str, "steps": list}
    """
    try:
        # 尝试导入 OpenManus
        try:
            from openmanus import ManusAgent
            agent = ManusAgent()
            if tools:
                agent.register_tools(tools)
            result = agent.run(task, mode=mode)
            return {
                "success": True,
                "result": result.get("output", str(result)[:1000]),
                "steps": result.get("steps", [])
            }
        except ImportError:
            # 回退：使用系统 agent_core
            from api.agent_core import create_engine, exec_tool
            from pathlib import Path
            from api.agent_llm import call_llm

            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                return {"success": False, "error": "需要设置 OPENAI_API_KEY"}

            BASE = Path(__file__).resolve().parent.parent.parent
            OUT = BASE / "output"
            TOOLS_DIR = OUT / "tools"
            MEM_DB = BASE / "data" / "mem.db"
            process = create_engine(BASE, OUT, TOOLS_DIR, MEM_DB)
            result = process(task, key=api_key)
            return result

    except Exception as e:
        return {"success": False, "error": f"OpenManus 执行失败: {e}"}
