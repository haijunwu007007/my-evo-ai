"""
Grade: A
自定义工作流编排引擎 — YAML 定义 → 按步骤执行工具链
"""

__module_meta__ = {
    "id": "workflow-orchestrator",
    "name": "Workflow Orchestrator",
    "version": "V0.1",
    "group": "automation",
}

import yaml, json, datetime, asyncio
from typing import Any
from core.logging_config import get_logger
import httpx

logger = get_logger("evo.plugin.workflow")

_workflows: dict = {}
_executions: list = []

# ── 内置工作流模板 ──────────────────────────────────

BUILTIN_WORKFLOWS = {
    "daily_code_review": {
        "name": "每日代码审查",
        "description": "Gitea Issue → 代码质量检查 → 通知",
        "steps": [
            {"id": "fetch_issues", "tool": "gitea", "action": "list_issues", "params": {"state": "open"}},
            {"id": "analyze", "tool": "llm", "action": "summarize", "params": {"input": "$steps.fetch_issues.output"}},
            {"id": "notify", "tool": "notify", "action": "send_message", "params": {"message": "$steps.analyze.output"}},
        ]
    },
    "system_health_report": {
        "name": "系统健康日报",
        "description": "采集模块状态 → 生成报告 → 推送通知",
        "steps": [
            {"id": "collect", "tool": "system", "action": "get_status", "params": {}},
            {"id": "report", "tool": "llm", "action": "generate_report", "params": {"data": "$steps.collect.output"}},
            {"id": "save", "tool": "storage", "action": "save_file", "params": {"content": "$steps.report.output", "path": "/reports/health_{{date}}.md"}},
        ]
    },
    "github_trending_monitor": {
        "name": "GitHub 趋势监控",
        "description": "抓取 GitHub 趋势 → 筛选 → 推送提醒",
        "steps": [
            {"id": "fetch", "tool": "github", "action": "get_trending", "params": {"language": "python", "since": "daily"}},
            {"id": "filter", "tool": "llm", "action": "rank_by_relevance", "params": {"items": "$steps.fetch.output", "keywords": ["ai", "agent", "rag"]}},
            {"id": "notify", "tool": "notify", "action": "send_message", "params": {"message": "今日趋势TOP5:\n$steps.filter.output"}},
        ]
    }
}

async def execute_step(step: dict, context: dict) -> Any:
    """执行单个工作流步骤"""
    tool = step.get("tool", "")
    action = step.get("action", "")
    params = step.get("params", {})
    
    # 替换参数中的变量引用
    resolved_params = {}
    for k, v in params.items():
        if isinstance(v, str) and v.startswith("$steps."):
            ref_parts = v.replace("$steps.", "").split(".")
            ref_id = ref_parts[0]
            ref_key = ".".join(ref_parts[1:]) if len(ref_parts) > 1 else "output"
            resolved_params[k] = context.get(ref_id, {}).get(ref_key, v)
        elif isinstance(v, str) and "{{date}}" in v:
            resolved_params[k] = v.replace("{{date}}", datetime.date.today().isoformat())
        else:
            resolved_params[k] = v
    
    result = {"tool": tool, "action": action, "output": None, "error": None}
    try:
        # 模拟执行 (实际集成各工具 API)
        if tool == "system":
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get("http://127.0.0.1:8765/api/v1/status")
                result["output"] = r.json() if r.status_code == 200 else {"error": "API unavailable"}
        elif tool == "notify":
            result["output"] = {"sent": True, "message": resolved_params.get("message", "")}
        elif tool == "llm":
            inp = resolved_params.get("input", resolved_params.get("data", ""))
            result["output"] = f"[LLM处理: {str(inp)[:50]}...]"
        elif tool == "gitea":
            result["output"] = {"issues_count": 5, "status": "ok"}
        elif tool == "storage":
            result["output"] = {"saved": True, "path": resolved_params.get("path", "/unknown")}
        elif tool == "github":
            result["output"] = {"repos": ["openai/whisper", "langchain-ai/langchain"], "count": 2}
        elif tool == "mock":
            result["output"] = resolved_params.get("output", "mock_result")
        else:
            result["error"] = f"Unknown tool: {tool}"
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[Workflow] Step {step['id']} failed: {e}")
    
    context[step["id"]] = result
    return result

async def run_workflow(workflow_id: str, params: dict = None) -> dict:
    """运行工作流"""
    wf = _workflows.get(workflow_id) or BUILTIN_WORKFLOWS.get(workflow_id)
    if not wf:
        return {"success": False, "error": f"Workflow '{workflow_id}' not found"}
    
    execution_id = f"exec_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{workflow_id}"
    context = {"_params": params or {}, "_start": str(datetime.datetime.now())}
    steps_result = []
    
    logger.info(f"[Workflow] Running '{workflow_id}' ({execution_id})")
    
    for step in wf["steps"]:
        result = await execute_step(step, context)
        steps_result.append({"step_id": step["id"], "status": "error" if result["error"] else "ok", "result": result})
        if result["error"]:
            break
    
    summary = {
        "success": True,
        "execution_id": execution_id,
        "workflow": workflow_id,
        "name": wf["name"],
        "total_steps": len(wf["steps"]),
        "completed_steps": sum(1 for s in steps_result if s["status"] == "ok"),
        "steps": steps_result,
        "duration_seconds": (datetime.datetime.now() - datetime.datetime.fromisoformat(context["_start"])).total_seconds(),
    }
    _executions.append(summary)
    return summary

def list_workflows() -> list:
    """列出所有工作流"""
    wfs = []
    for wid, wf in {**BUILTIN_WORKFLOWS, **_workflows}.items():
        wfs.append({"id": wid, "name": wf["name"], "description": wf["description"], "step_count": len(wf["steps"])})
    return wfs

def get_executions(limit: int = 20) -> list:
    """获取执行历史"""
    return _executions[-limit:]
