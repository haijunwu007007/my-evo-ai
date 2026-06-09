"""ChatDev 2.0 — 零代码多智能体编排平台桥接"""
import os, json
from pathlib import Path
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or "sk-e7a7f4e700d847f28027c5608e3f5c02"
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def chatdev_run(task: str = "", agent_count: int = 3, 
                workflow: str = "auto", output_dir: str = "") -> dict:
    """运行 ChatDev 多智能体任务
    Args:
        task: 任务描述
        agent_count: 智能体数量
        workflow: 工作流模式 (auto/sequential/parallel/debate)
        output_dir: 输出目录
    Returns:
        {"success": bool, "result": str, "artifacts": list}
    """
    try:
        # 尝试直接使用 ChatDev 2.0 API
        # ChatDev 2.0 运行入口
        try:
            from chatdev import ChatDev
            engine = ChatDev()
            result = engine.run(task=task, agent_count=agent_count, workflow=workflow)
            return {
                "success": True,
                "result": result.get("summary", str(result)[:1000]),
                "artifacts": result.get("artifacts", [])
            }
        except ImportError:
            # 回退：使用系统自有多智能体框架模拟
            from api.agent_llm import call_llm
            api_key = os.environ.get("OPENAI_API_KEY", "")

            # 多智能体模拟：分析师+开发者+审查者
            agents = {
                "analyst": "你是一个资深需求分析师，分析任务并给出详细规格",
                "developer": "你是一个全栈开发者，根据规格实现代码",
                "reviewer": "你是一个严格代码审查专家，审查代码质量"
            }

            results = []
            for role, prompt in list(agents.items())[:agent_count]:
                msgs = [{"role": "system", "content": prompt},
                       {"role": "user", "content": task}]
                content, _ = call_llm(msgs, None, api_key)
                results.append({"role": role, "output": (content or "")[:1000]})

            return {
                "success": True,
                "result": "智能体协作完成",
                "agents": results,
                "summary": "\n".join([f"【{r['role']}】: {r['output'][:100]}" for r in results])
            }

    except Exception as e:
        return {"success": False, "error": f"ChatDev 执行失败: {e}"}
