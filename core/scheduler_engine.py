"""
AUTO-EVO-AI V0.1 — 定时调度引擎 (Scheduler Engine)
====================================================
上市公司级任务调度:
- Cron表达式解析 (分 时 日 月 周)
- 管线定时触发
- 模块直接执行调度
- 间隔调度 (每N秒/分/时)
- 任务日历视图 (过去/未来N次执行时间)
- 超时保护 + 失败重试
- 持久化 (SQLite) + 断电恢复
- 并发控制 (同时运行上限)
"""

from __future__ import annotations

import os
import re
import json
import time
import asyncio
import sqlite3
from core.logging_config import get_logger
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = get_logger("evo.scheduler")


# ═══════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════

class ScheduleType(str, Enum):
    CRON = "cron"           # Cron表达式
    INTERVAL = "interval"   # 固定间隔
    ONCE = "once"           # 一次性

class TaskStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExecStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"

class TargetType(str, Enum):
    PIPELINE = "pipeline"   # 执行管线
    MODULE = "module"       # 执行模块
    HTTP = "http"           # HTTP回调


@dataclass
class ScheduledTask:
    """调度任务"""
    id: str = ""
    name: str = ""
    description: str = ""
    schedule_type: str = "interval"     # cron / interval / once
    cron_expr: str = ""                  # "0 8 * * *" 每天8点
    interval_seconds: int = 3600        # 间隔秒数
    once_time: str = ""                  # ISO时间 "2026-05-13T08:00:00"
    target_type: str = "module"          # pipeline / module / http
    target_id: str = ""                  # pipeline_id 或 module_name
    target_params: dict = field(default_factory=dict)  # 执行参数
    status: str = "active"               # active / paused / completed
    timeout_seconds: int = 300           # 单次执行超时
    max_retries: int = 0                 # 失败重试次数
    retry_delay: int = 60                # 重试间隔(秒)
    max_concurrent: int = 1              # 最大并发数
    tags: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    last_run_at: str = ""
    next_run_at: str = ""
    run_count: int = 0
    fail_count: int = 0

    def __post_init__(self) -> Any:
        if not self.id:
            import secrets
            self.id = secrets.token_hex(8)
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

@dataclass
class TaskExecution:
    """执行记录"""
    id: str = ""
    task_id: str = ""
    task_name: str = ""
    status: str = "pending"
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    result: dict = field(default_factory=dict)
    error: str = ""
    retry_count: int = 0
    scheduled_at: str = ""

    def __post_init__(self) -> Any:
        if not self.id:
            import secrets
            self.id = secrets.token_hex(12)


# ═══════════════════════════════════════════════════════════
# Cron表达式解析器 (支持 分 时 日 月 周)
# ═══════════════════════════════════════════════════════════

