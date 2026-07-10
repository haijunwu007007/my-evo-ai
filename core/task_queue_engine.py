"""
AUTO-EVO-AI V0.1 — 持久化任务队列 (Task Queue Engine)
======================================================
上市公司级任务队列:
- 多优先级队列 (urgent/high/normal/low)
- 延迟任务 (指定时间执行)
- 失败重试 (指数退避, 可配最大次数)
- 死信队列 (超过重试次数自动转入)
- 持久化 (SQLite WAL) + 断电恢复
- 并发控制 (worker数量可配)
- 任务取消 + 超时保护
- 任务结果持久化
"""

from __future__ import annotations

import os
import json
import time
import asyncio
import sqlite3
from core.logging_config import get_logger
import secrets
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections.abc import Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import heapq

logger = get_logger("evo.taskqueue")


class TaskPriority(str, Enum):
    URGENT = "urgent"      # 紧急, 立即执行
    HIGH = "high"           # 高优先级
    NORMAL = "normal"       # 普通
    LOW = "low"             # 低优先级

PRIORITY_WEIGHT = {
    TaskPriority.URGENT: 0,
    TaskPriority.HIGH: 1,
    TaskPriority.NORMAL: 2,
    TaskPriority.LOW: 3,
}


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    DEAD = "dead"           # 死信队列


@dataclass(order=False)
class TaskItem:
    """任务项"""
    id: str = ""
    name: str = ""
    description: str = ""
    # 目标
    target_type: str = "module"       # module / pipeline / function / url
    target_id: str = ""
    target_params: dict = field(default_factory=dict)
    # 调度
    priority: str = "normal"
    status: str = "pending"
    # 延迟
    delay_until: str = ""             # ISO时间, 空表示立即执行
    # 重试
    max_retries: int = 3
    retry_count: int = 0
    retry_delay_base: float = 5.0     # 重试基础延迟(秒)
    # 超时
    timeout_seconds: float = 300.0    # 5分钟默认
    # 结果
    result: dict = field(default_factory=dict)
    error: str = ""
    # 队列
    queue_name: str = "default"
    parent_task_id: str = ""          # 父任务ID (链式任务)
    # 统计
    started_at: str = ""
    finished_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = secrets.token_hex(12)
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    @property
    def priority_weight(self) -> int:
        return PRIORITY_WEIGHT.get(TaskPriority(self.priority), 2)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> TaskItem:
        d = dict(row)
        d["target_params"] = json.loads(d.get("target_params") or "{}")
        d["result"] = json.loads(d.get("result") or "{}")
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════
# 任务存储
# ═══════════════════════════════════════════════════════════

