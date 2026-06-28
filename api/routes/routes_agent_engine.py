"""🧠 自主Agent引擎 V2 — LLM自动识别意图 → 注入外部SKILL.md → 多步技能执行 → 汇总结果

关键改进:
1. 启动时扫描 ~/.workbuddy/skills/ 下所有外部 Skill（含 auto-discovered 和市场）
2. 任务规划: LLM 获得完整 Skill 目录（含描述）+ 注入匹配 SKILL.md 内容
3. 执行: 先试 /api/v1/skills/{name}/execute, 降级则读 SKILL.md 注入 LLM 自主执行
4. 汇总: LLM 自动整理多步结果
5. 快速通道: 简单查询直接返回，不走LLM规划
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import json, time, asyncio, httpx, os
from pathlib import Path

logger = get_logger("evo.api.agent_engine")
router = APIRouter()

# ── 外部 Skill 目录扫描 ──
_SKILL_CATALOG: list[dict] = []

def _scan_external_skills():
    catalog = []
    search_dirs = [
        Path.home() / ".workbuddy" / "skills" / "auto-discovered",
        Path.home() / ".workbuddy" / "skills",
    ]
    for base_dir in search_dirs:
        if not base_dir.exists():
            continue
        for skill_dir in base_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            meta_json = skill_dir / "_meta.json"
            if not skill_md.exists():
                continue
            try:
                md_content = skill_md.read_text(encoding="utf-8", errors="replace")
                stars = 0
                category = ""
                if meta_json.exists():
                    try:
                        meta = json.loads(meta_json.read_text(encoding="utf-8"))
                        stars = meta.get("stars", 0)
                        category = meta.get("category", "")
                    except Exception:
                        pass
                desc = ""
                for line in md_content.splitlines():
                    line = line.strip()
                    if line.startswith("description:") or line.startswith("name:"):
                        desc = line.split(":", 1)[-1].strip()
                    if desc and len(desc) > 5:
                        break
                if not desc:
                    desc = skill_dir.name
                catalog.append({
                    "name": skill_dir.name,
                    "description": desc[:200],
                    "stars": stars,
                    "category": category,
                })
            except Exception as e:
                logger.warning(f"[AgentEngine] 扫描 Skill 失败: {skill_dir.name} - {e}")
    return catalog

try:
    _SKILL_CATALOG = _scan_external_skills()
except Exception:
    pass

# ── 任务状态存储 ──
_AGENT_TASKS: dict = {}

class AgentRunRequest(BaseModel):
    task: str
    context: Optional[list] = None

class AgentStatusRequest(BaseModel):
    task_id: str

# 快速通道：无需LLM规划的简单查询
_FAST_TRACK = {
    "系统状态": "直接调用 /api/v1/status 返回系统运行状态",
    "系统怎么样": "直接调用 /api/v1/status 返回系统运行状态",
    "查看版本": "直接调用 /api/v1/version 返回版本信息",
    "版本": "直接调用 /api/v1/version 返回版本信息",
    "健康检查": "直接调用 /api/v1/health 返回健康状态",
    "模块列表": "直接调用 /api/v1/modules 返回所有模块",
}

async def _fast_track(task: str) -> dict | None:
    """快速通道：对简单查询直接调用API，不走LLM"""
    action = None
    for k, v in _FAST_TRACK.items():
        if k in task:
            action = v
            break
    if not action:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            path = "/api/v1/status"
            if "版本" in task or "version" in task:
                path = "/api/v1/version"
            elif "健康" in task or "health" in task or "health" in task.lower():
                path = "/api/v1/health"
            elif "模块" in task or "modules" in task.lower():
                path = "/api/v1/modules"
            r = await c.get(f"http://127.0.0.1:8765{path}", timeout=10)
            return {"result": r.text, "path": path}
    except Exception:
        return None

@router.post("/api/v1/agent/run")
async def agent_run(req: AgentRunRequest):
    task = req.task.strip()
    task_id = f"task-{int(time.time()*1000)}-{os.urandom(3).hex()}"
    _AGENT_TASKS[task_id] = {"task": task, "status": "starting", "progress": 0, "result": "", "steps": [], "total_steps": 0}

    try:
        # ── 0. 快速通道：简单查询直奔API ──
        fast = await _fast_track(task)
        if fast:
            _AGENT_TASKS[task_id]["status"] = "completed"
            _AGENT_TASKS[task_id]["progress"] = 100
            _AGENT_TASKS[task_id]["result"] = fast["result"]
            return {"success": True, "task_id": task_id, "result": fast["result"]}

        # ── 1. 构建 Skill 目录 ──
        skill_list = "\n".join(
            f"  - {s['name']}: {s['description'][:120]}" + (f" (⭐{s['stars']})" if s['stars'] else "")
            for s in _SKILL_CATALOG[:50]
        )

        # ── 2. LLM 规划（限时20s）──
        plan_prompt = f"""你是一个AI任务规划器。分析任务: "{task}"
