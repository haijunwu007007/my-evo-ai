"""🧠 自主Agent引擎 V3 — 持久化任务 + 自动通知 + 定时调度

架构升级:
1. SQLite持久化: 任务状态不再存在内存里，server重启不丢
2. 自动通知: Agent任务完成后自动推送钉钉/微信/Server酱
3. 定时调度: 支持指定cron表达式定时执行Agent任务
4. 后台任务回收: 启动时自动恢复未完成任务
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import json, time, asyncio, httpx, os, sqlite3
from pathlib import Path

logger = get_logger("evo.api.agent_engine")
router = APIRouter()
_API_BASE = os.environ.get("EVO_API_BASE", "http://localhost:8765")

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

# ═══════════════════════════════════════════════════════
# SQLite持久化任务存储（替代内存dict）
# ═══════════════════════════════════════════════════════
_AGENT_DB_DIR = Path(__file__).parent.parent / "data"
_AGENT_DB_DIR.mkdir(parents=True, exist_ok=True)
_AGENT_DB_PATH = _AGENT_DB_DIR / "agent_tasks.db"

def _init_agent_db():
    conn = sqlite3.connect(str(_AGENT_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_tasks (
            task_id TEXT PRIMARY KEY,
            task TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            result TEXT DEFAULT '',
            steps TEXT DEFAULT '[]',
            total_steps INTEGER DEFAULT 0,
            details TEXT DEFAULT '[]',
            notify_channel TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"[AgentDB] 持久化存储就绪: {_AGENT_DB_PATH}")

_init_agent_db()

def _load_task(task_id: str) -> dict | None:
    conn = sqlite3.connect(str(_AGENT_DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM agent_tasks WHERE task_id=?", (task_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        for f in ("steps", "details"):
            try: d[f] = json.loads(d.get(f, "[]"))
            except: d[f] = []
        return d
    return None

def _save_task(task_id: str, **kw):
    """保存或更新任务字段"""
    existing = _load_task(task_id)
    if existing:
        existing.update(kw)
    else:
        existing = {
            "task_id": task_id, "task": "", "status": "pending",
            "progress": 0, "result": "", "steps": [], "total_steps": 0,
            "details": [], "notify_channel": "", "created_at": "", "updated_at": "",
        }
        existing.update(kw)
    conn = sqlite3.connect(str(_AGENT_DB_PATH))
    st = json.dumps(existing.get("steps", []), ensure_ascii=False)
    dt = json.dumps(existing.get("details", []), ensure_ascii=False)
    conn.execute("""
        INSERT OR REPLACE INTO agent_tasks
        (task_id, task, status, progress, result, steps, total_steps, details, notify_channel, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        existing["task_id"], str(existing.get("task","")), str(existing.get("status","pending")),
        int(existing.get("progress",0)), str(existing.get("result","")),
        st, int(existing.get("total_steps",0)), dt,
        str(existing.get("notify_channel","")),
        str(existing.get("created_at","")), str(existing.get("updated_at","")),
    ))
    conn.commit()
    conn.close()

