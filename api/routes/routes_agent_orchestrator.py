"""
🔄 智能体编排器 — Agent 注册中心 + 跨平台任务分发 + 结果合并
支持国内(GLM/DeepSeek) + 开源(Ollama/Qwen) + 国外(OpenAI/Claude) 混合组队
"""
import json, time, re, threading, asyncio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import httpx

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# ===== Agent 注册中心 =====
_AGENT_REGISTRY = {}  # {name: {capabilities, llm, endpoint, status, ...}}
_TASK_QUEUE = {}      # {task_id: {status, subtasks, results, ...}}
_lock = threading.Lock()

DEFAULT_AGENTS = {
    "planner": {
        "name": "📋 规划师", "capabilities": ["task_decomposition", "project_planning"],
        "llm": "GLM-4-Flash", "endpoint": "internal", "status": "ready", "icon": "📋"
    },
    "coder": {
        "name": "💻 程序员", "capabilities": ["code_generation", "code_review", "debugging"],
        "llm": "DeepSeek", "endpoint": "internal", "status": "ready", "icon": "💻"
    },
    "designer": {
        "name": "🎨 设计师", "capabilities": ["ui_design", "css_styling", "visualization"],
        "llm": "GLM-4-Flash", "endpoint": "internal", "status": "ready", "icon": "🎨"
    },
    "reviewer": {
        "name": "🔍 审查员", "capabilities": ["code_review", "security_audit", "qa"],
        "llm": "DeepSeek", "endpoint": "internal", "status": "ready", "icon": "🔍"
    },
    "analyst": {
        "name": "📊 分析师", "capabilities": ["data_analysis", "reporting", "research"],
        "llm": "GLM-4-Flash", "endpoint": "internal", "status": "ready", "icon": "📊"
    },
    "deployer": {
        "name": "🚀 部署员", "capabilities": ["deployment", "docker", "nginx", "devops"],
        "llm": "DeepSeek", "endpoint": "internal", "status": "ready", "icon": "🚀"
    },
}
_AGENT_REGISTRY.update(DEFAULT_AGENTS)

class AgentRegister(BaseModel):
    name: str
    display_name: str
    capabilities: list[str]
    llm: str = "GLM-4-Flash"
    endpoint: str = "internal"
    icon: str = "🤖"

class TaskRequest(BaseModel):
    task: str
    agents: Optional[list[str]] = None  # 指定 Agent; None=自动分配
    mode: str = "auto"  # auto | parallel | serial

# ===== API =====

@router.get("/registry")
def list_agents():
    """列出所有已注册的智能体"""
    return {"success": True, "agents": {k: {kk: vv for kk, vv in v.items() if kk != "endpoint"} for k, v in _AGENT_REGISTRY.items()}}

@router.post("/registry")
def register_agent(data: AgentRegister):
    """注册新的智能体"""
    with _lock:
        _AGENT_REGISTRY[data.name] = {
            "name": data.display_name, "capabilities": data.capabilities,
            "llm": data.llm, "endpoint": data.endpoint, "status": "ready", "icon": data.icon
        }
    return {"success": True, "agent": data.name}

@router.delete("/registry/{name}")
def unregister_agent(name: str):
    with _lock:
        _AGENT_REGISTRY.pop(name, None)
    return {"success": True}

@router.post("/dispatch")
async def dispatch_task(data: TaskRequest):
    """接收任务 → 自动拆解 → 分派给Agent → 汇总结果"""
    task_id = f"T{int(time.time())}{len(_TASK_QUEUE)}"
    with _lock:
        _TASK_QUEUE[task_id] = {"task": data.task, "status": "decomposing", "subtasks": [], "results": {}, "progress": 0}

    # 1. 任务拆解 (调用 LLM)
    subtasks = await _decompose_task(data.task)
    with _lock:
        _TASK_QUEUE[task_id]["subtasks"] = subtasks
        _TASK_QUEUE[task_id]["status"] = "dispatching"
        _TASK_QUEUE[task_id]["total"] = len(subtasks)

    # 2. 分派给 Agent 执行
    results = await _execute_subtasks(task_id, subtasks, data.agents, data.mode)

    # 3. 结果合并
    merged = await _merge_results(data.task, results)

    with _lock:
        _TASK_QUEUE[task_id]["status"] = "completed"
        _TASK_QUEUE[task_id]["results"] = results
        _TASK_QUEUE[task_id]["merged"] = merged
        _TASK_QUEUE[task_id]["progress"] = 100

    return {"success": True, "task_id": task_id, "subtasks": subtasks, "merged": merged}

@router.get("/tasks")
def list_tasks():
    """查看所有任务"""
    return {"success": True, "tasks": {k: {"task": v["task"], "status": v["status"], "progress": v.get("progress",0), "subtask_count": len(v.get("subtasks",[]))} for k, v in _TASK_QUEUE.items()}}

