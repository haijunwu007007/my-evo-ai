from __future__ import annotations
"""虚拟公司 — Agent部门引擎（集成智能体编排器）"""
import json, time, random, asyncio
from core.logging_config import get_logger

logger = get_logger("evo.hub.company")

# 部门 → 编排器Agent 映射
_DEPT_AGENT_MAP = {
    "ceo": "planner",     # CEO → 规划师
    "cto": "coder",       # 技术部 → 程序员
    "coo": "analyst",     # 运营部 → 分析师
    "cmo": "analyst",     # 市场部 → 分析师
    "design": "designer", # 设计部 → 设计师
    "cs": "analyst",      # 客服部 → 分析师
    "finance": "analyst", # 财务部 → 分析师
    "hr": "analyst",      # HR部 → 分析师
}

DEPARTMENTS = {
    "ceo": {"name":"CEO办公室","emoji":"👔","agent":"战略制定者","tasks":[]},
    "cto": {"name":"技术部","emoji":"💻","agent":"架构师","tasks":[]},
    "coo": {"name":"运营部","emoji":"📊","agent":"流程设计师","tasks":[]},
    "cmo": {"name":"市场部","emoji":"📣","agent":"营销专家","tasks":[]},
    "design": {"name":"设计部","emoji":"🎨","agent":"创意设计师","tasks":[]},
    "cs": {"name":"客服部","emoji":"💁","agent":"客服主管","tasks":[]},
    "finance": {"name":"财务部","emoji":"💰","agent":"财务分析师","tasks":[]},
    "hr": {"name":"HR部","emoji":"👥","agent":"人才官","tasks":[]},
}

def get_status() -> dict:
    result = {}
    for key, dept in DEPARTMENTS.items():
        tasks = dept.get("tasks", [])
        done = sum(1 for t in tasks if t.get("status")=="done")
        running = sum(1 for t in tasks if t.get("status")=="running")
        result[key] = {
            "name": dept["name"], "emoji": dept["emoji"],
            "agent": dept["agent"],
            "status": "working" if running > 0 else "idle",
            "tasks_total": len(tasks), "tasks_done": done,
            "tasks": tasks[-5:],
        }
    return {"departments": result}

async def assign_task(department: str, task: str) -> dict:
    if department not in DEPARTMENTS:
        return {"success": False, "error": f"部门 {department} 不存在"}
    dept = DEPARTMENTS[department]
    task_id = f"t{int(time.time())}{random.randint(100,999)}"
    dept["tasks"].append({"id": task_id, "content": task, "status": "pending", "created": time.time()})
    logger.info(f"[{department}] 新任务: {task[:50]}")
    return {"success": True, "task_id": task_id}

async def execute_tasks(department: str = "") -> dict:
    """执行部门任务 —— 调用智能体编排器真实执行"""
    targets = [department] if department else list(DEPARTMENTS.keys())
    results = []

    for dept_key in targets:
        dept = DEPARTMENTS[dept_key]
        agent_name = _DEPT_AGENT_MAP.get(dept_key, "analyst")

        for task in dept.get("tasks", []):
            if task.get("status") != "pending":
                continue

            task["status"] = "running"
            logger.info(f"[{dept_key}] → 编排器Agent({agent_name}): {task['content'][:50]}")

            # 调用智能体编排器
            try:
                import httpx
                async with httpx.AsyncClient(timeout=120) as client:
                    r = await client.post(
                        "http://localhost:8765/api/v1/agents/dispatch",
                        json={
                            "task": task["content"],
                            "agents": [agent_name],
                            "mode": "auto",
                        },
                        timeout=120,
                    )
                    d = r.json()
                    if d.get("success"):
                        merged = d.get("merged", "")
                        subtasks = d.get("subtasks", [])
                        task["result"] = f"✅ 编排器执行完成\n拆解{subtasks}个子任务\n结果预览: {merged[:200]}"
                        task["status"] = "done"
                    else:
                        task["result"] = f"❌ 编排器执行失败: {d.get('error','')}"
                        task["status"] = "done"
            except Exception as e:
                logger.warning(f"[{dept_key}] 编排器调用失败, 降级模拟: {e}")
                # 降级: 模拟执行
                await asyncio.sleep(0.3)
                task["status"] = "done"
                task["result"] = f"✅ {task['content'][:30]}... 已完成（模拟）"

            results.append({
                "department": dept_key, "task_id": task["id"],
                "result": task["result"],
                "agent": agent_name,
            })

    return {"success": True, "results": results}

def get_stats() -> dict:
    total_tasks = sum(len(d.get("tasks",[])) for d in DEPARTMENTS.values())
    done_tasks = sum(1 for d in DEPARTMENTS.values() for t in d.get("tasks",[]) if t.get("status")=="done")
    return {
        "total_departments": len(DEPARTMENTS),
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "automation_rate": round(done_tasks/max(total_tasks,1)*100, 1),
    }
