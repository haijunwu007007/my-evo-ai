"""虚拟公司 — API路由（集成智能体编排器）"""
from fastapi import APIRouter
import json, httpx, asyncio
from core.logging_config import get_logger
from api.hub.company import get_status, assign_task, execute_tasks, get_stats, DEPARTMENTS

logger = get_logger("evo.api.company")
router = APIRouter(prefix="/api/v1/company")

@router.get("/status")
async def company_status():
    return {"success": True, **get_status()}

@router.get("/stats")
async def company_stats():
    return {"success": True, **get_stats()}

@router.post("/task")
async def company_task(data: dict):
    dept = data.get("department", "")
    task = data.get("task", "")
    return await assign_task(dept, task)

@router.post("/execute")
async def company_execute(data: dict = {}):
    dept = data.get("department", "")
    return await execute_tasks(dept)

@router.post("/goal")
async def company_goal(data: dict):
    """接收目标 → CEO拆解→分发部门→执行"""
    goal = data.get("goal", "")
    if not goal:
        return {"success": False, "error": "需要目标"}

    logger.info(f"[公司] 新目标: {goal[:60]}")
    # 1. 用规划师Agent拆解目标为部门任务
    subtasks_response = []
    try:
        r = await asyncio.wait_for(httpx.AsyncClient(timeout=30).post(
            "http://localhost:8765/api/v1/agents/dispatch",
            json={"task": f"把以下目标拆解为各部门任务: {goal}", "agents": ["planner"], "mode": "auto"},
            timeout=30), timeout=30)
        d = r.json()
        if d.get("subtasks"):
            for s in d["subtasks"]:
                agent = s.get("agent", "")
                # 映射Agent到部门
                rev_map = {v:k for k,v in {"ceo":"planner","cto":"coder","coo":"analyst",
                                            "cmo":"analyst","design":"designer",
                                            "cs":"analyst","finance":"analyst","hr":"analyst"}.items()}
                dept_key = rev_map.get(agent, "cto")
                await assign_task(dept_key, s.get("action", goal))
                subtasks_response.append({"department": dept_key, "task": s.get("action","")})
    except:
        pass

    # 2. 执行所有部门任务
    results = await execute_tasks()
    return {"success": True, "goal": goal, "subtasks": subtasks_response, "results": results.get("results",[]), **get_stats()}

@router.post("/cycle")
async def company_cycle():
    """执行一轮所有部门任务"""
    results = await execute_tasks()
    return {"success": True, **results, **get_stats()}
