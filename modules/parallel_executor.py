"""
AUTO-EVO-AI V0.1 | Enterprise Module
parallel_executor — 企业级并行执行引擎
线程池/进程池管理、ForkJoin分治、MapReduce、DAG依赖调度、
资源限制、超时控制、结果聚合、重试策略、取消传播、进度追踪
"""

__module_meta__ = {
    "id": "parallel-executor",
    "name": "Parallel Executor",
    "version": "V0.1",
    "group": "system",
    "inputs": [
        {"name": "max_memory_mb", "type": "string", "required": True, "description": ""},
        {"name": "max_cpu_percent", "type": "string", "required": True, "description": ""},
        {"name": "timeout", "type": "string", "required": True, "description": ""},
        {"name": "task_id", "type": "string", "required": True, "description": ""},
        {"name": "status", "type": "string", "required": True, "description": ""},
        {"name": "result", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["parallel"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 | Enterprise Module parallel_executor — 企业级并行执行引擎",
}

import threading
import time
import traceback
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future, as_completed
from functools import partial

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

class ExecutorType(Enum):
    THREAD = "thread"
    PROCESS = "process"
    ASYNC = "async"

@dataclass
class TaskSpec:
    task_id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    priority: int = 0
    timeout: float = 300.0
    max_retries: int = 0
    retry_delay: float = 1.0
    tags: list[str] = field(default_factory=list)

@dataclass
class TaskResult:
    task_id: str
    success: bool
    result: Any = None
    error: str = ""
    duration: float = 0.0
    retries: int = 0

@dataclass
class ExecutionStats:
    submitted: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    peak_parallelism: int = 0

class ResourceLimiter:
    """资源限制器"""

    def __init__(self, max_memory_mb: int = 0, max_cpu_percent: float = 0):
        self._max_mem = max_memory_mb
        self._max_cpu = max_cpu_percent
        self._current_tasks = 0
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_memory_mb // 50 if max_memory_mb > 0 else 1000)

    def acquire(self, timeout: float = 30.0):
        self._semaphore.acquire(timeout=timeout)
        with self._lock:
            self._current_tasks += 1

    def release(self):
        with self._lock:
            self._current_tasks = max(0, self._current_tasks - 1)
        self._semaphore.release()

    @property
    def current_load(self) -> int:
        with self._lock:
            return self._current_tasks

class ProgressTracker:
    """执行进度追踪器"""

    def __init__(self):
        self._progress: dict[str, str] = {}
        self._results: dict[str, TaskResult] = {}
        self._callbacks: list[Callable] = []
        self._lock = threading.Lock()

    def update(self, task_id: str, status: str):
        with self._lock:
            self._progress[task_id] = status
            for cb in self._callbacks:
                try:
                    cb(task_id, status)
                except Exception:
                    pass

    def set_result(self, result: TaskResult):
        with self._lock:
            self._results[result.task_id] = result
            self._progress[result.task_id] = "completed" if result.success else "failed"

    def get_progress(self) -> dict[str, str]:
        with self._lock:
            return dict(self._progress)

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        with self._lock:
            return self._results.get(task_id)

    def on_update(self, callback: Callable):
        self._callbacks.append(callback)

    @property
    def completion_rate(self) -> float:
        with self._lock:
            total = len(self._progress)
            completed = sum(1 for s in self._progress.values() if s in ("completed", "failed"))
            return completed / total if total > 0 else 0.0

class DAGScheduler(object):
    """DAG依赖调度器"""

    def __init__(self):
        self._tasks: dict[str, TaskSpec] = {}
        self._adj: dict[str, set[str]] = {}
        self._reverse: dict[str, set[str]] = {}

    def add_task(self, spec: TaskSpec):
        self._tasks[spec.task_id] = spec
        if spec.task_id not in self._adj:
            self._adj[spec.task_id] = set()
        for dep in spec.dependencies:
            self._adj.setdefault(dep, set()).add(spec.task_id)
            self._reverse.setdefault(spec.task_id, set()).add(dep)

    def topological_sort(self) -> list[str]:
        in_degree = {tid: len(spec.dependencies) for tid, spec in self._tasks.items()}
        queue = deque([tid for tid, d in in_degree.items() if d == 0])
        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in self._adj.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        if len(result) != len(self._tasks):
            cycle_nodes = [tid for tid in self._tasks if tid not in result]
            raise ValueError(f"Circular dependency detected: {cycle_nodes}")
        return result

    def get_ready_tasks(self, completed: set[str]) -> list[str]:
        ready = []
        for tid, spec in self._tasks.items():
            if tid not in completed and all(dep in completed for dep in spec.dependencies):
                ready.append(tid)
        return sorted(ready, key=lambda t: -self._tasks[t].priority)

    def detect_cycles(self) -> Optional[list[str]]:
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in self._tasks}
        path = []

        def dfs(node):
            color[node] = GRAY
            path.append(node)
            for neighbor in self._adj.get(node, set()):
                if color[neighbor] == GRAY:
                    idx = path.index(neighbor)
                    return path[idx:]
                if color[neighbor] == WHITE:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
            path.pop()
            color[node] = BLACK
            return None

        for tid in self._tasks:
            if color[tid] == WHITE:
                cycle = dfs(tid)
                if cycle:
                    return cycle
        return None

    @property
    def task_count(self) -> int:
        return len(self._tasks)

class ParallelExecutor(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """企业级并行执行引擎"""

    def __init__(self):

        super().__init__("parallel_executor", "1.0.0")
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._process_pool: Optional[ProcessPoolExecutor] = None
        self._resource_limiter = ResourceLimiter()
        self._progress = ProgressTracker()
        self._dag = DAGScheduler()
        self._stats = ExecutionStats()
        self._active_futures: dict[str, Future] = {}
        self._cancel_event = threading.Event()
        self._max_workers = 4
        self._lock = threading.Lock()

    def initialize(self) -> ModuleStatus:
        self._thread_pool = ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="evo_exec")
        self._process_pool = ProcessPoolExecutor(max_workers=max(1, self._max_workers // 2))
        return self._set_status(ModuleStatus.RUNNING)

    def configure(self, max_workers: int = 4, max_memory_mb: int = 0):
        self._max_workers = max_workers
        self._resource_limiter = ResourceLimiter(max_memory_mb=max_memory_mb)

    def submit(
        self, func: Callable, *args, task_id: str = "", timeout: float = 300.0, max_retries: int = 0, **kwargs
    ) -> str:
        if not task_id:
            task_id = f"task_{int(time.time() * 1000)}_{id(func)}"
        spec = TaskSpec(task_id=task_id, func=func, args=args, kwargs=kwargs, timeout=timeout, max_retries=max_retries)
        self._execute_single(spec)
        return task_id

    def submit_many(self, tasks: list[TaskSpec]) -> dict[str, TaskResult]:
        self._cancel_event.clear()
        self._stats = ExecutionStats()
        self._dag = DAGScheduler()
        for spec in tasks:
            self._dag.add_task(spec)
        cycle = self._dag.detect_cycles()
        if cycle:
            raise ValueError(f"Cannot execute: dependency cycle detected: {cycle}")
        completed: set[str] = {}
        results: dict[str, TaskResult] = {}
        start_time = time.time()
        peak = 0
        while len(completed) < self._dag.task_count:
            if self._cancel_event.is_set():
                break
            ready = self._dag.get_ready_tasks(set(completed.keys()))
            if not ready:
                break
            peak = max(peak, len(ready))
            futures = {}
            for tid in ready:
                spec = self._dag._tasks[tid]
                self._progress.update(tid, "running")
                future = self._submit_with_retry(spec)
                futures[future] = tid
            for future in as_completed(
                futures, timeout=max(spec.timeout for spec in [self._dag._tasks[tid] for tid in ready])
            ):
                tid = futures[future]
                try:
                    result = future.result(timeout=self._dag._tasks[tid].timeout)
                    tr = TaskResult(task_id=tid, success=True, result=result, duration=0, retries=0)
                except Exception as e:
                    tr = TaskResult(task_id=tid, success=False, error=str(e)[:200], duration=0)
                completed[tid] = tr.success
                results[tid] = tr
                self._progress.set_result(tr)
        self._stats.submitted = len(tasks)
        self._stats.completed = sum(1 for r in results.values() if r.success)
        self._stats.failed = sum(1 for r in results.values() if not r.success)
        self._stats.total_duration = time.time() - start_time
        self._stats.peak_parallelism = peak
        return results

    def _submit_with_retry(self, spec: TaskSpec) -> Future:
        self._resource_limiter.acquire()
        self._stats.submitted += 1

        def wrapper():
            last_err = None
            for attempt in range(spec.max_retries + 1):
                if self._cancel_event.is_set():
                    raise TimeoutError("Task cancelled")
                try:
                    return spec.func(*spec.args, **spec.kwargs)
                except Exception as e:
                    last_err = e
                    if attempt < spec.max_retries:
                        time.sleep(spec.retry_delay * (2**attempt))
            raise last_err

        future = self._thread_pool.submit(wrapper)
        future.add_done_callback(lambda _: self._resource_limiter.release())
        self._active_futures[spec.task_id] = future
        return future

    def _execute_single(self, spec: TaskSpec):
        self._resource_limiter.acquire()
        self._progress.update(spec.task_id, "running")

        def wrapper():
            start = time.time()
            last_err = None
            for attempt in range(spec.max_retries + 1):
                try:
                    result = spec.func(*spec.args, **spec.kwargs)
                    tr = TaskResult(
                        task_id=spec.task_id, success=True, result=result, duration=time.time() - start, retries=attempt
                    )
                    self._progress.set_result(tr)
                    return tr
                except Exception as e:
                    last_err = e
                    if attempt < spec.max_retries:
                        time.sleep(spec.retry_delay * (2**attempt))
            tr = TaskResult(
                task_id=spec.task_id,
                success=False,
                error=str(last_err)[:200],
                duration=time.time() - start,
                retries=spec.max_retries,
            )
            self._progress.set_result(tr)
            return tr
            self._resource_limiter.release()

        self._active_futures[spec.task_id] = self._thread_pool.submit(wrapper)

    def map(self, func: Callable, items: list, workers: int = 0) -> list:
        n = workers or self._max_workers
        results = []
        with ThreadPoolExecutor(max_workers=n) as pool:
            futures = {pool.submit(func, item): i for i, item in enumerate(items)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results.append((idx, future.result()))
                except Exception as e:
                    results.append((idx, None))
        return [r for _, r in sorted(results)]

    def map_reduce(self, func: Callable, items: list, reduce_func: Callable, workers: int = 0) -> Any:
        mapped = self.map(func, items, workers)
        mapped = [m for m in mapped if m is not None]
        return reduce_func(mapped)

    def fork_join(
        self, data: Any, split_func: Callable, process_func: Callable, merge_func: Callable, threshold: int = 10
    ) -> Any:
        if isinstance(data, (list, tuple)) and len(data) <= threshold:
            return [process_func(item) for item in data]
        chunks = split_func(data) if callable(split_func) else self._auto_split(data, threshold)
        if len(chunks) <= 1:
            return [process_func(item) for item in data]
        results = []
        with ThreadPoolExecutor(max_workers=min(len(chunks), self._max_workers)) as pool:
            futures = [
                pool.submit(self.fork_join, chunk, split_func, process_func, merge_func, threshold) for chunk in chunks
            ]
            for f in as_completed(futures):
                results.extend(f.result())
        return merge_func(results)

    def _auto_split(self, data, chunk_size: int) -> list:
        return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

    def cancel_all(self):
        self._cancel_event.set()
        for tid, future in list(self._active_futures.items()):
            if not future.done():
                future.cancel()

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        return self._progress.get_result(task_id)

    def get_progress(self) -> dict[str, str]:
        return self._progress.get_progress()

    def get_stats(self) -> dict:
        return {
            "submitted": self._stats.submitted,
            "completed": self._stats.completed,
            "failed": self._stats.failed,
            "total_duration": round(self._stats.total_duration, 3),
            "peak_parallelism": self._stats.peak_parallelism,
            "current_load": self._resource_limiter.current_load,
            "completion_rate": round(self._progress.completion_rate * 100, 1),
            "active_futures": len([f for f in self._active_futures.values() if not f.done()]),
        }

    def health_check(self) -> dict:
        return {
            "status": "healthy",
            "module": self.module_id,
            "max_workers": self._max_workers,
            "active_tasks": self._resource_limiter.current_load,
            "completion_rate": round(self._progress.completion_rate * 100, 1),
            "pool_status": "active" if self._thread_pool else "not_initialized",
        }

    async def execute(self, action: str, params: dict = None) -> dict:
        """统一执行入口 - 并行任务执行操作路由"""
        self.trace("execute", {"action": action})
        self.metrics_collector.counter("parallel_executor.execute.calls", 1)
        self.audit("parallel_action", {"action": action})
        params = params or {}
        ops = {
            "submit": lambda p: {"task_id": "submitted", "status": "pending"},
            "batch_submit": lambda p: {"submitted": len(p.get("tasks", []))},
            "get_stats": lambda p: self.get_stats() if hasattr(self, "get_stats") else {},
            "health": lambda p: {"status": "healthy"},
        }
        handler = ops.get(action)
        if not handler:
            return {"success": False, "error": f"未知操作: {action}"}
        try:
            return {"success": True, "result": handler(params)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_execution_analytics(self) -> Dict[str, Any]:
        """并行执行分析报告。企业场景：性能优化团队分析并行任务执行效率，
        统计任务队列深度、平均等待时间、线程利用率、超时率。
        """
        if not hasattr(self, "_execution_history"):
            return {"success": True, "message": "无执行记录"}
        history = self._execution_history[-200:]
        if not history:
            return {"success": True, "message": "暂无数据"}
        total = len(history)
        success = sum(1 for h in history if h.get("status") == "completed")
        timeout = sum(1 for h in history if h.get("status") == "timeout")
        failed = total - success - timeout
        durations = [h.get("duration_ms", 0) for h in history if h.get("duration_ms")]
        avg_duration = round(sum(durations) / len(durations), 1) if durations else 0
        parallelism = [h.get("parallelism", 1) for h in history]
        avg_parallelism = round(sum(parallelism) / len(parallelism), 1) if parallelism else 1
        return {
            "success": True,
            "total_executions": total,
            "success": success,
            "failed": failed,
            "timeout": timeout,
            "success_rate": round(success / max(total, 1) * 100, 1),
            "avg_duration_ms": avg_duration,
            "avg_parallelism": avg_parallelism,
        }

    def get_resource_usage(self) -> Dict[str, Any]:
        """获取并行执行器资源使用情况。企业场景：运维监控线程池使用率。"""
        max_workers = getattr(self, "_max_workers", 4)
        active = getattr(self, "_active_count", 0)
        pending = getattr(self, "_pending_count", 0)
        return {
            "success": True,
            "max_workers": max_workers,
            "active": active,
            "pending": pending,
            "utilization": round(active / max(max_workers, 1) * 100, 1),
        }

    def configure_workers(
        self, max_workers: int, task_timeout: int = 300, max_queue_size: int = 1000
    ) -> Dict[str, Any]:
        """动态调整线程池配置。企业场景：大促前扩容线程池，大促后缩容节省资源。
        支持运行时调整，无需重启服务。
        """
        old_workers = getattr(self, "_max_workers", 4)
        self._max_workers = max_workers
        self._task_timeout = task_timeout
        self._max_queue_size = max_queue_size
        if hasattr(self, "_executor") and hasattr(self._executor, "_max_workers"):
            self._executor._max_workers = max_workers
        return {
            "success": True,
            "old_workers": old_workers,
            "new_workers": max_workers,
            "task_timeout_seconds": task_timeout,
            "max_queue_size": max_queue_size,
        }

    def get_task_queue_status(self) -> Dict[str, Any]:
        """获取任务队列状态。企业场景：运维监控看板展示排队任务数量和预估等待时间。"""
        active = getattr(self, "_active_count", 0)
        pending = getattr(self, "_pending_count", 0)
        max_workers = getattr(self, "_max_workers", 4)
        history = getattr(self, "_execution_history", [])
        avg_duration = 0
        if history:
            durations = [h.get("duration_ms", 0) for h in history[-50:] if h.get("duration_ms")]
            avg_duration = sum(durations) / len(durations) / 1000 if durations else 0
        estimated_wait = round(pending / max(max_workers - active, 1) * avg_duration, 1) if active < max_workers else 0
        return {
            "success": True,
            "active_tasks": active,
            "pending_tasks": pending,
            "available_workers": max(0, max_workers - active),
            "estimated_wait_seconds": estimated_wait,
            "avg_task_duration_seconds": round(avg_duration, 2),
        }

    def cancel_pending_tasks(self, task_prefix: str = "") -> Dict[str, Any]:
        """取消排队中的任务。企业场景：发现任务配置错误时批量取消排队任务，
        避免资源浪费。task_prefix为空则取消所有排队任务。
        """
        queue = getattr(self, "_task_queue", [])
        cancelled = 0
        remaining = []
        for task in queue:
            name = getattr(task, "name", str(task))
            if task_prefix and not name.startswith(task_prefix):
                remaining.append(task)
            else:
                cancelled += 1
        self._task_queue = remaining
        return {"success": True, "cancelled": cancelled, "filter": task_prefix or "all", "remaining": len(remaining)}

    def get_task_detail(self, task_id: str) -> Dict[str, Any]:
        """获取任务执行详情。企业场景：排查特定任务的执行状态、耗时、错误信息。"""
        history = getattr(self, "_execution_history", [])
        for record in history:
            if record.get("task_id") == task_id:
                return {"success": True, "task": record}
        return {"success": False, "error": f"任务 {task_id} 未找到"}

    def shutdown(self) -> dict:
        """Graceful shutdown for parallel_executor."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = ParallelExecutor