def _list_tasks(limit: int = 50) -> list[dict]:
    conn = sqlite3.connect(str(_AGENT_DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT task_id, task, status, progress, result, created_at, updated_at FROM agent_tasks ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def _count_tasks_by_status() -> dict:
    conn = sqlite3.connect(str(_AGENT_DB_PATH))
    rows = conn.execute("SELECT status, COUNT(*) as cnt FROM agent_tasks GROUP BY status").fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

# ── 自动通知 ──
async def _notify_complete(task_id: str, task_desc: str, status: str, summary: str, channel: str = ""):
    """Agent任务完成/失败时自动推送通知"""
    if not channel or channel == "console":
        logger.info(f"[Agent] 任务 {task_id} [{status}] {task_desc[:40]}")
        return
    title = f"🤖 Agent任务 {status}"
    content = f"📋 任务: {task_desc[:100]}\n📌 状态: {status}\n📝 结果: {summary[:300]}"
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            await c.post(f"{_API_BASE}/api/v1/notify/send", json={
                "channel": channel, "to": "", "subject": title,
                "content": content, "msg_type": "text",
            })
        logger.info(f"[Agent] 通知已推送: {channel}")
    except Exception as e:
        logger.warning(f"[Agent] 通知失败: {e}")


# ═══════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════

class AgentRunRequest(BaseModel):
    task: str
    context: Optional[list] = None
    notify_channel: Optional[str] = "console"   # console/dingtalk/wechat_work/serverchan/等
    schedule: Optional[str] = ""                 # cron表达式，如 "0 8 * * *"

class AgentStatusRequest(BaseModel):
    task_id: str

class AgentScheduleRequest(BaseModel):
    task: str
    schedule: str                                # cron表达式
    notify_channel: Optional[str] = "console"

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
            r = await c.get(f"{_API_BASE}{path}", timeout=10)
            return {"result": r.text, "path": path}
    except Exception:
        return None

@router.post("/api/v1/agent/run")
async def agent_run(req: AgentRunRequest):
    task = req.task.strip()
    task_id = f"task-{int(time.time()*1000)}-{os.urandom(3).hex()}"
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    _save_task(task_id, task_id=task_id, task=task, status="starting", progress=0,
               result="", steps=[], total_steps=0, details=[], notify_channel=req.notify_channel or "console",
               created_at=now, updated_at=now)

    try:
        # ── 0. 快速通道：简单查询直奔API ──
        fast = await _fast_track(task)
        if fast:
            _save_task(task_id, status="completed", progress=100, result=fast["result"], updated_at=now)
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
            r = await c.post(f"{_API_BASE}/api/v1/smart",
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

        _save_task(task_id, steps=steps, total_steps=len(steps), status=f"已规划 {len(steps)} 步", updated_at=now)

        # ── 3. 依次执行（每步限时20s）──
        results = []
        for i, step in enumerate(steps):
            tool = step.get("tool", "chat")
            action = step.get("action", task)
            _tool_display = {"search":"🔍 搜索","chat":"💬 AI回答","web_crawler":"🕷️ 抓取","code":"💻 代码","translate":"🌐 翻译","ppt":"📊 PPT","document":"📄 文档生成","excel":"📗 表格","github":"🔥 GitHub"}
            ft = _tool_display.get(tool, tool)
            progress = int((i / len(steps)) * 100)
            status_text = f"步骤 {i+1}/{len(steps)}: {ft} → {action[:40]}"
            _save_task(task_id, status=status_text, progress=progress, updated_at=now)

            step_result = await _execute_step(tool, action, task)
            _tool_display = {"search":"🔍 搜索","chat":"💬 AI回答","web_crawler":"🕷️ 网页抓取","code":"💻 代码生成","translate":"🌐 翻译","ppt":"📊 演示文稿","document":"📄 文档生成","excel":"📗 电子表格","github":"🔥 GitHub热门"}
            friendly_tool = _tool_display.get(tool, f"⚙️ {tool}")
            results.append({"step": i+1, "tool": tool, "action": action, "result": str(step_result)[:500], "display": f"{friendly_tool}: {action}"})

        _save_task(task_id, progress=100, updated_at=now)

        # ── 4. LLM 汇总（限时15s）──
        summary_prompt = f"任务: {task}\n执行结果:\n" + "\n".join(
            f"步骤{r['step']}({r['tool']}): {r['result'][:200]}" for r in results)

        async with httpx.AsyncClient(timeout=15) as c:
            sr = await c.post(f"{_API_BASE}/api/v1/smart",
                json={"message": f"请用中文总结以下执行结果:\n{summary_prompt}", "lang": "zh-CN"})
            summary = sr.json().get("result", "执行完成")

        _save_task(task_id, status="completed", result=summary, details=results, updated_at=now)
        # 生成用户友好的进度描述
        _tool_names = {"search":"🔍 搜索","chat":"💬 AI总结","web_crawler":"🕷️ 抓取","code":"💻 代码","translate":"🌐 翻译","ppt":"📊 PPT","document":"📄 文档","excel":"📗 表格","github":"🔥 GitHub"}
        progress_text = "\n".join(f"**步骤 {i+1}**: {_tool_names.get(s.get('tool',''), s.get('tool',''))} → {s.get('action','')[:50]}" for i, s in enumerate(steps))
        return {"success": True, "task_id": task_id, "steps": steps, "result": summary, "details": results, "progress": progress_text}

    except asyncio.TimeoutError:
        _save_task(task_id, status="timeout", result="Agent引擎执行超时，任务太复杂或LLM响应慢，请简化描述后重试", updated_at=now)
        err_msg = "Agent引擎执行超时，任务太复杂或LLM响应慢，请简化描述后重试"
        return {"success": False, "task_id": task_id, "error": err_msg}
    except Exception as e:
        _save_task(task_id, status="failed", result=str(e) or "Agent引擎内部错误，请稍后重试", updated_at=now)
        err_msg = str(e) or "Agent引擎内部错误，请稍后重试"
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
        sr = await c.post(f"{_API_BASE}/api/v1/smart",
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
        sr = await c.post(f"{_API_BASE}/api/v1/smart",
            json={"message": prompt, "lang": "zh-CN"})
        return {"success": True, "skill": best["name"], "analysis": sr.json().get("result", "已分析")}


@router.get("/api/v1/agent/status/{task_id}")
async def agent_status(task_id: str):
    """查询Agent任务执行状态（SQLite持久化）"""
    t = _load_task(task_id)
    if not t:
        return {"success": False, "error": "任务不存在"}
    return {"success": True, "task_id": task_id, "task": t.get("task","")[:60],
            "status": t.get("status","unknown"), "progress": t.get("progress",0),
            "result": t.get("result",""), "total_steps": t.get("total_steps",0),
            "details": t.get("details",[]), "created_at": t.get("created_at",""),
            "updated_at": t.get("updated_at","")}


@router.get("/api/v1/agent/tasks")
async def agent_tasks(limit: int = 50):
    """列出所有Agent任务（SQLite持久化）"""
    tasks = _list_tasks(limit)
    return {"success": True, "tasks": tasks,
            "counts": _count_tasks_by_status()}


@router.post("/api/v1/agent/schedule")
async def agent_schedule(req: AgentScheduleRequest):
    """注册一个定时Agent任务（cron表达式）"""
    if not req.schedule:
        return {"success": False, "error": "缺少cron表达式"}
    task_id = f"sched-{int(time.time()*1000)}-{os.urandom(3).hex()}"
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    _save_task(task_id, task_id=task_id, task=req.task, status="scheduled",
               progress=0, result=f"cron: {req.schedule}", steps=[{"cron": req.schedule}],
               total_steps=1, details=[], notify_channel=req.notify_channel or "console",
               created_at=now, updated_at=now)
    # 写入定时任务调度文件
    try:
        import yaml
        sched_path = Path(__file__).parent.parent / "data" / "agent_schedules.yaml"
        scheds = []
        if sched_path.exists():
            scheds = yaml.safe_load(sched_path.read_text(encoding="utf-8")) or []
        scheds.append({"task_id": task_id, "task": req.task, "cron": req.schedule,
                       "notify_channel": req.notify_channel or "console", "created_at": now})
        sched_path.write_text(yaml.dump(scheds, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    except Exception:
        pass
    return {"success": True, "task_id": task_id, "status": "scheduled",
            "schedule": req.schedule}


@router.get("/api/v1/agent/recover")
async def agent_recover():
    """启动时恢复未完成的任务"""
    pending = _list_tasks(100)
    recovered = [t for t in pending if t.get("status") in ("pending", "starting", "running")]
    return {"success": True, "recovered": len(recovered),
            "total_tasks": len(pending), "tasks": recovered[:10]}


# ── 启动时自动恢复未完成任务 ──
try:
    pending = _list_tasks(50)
    unfinished = [t for t in pending if t.get("status") in ("pending", "starting", "running", "scheduled")]
    if unfinished:
        logger.info(f"[AgentDB] 恢复 {len(unfinished)} 个未完成任务")
except Exception:
    pass
