# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 — 调度/事件/管线/队列 路由（引擎优先，退化到字典存储）"""
import importlib, logging, os, json, time, asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
logger = logging.getLogger("evo.api.scheduler")

from api._data_store import (
    _now, _next_id, _ts, _save_all,
    _scheduler_tasks_db, _events_db, _pipelines_db,
    _queue_tasks_db, _rules_db, _TASK_TEMPLATES,
)

router = APIRouter()

# ── 引擎层：优先加载核心引擎，失败时退化到字典存储 ──
HAS_SCHEDULER = False; _scheduler_instance = None
HAS_EVENTS = False; _event_engine = None
HAS_PIPELINE = False; _pipeline_engine = None
HAS_QUEUE = False; _queue_instance = None
SchedulerEngineCls = None; EventEngineCls = None
PipelineEngineCls = None; TaskQueueCls = None
_engine_tasks: List[asyncio.Task] = []

try:
    _sch = importlib.import_module("core.scheduler_engine")
    SchedulerEngineCls = getattr(_sch, "SchedulerEngine", None)
    if SchedulerEngineCls:
        _scheduler_instance = SchedulerEngineCls()
        HAS_SCHEDULER = True
        logger.info("[ENGINE] SchedulerEngine 加载成功")
except Exception as e:
    logger.warning(f"[ENGINE] SchedulerEngine 不可用: {e}, 退化到字典存储")

try:
    _evt = importlib.import_module("core.event_engine")
    EventEngineCls = getattr(_evt, "EventEngine", None)
    if EventEngineCls:
        _event_engine = EventEngineCls()
        HAS_EVENTS = True
        logger.info("[ENGINE] EventEngine 加载成功")
except Exception as e:
    logger.warning(f"[ENGINE] EventEngine 不可用: {e}")

try:
    _pip = importlib.import_module("core.pipeline_engine")
    PipelineEngineCls = getattr(_pip, "PipelineEngine", None)
    if PipelineEngineCls:
        _pipeline_engine = PipelineEngineCls()
        HAS_PIPELINE = True
        logger.info("[ENGINE] PipelineEngine 加载成功")
except Exception as e:
    logger.warning(f"[ENGINE] PipelineEngine 不可用: {e}")

try:
    _q = importlib.import_module("core.task_queue_engine")
    TaskQueueCls = getattr(_q, "TaskQueue", None)
    if TaskQueueCls:
        _queue_instance = TaskQueueCls()
        HAS_QUEUE = True
        logger.info("[ENGINE] TaskQueue 加载成功")
except Exception as e:
    logger.warning(f"[ENGINE] TaskQueue 不可用: {e}")


def start_engines() -> None:
    """启动所有已加载引擎的后台循环"""
    global _engine_tasks
    if HAS_SCHEDULER and hasattr(_scheduler_instance, 'start'):
        _engine_tasks.append(asyncio.create_task(_scheduler_instance.start(), name="scheduler-engine"))
    if HAS_EVENTS and hasattr(_event_engine, 'start'):
        _engine_tasks.append(asyncio.create_task(_event_engine.start(), name="event-engine"))
    if HAS_QUEUE and hasattr(_queue_instance, 'initialize'):
        _engine_tasks.append(asyncio.create_task(_queue_instance.initialize(), name="queue-init"))
    logger.info("[ENGINES] 调度器/事件引擎/任务队列 已启动")


def stop_engines() -> None:
    """停止所有引擎的后台循环"""
    for t in _engine_tasks:
        t.cancel()
    _engine_tasks.clear()


# ═══════════════════════════════════════════════════════════
# 调度器 — Scheduler
# ═══════════════════════════════════════════════════════════

@router.get("/api/scheduler/status")
async def scheduler_status():
    if HAS_SCHEDULER and _scheduler_instance:
        try:
            st = _scheduler_instance.get_stats() if hasattr(_scheduler_instance, 'get_stats') else {}
            return {"success": True, "running": True,
                    "active_tasks": st.get("active_tasks", len(_scheduler_tasks_db)),
                    "total_tasks": st.get("total_tasks", len(_scheduler_tasks_db)),
                    "engine": "core"}
        except Exception:
            pass
    active = sum(1 for t in _scheduler_tasks_db.values() if t.get("status") in ("active", "running"))
    return {"success": True, "running": True, "active_tasks": active,
            "total_tasks": len(_scheduler_tasks_db), "engine": "dict"}


