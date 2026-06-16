"""虚拟公司 — Agent部门引擎"""
from __future__ import annotations
import json, time, random, httpx
from core.logging_config import get_logger

logger = get_logger("evo.hub.company")

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
        result[key] = {
            "name": dept["name"], "emoji": dept["emoji"],
            "agent": dept["agent"], "status": "active" if key=="cto" else "idle",
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
    targets = [department] if department else list(DEPARTMENTS.keys())
    results = []
    for dept_key in targets:
        dept = DEPARTMENTS[dept_key]
        for task in dept.get("tasks", []):
            if task.get("status") != "pending": continue
            # 模拟执行（实际可调LLM）
            task["status"] = "running"
            time.sleep(0.5)
            task["status"] = "done"
            task["result"] = f"✅ {task['content'][:30]}... 已完成"
            results.append({"department": dept_key, "task_id": task["id"], "result": task["result"]})
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