可用技能目录（共{len(_SKILL_CATALOG)}个）:
{skill_list if skill_list else "（无外部技能，使用内置工具）"}
内置工具: search/翻译/计算/文档生成/PPT/Excel/代码生成/系统状态/待办/GitHub/爬虫

请列出需要执行的步骤（最多3步），每步格式: "步骤号. 技能名: 操作描述"
返回JSON数组: [{{"step":1,"tool":"技能名","action":"操作描述"}}]
如果任务匹配某个外部Skill，优先使用它。"""

        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post("http://127.0.0.1:8765/api/v1/smart",
                json={"message": plan_prompt, "lang": "zh-CN"})
            plan_data = r.json().get("result", "[]")

        import re
        steps = []
        try:
            steps = json.loads(plan_data)
        except (json.JSONDecodeError, TypeError):
            try:
                arr_match = re.search(r'\[.*?\]', plan_data, re.DOTALL)
                if arr_match:
                    steps = json.loads(arr_match.group())
            except Exception:
                pass

        if not steps:
            steps = [{"step": 1, "tool": "search", "action": f"搜索关于'{task}'的信息"},
                     {"step": 2, "tool": "chat", "action": f"总结搜索结果并回答: {task}"}]

        _AGENT_TASKS[task_id]["steps"] = steps
        _AGENT_TASKS[task_id]["total_steps"] = len(steps)

        # ── 3. 依次执行（每步限时20s）──
        results = []
        for i, step in enumerate(steps):
            _AGENT_TASKS[task_id]["status"] = f"执行步骤 {i+1}/{len(steps)}"
            _AGENT_TASKS[task_id]["progress"] = int((i / len(steps)) * 100)

            tool = step.get("tool", "chat")
            action = step.get("action", task)

            step_result = await _execute_step(tool, action, task)
            results.append({"step": i+1, "tool": tool, "action": action, "result": str(step_result)[:500]})

        _AGENT_TASKS[task_id]["status"] = "completed"
        _AGENT_TASKS[task_id]["progress"] = 100

        # ── 4. LLM 汇总（限时15s）──
        summary_prompt = f"任务: {task}\n执行结果:\n" + "\n".join(
            f"步骤{r['step']}({r['tool']}): {r['result'][:200]}" for r in results)

        async with httpx.AsyncClient(timeout=15) as c:
            sr = await c.post("http://127.0.0.1:8765/api/v1/smart",
                json={"message": f"请用中文总结以下执行结果:\n{summary_prompt}", "lang": "zh-CN"})
            summary = sr.json().get("result", "执行完成")

        _AGENT_TASKS[task_id]["result"] = summary
        return {"success": True, "task_id": task_id, "result": summary}

    except asyncio.TimeoutError:
        _AGENT_TASKS[task_id]["status"] = "timeout"
        err_msg = "Agent引擎执行超时，任务太复杂或LLM响应慢，请简化描述后重试"
        _AGENT_TASKS[task_id]["result"] = err_msg
        return {"success": False, "task_id": task_id, "error": err_msg}
    except Exception as e:
        _AGENT_TASKS[task_id]["status"] = "failed"
        err_msg = str(e) or "Agent引擎内部错误，请稍后重试"
        _AGENT_TASKS[task_id]["result"] = err_msg
        return {"success": False, "task_id": task_id, "error": err_msg}


async def _execute_step(tool: str, action: str, original_task: str) -> str:
    """执行单一步骤 — 优先调用外部Skill，降级到内置工具"""
    smart_msg = action

    # 尝试外部 Skill
    for skill in _SKILL_CATALOG:
        if tool.lower() in skill["name"].lower() or skill["name"].lower() in tool.lower():
            try:
                async with httpx.AsyncClient(timeout=20) as c:
                    r = await c.post(
                        f"http://127.0.0.1:8765/api/v1/skills/{skill['name']}/execute",
                        json={"params": {"action": action, "task": original_task}, "context": {}},
                        timeout=15
                    )
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("success"):
                            result = data.get("result", "")
                            if result:
                                return result[:3000]
            except Exception:
                pass

    # 降级：注入 SKILL.md 让 LLM 自主执行
    for skill in _SKILL_CATALOG:
        if tool.lower() in skill["name"].lower() or skill["name"].lower() in tool.lower():
            md = skill.get("skill_md_content", "")
            if md:
                smart_msg = f"""你是一个AI助手，请使用以下技能完成任务。

