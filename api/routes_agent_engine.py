"""🧠 自主Agent引擎 — 任务→LLM规划→多步技能执行→结果"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import json, time, asyncio, httpx
from pathlib import Path

logger = get_logger("evo.api.agent_engine")
router = APIRouter()

_AGENT_TASKS = {}  # {task_id: {status, steps, result, progress}}

@router.post("/api/v1/agent/run")
async def agent_run(task: str = "", context: str = ""):
    """自主执行：LLM规划→调用技能→返回结果"""
    if not task:
        raise HTTPException(400, "需要提供任务描述")
    task_id = f"task-{int(time.time())}"
    
    _AGENT_TASKS[task_id] = {"status": "planning", "task": task, "steps": [], "result": None, "progress": 0}
    
    try:
        # 1. LLM 规划步骤
        plan_prompt = f"""你是一个AI任务规划器。分析任务: "{task}"
请列出需要执行的步骤（最多8步），每步格式: "步骤号. 工具名: 操作描述"
可用工具: 搜索/爬虫/GitHub热门/翻译/数学计算/文档生成/PPT/Excel/代码生成/系统状态/记忆/待办
返回JSON数组: [{{"step":1,"tool":"工具名","action":"操作描述"}}]"""
        
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post("http://127.0.0.1:8765/api/v1/smart",
                json={"message": plan_prompt, "lang": "zh-CN"})
            plan_data = r.json().get("result", "[]")
        
        # 解析规划
        import re
        steps = []
        try:
            steps = json.loads(plan_data)
        except:
            lines = plan_data.strip().split("\n")
            for i, line in enumerate(lines):
                m = re.search(r'["\']?step["\']?\s*:\s*(\d+)', line)
                t = re.search(r'["\']?tool["\']?\s*:\s*["\']([^"\']+)["\']', line)
                a = re.search(r'["\']?action["\']?\s*:\s*["\']([^"\']+)["\']', line)
                if m and t and a:
                    steps.append({"step": int(m.group(1)), "tool": t.group(1), "action": a.group(1)})
        
        if not steps:
            steps = [{"step": 1, "tool": "search", "action": f"搜索关于'{task}'的信息"},
                     {"step": 2, "tool": "chat", "action": f"总结搜索结果并回答: {task}"}]
        
        _AGENT_TASKS[task_id]["steps"] = steps
        _AGENT_TASKS[task_id]["total_steps"] = len(steps)
        
        # 2. 依次执行
        results = []
        for i, step in enumerate(steps):
            _AGENT_TASKS[task_id]["status"] = f"执行步骤 {i+1}/{len(steps)}"
            _AGENT_TASKS[task_id]["progress"] = int((i / len(steps)) * 100)
            
            tool = step.get("tool", "chat")
            action = step.get("action", task)
            
            # 映射到系统技能
            smart_msg = action
            if tool in ("search", "搜索"):
                smart_msg = f"帮我搜索: {action}"
            elif tool in ("crawl", "爬虫", "web"):
                smart_msg = f"爬取: {action}"
            elif tool in ("github", "trending"):
                smart_msg = "GitHub今天热门项目"
            elif tool in ("math", "计算"):
                smart_msg = f"计算: {action}"
            elif tool in ("translate", "翻译"):
                smart_msg = f"翻译: {action}"
            elif tool in ("doc", "文档", "word"):
                smart_msg = f"帮我写一份文档: {action}"
            elif tool in ("ppt",):
                smart_msg = f"帮我做一个PPT: {action}"
            elif tool in ("excel", "table"):
                smart_msg = f"帮我做表格: {action}"
            elif tool in ("code", "代码"):
                smart_msg = f"写代码: {action}"
            elif tool in ("status", "系统"):
                smart_msg = "系统怎么样"
            
            async with httpx.AsyncClient(timeout=60) as c:
                sr = await c.post("http://127.0.0.1:8765/api/v1/smart",
                    json={"message": smart_msg, "lang": "zh-CN"})
                sd = sr.json()
                step_result = sd.get("result", sd.get("detail", "完成"))
                results.append({"step": i+1, "tool": tool, "action": action, "result": step_result[:200]})
        
        _AGENT_TASKS[task_id]["status"] = "completed"
        _AGENT_TASKS[task_id]["progress"] = 100
        
        # 3. LLM 汇总结果
        summary_prompt = f"任务: {task}\n执行结果:\n" + "\n".join(
            f"步骤{r['step']}({r['tool']}): {r['result'][:100]}" for r in results)
        
        async with httpx.AsyncClient(timeout=30) as c:
            sr = await c.post("http://127.0.0.1:8765/api/v1/smart",
                json={"message": f"请用中文总结以下执行结果:\n{summary_prompt}", "lang": "zh-CN"})
            summary = sr.json().get("result", "执行完成")
        
        _AGENT_TASKS[task_id]["result"] = summary
        return {"success": True, "task_id": task_id, "steps": steps, "result": summary, "details": results}
    
    except Exception as e:
        _AGENT_TASKS[task_id]["status"] = "failed"
        _AGENT_TASKS[task_id]["result"] = str(e)
        return {"success": False, "task_id": task_id, "error": str(e)}

@router.get("/api/v1/agent/status/{task_id}")
async def agent_status(task_id: str):
    t = _AGENT_TASKS.get(task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    return {"success": True, "task": t}