class TaskQueueStore:
    """SQLite持久化任务队列"""

    def __init__(self, data_dir: str = ".evo_data/taskqueue"):
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "queue.db"
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS task_queue (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    target_type TEXT DEFAULT 'module',
                    target_id TEXT DEFAULT '',
                    target_params TEXT DEFAULT '{}',
                    priority TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'pending',
                    delay_until TEXT DEFAULT '',
                    max_retries INTEGER DEFAULT 3,
                    retry_count INTEGER DEFAULT 0,
                    retry_delay_base REAL DEFAULT 5.0,
                    timeout_seconds REAL DEFAULT 300.0,
                    result TEXT DEFAULT '{}',
                    error TEXT DEFAULT '',
                    queue_name TEXT DEFAULT 'default',
                    parent_task_id TEXT DEFAULT '',
                    started_at TEXT DEFAULT '',
                    finished_at TEXT DEFAULT '',
                    created_at TEXT DEFAULT '',
                    updated_at TEXT DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_queue_status ON task_queue(status, priority);
                CREATE INDEX IF NOT EXISTS idx_queue_delay ON task_queue(delay_until);
                CREATE INDEX IF NOT EXISTS idx_queue_parent ON task_queue(parent_task_id);
                CREATE INDEX IF NOT EXISTS idx_queue_created ON task_queue(created_at);
            """)
            conn.commit()
        finally:
            conn.close()

    def save_task(self, task: TaskItem) -> TaskItem:
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO task_queue
                (id, name, description, target_type, target_id, target_params,
                 priority, status, delay_until, max_retries, retry_count,
                 retry_delay_base, timeout_seconds, result, error,
                 queue_name, parent_task_id, started_at, finished_at,
                 created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                task.id, task.name, task.description, task.target_type, task.target_id,
                json.dumps(task.target_params, ensure_ascii=False),
                task.priority, task.status, task.delay_until,
                task.max_retries, task.retry_count, task.retry_delay_base,
                task.timeout_seconds, json.dumps(task.result, ensure_ascii=False),
                task.error, task.queue_name, task.parent_task_id,
                task.started_at, task.finished_at, task.created_at, task.updated_at
            ))
            conn.commit()
        finally:
            conn.close()
        return task

    def get_task(self, task_id: str) -> TaskItem | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM task_queue WHERE id=?", (task_id,)).fetchone()
            return TaskItem.from_row(row) if row else None
        finally:
            conn.close()

    def list_tasks(self, status: str | None = None, queue: str | None = None,
                   priority: str | None = None, parent_id: str | None = None,
                   limit: int = 50, offset: int = 0) -> list[TaskItem]:
        conn = self._get_conn()
        try:
            conds, params = [], []
            if status:
                conds.append("status=?"); params.append(status)
            if queue:
                conds.append("queue_name=?"); params.append(queue)
            if priority:
                conds.append("priority=?"); params.append(priority)
            if parent_id:
                conds.append("parent_task_id=?"); params.append(parent_id)

            where = f"WHERE {' AND '.join(conds)}" if conds else ""
            rows = conn.execute(
                f"SELECT * FROM task_queue {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [limit, offset]
            ).fetchall()
            return [TaskItem.from_row(r) for r in rows]
        finally:
            conn.close()

    def next_pending(self, exclude_ids: set | None = None) -> TaskItem | None:
        """获取下一个待执行任务 (按优先级+创建时间)"""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            rows = conn.execute("""
                SELECT * FROM task_queue
                WHERE status IN ('pending', 'retrying')
                  AND (delay_until = '' OR delay_until <= ?)
                ORDER BY
                    CASE priority
                        WHEN 'urgent' THEN 0
                        WHEN 'high' THEN 1
                        WHEN 'normal' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 2
                    END,
                    created_at ASC
                LIMIT 1
            """, (now,)).fetchall()

            for r in rows:
                task = TaskItem.from_row(r)
                if exclude_ids and task.id in exclude_ids:
                    continue
                return task
            return None
        finally:
            conn.close()

    def count_by_status(self) -> dict[str, int]:
        conn = self._get_conn()
        try:
            counts = {}
            for row in conn.execute("SELECT status, COUNT(*) as cnt FROM task_queue GROUP BY status").fetchall():
                counts[row['status']] = row['cnt']
            return counts
        finally:
            conn.close()

    def update_status(self, task_id: str, status: str, result: dict = None,
                      error: str = "", retry_count: int = None):
        conn = self._get_conn()
        try:
            updates = ["status=?", "updated_at=?"]
            params = [status, datetime.now().isoformat()]
            if result is not None:
                updates.append("result=?")
                params.append(json.dumps(result, ensure_ascii=False))
            if error:
                updates.append("error=?")
                params.append(error)
            if retry_count is not None:
                updates.append("retry_count=?")
                params.append(retry_count)
            if status == "running":
                updates.append("started_at=?")
                params.append(datetime.now().isoformat())
            elif status in ("success", "failed", "timeout", "cancelled", "dead"):
                updates.append("finished_at=?")
                params.append(datetime.now().isoformat())

            params.append(task_id)
            conn.execute(f"UPDATE task_queue SET {','.join(updates)} WHERE id=?", params)
            conn.commit()
        finally:
            conn.close()

    def delete_task(self, task_id: str) -> bool:
        conn = self._get_conn()
        try:
            c = conn.execute("DELETE FROM task_queue WHERE id=?", (task_id,))
            conn.commit()
            return c.rowcount > 0
        finally:
            conn.close()

    def cleanup(self, keep_days: int = 30):
        """清理已完成/已取消的旧任务"""
        conn = self._get_conn()
        try:
            c = conn.execute(
                "DELETE FROM task_queue WHERE status IN ('success','cancelled','dead','timeout') "
                "AND finished_at < datetime('now', ?)",
                (f'-{keep_days} days',)
            )
            conn.commit()
            return c.rowcount
        finally:
            conn.close()

    def stats(self) -> dict:
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM task_queue").fetchone()[0]
            counts = self.count_by_status()
            # 队列积压
            pending = counts.get("pending", 0) + counts.get("retrying", 0)
            # 延迟任务数
            delayed = conn.execute(
                "SELECT COUNT(*) FROM task_queue WHERE status='pending' AND delay_until > datetime('now')"
            ).fetchone()[0]
            return {
                "total": total,
                "pending": counts.get("pending", 0),
                "running": counts.get("running", 0),
                "success": counts.get("success", 0),
                "failed": counts.get("failed", 0),
                "retrying": counts.get("retrying", 0),
                "timeout": counts.get("timeout", 0),
                "cancelled": counts.get("cancelled", 0),
                "dead": counts.get("dead", 0),
                "backlog": pending,
                "delayed": delayed
            }
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════
# 任务队列引擎
# ═══════════════════════════════════════════════════════════

class TaskQueueEngine:
    """
    持久化任务队列引擎
    - 多Worker并发消费
    - 断电恢复: 重启后自动恢复running状态的任务
    - 指数退避重试
    - 死信队列
    """

    def __init__(self, data_dir: str = ".evo_data/taskqueue",
                 max_workers: int = 4, poll_interval: float = 1.0):
        self._store = TaskQueueStore(data_dir)
        self._max_workers = max_workers
        self._poll_interval = poll_interval
        self._running = False
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._worker_task: asyncio.Task | None = None
        self._total_processed = 0
        self._on_task_complete: Callable | None = None  # 任务完成回调
        logger.info("[TaskQueue] 初始化 | max_workers=%d", max_workers)

    @property
    def store(self) -> TaskQueueStore:
        return self._store

    # ─── 生命周期 ───

    async def start(self):
        if self._running:
            return
        self._running = True
        # 恢复中断的任务
        self._recover_stuck_tasks()
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("[TaskQueue] 已启动 | workers=%d", self._max_workers)

    async def stop(self):
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        # 等待运行中任务完成 (最多10秒)
        for _ in range(20):
            if not self._running_tasks:
                break
            await asyncio.sleep(0.5)
        logger.info("[TaskQueue] 已停止 | processed=%d", self._total_processed)

    def _recover_stuck_tasks(self):
        """恢复running状态的任务→pending"""
        conn = self._store._get_conn()
        try:
            stuck = conn.execute(
                "SELECT id FROM task_queue WHERE status='running'"
            ).fetchall()
            for r in stuck:
                logger.warning("[TaskQueue] 恢复卡住任务: %s", r['id'])
                self._store.update_status(r['id'], 'pending')
        finally:
            conn.close()

    # ─── 任务提交 ───

    def enqueue(self, name: str, target_type: str = "module",
                target_id: str = "", target_params: dict = None,
                priority: str = "normal", delay_until: str = "",
                max_retries: int = 3, timeout_seconds: float = 300.0,
                queue_name: str = "default", description: str = "",
                parent_task_id: str = "") -> TaskItem:
        """提交任务到队列"""
        task = TaskItem(
            name=name, target_type=target_type, target_id=target_id,
            target_params=target_params or {}, priority=priority,
            delay_until=delay_until, max_retries=max_retries,
            timeout_seconds=timeout_seconds, queue_name=queue_name,
            description=description, parent_task_id=parent_task_id
        )
        self._store.save_task(task)
        logger.info("[TaskQueue] 入队: %s (%s/%s) priority=%s", task.id[:12], task.name, task.target_type, task.priority)
        return task

    def enqueue_many(self, tasks: list[dict]) -> list[TaskItem]:
        """批量提交"""
        return [self.enqueue(**t) for t in tasks]

    # ─── Worker循环 ───

    async def _worker_loop(self):
        while self._running:
            try:
                await self._try_dispatch()
            except Exception as e:
                logger.error("[TaskQueue] Worker异常: %s", e)
            await asyncio.sleep(self._poll_interval)

    async def _try_dispatch(self):
        """尝试调度下一个任务"""
        async with self._lock:
            if len(self._running_tasks) >= self._max_workers:
                return

        task = self._store.next_pending(exclude_ids=set(self._running_tasks.keys()))
        if not task:
            return

        asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: TaskItem):
        """执行单个任务"""
        self._running_tasks[task.id] = asyncio.current_task()
        self._store.update_status(task.id, "running")

        logger.info("[TaskQueue] 执行: %s (%s/%s)", task.id[:12], task.name, task.target_type)

        try:
            # 带超时执行
            result = await asyncio.wait_for(
                self._dispatch(task),
                timeout=task.timeout_seconds
            )
            self._store.update_status(task.id, "success", result=result)
            logger.info("[TaskQueue] 成功: %s (%s)", task.id[:12], task.name)

        except TimeoutError:
            self._store.update_status(task.id, "timeout",
                                      error=f"超时 ({task.timeout_seconds}s)")
            logger.warning("[TaskQueue] 超时: %s (%s)", task.id[:12], task.name)
            self._handle_failure(task, "timeout")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self._store.update_status(task.id, "failed", error=error_msg)
            logger.error("[TaskQueue] 失败: %s (%s) %s", task.id[:12], task.name, error_msg)
            self._handle_failure(task, error_msg)

        finally:
            self._running_tasks.pop(task.id, None)
            self._total_processed += 1
            if self._on_task_complete:
                try:
                    self._on_task_complete(task)
                except Exception as _e:
                    logger.warning(f"error: {_e}")

    def _handle_failure(self, task: TaskItem, error: str):
        """处理失败: 重试或进入死信"""
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            delay = task.retry_delay_base * (2 ** (task.retry_count - 1))
            delay_until = (datetime.now() + timedelta(seconds=delay)).isoformat()
            self._store.update_status(task.id, "retrying", retry_count=task.retry_count)
            # 更新delay_until
            conn = self._store._get_conn()
            try:
                conn.execute("UPDATE task_queue SET delay_until=? WHERE id=?", (delay_until, task.id))
                conn.commit()
            finally:
                conn.close()
            logger.info("[TaskQueue] 重试 #%d: %s (%.1fs后)", task.retry_count, task.id[:12], delay)
        else:
            # 进入死信队列
            self._store.update_status(task.id, "dead", error=f"达到最大重试次数 | {error}")
            logger.error("[TaskQueue] 死信: %s (%s)", task.id[:12], task.name)

    async def _dispatch(self, task: TaskItem) -> dict:
        """分发执行任务"""
        if task.target_type == "module":
            return await self._execute_module(task)
        elif task.target_type == "pipeline":
            return await self._execute_pipeline(task)
        elif task.target_type == "url":
            return await self._execute_url(task)
        else:
            return {"error": f"不支持的目标类型: {task.target_type}"}

    async def _execute_module(self, task: TaskItem) -> dict:
        """执行模块"""
        try:
            from modules.module_registry import ModuleRegistry
            mm = ModuleRegistry()
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: mm.execute_module(task.target_id, **task.target_params)
            )
            return {"success": True, "result": result}
        except Exception as e:
            # 尝试直接import
            try:
                import importlib
                mod = importlib.import_module(f"modules.{task.target_id}")
                if hasattr(mod, "execute"):
                    result = mod.execute(**task.target_params)
                    return {"success": True, "result": result}
            except Exception as e2:
                raise RuntimeError(f"模块执行失败: {task.target_id} - {e2}")

    async def _execute_pipeline(self, task: TaskItem) -> dict:
        """执行管线"""
        try:
            from core.pipeline_engine import get_pipeline_engine
            engine = get_pipeline_engine()
            result = await engine.execute(task.target_id, params=task.target_params)
            return {"success": True, "result": result}
        except Exception as e:
            raise RuntimeError(f"管线执行失败: {task.target_id} - {e}")

    async def _execute_url(self, task: TaskItem) -> dict:
        """执行HTTP请求"""
        import aiohttp
        method = task.target_params.get("method", "GET").upper()
        url = task.target_id
        headers = task.target_params.get("headers", {})
        body = task.target_params.get("body", {})
        timeout = aiohttp.ClientTimeout(total=task.timeout_seconds)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, headers=headers, json=body) as resp:
                return {
                    "success": True,
                    "status": resp.status,
                    "body": await resp.text()[:5000]
                }

    # ─── 任务管理 ───

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._store.get_task(task_id)
        if not task:
            return False
        if task.status in ("running",):
            # 尝试取消asyncio task
            at = self._running_tasks.get(task_id)
            if at:
                at.cancel()
        if task.status in ("pending", "retrying"):
            self._store.update_status(task_id, "cancelled")
            return True
        return False

    def retry_task(self, task_id: str) -> bool:
        """手动重试任务"""
        task = self._store.get_task(task_id)
        if not task:
            return False
        if task.status in ("failed", "dead", "timeout"):
            task.retry_count = 0
            task.status = "pending"
            task.delay_until = ""
            task.error = ""
            self._store.save_task(task)
            return True
        return False

    # ─── 查询 ───

    def get_task(self, task_id: str) -> dict | None:
        task = self._store.get_task(task_id)
        return task.to_dict() if task else None

    def list_tasks(self, **kwargs) -> list[dict]:
        tasks = self._store.list_tasks(**kwargs)
        return [t.to_dict() for t in tasks]

    def stats(self) -> dict:
        s = self._store.stats()
        s["workers_active"] = len(self._running_tasks)
        s["max_workers"] = self._max_workers
        s["total_processed"] = self._total_processed
        return s

    def on_complete(self, callback: Callable):
        """注册任务完成回调"""
        self._on_task_complete = callback


# ─── 全局单例 ───

_engine: TaskQueueEngine | None = None

def get_task_queue_engine() -> TaskQueueEngine:
    global _engine
    if _engine is None:
        _engine = TaskQueueEngine()
    return _engine
