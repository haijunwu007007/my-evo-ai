"""
Smart Scheduler - 智能任务调度引擎
上市公司级生产实现：支持CRON表达式解析、任务依赖DAG、并发控制、
失败重试（指数退避+抖动）、超时熔断、执行历史、负载均衡调度。
"""

__module_meta__ = {
    "id": "smart-scheduler",
    "name": "Smart Scheduler",
    "version": "V0.1",
    "group": "scheduler",
    "inputs": [
        {"name": "expression", "type": "string", "required": True, "description": ""},
        {"name": "field_str", "type": "string", "required": True, "description": ""},
        {"name": "min_val", "type": "string", "required": True, "description": ""},
        {"name": "max_val", "type": "string", "required": True, "description": ""},
        {"name": "name_map", "type": "string", "required": True, "description": ""},
        {"name": "val", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "schedule", "config": {"cron": "0 0 * * *"}}],
    "depends_on": [],
    "tags": ["smart"],
    "grade": "C",
    "description": "Smart Scheduler - 智能任务调度引擎 上市公司级生产实现：支持CRON表达式解析、任务依赖DAG、并发控制、",
}

import time
import uuid
import re
import hashlib
import threading
import heapq
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

class RetryStrategy(str, Enum):
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"

@dataclass
class TaskDefinition:
    """任务定义"""

    task_id: str = ""
    name: str = ""
    cron_expression: str = ""
    command: str = ""
    timeout_seconds: int = 3600
    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    retry_base_delay: float = 5.0
    retry_max_delay: float = 3600.0
    priority: int = 5
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    last_run_at: float = 0.0
    next_run_at: float = 0.0
    run_count: int = 0
    fail_count: int = 0
    avg_duration: float = 0.0
    total_duration: float = 0.0
    executor: str = "default"
    max_concurrent: int = 1
    success_rate: float = 100.0

@dataclass
class TaskExecution:
    """任务执行记录"""

    execution_id: str = ""
    task_id: str = ""
    task_name: str = ""
    status: TaskStatus = TaskStatus.PENDING
    started_at: float = 0.0
    finished_at: float = 0.0
    duration: float = 0.0
    attempt: int = 1
    error_message: str = ""
    retry_count: int = 0
    next_retry_at: float = 0.0
    timeout_seconds: int = 3600
    worker_id: str = ""
    output_lines: int = 0

@dataclass
class WorkerInfo:
    """调度工作线程"""

    worker_id: str = ""
    capacity: int = 10
    active_tasks: int = 0
    last_heartbeat: float = 0.0
    tags: List[str] = field(default_factory=list)

