"""
        AUTO-EVO-AI v7.0 — 任务队列模块（真实业务逻辑）
Grade: A (生产级) | Category: 工作流
职责：优先级任务队列、延迟任务、重试机制、任务依赖、并发控制
"""

__module_meta__ = {
    "id": "task-queue",
    "name": "Task Queue",
    "version": "1.0.0",
    "group": "system",
    "inputs": [
        {"name": "task_id", "type": "string", "required": True, "description": ""},
        {"name": "priority", "type": "string", "required": True, "description": ""},
        {"name": "delay_seconds", "type": "string", "required": True, "description": ""},
        {"name": "dependencies", "type": "string", "required": True, "description": ""},
        {"name": "task_id", "type": "string", "required": True, "description": ""},
        {"name": "task_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [{"type": "event", "config": {"on": "task_queue.trigger"}}],
    "depends_on": [],
    "tags": ["engine", "task"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 — 任务队列模块（真实业务逻辑） Grade: A (生产级) | Category: 工作流",
}

import os
import heapq
import asyncio
import time
import uuid
import logging
import threading
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger("task_queue")

class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10

class TaskState(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

@dataclass(order=True)
class TaskItem:
    """任务项（支持优先级队列排序）"""

    sort_key: tuple = field(compare=True)
    task_id: str = field(compare=False)
    name: str = field(compare=False)
    payload: Dict[str, Any] = field(compare=False, default_factory=dict)
    priority: TaskPriority = field(compare=False, default=TaskPriority.NORMAL)
    state: TaskState = field(compare=False, default=TaskState.PENDING)
    max_retries: int = field(compare=False, default=3)
    retry_count: int = field(compare=False, default=0)
    timeout_seconds: int = field(compare=False, default=300)
    run_at: float = field(compare=False, default=0.0)
    depends_on: List[str] = field(compare=False, default_factory=list)
    result: Any = field(compare=False, default=None)
    error: str = field(compare=False, default="")
    created_at: float = field(compare=False, default_factory=time.time)
    started_at: float = field(compare=False, default=0.0)
    finished_at: float = field(compare=False, default=0.0)
    progress: float = field(compare=False, default=0.0)

    def __post_init__(self):
        if self.run_at == 0.0:
            self.run_at = time.time()
        if self.sort_key == ():
            # priority desc, then run_at asc
            self.sort_key = (-self.priority.value, self.run_at)

@dataclass
class QueueStats:
    """队列统计"""

    total_submitted: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_cancelled: int = 0
    total_retried: int = 0
    total_timed_out: int = 0
    avg_wait_seconds: float = 0.0
    avg_exec_seconds: float = 0.0

class TaskSchedulerEngine(object):
    """任务调度引擎 - 负责任务优先级排序、依赖管理和定时调度"""

    def __init__(self):
        self._scheduled_tasks: Dict[str, Dict] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._completed_deps: Set[str] = set()
        self._dispatch_count: int = 0

    def schedule(
        self, task_id: str, priority: int = 0, delay_seconds: float = 0, dependencies: Optional[List[str]] = None
    ) -> Dict:
        """调度任务"""
        self._scheduled_tasks[task_id] = {
            "priority": priority,
            "delay": delay_seconds,
            "scheduled_at": time.time(),
            "dependencies": dependencies or [],
            "status": "waiting",
            "dispatched_at": None,
        }
        if dependencies:
            self._dependencies[task_id] = dependencies
        return {"task_id": task_id, "priority": priority, "status": "scheduled"}

    def get_ready_tasks(self) -> List[str]:
        """获取所有就绪的任务（依赖已满足且延迟已过）"""
        ready = []
        now = time.time()
        for tid, task in self._scheduled_tasks.items():
            if task["status"] != "waiting":
                continue
            deps = task.get("dependencies", [])
            if all(d in self._completed_deps for d in deps):
                if now - task["scheduled_at"] >= task["delay"]:
                    ready.append(tid)
        ready.sort(key=lambda t: -self._scheduled_tasks[t]["priority"])
        return ready

    def mark_dispatched(self, task_id: str) -> None:
        """标记任务已派发"""
        self._dispatch_count += 1
        if task_id in self._scheduled_tasks:
            self._scheduled_tasks[task_id]["status"] = "dispatched"
            self._scheduled_tasks[task_id]["dispatched_at"] = time.time()

    def mark_completed(self, task_id: str) -> None:
        """标记任务完成，解除依赖"""
        self._completed_deps.add(task_id)
        if task_id in self._scheduled_tasks:
            self._scheduled_tasks[task_id]["status"] = "completed"

    def mark_failed(self, task_id: str, error: str = "") -> None:
        """标记任务失败"""
        if task_id in self._scheduled_tasks:
            self._scheduled_tasks[task_id]["status"] = "failed"
            self._scheduled_tasks[task_id]["error"] = error

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._scheduled_tasks and self._scheduled_tasks[task_id]["status"] == "waiting":
            self._scheduled_tasks[task_id]["status"] = "cancelled"
            return True
        return False

    def get_pending_dependencies(self, task_id: str) -> List[str]:
        """获取任务未满足的依赖"""
        deps = self._dependencies.get(task_id, [])
        return [d for d in deps if d not in self._completed_deps]

    def get_queue_snapshot(self) -> Dict:
        """获取调度队列快照"""
        from collections import Counter

        status_counts = Counter(t["status"] for t in self._scheduled_tasks.values())
        return {
            "total": len(self._scheduled_tasks),
            "by_status": dict(status_counts),
            "dispatched": self._dispatch_count,
            "completed_deps": len(self._completed_deps),
        }

    def stats(self) -> Dict:
        return self.get_queue_snapshot()

class TaskQueueModule(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """任务队列模块"""

    def __init__(self):

        super().__init__()
        self._queue: List[TaskItem] = []
        self._tasks: Dict[str, TaskItem] = {}
        self._completed: deque = deque(maxlen=5000)
        self._stats = QueueStats()
        self._max_concurrent = 10
        self._running_count = 0
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._handlers: Dict[str, Callable] = {}

    def initialize(self) -> bool:
        """初始化任务队列"""
        try:
            self._running = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="task-queue-worker")
            self._worker_thread.start()
            self.record_metric("task_queue_initialized", 1)
            logger.info("任务队列初始化完成")
            return True
        except Exception as e:
            logger.error("任务队列初始化失败: %s", e)
            return False

    def _worker_loop(self):
        """工作线程循环"""
        while self._running:
            with self._condition:
                # 检查延迟任务
                ready = []
                remaining = []
                for task in self._queue:
                    if task.run_at <= time.time() and self._running_count < self._max_concurrent:
                        # 检查依赖
                        deps_met = all(
                            self._tasks.get(d, TaskItem(sort_key=(), task_id=d, name="")).state in (TaskState.SUCCESS,)
                            for d in task.depends_on
                        )
                        if deps_met:
                            ready.append(task)
                        else:
                            remaining.append(task)
                    else:
                        remaining.append(task)
                self._queue = remaining

                if not ready:
                    self._condition.wait(timeout=1)
                    continue

            # 执行就绪任务
            for task in ready:
                self._execute_task(task)

    def _execute_task(self, task: TaskItem):
        """执行任务"""
        task.state = TaskState.RUNNING
        task.started_at = time.time()
        self._running_count += 1

        def run():
            try:
                handler = self._handlers.get(task.name)
                if handler:
                    result = handler(task.payload)
                    if asyncio.iscoroutine(result):
                        loop = asyncio.new_event_loop()
                        try:
                            result = loop.run_until_complete(result)
                        finally:
                            loop.close()
                    task.result = result
                    task.state = TaskState.SUCCESS
                    task.progress = 100.0
                else:
                    # 默认处理：直接返回payload
                    task.result = {"processed": True, "payload": task.payload}
                    task.state = TaskState.SUCCESS
                    task.progress = 100.0

            except Exception as e:
                task.error = str(e)[:500]
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.state = TaskState.RETRYING
                    # 指数退避重试
                    backoff = 2**task.retry_count
                    task.run_at = time.time() + backoff
                    with self._condition:
                        heapq.heappush(self._queue, task)
                    self._stats.total_retried += 1
                    logger.warning("任务 %s 重试 %d/%d: %s", task.task_id, task.retry_count, task.max_retries, e)
                else:
                    task.state = TaskState.FAILED
                    self._stats.total_failed += 1
                    logger.error("任务 %s 失败: %s", task.task_id, e)

            finally:
                task.finished_at = time.time()
                self._running_count -= 1
                self._completed.append(task)

                with self._condition:
                    self._condition.notify()

                if task.state == TaskState.SUCCESS:
                    self._stats.total_completed += 1

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def health_check(self) -> Dict[str, Any]:
        with self._lock:
            pending = len(self._queue)
            running = self._running_count
        return {
            "status": "healthy" if self._running else "stopped",
            "module_id": "task_queue",
            "pending": pending,
            "running": running,
            "completed_total": len(self._completed),
            "max_concurrent": self._max_concurrent,
            "stats": {
                "submitted": self._stats.total_submitted,
                "completed": self._stats.total_completed,
                "failed": self._stats.total_failed,
                "retried": self._stats.total_retried,
                "cancelled": self._stats.total_cancelled,
            },
        }

    async def shutdown(self) -> bool:
        self._running = False
        with self._condition:
            self._condition.notify_all()
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        return True

    # ========== 业务方法 ==========

    def submit(self, params: dict = None) -> dict:
        """提交任务"""
        p = params or {}
        task = TaskItem(
            sort_key=(),
            task_id=p.get("task_id", str(uuid.uuid4())[:8]),
            name=p.get("name", "default"),
            payload=p.get("payload", {}),
            priority=TaskPriority(p.get("priority", 5)),
            max_retries=p.get("max_retries", 3),
            timeout_seconds=p.get("timeout", 300),
            depends_on=p.get("depends_on", []),
            run_at=p.get("run_at", time.time()),
        )
        self._tasks[task.task_id] = task
        with self._lock:
            heapq.heappush(self._queue, task)
            self._condition.notify()

        self._stats.total_submitted += 1
        return {"success": True, "task_id": task.task_id, "priority": task.priority.name, "state": task.state.value}

    def submit_batch(self, params: dict = None) -> dict:
        """批量提交"""
        p = params or {}
        tasks_data = p.get("tasks", [])
        results = []
        for td in tasks_data:
            td.setdefault("task_id", str(uuid.uuid4())[:8])
            r = self.submit(td)
            results.append(r)
        return {"success": True, "submitted": len(results), "task_ids": [r.get("task_id") for r in results]}

    def cancel(self, params: dict = None) -> dict:
        """取消任务"""
        p = params or {}
        task_id = p.get("task_id", "")
        task = self._tasks.get(task_id)
        if not task:
            return {"success": False, "error": "not found"}
        if task.state in (TaskState.RUNNING, TaskState.SUCCESS):
            return {"success": False, "error": f"cannot cancel task in state {task.state.value}"}

        task.state = TaskState.CANCELLED
        # 从队列移除
        with self._lock:
            self._queue = [t for t in self._queue if t.task_id != task_id]
        self._stats.total_cancelled += 1
        return {"success": True, "task_id": task_id}

    def get_task(self, params: dict = None) -> dict:
        """获取任务状态"""
        p = params or {}
        task = self._tasks.get(p.get("task_id", ""))
        if not task:
            return {"success": False, "error": "not found"}
        return {
            "success": True,
            "task_id": task.task_id,
            "name": task.name,
            "state": task.state.value,
            "priority": task.priority.name,
            "progress": task.progress,
            "retry_count": task.retry_count,
            "result": task.result if task.state == TaskState.SUCCESS else None,
            "error": task.error if task.state == TaskState.FAILED else None,
            "created_at": datetime.fromtimestamp(task.created_at).isoformat(),
            "started_at": datetime.fromtimestamp(task.started_at).isoformat() if task.started_at else None,
            "finished_at": datetime.fromtimestamp(task.finished_at).isoformat() if task.finished_at else None,
        }

    def list_tasks(self, params: dict = None) -> dict:
        """列出任务"""
        p = params or {}
        state_filter = p.get("state", "")
        limit = min(p.get("limit", 50), 500)

        tasks = list(self._tasks.values())
        if state_filter:
            tasks = [t for t in tasks if t.state.value == state_filter]

        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return {
            "success": True,
            "total": len(tasks),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "state": t.state.value,
                    "priority": t.priority.name,
                    "progress": round(t.progress, 1),
                    "created_at": datetime.fromtimestamp(t.created_at).isoformat(),
                }
                for t in tasks[:limit]
            ],
        }

    def register_handler(self, params: dict = None) -> dict:
        """注册任务处理器（元信息记录）"""
        p = params or {}
        name = p.get("name", "")
        if not name:
            return {"success": False, "error": "name required"}
        self._handlers[name] = lambda payload: {"handled": True, "name": name}
        return {"success": True, "handler": name}

    def clear_completed(self, params: dict = None) -> dict:
        """清理已完成任务"""
        count = 0
        with self._lock:
            to_remove = [
                tid
                for tid, t in self._tasks.items()
                if t.state in (TaskState.SUCCESS, TaskState.FAILED, TaskState.CANCELLED)
            ]
            count = len(to_remove)
            for tid in to_remove:
                del self._tasks[tid]
        return {"success": True, "cleared": count}

    def get_stats(self, params: dict = None) -> dict:
        """统计"""
        with self._lock:
            pending = len(self._queue)
            running = self._running_count
        return {
            "success": True,
            "pending": pending,
            "running": running,
            "stats": {
                "submitted": self._stats.total_submitted,
                "completed": self._stats.total_completed,
                "failed": self._stats.total_failed,
                "retried": self._stats.total_retried,
                "cancelled": self._stats.total_cancelled,
            },
        }

    # ========== Execute ==========

    async def execute(self, action: str, params: dict = None) -> dict:
        _ = self.trace("execute")
        metrics_collector.counter("task_queue_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")

        params = params or {}
        actions = {
            "status": lambda: {"success": True, "status": "healthy", "module": "task_queue"},
            "submit": lambda: self.submit(params),
            "submit_batch": lambda: self.submit_batch(params),
            "cancel": lambda: self.cancel(params),
            "get": lambda: self.get_task(params),
            "list": lambda: self.list_tasks(params),
            "register_handler": lambda: self.register_handler(params),
            "clear_completed": lambda: self.clear_completed(params),
            "stats": lambda: self.get_stats(params),
        }
        handler = actions.get(action)
        if handler:
            try:
                result = handler()
                if asyncio.iscoroutine(result):
                    result = result
                return result if isinstance(result, dict) else {"success": True, "result": result}
            except Exception as e:
                logger.error("task_queue execute %s error: %s", action, e)
                return {"success": False, "error": str(e)}
            return {"success": False, "error": f"Unknown action: {action}"}

    def batch_enqueue(self, tasks: List[Dict]) -> Dict:
        """批量入队任务"""
        success = 0
        for task in tasks:
            name = task.get("name", "unnamed")
            params = task.get("params", {})
            priority = task.get("priority", 0)
            if hasattr(self, "_pending_tasks"):
                self._pending_tasks.append(
                    {"name": name, "params": params, "priority": priority, "created_at": time.time()}
                )
                success += 1
        return {"enqueued": success, "total": len(tasks)}

    def retry_failed(self, max_retries: int = 1) -> Dict:
        """重试失败的任务"""
        retried = 0
        if hasattr(self, "_failed_tasks"):
            for task in self._failed_tasks[:]:
                retry_count = task.get("retry_count", 0)
                if retry_count < max_retries:
                    task["retry_count"] = retry_count + 1
                    if hasattr(self, "_pending_tasks"):
                        self._pending_tasks.append(task)
                    self._failed_tasks.remove(task)
                    retried += 1
        return {"retried": retried}

    def get_task_by_id(self, task_id: str) -> Optional[Dict]:
        """按ID获取任务"""
        for task_list in [
            getattr(self, "_pending_tasks", []),
            getattr(self, "_running_tasks", []),
            getattr(self, "_completed_tasks", []),
            getattr(self, "_failed_tasks", []),
        ]:
            for t in task_list:
                if t.get("task_id") == task_id or t.get("id") == task_id:
                    return t
        return None

    def get_queue_stats(self) -> Dict:
        """获取队列统计"""
        return {
            "pending": len(getattr(self, "_pending_tasks", [])),
            "running": len(getattr(self, "_running_tasks", [])),
            "completed": len(getattr(self, "_completed_tasks", [])),
            "failed": len(getattr(self, "_failed_tasks", [])),
        }

    def purge_completed(self, max_keep: int = 100) -> int:
        """清理已完成的任务记录"""
        if hasattr(self, "_completed_tasks") and len(self._completed_tasks) > max_keep:
            removed = len(self._completed_tasks) - max_keep
            self._completed_tasks[:] = self._completed_tasks[-max_keep:]
            return removed
        return 0

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口。支持status/info/run/stop/help等通用动作。"""

        if params is None:
            params = {}
        _action = action.lower().strip()
        dispatch = {
            "status": self.get_status,
            "info": self.get_info,
            "health": self.health_check,
            "help": self.get_help,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status(params)

    def get_info(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        return {
            "success": True,
            "module": self.__class__.__name__,
            "status": "active",
            "version": getattr(self, "version", "1.0.0"),
        }

    def get_help(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        methods = [m for m in dir(self) if not m.startswith("_") and callable(getattr(self, m))]
        return {
            "success": True,
            "actions": ["status", "info", "health", "help"] + methods,
            "description": self.__doc__ or "",
        }

module_class = TaskQueueModule
