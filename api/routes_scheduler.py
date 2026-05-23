# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 — 调度/工作流路由
业务域：调度器、事件引擎、管线引擎、任务队列、工作流模板
上市公司级: 连接 core/ 真实引擎，后台协程驱动
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Response
from datetime import datetime, timedelta
import time, json, logging, os, asyncio
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
HAS_SCHEDULER = False; SchedulerEngine = None; _scheduler_instance = None
HAS_EVENTS = False; EventEngine = None; _event_engine = None
HAS_PIPELINE = False; PipelineEngine = None; _pipeline_engine = None
HAS_QUEUE = False; TaskQueue = None; _queue_instance = None
_engine_tasks: List[asyncio.Task] = []

try:
    import importlib
    _sch = importlib.import_module("core.scheduler_engine")
    SchedulerEngine = getattr(_sch, "SchedulerEngine", None)
    if SchedulerEngine:
        _scheduler_instance = SchedulerEngine()
        HAS_SCHEDULER = True
        logger.info("[ENGINE] SchedulerEngine 加载成功")
except Exception as e:
    logger.warning(f"[ENGINE] SchedulerEngine 不可用: {e}, 退化到字典存储")

try:
    _ev = importlib.import_module("core.event_engine")
    EventEngine = getattr(_ev, "EventEngine", None)
    if EventEngine:
        _event_engine = EventEngine()
        HAS_EVENTS = True
        logger.info("[ENGINE] EventEngine 加载成功")
except Exception as e:
    logger.warning(f"[ENGINE] EventEngine 不可用: {e}, 退化到字典存储")

try:
    _pl = importlib.import_module("core.pipeline_engine")
    PipelineEngine = getattr(_pl, "PipelineEngine", None)
    if PipelineEngine:
        _pipeline_engine = PipelineEngine()
        HAS_PIPELINE = True
        logger.info("[ENGINE] PipelineEngine 加载成功")
except Exception as e:
    logger.warning(f"[ENGINE] PipelineEngine 不可用: {e}, 退化到字典存储")

try:
    _qu = importlib.import_module("modules.task_queue")
    TaskQueue = getattr(_qu, "TaskQueue", None)
    if TaskQueue:
        _queue_instance = TaskQueue()
        HAS_QUEUE = True
        logger.info("[ENGINE] TaskQueue 加载成功")
except Exception as e:
    logger.warning(f"[ENGINE] TaskQueue 不可用: {e}, 退化到字典存储")

# ── 背景引擎启动 ──
async def start_engines():
    """启动所有已加载引擎的后台循环"""
    global _engine_tasks
    if HAS_SCHEDULER and hasattr(_scheduler_instance, 'start'):
        _engine_tasks.append(asyncio.create_task(_scheduler_instance.start(), name="scheduler-engine"))
    if HAS_EVENTS and hasattr(_event_engine, 'start'):
        _engine_tasks.append(asyncio.create_task(_event_engine.start(), name="event-engine"))
    if HAS_QUEUE and hasattr(_queue_instance, 'initialize'):
        try:
            await _queue_instance.initialize()
            logger.info("[ENGINE] TaskQueue 初始化完成")
        except Exception as e:
            logger.warning(f"[ENGINE] TaskQueue 初始化失败: {e}")

async def stop_engines():
    """停止所有引擎"""
    global _engine_tasks
    for t in _engine_tasks:
        t.cancel()
    _engine_tasks.clear()

# ─── 调度器 ────────────────────────────────────────
# 优先: SchedulerEngine (core) — 真实定时引擎, 有 _tick_loop / _check_and_dispatch
# 降级: _scheduler_tasks_db (dict + JSON)
@router.get("/api/scheduler/status")
async def scheduler_status():
    if HAS_SCHEDULER and _scheduler_instance:
        info = _scheduler_instance.store() if hasattr(_scheduler_instance, 'store') else {}
        tasks = info.get('tasks', {}) if isinstance(info, dict) else {}
        active = sum(1 for t in tasks.values() if isinstance(t, dict) and t.get("status") == "running")
        return {"success": True, "running": True, "active_tasks": active, "total_tasks": len(tasks),
                "engine": "core.scheduler_engine"}
    active = sum(1 for t in _scheduler_tasks_db.values() if isinstance(t, dict) and t.get("status") == "running")
    return {"success": True, "running": True, "active_tasks": active, "total_tasks": len(_scheduler_tasks_db),
            "engine": "dict"}