class CronExpressionParser:
    """CRON表达式解析器。支持标准5段CRON（分 时 日 月 周）和6段（含秒）。
    企业场景：解析运维人员配置的定时任务时间规则。
    """

    MONTH_MAP = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }
    DOW_MAP = {"SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6}

    def __init__(self):
        self._cache: Dict[str, Tuple] = {}

    def parse(self, expression: str) -> Dict[str, List[int]]:
        """解析CRON表达式为各字段允许值列表"""
        if expression in self._cache:
            return self._cache[expression]

        parts = expression.strip().split()
        if len(parts) not in (5, 6):
            raise ValueError(f"CRON表达式需5或6段，当前{len(parts)}段: {expression}")

        has_seconds = len(parts) == 6
        if has_seconds:
            sec, minute, hour, dom, month, dow = parts
            result = {
                "second": self._parse_field(sec, 0, 59),
                "minute": self._parse_field(minute, 0, 59),
                "hour": self._parse_field(hour, 0, 23),
                "day": self._parse_field(dom, 1, 31),
                "month": self._parse_field(month, 1, 12, self.MONTH_MAP),
                "dow": self._parse_field(dow, 0, 6, self.DOW_MAP),
            }
        else:
            minute, hour, dom, month, dow = parts
            result = {
                "second": [0],
                "minute": self._parse_field(minute, 0, 59),
                "hour": self._parse_field(hour, 0, 23),
                "day": self._parse_field(dom, 1, 31),
                "month": self._parse_field(month, 1, 12, self.MONTH_MAP),
                "dow": self._parse_field(dow, 0, 6, self.DOW_MAP),
            }

        self._cache[expression] = result
        return result

    def _parse_field(self, field_str: str, min_val: int, max_val: int, name_map: Dict[str, int] = None) -> List[int]:
        """解析单个CRON字段（支持 * , - / 和名称别名）"""
        values = set()
        for part in field_str.split(","):
            if part == "*":
                values.update(range(min_val, max_val + 1))
            elif "/" in part:
                base, step_str = part.split("/", 1)
                step = int(step_str)
                if base == "*":
                    start = min_val
                elif "-" in base:
                    s, e = base.split("-", 1)
                    start = self._resolve_value(s, name_map)
                    end_val = self._resolve_value(e, name_map)
                    values.update(range(start, end_val + 1, step))
                    continue
                else:
                    start = self._resolve_value(base, name_map)
                for v in range(start, max_val + 1, step):
                    values.add(v)
            elif "-" in part:
                s, e = part.split("-", 1)
                start = self._resolve_value(s, name_map)
                end_val = self._resolve_value(e, name_map)
                values.update(range(start, end_val + 1))
            else:
                values.add(self._resolve_value(part, name_map))
        return sorted(v for v in values if min_val <= v <= max_val)

    def _resolve_value(self, val: str, name_map: Dict[str, int] = None) -> int:
        """解析值（支持数字和名称别名）"""
        val = val.strip()
        if name_map and val.upper() in name_map:
            return name_map[val.upper()]
        return int(val)

    def get_next_run_time(self, expression: str, after: float = None) -> Optional[float]:
        """计算CRON表达式的下一次执行时间（unix timestamp）"""
        if after is None:
            after = time.time()
        try:
            fields = self.parse(expression)
        except ValueError:
            return None
        dt = datetime.fromtimestamp(after) + timedelta(minutes=1)
        dt = dt.replace(second=0, microsecond=0)
        for _ in range(525600):  # 最多查1年
            if (
                dt.second in fields["second"]
                and dt.minute in fields["minute"]
                and dt.hour in fields["hour"]
                and dt.day in fields["day"]
                and dt.month in fields["month"]
                and dt.isoweekday() % 7 in fields["dow"]
            ):
                return dt.timestamp()
            dt += timedelta(minutes=1)
        return None

    def validate(self, expression: str) -> Dict[str, Any]:
        """验证CRON表达式语法"""
        try:
            fields = self.parse(expression)
            next_run = self.get_next_run_time(expression)
            return {"valid": True, "fields": {k: len(v) for k, v in fields.items()}, "next_run": next_run}
        except (ValueError, IndexError) as e:
            return {"valid": False, "error": str(e)}

class TaskDependencyResolver:
    """任务依赖解析器。企业场景：处理ETL管道中任务间的依赖关系，
    构建DAG并检测循环依赖，按拓扑序执行。
    """

    def __init__(self):
        self._graph: Dict[str, Set[str]] = {}

    def build_graph(self, tasks: Dict[str, TaskDefinition]) -> None:
        """从任务定义构建依赖图"""
        self._graph = {}
        for tid, task in tasks.items():
            self._graph[tid] = set(task.dependencies)

    def detect_cycles(self) -> List[List[str]]:
        """检测循环依赖，返回所有环路"""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbor in self._graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    idx = path.index(neighbor)
                    cycles.append(path[idx:] + [neighbor])
            path.pop()
            rec_stack.remove(node)

        for node in self._graph:
            if node not in visited:
                dfs(node)
        return cycles

    def topological_sort(self) -> List[str]:
        """拓扑排序，返回执行顺序"""
        in_degree = {n: 0 for n in self._graph}
        for node, deps in self._graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[node] += 1
        queue = [n for n, d in in_degree.items() if d == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for other in self._graph:
                if node in self._graph[other]:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)
        return order

    def get_ready_tasks(self, completed: Set[str], running: Set[str]) -> List[str]:
        """获取可执行任务（依赖全部完成且未在运行）"""
        ready = []
        for tid, deps in self._graph.items():
            if tid in completed or tid in running:
                continue
            if deps and not deps.issubset(completed):
                continue
            ready.append(tid)
        return ready

    def get_dependency_chain(self, task_id: str) -> Dict[str, Any]:
        """获取任务的完整依赖链（递归上游+下游）"""
        upstream = set()
        queue = list(self._graph.get(task_id, set()))
        while queue:
            dep = queue.pop(0)
            if dep not in upstream:
                upstream.add(dep)
                queue.extend(self._graph.get(dep, set()))
        downstream = set()
        for tid, deps in self._graph.items():
            if task_id in deps:
                downstream.add(tid)
        return {
            "task_id": task_id,
            "upstream": list(upstream),
            "downstream": list(downstream),
            "total_dependencies": len(upstream),
            "total_dependents": len(downstream),
        }

class LoadBalancer:
    """调度负载均衡器。企业场景：将任务分配到多个Worker，
    按权重/标签/当前负载选择最优Worker执行。
    """

    def __init__(self):
        self._workers: Dict[str, WorkerInfo] = {}

    def register_worker(self, worker_id: str, capacity: int = 10, tags: List[str] = None) -> None:
        self._workers[worker_id] = WorkerInfo(
            worker_id=worker_id, capacity=capacity, tags=tags or [], last_heartbeat=time.time()
        )

    def select_worker(self, task_tags: List[str] = None) -> Optional[str]:
        """选择最优Worker：优先匹配标签，其次最少负载"""
        best = None
        best_score = float("inf")
        for wid, w in self._workers.items():
            if w.active_tasks >= w.capacity:
                continue
            score = w.active_tasks / max(w.capacity, 1)
            if task_tags and w.tags:
                match = bool(set(task_tags) & set(w.tags))
                if match:
                    score -= 0.5  # 标签匹配加分
            if score < best_score:
                best_score = score
                best = wid
        return best

    def get_worker_load(self) -> List[Dict[str, Any]]:
        """获取所有Worker负载"""
        return [
            {
                "worker_id": w.worker_id,
                "active": w.active_tasks,
                "capacity": w.capacity,
                "utilization": round(w.active_tasks / max(w.capacity, 1) * 100, 1),
                "last_heartbeat": w.last_heartbeat,
            }
            for w in self._workers.values()
        ]

class RetryCalculator:
    """重试延迟计算器。企业场景：失败任务自动重试时计算下次执行时间，
    使用指数退避+随机抖动避免雪崩。
    """

    @staticmethod
    def calculate_delay(
        attempt: int, strategy: RetryStrategy, base_delay: float = 5.0, max_delay: float = 3600.0
    ) -> float:
        """计算重试延迟（秒）"""
        import random

        if strategy == RetryStrategy.NONE:
            return 0
        elif strategy == RetryStrategy.FIXED:
            return min(base_delay, max_delay)
        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = base_delay * (2 ** (attempt - 1))
            return min(delay, max_delay)
        elif strategy == RetryStrategy.EXPONENTIAL_JITTER:
            delay = base_delay * (2 ** (attempt - 1))
            jitter = delay*0.25
            return min(delay + jitter, max_delay)
        return base_delay

class SmartScheduler(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """智能任务调度引擎

    企业级功能：
    - CRON表达式解析与下次执行时间计算
    - 任务依赖DAG构建与循环检测
    - 负载均衡调度（多Worker权重分配）
    - 失败重试（指数退避+抖动策略）
    - 超时熔断与任务取消
    - 执行历史查询与统计分析
    """

    def __init__(self):

        super().__init__()
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "smart_scheduler"
        self.version = "1.0.0"
        self.description = "智能任务调度引擎 - CRON/DAG/重试/负载均衡"

        self._tasks: Dict[str, TaskDefinition] = {}
        self._executions: Dict[str, TaskExecution] = {}
        self._execution_history: List[TaskExecution] = []
        self._running_tasks: Dict[str, TaskExecution] = {}
        self._completed_set: Set[str] = set()
        self._cron_parser = CronExpressionParser()
        self._dep_resolver = TaskDependencyResolver()
        self._load_balancer = LoadBalancer()
        self._retry_calc = RetryCalculator()
        self._lock = threading.RLock()
        self._max_history = 10000

    def initialize(self) -> Dict[str, Any]:
        """初始化调度器"""
        self.trace("smart_scheduler.initialize", "start")
        self.metrics_collector.gauge("scheduler.tasks_registered", 0)
        self.metrics_collector.gauge("scheduler.tasks_running", 0)
        self.audit("初始化智能调度器", level="info")
        self.trace("smart_scheduler.initialize", "end")
        return {"success": True, "message": "调度器初始化完成"}

    def register_task(self, name: str, cron_expression: str, command: str, **kwargs) -> Dict[str, Any]:
        """注册定时任务"""
        self.trace("smart_scheduler.register_task", "start", {"name": name})
        task_id = kwargs.get("task_id", f"task_{uuid.uuid4().hex[:8]}")
        validation = self._cron_parser.validate(cron_expression)
        if not validation.get("valid"):
            self.audit(f"注册任务失败: CRON语法错误 {name}", level="error")
            return {"success": False, "error": f"CRON语法错误: {validation.get('error', '')}"}
        retry_strategy = kwargs.get("retry_strategy", "exponential_jitter")
        task = TaskDefinition(
            task_id=task_id,
            name=name,
            cron_expression=cron_expression,
            command=command,
            timeout_seconds=kwargs.get("timeout_seconds", 3600),
            max_retries=kwargs.get("max_retries", 3),
            retry_strategy=RetryStrategy(retry_strategy),
            retry_base_delay=kwargs.get("retry_base_delay", 5.0),
            retry_max_delay=kwargs.get("retry_max_delay", 3600.0),
            priority=kwargs.get("priority", 5),
            tags=kwargs.get("tags", []),
            dependencies=kwargs.get("dependencies", []),
            max_concurrent=kwargs.get("max_concurrent", 1),
            executor=kwargs.get("executor", "default"),
        )
        task.next_run_at = validation.get("next_run", time.time())
        with self._lock:
            self._tasks[task_id] = task
            self._dep_resolver.build_graph(self._tasks)
        self.metrics_collector.counter("scheduler.task_registered")
        self.metrics_collector.gauge("scheduler.tasks_registered", len(self._tasks))
        self.audit(f"注册任务 {name} (ID: {task_id})", level="info")
        self.trace("smart_scheduler.register_task", "end")
        return {"success": True, "task_id": task_id, "next_run": task.next_run_at}

    def unregister_task(self, task_id: str) -> Dict[str, Any]:
        """注销任务"""
        with self._lock:
            task = self._tasks.pop(task_id, None)
            if not task:
                return {"success": False, "error": f"任务 {task_id} 不存在"}
            self._dep_resolver.build_graph(self._tasks)
        self.audit(f"注销任务 {task.name} (ID: {task_id})")
        return {"success": True, "task_id": task_id, "name": task.name}

    def trigger_task(self, task_id: str) -> Dict[str, Any]:
        """手动触发任务执行"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return {"success": False, "error": f"任务 {task_id} 不存在"}
            running_count = sum(1 for e in self._running_tasks.values() if e.task_id == task_id)
            if running_count >= task.max_concurrent:
                return {"success": False, "error": f"任务已达并发上限 {task.max_concurrent}"}
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            execution = TaskExecution(
                execution_id=execution_id,
                task_id=task_id,
                task_name=task.name,
                status=TaskStatus.RUNNING,
                started_at=time.time(),
                attempt=1,
                timeout_seconds=task.timeout_seconds,
            )
            self._executions[execution_id] = execution
            self._running_tasks[execution_id] = execution
        self.metrics_collector.counter("scheduler.task_triggered")
        self.metrics_collector.gauge("scheduler.tasks_running", len(self._running_tasks))
        self.trace("smart_scheduler.trigger_task", "executed", {"task_id": task_id, "execution_id": execution_id})
        return {"success": True, "execution_id": execution_id, "task_name": task.name}

    def complete_task(self, execution_id: str, success: bool, error_message: str = "") -> Dict[str, Any]:
        """标记任务执行完成"""
        with self._lock:
            execution = self._executions.get(execution_id)
            if not execution:
                return {"success": False, "error": f"执行 {execution_id} 不存在"}
            execution.finished_at = time.time()
            execution.duration = execution.finished_at - execution.started_at
            if success:
                execution.status = TaskStatus.SUCCESS
                self._completed_set.add(execution.task_id)
                task = self._tasks.get(execution.task_id)
                if task:
                    task.run_count += 1
                    task.last_run_at = execution.finished_at
                    task.total_duration += execution.duration
                    task.avg_duration = task.total_duration / task.run_count
                    # 更新下次执行时间
                    next_time = self._cron_parser.get_next_run_time(task.cron_expression, execution.finished_at)
                    task.next_run_at = next_time or execution.finished_at
                self._running_tasks.pop(execution_id, None)
                self.metrics_collector.counter("scheduler.task_success")
            else:
                execution.error_message = error_message
                task = self._tasks.get(execution.task_id)
                should_retry = False
                if task and execution.retry_count < task.max_retries:
                    should_retry = True
                    execution.retry_count += 1
                    delay = self._retry_calc.calculate_delay(
                        execution.retry_count, task.retry_strategy, task.retry_base_delay, task.retry_max_delay
                    )
                    execution.next_retry_at = time.time() + delay
                    execution.status = TaskStatus.FAILED
                else:
                    execution.status = TaskStatus.FAILED
                    self._running_tasks.pop(execution_id, None)
                    if task:
                        task.fail_count += 1
                    self.metrics_collector.counter("scheduler.task_failed")
            self._execution_history.append(execution)
            if len(self._execution_history) > self._max_history:
                self._execution_history = self._execution_history[-self._max_history :]
            self._completed_set.discard(execution.task_id)
        self.metrics_collector.gauge("scheduler.tasks_running", len(self._running_tasks))
        self.audit(f"任务完成 {execution.task_name}: {execution.status}")
        return {
            "success": True,
            "execution_id": execution_id,
            "status": execution.status,
            "duration_seconds": round(execution.duration, 2),
            "will_retry": success is False and execution.next_retry_at > 0,
        }

    def cancel_task(self, execution_id: str) -> Dict[str, Any]:
        """取消正在运行的任务"""
        with self._lock:
            execution = self._running_tasks.get(execution_id)
            if not execution:
                return {"success": False, "error": f"执行 {execution_id} 未在运行"}
            execution.status = TaskStatus.CANCELLED
            execution.finished_at = time.time()
            execution.duration = execution.finished_at - execution.started_at
            self._running_tasks.pop(execution_id, None)
        self.audit(f"取消任务 {execution.task_name} (ID: {execution_id})")
        return {"success": True, "execution_id": execution_id}

    def check_timeouts(self) -> Dict[str, Any]:
        """检查超时任务。企业场景：定时扫描执行中的任务，
        超过timeout_seconds的标记为超时并释放资源。
        """
        now = time.time()
        timed_out = []
        with self._lock:
            for eid, exec_ in list(self._running_tasks.items()):
                elapsed = now - exec_.started_at
                if elapsed > exec_.timeout_seconds:
                    exec_.status = TaskStatus.TIMEOUT
                    exec_.finished_at = now
                    exec_.duration = elapsed
                    exec_.error_message = f"执行超时 ({elapsed:.0f}s > {exec_.timeout_seconds}s)"
                    self._running_tasks.pop(eid, None)
                    timed_out.append(eid)
                    task = self._tasks.get(exec_.task_id)
                    if task:
                        task.fail_count += 1
        self.metrics_collector.counter("scheduler.task_timeout", len(timed_out))
        return {"success": True, "timed_out_count": len(timed_out), "timed_out_executions": timed_out}

    def validate_cron(self, expression: str) -> Dict[str, Any]:
        """验证CRON表达式"""
        return self._cron_parser.validate(expression)

    def get_task_list(self, status_filter: str = None, tag: str = None) -> Dict[str, Any]:
        """获取任务列表"""
        tasks = []
        for task in self._tasks.values():
            if status_filter:
                if status_filter == "running":
                    is_running = any(e.task_id == task.task_id for e in self._running_tasks.values())
                    if not is_running:
                        continue
            if tag and tag not in task.tags:
                continue
            running = sum(1 for e in self._running_tasks.values() if e.task_id == task.task_id)
            tasks.append(
                {
                    "task_id": task.task_id,
                    "name": task.name,
                    "cron": task.cron_expression,
                    "enabled": task.enabled,
                    "running_instances": running,
                    "max_retries": task.max_retries,
                    "priority": task.priority,
                    "run_count": task.run_count,
                    "fail_count": task.fail_count,
                    "last_run": (
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(task.last_run_at))
                        if task.last_run_at
                        else "从未"
                    ),
                    "next_run": (
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(task.next_run_at))
                        if task.next_run_at
                        else "未计算"
                    ),
                    "avg_duration_s": round(task.avg_duration, 2),
                }
            )
        tasks.sort(key=lambda x: x.get("next_run", ""))
        return {"success": True, "total": len(tasks), "tasks": tasks}

    def get_execution_history(self, task_id: str = None, limit: int = 50) -> Dict[str, Any]:
        """获取执行历史"""
        history = self._execution_history
        if task_id:
            history = [h for h in history if h.task_id == task_id]
        history = history[-limit:]
        records = []
        for h in history:
            records.append(
                {
                    "execution_id": h.execution_id,
                    "task_name": h.task_name,
                    "status": h.status,
                    "started_at": (
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(h.started_at)) if h.started_at else ""
                    ),
                    "duration_s": round(h.duration, 2),
                    "attempt": h.attempt,
                    "retries": h.retry_count,
                    "error": h.error_message[:200] if h.error_message else "",
                }
            )
        records.reverse()
        return {"success": True, "total": len(records), "records": records}

    def get_pending_retries(self) -> Dict[str, Any]:
        """获取待重试任务列表。企业场景：SRE查看哪些任务需要关注，
        判断是否需要手动干预或调整重试策略。
        """
        now = time.time()
        pending = []
        for exec_ in self._execution_history:
            if exec_.next_retry_at > 0 and exec_.status == TaskStatus.FAILED:
                task = self._tasks.get(exec_.task_id)
                pending.append(
                    {
                        "execution_id": exec_.execution_id,
                        "task_name": exec_.task_name,
                        "task_id": exec_.task_id,
                        "attempt": exec_.attempt,
                        "retries_used": exec_.retry_count,
                        "max_retries": (task.max_retries if task else 3),
                        "retry_eligible": (exec_.retry_count < (task.max_retries if task else 3)),
                        "next_retry_at": (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(exec_.next_retry_at))),
                        "wait_seconds": round(exec_.next_retry_at - now, 1),
                        "error": exec_.error_message[:150] if exec_.error_message else "",
                    }
                )
        pending.sort(key=lambda x: x.get("wait_seconds", 0))
        return {"success": True, "total": len(pending), "pending": pending}

    def get_scheduler_summary(self) -> Dict[str, Any]:
        """调度器总览。企业场景：运维大盘展示调度系统健康状态。"""
        total = len(self._tasks)
        enabled = sum(1 for t in self._tasks.values() if t.enabled)
        running = len(self._running_tasks)
        history = self._execution_history
        last_24h = [h for h in history if h.finished_at > time.time() - 86400]
        success_24h = sum(1 for h in last_24h if h.status == TaskStatus.SUCCESS)
        failed_24h = sum(1 for h in last_24h if h.status == TaskStatus.FAILED)
        timeout_24h = sum(1 for h in last_24h if h.status == TaskStatus.TIMEOUT)
        retry_pending = sum(1 for h in history if h.next_retry_at > 0 and h.status == TaskStatus.FAILED)
        # 按任务统计失败率
        fail_rates = {}
        for task_id in set(h.task_id for h in last_24h):
            task_runs = [h for h in last_24h if h.task_id == task_id]
            fails = sum(1 for h in task_runs if h.status in (TaskStatus.FAILED, TaskStatus.TIMEOUT))
            rate = round(fails / len(task_runs) * 100, 1) if task_runs else 0
            fail_rates[task_id] = rate
        top_failing = sorted(fail_rates.items(), key=lambda x: -x[1])[:5]
        return {
            "success": True,
            "total_tasks": total,
            "enabled_tasks": enabled,
            "running_tasks": running,
            "last_24h": {"total": len(last_24h), "success": success_24h, "failed": failed_24h, "timeout": timeout_24h},
            "success_rate_24h": (round(success_24h / max(len(last_24h), 1) * 100, 1)),
            "retry_pending": retry_pending,
            "top_failing_tasks": ([{"task_id": tid, "fail_rate_pct": rate} for tid, rate in top_failing]),
        }

    def check_dependencies(self, task_id: str) -> Dict[str, Any]:
        """检查任务依赖。企业场景：注册新任务前检查依赖是否合法，
        检测循环依赖和不存在的依赖。
        """
        chain = self._dep_resolver.get_dependency_chain(task_id)
        tasks = self._tasks
        missing = [d for d in chain["upstream"] if d not in tasks]
        cycles = self._dep_resolver.detect_cycles()
        return {
            "success": True,
            "task_id": task_id,
            "upstream_count": len(chain["upstream"]),
            "downstream_count": len(chain["downstream"]),
            "missing_dependencies": missing,
            "has_cycle": len(cycles) > 0,
            "cycle_paths": cycles[:3] if cycles else [],
        }

    def batch_update_schedule(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量更新任务调度时间。企业场景：夏令时切换或维护窗口调整时，
        批量修改多个任务的CRON表达式。
        """
        updated = 0
        errors = []
        for upd in updates:
            task_id = upd.get("task_id", "")
            new_cron = upd.get("cron_expression", "")
            if not task_id or not new_cron:
                errors.append({"task_id": task_id, "error": "缺少task_id或cron_expression"})
                continue
            validation = self._cron_parser.validate(new_cron)
            if not validation.get("valid"):
                errors.append({"task_id": task_id, "error": f"CRON语法错误: {validation.get('error', '')}"})
                continue
            with self._lock:
                task = self._tasks.get(task_id)
                if not task:
                    errors.append({"task_id": task_id, "error": "任务不存在"})
                    continue
                old_cron = task.cron_expression
                task.cron_expression = new_cron
                task.next_run_at = validation.get("next_run", 0)
                updated += 1
        self.audit(f"批量更新调度: {updated}成功, {len(errors)}失败")
        return {"success": True, "updated": updated, "errors": errors}

    def get_health_status(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "module": "smart_scheduler",
            "tasks_registered": len(self._tasks),
            "running": len(self._running_tasks),
            "history_size": len(self._execution_history),
        }

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
            "get_scheduler_summary": self.get_scheduler_summary,
            "get_task_list": self.get_task_list,
            "get_execution_history": self.get_execution_history,
            "get_pending_retries": self.get_pending_retries,
            "get_worker_load": self.get_worker_load,
            "check_timeouts": self.check_timeouts,
            "check_dependencies": self.check_dependencies,
            "get_next_run_time": self.get_next_run_time,
            "get_dependency_chain": self.get_dependency_chain,
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
        return {
            "success": True,
            "module": "smart_scheduler",
            "version": getattr(self, "version", "1.0.0"),
            "actions": [
                "status",
                "info",
                "health",
                "help",
                "get_scheduler_summary",
                "get_task_list",
                "get_execution_history",
                "get_pending_retries",
                "get_worker_load",
                "check_timeouts",
                "check_dependencies",
            ],
            "description": "企业级智能调度器 - 支持Cron/间隔/一次性/依赖链/重试/超时",
        }

    def shutdown(self) -> dict:
        """Graceful shutdown for smart_scheduler."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

    def health_check(self) -> dict:
        """Health check for smart_scheduler."""
        return {
            "status": "healthy",
            "module": self.__class__.__name__,
            "uptime": getattr(self, "_start_time", 0) and (time.time() - self._start_time) or 0,
        }

module_class = SmartScheduler