@router.get("/api/scheduler/tasks")
async def scheduler_tasks():
    # 优先从引擎SQLite读（有15个持久化任务）
    try:
        import sqlite3, json
        _db = Path(".evo_data/scheduler/scheduler.db")
        if _db.exists():
            conn = sqlite3.connect(str(_db))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM scheduled_tasks ORDER BY created_at DESC").fetchall()
            conn.close()
            if rows:
                items = []
                for r in rows:
                    d = dict(r)
                    d['target_params'] = json.loads(d.get('target_params') or '{}')
                    items.append(d)
                    # 同步到内存字典
                    if d.get('id') not in _scheduler_tasks_db:
                        _scheduler_tasks_db[d['id']] = d
                return {"success": True, "tasks": items, "count": len(items), "running": True, "engine": "dict"}
    except Exception:
        pass
    # 字典兜底
    items = sorted(_scheduler_tasks_db.values(), key=lambda t: t.get("created_at", ""), reverse=True)
    return {"success": True, "tasks": items, "count": len(items), "running": True, "engine": "dict"}


@router.post("/api/scheduler/tasks")
async def scheduler_create(body: dict = None):
    body = body or {}
    tid = _next_id()
    task = {
        "id": tid, "name": body.get("name", f"任务{tid}"),
        "target_type": body.get("target_type", "module"),
        "target_id": body.get("target_id", ""),
        "cron": body.get("cron", ""),
        "status": "active",
        "created_at": _ts(), "last_run": "", "next_run": _ts(),
    }

    # 引擎路径：创建到SQLite，引擎tick_loop会自动调度
    if HAS_SCHEDULER and _scheduler_instance and SchedulerEngineCls:
        try:
            from core.scheduler_engine import ScheduledTask
            st = ScheduledTask(
                id=tid,
                name=body.get("name", f"任务{tid}"),
                schedule_type="cron" if body.get("cron") else "interval",
                cron_expr=body.get("cron", ""),
                interval_seconds=body.get("interval_seconds", 3600),
                target_type=body.get("target_type", "module"),
                target_id=body.get("target_id", ""),
                target_params={"action": body.get("action", "status"), **(body.get("params", {}) or {})},
                status="active",
            )
            _scheduler_instance.create_task(st)
            _scheduler_tasks_db[tid] = task; _save_all()  # 字典兜底
            return {"success": True, "task": task, "engine": "core"}
        except Exception as e:
            logger.warning(f"[ENGINE] SchedulerEngine.create_task 失败: {e}")

    # 字典路径
    _scheduler_tasks_db[tid] = task; _save_all()
    return {"success": True, "task": task, "engine": "dict"}


@router.post("/api/scheduler/tasks/{task_id}/toggle")
async def scheduler_toggle(task_id: str):
    if HAS_SCHEDULER and _scheduler_instance:
        try:
            if hasattr(_scheduler_instance, 'toggle_task'):
                _scheduler_instance.toggle_task(task_id)
                return {"success": True, "engine": "core"}
        except Exception:
            pass
    if task_id in _scheduler_tasks_db:
        t = _scheduler_tasks_db[task_id]
        t["status"] = "paused" if t.get("status") == "running" else "running"
        _save_all()
    return {"success": True}


@router.post("/api/scheduler/tasks/{task_id}/trigger")
async def scheduler_trigger(task_id: str):
    if HAS_SCHEDULER and _scheduler_instance:
        try:
            if hasattr(_scheduler_instance, 'trigger_task'):
                await _scheduler_instance.trigger_task(task_id)
            return {"success": True, "triggered": True, "engine": "core"}
        except Exception:
            pass
    if task_id in _scheduler_tasks_db:
        _scheduler_tasks_db[task_id]["last_run"] = _ts()
        _save_all()
    return {"success": True, "triggered": True}


@router.delete("/api/scheduler/tasks/{task_id}")
async def scheduler_delete(task_id: str):
    if HAS_SCHEDULER and _scheduler_instance:
        try:
            if hasattr(_scheduler_instance, 'remove_task'):
                _scheduler_instance.remove_task(task_id)
            return {"success": True, "engine": "core"}
        except Exception:
            pass
    _scheduler_tasks_db.pop(task_id, None); _save_all()
    return {"success": True}


# ═══════════════════════════════════════════════════════════
# 事件引擎 — Events
# ═══════════════════════════════════════════════════════════