class CronParser:
    """标准5字段Cron解析: minute hour day month weekday"""

    MONTH_NAMES = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    WEEKDAY_NAMES = {
        'sun': 0, 'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6
    }

    @staticmethod
    def parse_field(expr: str, min_val: int, max_val: int, names: dict = None) -> list[int]:
        """解析单个Cron字段 → 值列表"""
        expr = expr.strip().lower()
        if names:
            for name, val in names.items():
                expr = expr.replace(name, str(val))

        result = set()
        for part in expr.split(','):
            if '/' in part:
                range_part, step = part.split('/', 1)
                step = int(step)
            else:
                range_part = part
                step = 1

            if range_part == '*':
                start, end = min_val, max_val
            elif '-' in range_part:
                parts = range_part.split('-', 1)
                start, end = int(parts[0]), int(parts[1])
            else:
                start = end = int(range_part)

            for v in range(start, end + 1, step):
                if min_val <= v <= max_val:
                    result.add(v)

        return sorted(result)

    @classmethod
    def parse(cls, expr: str) -> tuple[list[int], list[int], list[int], list[int], list[int]]:
        """解析5字段Cron → (分钟, 小时, 日, 月, 周)"""
        fields = expr.strip().split()
        if len(fields) != 5:
            raise ValueError(f"Cron表达式需要5个字段, 得到{len(fields)}个: {expr}")

        minutes = cls.parse_field(fields[0], 0, 59)
        hours = cls.parse_field(fields[1], 0, 23)
        days = cls.parse_field(fields[2], 1, 31)
        months = cls.parse_field(fields[3], 1, 12, cls.MONTH_NAMES)
        weekdays = cls.parse_field(fields[4], 0, 6, cls.WEEKDAY_NAMES)

        return minutes, hours, days, months, weekdays

    @classmethod
    def next_run(cls, expr: str, after: datetime | None = None) -> datetime | None:
        """计算下一次执行时间"""
        try:
            minutes, hours, days, months, weekdays = cls.parse(expr)
        except ValueError:
            return None

        if after is None:
            after = datetime.now()
        # 从下一分钟开始搜索
        dt = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # 最多搜索366天
        for _ in range(525960):  # 366天 * 24 * 60
            if (dt.month in months and
                (dt.day in days or (dt.weekday() in weekdays if weekdays != list(range(0,7)) else False)) and
                dt.hour in hours and
                dt.minute in minutes):
                return dt
            # 简单跳到下一分钟
            dt += timedelta(minutes=1)
            if dt.month not in months:
                # 跳到下个月
                if dt.month == 12:
                    dt = dt.replace(year=dt.year + 1, month=1, day=1, hour=0, minute=0)
                else:
                    dt = dt.replace(month=dt.month + 1, day=1, hour=0, minute=0)
            elif dt.hour not in hours:
                dt = dt.replace(minute=0) + timedelta(hours=1)
        return None

    @classmethod
    def get_calendar(cls, expr: str, count: int = 10, after: datetime | None = None) -> list[str]:
        """获取未来N次执行时间"""
        times = []
        dt = after or datetime.now()
        for _ in range(count):
            dt = cls.next_run(expr, dt)
            if dt is None:
                break
            times.append(dt.isoformat())
            dt += timedelta(minutes=1)
        return times

    @classmethod
    def describe(cls, expr: str) -> str:
        """将Cron表达式翻译为中文描述"""
        try:
            minutes, hours, days, months, weekdays = cls.parse(expr)
        except ValueError:
            return f"无效表达式: {expr}"

        parts = []
        if minutes == [0] and hours == [0]:
            parts.append("每小时")
        elif len(hours) == 1 and len(minutes) == 1:
            parts.append(f"每天 {hours[0]:02d}:{minutes[0]:02d}")
        elif len(hours) > 1:
            h_str = '/'.join(f'{h:02d}' for h in hours[:5])
            parts.append(f"每天 {h_str}点")
        if weekdays != list(range(0, 7)):
            names = ['日', '一', '二', '三', '四', '五', '六']
            w_str = '/'.join(names[w] for w in weekdays)
            parts.append(f"周{w_str}")
        if days != list(range(1, 32)):
            d_str = '/'.join(str(d) for d in days[:5])
            parts.append(f"每月{d_str}号")

        return ' '.join(parts) if parts else expr


# ═══════════════════════════════════════════════════════════
# SQLite持久化存储
# ═══════════════════════════════════════════════════════════