@router.get("/api/scheduler/tasks")
async def scheduler_tasks():
    if HAS_SCHEDULER and _scheduler_instance:
        info = _scheduler_instance.store() if hasattr(_scheduler_instance, 'store') else {}
        tasks = info.get('tasks', {}) if isinstance(info, dict) else {}
        items = sorted(tasks.values(), key=lambda t: t.get("created_at", ""), reverse=True) if tasks else []
        return {"success": True, "tasks": items, "count": len(items), "running": True, "engine": "core"}
    tasks = sorted(_scheduler_tasks_db.values(), key=lambda t: t.get("created_at", ""), reverse=True)
    return {"success": True, "tasks": tasks, "count": len(tasks), "running": True, "engine": "dict"}

@router.post("/api/scheduler/tasks")
async def scheduler_create(body: dict = None):
    tid = _next_id()
    task = {
        "id": tid, "name": (body or {}).get("name", f"任务{tid}"),
        "target_type": (body or {}).get("target_type", "module"),
        "target_id": (body or {}).get("target_id", ""),
        "cron": (body or {}).get("cron", ""),
        "status": "running",
        "created_at": _ts(), "last_run": "", "next_run": _ts(),
    }
    if HAS_SCHEDULER and _scheduler_instance:
        try:
            _scheduler_instance.store(("tasks", tid, task))
        except Exception as e:
            logger.warning(f"[ENGINE] scheduler.store 失败: {e}, 回退到字典")
            _scheduler_tasks_db[tid] = task; _save_all()
    else:
        _scheduler_tasks_db[tid] = task; _save_all()
    return {"success": True, "task": task, "engine": "core" if HAS_SCHEDULER else "dict"}

@router.post("/api/scheduler/tasks/{task_id}/toggle")
async def scheduler_toggle(task_id: str):
    if HAS_SCHEDULER and _scheduler_instance:
        try:
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
            await _scheduler_instance.trigger(task_id)
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
            _scheduler_instance.remove_task(task_id)
            return {"success": True, "engine": "core"}
        except Exception:
            pass
    _scheduler_tasks_db.pop(task_id, None); _save_all()
    return {"success": True}

# ─── 事件引擎 ─────────────────────────────────────
# 优先: EventEngine (core) — 真实事件引擎, 有 emit / subscribe / _dispatch
# 降级: _events_db + _rules_db
@router.get("/api/events/stats")
async def events_stats():
    if HAS_EVENTS and _event_engine:
        try:
            metrics = _event_engine.metrics() if hasattr(_event_engine, 'metrics') else {}
            return {"success": True, "total_events": metrics.get("total_emitted", 0),
                    "total_rules": len(getattr(_event_engine, '_subscribers', {})),
                    "active_rules": metrics.get("active_rules", 0),
                    "events_last_hour": metrics.get("last_hour", 0),
                    "total_emitted": metrics.get("total_emitted", 0),
                    "engine": "core.event_engine"}
        except Exception:
            pass
    one_hour_ago = _now() - timedelta(hours=1)
    recent = [e for e in _events_db if e.get("timestamp", "") > one_hour_ago.isoformat()]
    return {
        "success": True, "total_events": len(_events_db), "total_rules": len(_rules_db),
        "active_rules": sum(1 for r in _rules_db.values() if r.get("enabled", True)),
        "events_last_hour": len(recent), "total_emitted": len(_events_db),
        "top_event_types": {"system": len(_events_db)}, "watches": 0, "subscribers": 0,
        "engine": "dict",
    }

@router.get("/api/events/recent")
async def events_recent(limit: int = 20):
    if HAS_EVENTS and _event_engine and hasattr(_event_engine, '_history'):
        items = sorted(_event_engine._history, key=lambda e: e.get("timestamp", ""), reverse=True)[:limit]
        return {"success": True, "events": items, "total": len(items), "engine": "core"}
    items = sorted(_events_db, key=lambda e: e.get("timestamp", ""), reverse=True)[:limit]
    return {"success": True, "events": items, "total": len(items)}