@router.get("/api/events/stats")
async def events_stats():
    if HAS_EVENTS and _event_engine:
        try:
            st = _event_engine.get_stats() if hasattr(_event_engine, 'get_stats') else {}
            return {"success": True,
                    "total_events": st.get("total_events", len(_events_db)),
                    "total_rules": st.get("total_rules", len(_rules_db)),
                    "active_rules": st.get("active_rules", len(_rules_db)),
                    "events_last_hour": st.get("events_last_hour", 0),
                    "total_emitted": st.get("total_emitted", len(_events_db)),
                    "top_event_types": st.get("top_event_types", {"system": len(_events_db)}),
                    "watches": st.get("watches", 0), "subscribers": st.get("subscribers", 0),
                    "engine": "core"}
        except Exception:
            pass
    one_hour_ago = _now() - timedelta(hours=1)
    recent = [e for e in _events_db if e.get("timestamp", "") > one_hour_ago.isoformat()]
    return {"success": True, "total_events": len(_events_db), "total_rules": len(_rules_db),
            "active_rules": sum(1 for r in _rules_db.values() if r.get("enabled", True)),
            "events_last_hour": len(recent), "total_emitted": len(_events_db),
            "top_event_types": {"system": len(_events_db)}, "watches": 0, "subscribers": 0,
            "engine": "dict"}


@router.get("/api/events/rules")
async def events_rules():
    if HAS_EVENTS and _event_engine and hasattr(_event_engine, 'list_rules'):
        try:
            engine_rules = _event_engine.list_rules()
            if engine_rules:
                return {"success": True, "rules": engine_rules, "count": len(engine_rules), "engine": "core"}
        except Exception:
            pass
    rules = sorted(_rules_db.values(), key=lambda r: r.get("created_at", ""), reverse=True)
    return {"success": True, "rules": rules, "count": len(rules), "engine": "dict"}


@router.post("/api/events/rules")
async def events_rule_create(body: dict = None):
    rid = _next_id()
    rule = {"id": rid, "name": (body or {}).get("name", f"规则{rid}"),
            "pattern": (body or {}).get("pattern", "*"), "action": (body or {}).get("action", "notify"),
            "enabled": True, "created_at": _ts()}
    _rules_db[rid] = rule; _save_all()
    return {"success": True, "rule": rule}


@router.delete("/api/events/rules/{rule_id}")
async def events_rule_delete(rule_id: str):
    _rules_db.pop(rule_id, None); _save_all()
    return {"success": True}


# ═══════════════════════════════════════════════════════════
# 管线引擎 — Pipeline
# ═══════════════════════════════════════════════════════════

@router.get("/api/pipeline/status")
async def pipeline_status():
    if HAS_PIPELINE and _pipeline_engine and hasattr(_pipeline_engine, 'get_status'):
        try:
            s = _pipeline_engine.get_status()
            return {"success": True, **s, "engine": "core"} if isinstance(s, dict) else {"success": True, "running": True, "engine": "core"}
        except Exception:
            pass
    active = sum(1 for p in _pipelines_db.values() if p.get("status") == "running")
    return {"success": True, "running": True, "pipelines": list(_pipelines_db.values()), "active_count": active,
            "engine": "dict"}


@router.get("/api/pipelines")
async def pipelines_list():
    if HAS_PIPELINE and _pipeline_engine and hasattr(_pipeline_engine, 'list_pipelines'):
        try:
            pl = _pipeline_engine.list_pipelines()
            if pl:
                return {"success": True, "pipelines": pl, "count": len(pl), "engine": "core"}
        except Exception:
            pass
    items = sorted(_pipelines_db.values(), key=lambda p: p.get("created_at", ""), reverse=True)
    return {"success": True, "pipelines": items, "count": len(items), "engine": "dict"}


@router.get("/api/pipelines/stats")
async def pipelines_stats():
    total = len(_pipelines_db)
    active = sum(1 for p in _pipelines_db.values() if p.get("status") == "running")
    done = sum(1 for p in _pipelines_db.values() if p.get("status") == "completed")
    failed = sum(1 for p in _pipelines_db.values() if p.get("status") == "failed")
    return {"success": True, "total": total, "active": active, "completed": done, "failed": failed, "engine": "dict"}


@router.post("/api/pipelines")
async def pipelines_create(body: dict = None):
    pid = _next_id()
    pipe = {"id": pid, "name": (body or {}).get("name", f"管线{pid}"),
            "description": (body or {}).get("description", ""), "steps": (body or {}).get("steps", []),
            "status": "running", "created_at": _ts(), "last_run": "", "execution_count": 0}
    _pipelines_db[pid] = pipe
    return {"success": True, "pipeline": pipe, "engine": "dict"}


@router.post("/api/pipelines/{pipeline_id}/execute")
async def pipelines_execute(pipeline_id: str):
    if pipeline_id in _pipelines_db:
        _pipelines_db[pipeline_id]["last_run"] = _ts()
        _pipelines_db[pipeline_id]["execution_count"] += 1
    return {"success": True, "executed": True}