## 技能名称: {skill['name']}
## 技能说明:
{md[:2000]}
## 任务:
{action}

请按照技能说明逐步完成任务，返回执行结果。"""
            break

    async with httpx.AsyncClient(timeout=20) as c:
        sr = await c.post("http://127.0.0.1:8765/api/v1/smart",
            json={"message": smart_msg, "lang": "zh-CN"})
        sd = sr.json()
        return sd.get("result", sd.get("detail", "完成"))[:3000]


@router.post("/api/v1/agent/skill-prepare")
async def skill_prepare(req: AgentRunRequest):
    """为任务准备最匹配的Skill（不执行，只返回Skill信息）"""
    task = req.task
    best = None
    for skill in _SKILL_CATALOG:
        kw = task.lower()
        if any(w in skill["name"].lower() or w in skill["description"].lower() for w in kw.split()):
            if best is None or len(skill["description"]) > len(best["description"]):
                best = skill
    if not best:
        return {"success": False, "result": "未找到匹配的Skill"}
    prompt = f"""分析以下任务最适合哪个技能:\n任务: {task}\n\n候选技能: {best['name']} - {best['description'][:200]}\n\n请返回YES或NO，以及一个短理由。"""
    async with httpx.AsyncClient(timeout=15) as c:
        sr = await c.post("http://127.0.0.1:8765/api/v1/smart",
            json={"message": prompt, "lang": "zh-CN"})
        return {"success": True, "skill": best["name"], "analysis": sr.json().get("result", "已分析")}


@router.get("/api/v1/agent/status/{task_id}")
async def agent_status(task_id: str):
    """查询Agent任务执行状态"""
    if task_id not in _AGENT_TASKS:
        return {"success": False, "error": "任务不存在"}
    t = _AGENT_TASKS[task_id]
    return {"success": True, "task_id": task_id, "status": t["status"],
            "progress": t["progress"], "result": t["result"]}


@router.get("/api/v1/agent/tasks")
async def agent_tasks():
    """列出所有Agent任务"""
    return {"success": True, "tasks": [
        {"task_id": tid, "task": t["task"][:50], "status": t["status"],
         "progress": t["progress"]} for tid, t in _AGENT_TASKS.items()
    ]}