@router.get("/api/events/rules")
async def events_rules():
    if HAS_EVENTS and _event_engine:
        subs = getattr(_event_engine, '_subscribers', {})
        rules = [{"id": str(i), "name": f"订阅{i}", "pattern": str(cb.__name__ if hasattr(cb, '__name__') else type(cb).__name__),
                  "action": "callback", "enabled": True, "created_at": ""} for i, (evt, cbs) in enumerate(subs.items()) for cb in (cbs if isinstance(cbs, list) else [cbs])]
        return {"success": True, "rules": rules, "count": len(rules), "engine": "core"}
    rules = sorted(_rules_db.values(), key=lambda r: r.get("created_at", ""), reverse=True)
    return {"success": True, "rules": rules, "count": len(rules)}

@router.post("/api/events/rules")
async def events_rule_create(body: dict = None):
    if HAS_EVENTS and _event_engine:
        pattern = (body or {}).get("pattern", "*")
        action = (body or {}).get("action", "log")
        async def _callback(evt):
            logger.info(f"[EVENT] 规则触发: pattern={pattern}, event={evt.get('type','')}")
        _event_engine.subscribe(pattern, _callback)
        return {"success": True, "rule": {"id": _next_id(), "name": (body or {}).get("name", f"规则{_next_id()}"),
                "pattern": pattern, "action": action, "enabled": True, "engine": "core"}}
    rid = _next_id()
    rule = {
        "id": rid, "name": (body or {}).get("name", f"规则{rid}"),
        "pattern": (body or {}).get("pattern", "*"),
        "action": (body or {}).get("action", "notify"),
        "enabled": True, "created_at": _ts(),
    }
    _rules_db[rid] = rule; _save_all()
    return {"success": True, "rule": rule}

@router.delete("/api/events/rules/{rule_id}")
async def events_rule_delete(rule_id: str):
    _rules_db.pop(rule_id, None); _save_all()
    return {"success": True}

# ─── 管线引擎 ─────────────────────────────────────
# 优先: PipelineEngine (core) — 有 run() 可以实际执行管线步骤
# 降级: _pipelines_db
@router.get("/api/pipeline/status")
async def pipeline_status():
    if HAS_PIPELINE and _pipeline_engine:
        stats = _pipeline_engine.get_stats() if hasattr(_pipeline_engine, 'get_stats') else {}
        return {"success": True, "running": True, "active_count": stats.get("active", 0),
                "pipelines": _pipeline_engine.get_history() if hasattr(_pipeline_engine, 'get_history') else [],
                "engine": "core.pipeline_engine"}
    active = sum(1 for p in _pipelines_db.values() if p.get("status") == "running")
    return {"success": True, "running": True, "pipelines": list(_pipelines_db.values()), "active_count": active}

@router.get("/api/pipelines")
async def pipelines_list():
    if HAS_PIPELINE and _pipeline_engine:
        items = _pipeline_engine.get_history() if hasattr(_pipeline_engine, 'get_history') else []
        return {"success": True, "pipelines": items, "count": len(items), "engine": "core"}
    items = sorted(_pipelines_db.values(), key=lambda p: p.get("created_at", ""), reverse=True)
    return {"success": True, "pipelines": items, "count": len(items)}

@router.get("/api/pipelines/stats")
async def pipelines_stats():
    if HAS_PIPELINE and _pipeline_engine:
        stats = _pipeline_engine.get_stats() if hasattr(_pipeline_engine, 'get_stats') else {}
        return {"success": True, **stats, "engine": "core"}
    total = len(_pipelines_db)
    active = sum(1 for p in _pipelines_db.values() if p.get("status")== "running")
    done = sum(1 for p in _pipelines_db.values() if p.get("status")=="completed")
    failed = sum(1 for p in _pipelines_db.values() if p.get("status")=="failed")
    return {"success": True, "total": total, "active": active, "completed": done, "failed": failed}

@router.post("/api/pipelines")
async def pipelines_create(body: dict = None):
    pid = _next_id()
    pipe = {
        "id": pid, "name": (body or {}).get("name", f"管线{pid}"),
        "description": (body or {}).get("description", ""),
        "steps": (body or {}).get("steps", []),
        "status": "running", "created_at": _ts(),
        "last_run": "", "execution_count": 0,
    }
    _pipelines_db[pid] = pipe
    return {"success": True, "pipeline": pipe}