@router.delete("/api/pipelines/{pipeline_id}")
async def pipelines_delete(pipeline_id: str):
    _pipelines_db.pop(pipeline_id, None); _save_all()
    return {"success": True}


# ═══════════════════════════════════════════════════════════
# 任务队列 — Queue
# ═══════════════════════════════════════════════════════════

@router.get("/api/queue/stats")
async def queue_stats():
    if HAS_QUEUE and _queue_instance and hasattr(_queue_instance, 'get_stats'):
        try:
            qs = _queue_instance.get_stats()
            if isinstance(qs, dict) and qs:
                return {"success": True, **qs, "engine": "core"}
        except Exception:
            pass
    q = _queue_tasks_db
    total = len(q); pending = sum(1 for t in q.values() if t.get("status") == "pending")
    running = sum(1 for t in q.values() if t.get("status") == "running")
    failed = sum(1 for t in q.values() if t.get("status") == "failed")
    done = sum(1 for t in q.values() if t.get("status") == "completed")
    return {"success": True, "total": total, "pending": pending, "running": running,
            "failed": failed, "completed": done, "workers_active": min(running, 4), "max_workers": 4,
            "backlog": pending, "delayed": 0, "dead": failed, "total_processed": total,
            "engine": "dict"}


@router.get("/api/queue/tasks")
async def queue_tasks(limit: int = 30):
    items = sorted(_queue_tasks_db.values(), key=lambda t: t.get("created_at", ""), reverse=True)[:limit]
    return {"success": True, "tasks": items, "total": len(items), "engine": "dict"}


@router.get("/api/queue/pending")
async def queue_pending():
    pending = [t for t in _queue_tasks_db.values() if t.get("status") == "pending"]
    return {"success": True, "tasks": sorted(pending, key=lambda t: t.get("created_at", ""), reverse=True),
            "count": len(pending)}


@router.post("/api/queue/tasks")
async def queue_enqueue(body: dict = None):
    qid = _next_id()
    task = {"id": qid, "name": (body or {}).get("name", f"任务{qid}"),
            "type": (body or {}).get("type", "execute"), "target": (body or {}).get("target", ""),
            "status": "pending", "priority": (body or {}).get("priority", 0),
            "created_at": _ts(), "started_at": "", "completed_at": ""}
    _queue_tasks_db[qid] = task; _save_all()
    return {"success": True, "task": task, "engine": "dict"}


@router.post("/api/queue/tasks/{task_id}/cancel")
async def queue_cancel(task_id: str):
    if task_id in _queue_tasks_db:
        _queue_tasks_db[task_id]["status"] = "cancelled"; _save_all()
    return {"success": True}


@router.post("/api/queue/tasks/{task_id}/retry")
async def queue_retry(task_id: str):
    if task_id in _queue_tasks_db:
        _queue_tasks_db[task_id]["status"] = "pending"; _save_all()
    return {"success": True}


# ═══════════════════════════════════════════════════════════
# 工作流模板 — Templates
# ═══════════════════════════════════════════════════════════

@router.get("/api/templates")
async def templates_list():
    tpls = [{"id": k, **v} for k, v in _TASK_TEMPLATES.items()]
    return {"success": True, "templates": tpls, "count": len(tpls)}


@router.post("/api/templates/{template_id}/apply")
async def templates_apply(template_id: str):
    tpl = _TASK_TEMPLATES.get(template_id)
    if not tpl:
        return {"success": False, "error": f"模板不存在: {template_id}"}
    tid = _next_id()
    task = {
        "id": tid, "name": tpl["name"], "desc": tpl["desc"],
        "steps": tpl["steps"], "status": "active",
        "cron": "0 */4 * * *" if template_id == "github_trending" else "0 * * * *",
        "created_at": _ts(), "last_run": "", "next_run": _ts(),
    }

    # 通过引擎创建真实调度任务
    if HAS_SCHEDULER and _scheduler_instance and SchedulerEngineCls:
        try:
            from core.scheduler_engine import ScheduledTask
            st = ScheduledTask(
                id=tid,
                name=tpl["name"],
                schedule_type="cron",
                cron_expr=task["cron"],
                target_type="module",
                target_id=tpl.get("steps", [{}])[0].get("module", "githubtrending"),
                target_params={"action": "scan_trending", "language": "python", "period": "daily"},
                status="active",
            )
            _scheduler_instance.create_task(st)
        except Exception as e:
            logger.warning(f"[ENGINE] 模板创建任务失败: {e}")

    _scheduler_tasks_db[tid] = task; _save_all()
    return {"success": True, "task": task, "engine": "core" if HAS_SCHEDULER else "dict",
            "message": f"模板 '{tpl['name']}' 已应用"}