@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    t = _TASK_QUEUE.get(task_id)
    if not t:
        return {"success": False, "error": "not found"}
    return {"success": True, "task": t}

# ===== 内部逻辑 =====

async def _decompose_task(task: str) -> list[dict]:
    """LLM 拆解任务为子任务"""
    prompt = f"""分析以下任务，拆解为3-6个子任务，每个子任务指定最合适的Agent类型。

可用Agent: {json.dumps(list(_AGENT_REGISTRY.keys()), ensure_ascii=False)}

任务: {task}

返回 JSON 数组 [{{"step": 序号, "agent": "agent名称", "action": "做什么", "expected": "期望输出"}}]"""
    try:
        import httpx
        r = await asyncio.wait_for(httpx.AsyncClient(timeout=30).post(
            "http://localhost:8765/api/v1/llm/chat",
            json={"messages": [{"role": "user", "content": prompt}], "model": "GLM-4-Flash"},
            timeout=30), timeout=30)
        txt = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        # 提取 JSON
        m = re.search(r'\[.*?\]', txt, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"[Orchestrator] decompose error: {e}")

    # 降级: 规则拆解
    if "博客" in task or "网站" in task or "page" in task.lower():
        return [
            {"step": 1, "agent": "planner", "action": "规划整体架构", "expected": "技术选型+页面结构"},
            {"step": 2, "agent": "designer", "action": "设计UI", "expected": "HTML/CSS 模板"},
            {"step": 3, "agent": "coder", "action": "编写前端页面", "expected": "完整 HTML/CSS/JS"},
            {"step": 4, "agent": "deployer", "action": "部署到服务器", "expected": "可访问 URL"},
        ]
    return [{"step": 1, "agent": "analyst", "action": "分析任务", "expected": "分析报告"}]

async def _execute_subtasks(task_id: str, subtasks: list, agent_filter: list[str] | None, mode: str) -> dict:
    """执行所有子任务"""
    results = {}
    for i, sub in enumerate(subtasks):
        agent_name = sub.get("agent", "analyst")
        if agent_filter and agent_name not in agent_filter:
            continue
        with _lock:
            if task_id in _TASK_QUEUE:
                _TASK_QUEUE[task_id]["status"] = f"agent_{agent_name}"
                _TASK_QUEUE[task_id]["progress"] = int((i / len(subtasks)) * 90)

        # 调用 LLM 执行子任务
        result = await _call_agent(agent_name, sub["action"], sub.get("expected", ""))
        results[f"step_{i+1}"] = {"agent": agent_name, "action": sub["action"], "result": result}

    return results

async def _call_agent(agent_name: str, action: str, expected: str) -> str:
    """调用指定 Agent 对应的 LLM 执行任务"""
    agent = _AGENT_REGISTRY.get(agent_name, {})
    prompt = f"""你是 Agent「{agent.get('name', agent_name)}」。
你的能力: {json.dumps(agent.get('capabilities', []), ensure_ascii=False)}
需要执行: {action}
期望输出: {expected}
请直接输出结果（代码/文本/步骤）。"""

    try:
        r = await asyncio.wait_for(httpx.AsyncClient(timeout=60).post(
            "http://localhost:8765/api/v1/llm/chat",
            json={"messages": [{"role": "user", "content": prompt}], "model": agent.get("llm", "GLM-4-Flash")},
            timeout=60), timeout=60)
        txt = r.json().get("choices", [{}])[0].get("message", {}).get("content", "（无响应）")
    except Exception as e:
        txt = f"（执行出错: {str(e)[:50]}）"

    # 如果 Agent 输出了代码，送入沙箱验证
    if "```" in txt and agent_name in ("coder", "deployer", "planner"):
        try:
            sr = await asyncio.wait_for(httpx.AsyncClient(timeout=120).post(
                "http://localhost:8765/api/v1/sandbox/run",
                json={"code": txt, "action": "install"}, timeout=120), timeout=120)
            sr_json = sr.json()
            if sr_json.get("success"):
                txt += "\n\n🛝 沙箱执行结果:\n" + str(sr_json.get("results", {}))
        except:
            pass

    return txt

async def _merge_results(task: str, results: dict) -> str:
    """合并所有 Agent 结果"""
    parts = []
    for k, v in results.items():
        parts.append(f"### {v['agent']}: {v['action']}\n{v['result']}\n")

    prompt = f"""原始任务: {task}

以下是各智能体的输出:
{chr(10).join(parts)}

请将这些结果合并为一份完整的交付报告。"""
    try:
        import httpx
        r = await asyncio.wait_for(httpx.AsyncClient(timeout=30).post(
            "http://localhost:8765/api/v1/llm/chat",
            json={"messages": [{"role": "user", "content": prompt}], "model": "GLM-4-Flash"},
            timeout=30), timeout=30)
        return r.json().get("choices", [{}])[0].get("message", {}).get("content", "（合并失败）")
    except:
        return "（合并失败）"