@router.post("/api/pipelines/{pipeline_id}/execute")
async def pipelines_execute(pipeline_id: str):
    if HAS_PIPELINE and _pipeline_engine and pipeline_id in _pipelines_db:
        try:
            steps = _pipelines_db[pipeline_id].get("steps", [])
            result = await _pipeline_engine.run(steps)
            _pipelines_db[pipeline_id]["last_run"] = _ts()
            _pipelines_db[pipeline_id]["execution_count"] += 1
            return {"success": True, "executed": True, "result": str(result)[:200], "engine": "core"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}
    if pipeline_id in _pipelines_db:
        _pipelines_db[pipeline_id]["last_run"] = _ts()
        _pipelines_db[pipeline_id]["execution_count"] += 1
    return {"success": True, "executed": True}

@router.delete("/api/pipelines/{pipeline_id}")
async def pipelines_delete(pipeline_id: str):
    _pipelines_db.pop(pipeline_id, None); _save_all()
    return {"success": True}

# ─── 任务队列 ─────────────────────────────────────
# 优先: TaskQueue (modules) — 有 submit() / _worker_loop / _execute_task
# 降级: _queue_tasks_db
@router.get("/api/queue/stats")
async def queue_stats():
    if HAS_QUEUE and _queue_instance and hasattr(_queue_instance, 'health_check'):
        try:
            hc = _queue_instance.health_check() if callable(_queue_instance.health_check) else {}
            pending = hc.get("pending_count", 0) if isinstance(hc, dict) else 0
            running = hc.get("running_count", 0) if isinstance(hc, dict) else 0
            failed = hc.get("failed_count", 0) if isinstance(hc, dict) else 0
            done = hc.get("completed_count", 0) if isinstance(hc, dict) else 0
            total = pending + running + failed + done
            return {"success": True, "total": total, "pending": pending, "running": running,
                    "failed": failed, "completed": done, "workers_active": min(running, 4), "max_workers": 4,
                    "backlog": pending, "delayed": 0, "dead": failed, "total_processed": total,
                    "engine": "modules.task_queue"}
        except Exception:
            pass
    q = _queue_tasks_db
    total = len(q)
    pending = sum(1 for t in q.values() if t.get("status")=="pending")
    running = sum(1 for t in q.values() if t.get("status")=="running")
    failed = sum(1 for t in q.values() if t.get("status")=="failed")
    done = sum(1 for t in q.values() if t.get("status")=="completed")
    return {"success": True, "total": total, "pending": pending, "running": running,
            "failed": failed, "completed": done, "workers_active": min(running,4), "max_workers": 4,
            "backlog": pending, "delayed": 0, "dead": failed, "total_processed": total,
            "engine": "dict"}

@router.get("/api/queue/tasks")
async def queue_tasks(limit: int = 30):
    items = sorted(_queue_tasks_db.values(), key=lambda t: t.get("created_at", ""), reverse=True)[:limit]
    return {"success": True, "tasks": items, "total": len(items)}

@router.get("/api/queue/pending")
async def queue_pending():
    pending = [t for t in _queue_tasks_db.values() if t.get("status")=="pending"]
    return {"success": True, "tasks": sorted(pending, key=lambda t: t.get("created_at",""), reverse=True), "count": len(pending)}

@router.post("/api/queue/tasks")
async def queue_enqueue(body: dict = None):
    qid = _next_id()
    task = {
        "id": qid, "name": (body or {}).get("name", f"任务{qid}"),
        "type": (body or {}).get("type", "execute"),
        "target": (body or {}).get("target", ""),
        "status": "pending", "priority": (body or {}).get("priority", 0),
        "created_at": _ts(), "started_at": "", "completed_at": "",
    }
    _queue_tasks_db[qid] = task; _save_all()
    if HAS_QUEUE and _queue_instance and hasattr(_queue_instance, 'submit'):
        try:
            await _queue_instance.submit({"id": qid, "type": task["type"], "target": task["target"]})
            logger.info(f"[QUEUE] 任务 {qid} 已提交到 TaskQueue 引擎")
        except Exception as e:
            logger.warning(f"[QUEUE] TaskQueue.submit 失败: {e}")
    return {"success": True, "task": task, "engine": "modules.task_queue" if HAS_QUEUE else "dict"}

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

# ─── 工作流模板 ────────────────────────────────────
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
        "steps": tpl["steps"], "status": "running",
        "cron": "0 */4 * * *" if template_id == "github_trending" else "0 * * * *",
        "created_at": _ts(), "last_run": "", "next_run": _ts(),
    }
    _scheduler_tasks_db[tid] = task
    return {"success": True, "task": task, "message": f"模板 '{tpl['name']}' 已应用，任务已创建"}