class ScheduleStore:
    """调度持久化"""

    def __init__(self, data_dir: str = ".evo_data/scheduler") -> None:
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "scheduler.db"
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> Any:
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    schedule_type TEXT DEFAULT 'interval',
                    cron_expr TEXT DEFAULT '',
                    interval_seconds INTEGER DEFAULT 3600,
                    once_time TEXT DEFAULT '',
                    target_type TEXT DEFAULT 'module',
                    target_id TEXT DEFAULT '',
                    target_params TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'active',
                    timeout_seconds INTEGER DEFAULT 300,
                    max_retries INTEGER DEFAULT 0,
                    retry_delay INTEGER DEFAULT 60,
                    max_concurrent INTEGER DEFAULT 1,
                    tags TEXT DEFAULT '[]',
                    created_at TEXT,
                    updated_at TEXT,
                    last_run_at TEXT DEFAULT '',
                    next_run_at TEXT DEFAULT '',
                    run_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON scheduled_tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_next ON scheduled_tasks(next_run_at);

                CREATE TABLE IF NOT EXISTS task_executions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    task_name TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    started_at TEXT DEFAULT '',
                    finished_at TEXT DEFAULT '',
                    duration_ms INTEGER DEFAULT 0,
                    result TEXT DEFAULT '{}',
                    error TEXT DEFAULT '',
                    retry_count INTEGER DEFAULT 0,
                    scheduled_at TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_exec_task ON task_executions(task_id);
                CREATE INDEX IF NOT EXISTS idx_exec_status ON task_executions(status);
            """)
            conn.commit()
        finally:
            conn.close()

    def _row_to_task(self, row: sqlite3.Row) -> ScheduledTask:
        d = dict(row)
        d['target_params'] = json.loads(d.get('target_params') or '{}')
        d['tags'] = json.loads(d.get('tags') or '[]')
        return ScheduledTask(**d)

    def create_task(self, task: ScheduledTask) -> ScheduledTask:
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO scheduled_tasks
                (id, name, description, schedule_type, cron_expr, interval_seconds, once_time,
                 target_type, target_id, target_params, status, timeout_seconds, max_retries,
                 retry_delay, max_concurrent, tags, created_at, updated_at, last_run_at,
                 next_run_at, run_count, fail_count)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (task.id, task.name, task.description, task.schedule_type, task.cron_expr,
                  task.interval_seconds, task.once_time, task.target_type, task.target_id,
                  json.dumps(task.target_params, ensure_ascii=False), task.status,
                  task.timeout_seconds, task.max_retries, task.retry_delay, task.max_concurrent,
                  json.dumps(task.tags, ensure_ascii=False), task.created_at, task.updated_at,
                  task.last_run_at, task.next_run_at, task.run_count, task.fail_count))
            conn.commit()
        finally:
            conn.close()
        return task

    def get_task(self, task_id: str) -> ScheduledTask | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM scheduled_tasks WHERE id=?", (task_id,)).fetchone()
            return self._row_to_task(row) if row else None
        finally:
            conn.close()

    def list_tasks(self, status: str | None = None, limit: int = 100, offset: int = 0) -> list[ScheduledTask]:
        conn = self._get_conn()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM scheduled_tasks WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (status, limit, offset)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM scheduled_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset)).fetchall()
            return [self._row_to_task(r) for r in rows]
        finally:
            conn.close()

    def update_task(self, task_id: str, **fields) -> bool:
        if not fields:
            return False
        fields['updated_at'] = datetime.now().isoformat()
        set_clause = ', '.join(f'{k}=?' for k in fields)
        vals = list(fields.values()) + [task_id]
        conn = self._get_conn()
        try:
            cursor = conn.execute(f"UPDATE scheduled_tasks SET {set_clause} WHERE id=?", vals)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_task(self, task_id: str) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM scheduled_tasks WHERE id=?", (task_id,))
            conn.execute("DELETE FROM task_executions WHERE task_id=?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def create_execution(self, exec_: TaskExecution) -> TaskExecution:
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO task_executions
                (id, task_id, task_name, status, started_at, finished_at, duration_ms,
                 result, error, retry_count, scheduled_at, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (exec_.id, exec_.task_id, exec_.task_name, exec_.status, exec_.started_at,
                  exec_.finished_at, exec_.duration_ms, json.dumps(exec_.result, ensure_ascii=False),
                  exec_.error, exec_.retry_count, exec_.scheduled_at, datetime.now().isoformat()))
            conn.commit()
        finally:
            conn.close()
        return exec_

    def update_execution(self, exec_id: str, **fields) -> bool:
        fields_ = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for k, v in fields.items()}
        set_clause = ', '.join(f'{k}=?' for k in fields_)
        vals = list(fields_.values()) + [exec_id]
        conn = self._get_conn()
        try:
            cursor = conn.execute(f"UPDATE task_executions SET {set_clause} WHERE id=?", vals)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def list_executions(self, task_id: str | None = None, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        try:
            if task_id:
                rows = conn.execute(
                    "SELECT * FROM task_executions WHERE task_id=? ORDER BY created_at DESC LIMIT ?",
                    (task_id, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM task_executions ORDER BY created_at DESC LIMIT ?",
                    (limit,)).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d['result'] = json.loads(d.get('result') or '{}')
                result.append(d)
            return result
        finally:
            conn.close()

    def stats(self) -> dict:
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM scheduled_tasks").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM scheduled_tasks WHERE status='active'").fetchone()[0]
            today_runs = conn.execute(
                "SELECT COUNT(*) FROM task_executions WHERE date(created_at)=date('now')").fetchone()[0]
            today_fail = conn.execute(
                "SELECT COUNT(*) FROM task_executions WHERE date(created_at)=date('now') AND status='failed'"
            ).fetchone()[0]
            return {"total_tasks": total, "active_tasks": active,
                    "today_executions": today_runs, "today_failures": today_fail}
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════
# 调度引擎核心
# ═══════════════════════════════════════════════════════════

class SchedulerEngine:
    """
    定时调度引擎 — 上市公司级任务调度
    """

    def __init__(self, data_dir: str = ".evo_data/scheduler") -> None:
        self._store = ScheduleStore(data_dir)
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None
        self._active_executions: dict[str, datetime] = {}  # task_id → start_time (并发控制)
        self._callbacks: list[callable] = []  # 执行回调
        logger.info("[Scheduler] 引擎初始化")

    @property
    def store(self) -> ScheduleStore:
        return self._store

    # ─── 生命周期 ───

    def start(self) -> None:
        """启动调度器 (在FastAPI lifespan中调用)"""
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_event_loop()

        # 恢复active任务, 计算next_run_at
        tasks = self._store.list_tasks(status="active")
        for t in tasks:
            self._update_next_run(t)

        self._task = self._loop.create_task(self._tick_loop())
        logger.info("[Scheduler] 调度器已启动 | 活跃任务: %d", len(tasks))

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("[Scheduler] 调度器已停止")

    async def _tick_loop(self) -> Any:
        """主循环: 每秒检查一次"""
        while self._running:
            try:
                await self._check_and_dispatch()
            except Exception as e:
                logger.error("[Scheduler] tick异常: %s", e)
            await asyncio.sleep(1)

    async def _check_and_dispatch(self) -> Any:
        """检查到时任务并分发执行"""
        now = datetime.now()
        active_tasks = self._store.list_tasks(status="active")

        for task in active_tasks:
            if not task.next_run_at:
                continue

            # 解析next_run
            try:
                next_dt = datetime.fromisoformat(task.next_run_at)
            except (ValueError, TypeError):
                self._update_next_run(task)
                continue

            if now < next_dt:
                continue

            # 并发控制
            active_count = sum(1 for tid, t in self._active_executions.items() if tid == task.id)
            if active_count >= task.max_concurrent:
                continue

            # 一次性任务完成后自动暂停
            if task.schedule_type == "once":
                self._store.update_task(task.id, status="completed")

            # 分发执行
            asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: ScheduledTask) -> Any:
        """执行单个调度任务"""
        now = datetime.now()
        exec_ = TaskExecution(
            task_id=task.id, task_name=task.name, status="running",
            started_at=now.isoformat(), scheduled_at=task.next_run_at
        )
        self._store.create_execution(exec_)
        self._active_executions[task.id] = now

        # 更新任务计数
        self._store.update_task(task.id, last_run_at=now.isoformat(),
                                run_count=task.run_count + 1)
        # 计算下一次执行时间
        self._update_next_run(task)

        result = {"success": False, "target": task.target_id}
        error_msg = ""

        try:
            # 超时控制
            result = await asyncio.wait_for(
                self._dispatch_target(task), timeout=task.timeout_seconds
            )
            exec_.status = "success"
        except TimeoutError:
            exec_.status = "timeout"
            error_msg = f"执行超时 ({task.timeout_seconds}s)"
        except Exception as e:
            exec_.status = "failed"
            error_msg = str(e)[:500]
            # 重试
            if exec_.retry_count < task.max_retries:
                exec_.retry_count += 1
                logger.warning("[Scheduler] 任务 %s 第%d次重试 (共%d次)",
                               task.id, exec_.retry_count, task.max_retries)
                await asyncio.sleep(task.retry_delay)
                # 递归重试 (简化实现, 实际生产中应用消息队列)
                asyncio.create_task(self._execute_task_with_retry(task, exec_))
                return
        finally:
            self._active_executions.pop(task.id, None)

        finished = datetime.now()
        exec_.finished_at = finished.isoformat()
        exec_.duration_ms = int((finished - now).total_seconds() * 1000)
        exec_.result = result if isinstance(result, dict) else {"data": str(result)[:1000]}
        exec_.error = error_msg
        self._store.update_execution(exec_.id, **asdict(exec_))

        if exec_.status == "failed":
            self._store.update_task(task.id, fail_count=task.fail_count + 1)
            logger.warning("[SCHEDULER FAIL] 任务 '%s' 失败: %s | 目标: %s | 耗时%dms",
                           task.name, error_msg or str(result.get("error",""))[:200],
                           task.target_id, exec_.duration_ms)

        # 触发回调
        for cb in self._callbacks:
            try:
                cb(task, exec_)
            except Exception:
                pass

        logger.info("[Scheduler] 任务 %s 执行完成: %s (%dms)",
                     task.name, exec_.status, exec_.duration_ms)

    async def _execute_task_with_retry(self, task: ScheduledTask, exec_: TaskExecution) -> Any:
        """重试执行"""
        now = datetime.now()
        exec_.started_at = now.isoformat()
        exec_.status = "running"

        try:
            result = await asyncio.wait_for(
                self._dispatch_target(task), timeout=task.timeout_seconds
            )
            exec_.status = "success"
            exec_.result = result if isinstance(result, dict) else {"data": str(result)[:1000]}
        except TimeoutError:
            exec_.status = "timeout"
            exec_.error = f"执行超时 ({task.timeout_seconds}s)"
        except Exception as e:
            exec_.status = "failed"
            exec_.error = str(e)[:500]

        finished = datetime.now()
        exec_.finished_at = finished.isoformat()
        exec_.duration_ms = int((finished - now).total_seconds() * 1000)
        self._store.update_execution(exec_.id, **asdict(exec_))
        if exec_.status == "failed":
            self._store.update_task(task.id, fail_count=task.fail_count + 1)

    async def _dispatch_target(self, task: ScheduledTask) -> dict:
        """分发到目标执行"""
        if task.target_type == "module":
            return await self._execute_module(task)
        elif task.target_type == "pipeline":
            return await self._execute_pipeline(task)
        elif task.target_type == "http":
            return await self._execute_http(task)
        else:
            return {"success": False, "error": f"未知目标类型: {task.target_type}"}

    async def _execute_module(self, task: ScheduledTask) -> dict:
        """执行模块"""
        try:
            module_name = task.target_id
            action = task.target_params.get("action", "")
            params = task.target_params.get("params", {})

            # 确保 sys.path 包含模块目录
            sys_path = os.environ.get("EVO_BASE_DIR", "")
            mod_path = os.environ.get("EVO_MODULES_DIR", "")
            for p in [sys_path, mod_path]:
                if p and p not in sys.path:
                    sys.path.insert(0, p)

            # 尝试带 modules. 前缀的完整模块名
            spec = importlib.util.find_spec(module_name)
            if not spec:
                # 尝试 modules.module_name
                spec = importlib.util.find_spec(f"modules.{module_name}")

            if not spec:
                return {"success": False, "error": f"模块 {module_name} 未找到 (sys.path: {sys.path[:3]})"}

            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # 查找模块类 — 优先 module_class 变量
            main_class = getattr(mod, "module_class", None)
            if isinstance(main_class, str):
                main_class = getattr(mod, main_class, None)

            if main_class and isinstance(main_class, type) and hasattr(main_class, 'execute'):
                instance = main_class()
                merged = {"action": action} if action else {}
                if params:
                    merged.update(params)
                result = instance.execute(**merged) if merged else instance.execute()
                return {"success": True, "module": module_name, "result": str(result)[:500]}

            # Fallback: 扫描所有类
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and hasattr(attr, 'execute') and not attr_name.startswith('_'):
                    try:
                        instance = attr()
                        merged = {"action": action} if action else {}
                        if params:
                            merged.update(params)
                        result = instance.execute(**merged) if merged else instance.execute()
                        return {"success": True, "module": module_name, "result": str(result)[:500]}
                    except Exception:
                        continue

            return {"success": False, "error": f"模块 {module_name} 中未找到execute类 (classes: {[n for n in dir(mod) if isinstance(getattr(mod,n),type) and not n.startswith('_')][:10]})"}
        except Exception as e:
            logger.error(f"[Scheduler] _execute_module 异常: {e}", exc_info=True)
            return {"success": False, "error": str(e)[:500]}

    async def _execute_pipeline(self, task: ScheduledTask) -> dict:
        """执行管线"""
        try:
            # 延迟导入避免循环依赖
            sys.path.insert(0, os.environ.get("EVO_BASE_DIR", "."))
            from core.pipeline_engine import get_pipeline_engine

            engine = get_pipeline_engine()
            exec_id = await engine.execute(task.target_id, params=task.target_params)
            return {"success": True, "pipeline_id": task.target_id, "execution_id": exec_id}
        except Exception as e:
            return {"success": False, "error": str(e)[:500]}

    async def _execute_http(self, task: ScheduledTask) -> dict:
        """执行HTTP回调"""
        import aiohttp
        url = task.target_id
        method = task.target_params.get("method", "POST").upper()
        headers = task.target_params.get("headers", {})
        body = task.target_params.get("body", {})
        timeout = aiohttp.ClientTimeout(total=task.timeout_seconds)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, json=body, headers=headers) as resp:
                    return {"success": resp.status < 400, "status": resp.status,
                            "body": (await resp.text())[:500]}
        except Exception as e:
            return {"success": False, "error": str(e)[:500]}

    # ─── 时间计算 ───

    def _update_next_run(self, task: ScheduledTask) -> Any:
        """更新任务的next_run_at"""
        now = datetime.now()
        if task.schedule_type == "cron":
            next_dt = CronParser.next_run(task.cron_expr, now)
            if next_dt:
                self._store.update_task(task.id, next_run_at=next_dt.isoformat())
        elif task.schedule_type == "interval":
            last = datetime.fromisoformat(task.last_run_at) if task.last_run_at else now
            next_dt = last + timedelta(seconds=task.interval_seconds)
            if next_dt <= now:
                next_dt = now + timedelta(seconds=task.interval_seconds)
            self._store.update_task(task.id, next_run_at=next_dt.isoformat())
        elif task.schedule_type == "once":
            if task.once_time:
                once_dt = datetime.fromisoformat(task.once_time)
                if once_dt > now:
                    self._store.update_task(task.id, next_run_at=once_dt.isoformat())

    # ─── 任务CRUD (代理到store) ───

    def add_task(self, **kwargs) -> ScheduledTask:
        """创建调度任务 (接受API传参, 适配ScheduledTask字段)"""
        now = datetime.now().isoformat()
        field_map = {
            'name': kwargs.get('name', 'unnamed_task'),
            'description': kwargs.get('description', ''),
            'schedule_type': kwargs.get('schedule_type', kwargs.get('cron', 'cron') and 'cron'),
            'cron_expr': kwargs.get('cron', kwargs.get('cron_expr', '')),
            'interval_seconds': kwargs.get('interval_seconds', kwargs.get('interval', 3600)),
            'once_time': kwargs.get('once_time', kwargs.get('scheduled_at', '')),
            'target_type': kwargs.get('target_type', kwargs.get('task_type', 'module')),
            'target_id': kwargs.get('target_id', kwargs.get('module', kwargs.get('pipeline', ''))),
            'target_params': kwargs.get('target_params', kwargs.get('config', kwargs.get('params', {}))),
            'status': kwargs.get('status', 'active' if kwargs.get('enabled', True) else 'paused'),
            'timeout_seconds': kwargs.get('timeout_seconds', kwargs.get('timeout', 300)),
            'max_retries': kwargs.get('max_retries', kwargs.get('retry', 3)),
            'retry_delay': kwargs.get('retry_delay', kwargs.get('retry_delay', 30)),
            'max_concurrent': kwargs.get('max_concurrent', 1),
            'tags': kwargs.get('tags', []),
            'created_at': now, 'updated_at': now,
        }
        # 从config中提取action
        config = kwargs.get('config', {})
        if isinstance(config, dict) and 'action' in config:
            field_map['target_params']['action'] = config['action']
        if isinstance(config, dict) and 'params' in config:
            field_map['target_params'].update(config['params'])

        task = ScheduledTask(**field_map)
        task = self._store.create_task(task)
        # 计算首次next_run
        self._update_next_run(task)
        return task

    def update_task(self, task_id: str, **kwargs) -> ScheduledTask | None:
        """更新调度任务"""
        fields = {}
        allowed = ['name', 'description', 'schedule_type', 'cron_expr', 'interval_seconds',
                    'once_time', 'target_type', 'target_id', 'target_params', 'status',
                    'timeout_seconds', 'max_retries', 'retry_delay', 'max_concurrent', 'tags']
        for k in allowed:
            if k in kwargs:
                val = kwargs[k]
                if k in ('target_params', 'tags') and not isinstance(val, str):
                    val = json.dumps(val, ensure_ascii=False)
                fields[k] = val
        if not fields:
            return self._store.get_task(task_id)
        self._store.update_task(task_id, **fields)
        # 如果修改了调度参数, 重新计算next_run
        if any(k in fields for k in ('cron_expr', 'interval_seconds', 'once_time', 'schedule_type')):
            task = self._store.get_task(task_id)
            if task:
                self._update_next_run(task)
        return self._store.get_task(task_id)

    def remove_task(self, task_id: str) -> bool:
        """删除调度任务"""
        return self._store.delete_task(task_id)

    def toggle_task(self, task_id: str) -> ScheduledTask | None:
        """启用/禁用任务"""
        task = self._store.get_task(task_id)
        if not task:
            return None
        new_status = "paused" if task.status == "active" else "active"
        self._store.update_task(task_id, status=new_status)
        return self._store.get_task(task_id)

    async def trigger_now(self, task_id: str) -> dict:
        """立即触发任务"""
        task = self._store.get_task(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        await self._execute_task(task)
        return {"success": True, "task_id": task_id, "task_name": task.name}

    def get_upcoming_runs(self, task: ScheduledTask, n: int = 10) -> list[str]:
        """获取未来N次执行时间"""
        runs = []
        if task.schedule_type == "cron" and task.cron_expr:
            try:
                runs = self._parse_cron(task.cron_expr, n)
            except Exception:
                pass
        elif task.schedule_type == "interval" and task.interval_seconds:
            now = datetime.now()
            for i in range(1, n + 1):
                runs.append((now + timedelta(seconds=task.interval_seconds * i)).isoformat())
        elif task.schedule_type == "once" and task.once_time:
            runs = [task.once_time]
        return runs

    # ─── 回调 ───

    def on_execution(self, callback: callable):
        """注册执行完成回调"""
        self._callbacks.append(callback)

    def stats(self) -> dict:
        """引擎统计"""
        s = self._store.stats()
        s["running"] = self._running
        s["next_run"] = min(
            (t.next_run_at for t in self._store.list_tasks(status="active", limit=1000) if t.next_run_at),
            default=""
        )
        return s

    # ─── 预置模板 ───

    @staticmethod
    def get_templates() -> list[dict]:
        """预置调度模板"""
        return [
            {"name": "每日安全扫描", "schedule_type": "cron", "cron_expr": "0 8 * * *",
             "target_type": "module", "target_id": "security_scanner",
             "description": "每天早上8点执行安全扫描"},
            {"name": "每小时性能采集", "schedule_type": "interval", "interval_seconds": 3600,
             "target_type": "module", "target_id": "perf_monitor",
             "description": "每小时采集一次性能指标"},
            {"name": "每周生成周报", "schedule_type": "cron", "cron_expr": "0 9 * * 1",
             "target_type": "pipeline", "target_id": "weekly_report",
             "description": "每周一9点自动生成周报"},
            {"name": "系统健康检查", "schedule_type": "interval", "interval_seconds": 300,
             "target_type": "module", "target_id": "health_checker",
             "description": "每5分钟检查系统健康状态"},
            {"name": "日志轮转清理", "schedule_type": "cron", "cron_expr": "0 2 * * *",
             "target_type": "module", "target_id": "log_rotator",
             "description": "每天凌晨2点清理过期日志"},
        ]


# ═══════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════

_scheduler_engine: SchedulerEngine | None = None

def get_scheduler_engine() -> SchedulerEngine:
    global _scheduler_engine
    if _scheduler_engine is None:
        _scheduler_engine = SchedulerEngine()
    return _scheduler_engine

def reset_scheduler_engine():
    global _scheduler_engine
    if _scheduler_engine and _scheduler_engine._running:
        asyncio.create_task(_scheduler_engine.stop())
    _scheduler_engine = None

import importlib.util  # noqa: E402 (needed for dynamic module loading)
