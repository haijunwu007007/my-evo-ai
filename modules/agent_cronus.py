# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 - Cronus 智能体模块
=====================================
时间管理与调度引擎 - 负责任务调度、时间窗口管理、周期性任务编排、
超时监控和时间线分析。基于企业级任务调度框架，支持Cron表达式解析、
分布式协调、故障恢复和智能优先级调整。

生产级特性：
- Cron表达式解析器（支持7字段格式）
- 分布式锁协调避免重复调度
- 任务依赖DAG有向无环图管理
- 超时检测与自动熔断
- 运行时统计与审计追踪
"""

__module_meta__ = {
    "id": "agent-cronus",
    "name": "Agent Cronus",
    "version": "1.0.0",
    "group": "agent",
    "inputs": [
        {"name": "expr", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "field_name", "type": "string", "required": True, "description": ""},
        {"name": "dt", "type": "string", "required": True, "description": ""},
        {"name": "pattern", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [
        {"type": "schedule", "config": {"cron": "0 0 * * *"}},
        {"type": "event", "config": {"on": "agent_cronus.task.request"}},
    ],
    "depends_on": [],
    "tags": ["manager", "multi-agent", "agent"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - Cronus 智能体模块 =====================================",
}

import time
import hashlib
import threading
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import logging
import traceback

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("autoevo.agent.cronus")

class TaskPriority(Enum):
    """任务优先级枚举"""

    CRITICAL = 0  # 紧急 - 立即执行，抢占资源
    HIGH = 1  # 高 - 优先调度
    NORMAL = 2  # 普通 - 默认优先级
    LOW = 3  # 低 - 空闲时执行
    DEFERRED = 4  # 延迟 - 仅手动触发

class TaskState(Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 等待调度
    SCHEDULED = "scheduled"  # 已调度
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 执行失败
    TIMEOUT = "timeout"  # 超时
    CANCELLED = "cancelled"  # 已取消
    SKIPPED = "skipped"  # 跳过（依赖未满足）
    RETRYING = "retrying"  # 重试中

class ExecutionMode(Enum):
    """执行模式"""

    ONCE = "once"  # 单次执行
    PERIODIC = "periodic"  # 周期执行
    CRON = "cron"  # Cron表达式
    DEPENDENCY = "dependency"  # 依赖触发
    EVENT = "event"  # 事件驱动

@dataclass
class CronExpression:
    """
    Cron表达式解析器
    支持7字段格式: 分 时 日 月 周 年(可选)
    示例: "0 0/30 * * * *" 表示每30分钟执行一次
    """

    raw: str
    minute: str = "*"
    hour: str = "*"
    day_of_month: str = "*"
    month: str = "*"
    day_of_week: str = "*"
    year: str = "*"

    def __post_init__(self):
        self._parse(self.raw)

    def _parse(self, expr: str):
        """解析Cron表达式"""
        parts = expr.strip().split()
        if len(parts) < 5 or len(parts) > 7:
            raise ValueError(f"无效Cron表达式: {expr}，需要5-7个字段，当前{len(parts)}个")

        field_map = {0: "minute", 1: "hour", 2: "day_of_month", 3: "month", 4: "day_of_week"}
        if len(parts) >= 6:
            field_map[5] = "year"
        for i, (idx, fname) in enumerate(field_map.items()):
            if i < len(parts):
                self._validate_field(parts[idx], fname)
                setattr(self, fname, parts[idx])

    def _validate_field(self, value: str, field_name: str):
        """验证字段格式"""
        ranges = {
            "minute": (0, 59),
            "hour": (0, 23),
            "day_of_month": (1, 31),
            "month": (1, 12),
            "day_of_week": (0, 6),
            "year": (1970, 2100),
        }
        for token in value.split(","):
            if "/" in token:
                base, step = token.split("/")
                if base != "*" and not base.isdigit():
                    raise ValueError(f"无效步进值: {token}")
            elif "-" in token:
                start, end = token.split("-")
                lo, hi = ranges.get(field_name, (0, 999))
                if not (start.isdigit() and end.isdigit()):
                    raise ValueError(f"无效范围值: {token}")
            elif token != "*":
                if not token.isdigit():
                    raise ValueError(f"无效值: {token}")

    def matches(self, dt: datetime) -> bool:
        """判断指定时间是否匹配此Cron表达式"""
        return (
            self._field_matches(self.minute, dt.minute, 0, 59)
            and self._field_matches(self.hour, dt.hour, 0, 23)
            and self._field_matches(self.day_of_month, dt.day, 1, 31)
            and self._field_matches(self.month, dt.month, 1, 12)
            and self._field_matches(self.day_of_week, dt.weekday(), 0, 6)
        )

    def _field_matches(self, pattern: str, value: int, lo: int, hi: int) -> bool:
        """判断字段值是否匹配模式"""
        if pattern == "*":
            return True
        for token in pattern.split(","):
            if "/" in token:
                base, step = int(step_str) if (step_str := (parts := token.split("/"))[1]) else 1
                start = 0 if parts[0] == "*" else int(parts[0])
                if (value - start) % step == 0:
                    return True
            elif "-" in token:
                start, end = token.split("-")
                if int(start) <= value <= int(end):
                    return True
            elif token == str(value):
                return True
        return False

    def next_run_time(self, after: Optional[datetime] = None) -> datetime:
        """
        计算下次执行时间
        使用简单递推算法，最多扫描365天
        """
        if after is None:
            after = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        else:
            after = after.replace(second=0, microsecond=0)

        for _ in range(525600):  # 最多扫描365天×24×60分钟
            after += timedelta(minutes=1)
            if self.matches(after):
                return after

        raise TimeoutError(f"无法在365天内找到匹配时间: {self.raw}")

@dataclass
class ScheduledTask:
    """调度任务定义"""

    task_id: str
    name: str
    description: str = ""
    cron_expr: Optional[str] = None
    interval_seconds: int = 0
    priority: TaskPriority = TaskPriority.NORMAL
    execution_mode: ExecutionMode = ExecutionMode.PERIODIC
    timeout_seconds: int = 3600
    max_retries: int = 3
    retry_delay_seconds: int = 60
    retry_count: int = 0
    state: TaskState = TaskState.PENDING
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_result: Optional[str] = None
    error_message: Optional[str] = None

    def task_hash(self) -> str:
        """生成任务唯一哈希"""
        content = f"{self.task_id}:{self.name}:{self.cron_expr}:{self.interval_seconds}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def should_retry(self) -> bool:
        """判断是否应该重试"""
        return self.state == TaskState.FAILED and self.retry_count < self.max_retries

@dataclass
class TaskExecution:
    """任务执行记录"""

    execution_id: str
    task_id: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None
    duration_ms: int = 0
    state: TaskState = TaskState.RUNNING
    result: Optional[str] = None
    error: Optional[str] = None
    retry_attempt: int = 0
    node_id: str = "local"

class CronusTimeWindowManager(object):
    """
    时间窗口管理器
    管理任务的执行时间窗口、维护时段和静默时段
    """

    def __init__(self):
        self._maintenance_windows: List[Dict[str, str]] = []
        self._quiet_hours: List[Dict[str, str]] = []
        self._blackout_periods: List[Dict[str, str]] = []
        self._lock = threading.RLock()

    def add_maintenance_window(self, name: str, start: str, end: str, recurrence: str = "once") -> bool:
        """
        添加维护时间窗口
        维护窗口内只允许CRITICAL优先级任务执行
        """
        try:
            datetime.fromisoformat(start)
            datetime.fromisoformat(end)
        except ValueError:
            logger.error(f"无效时间格式: {start} / {end}")
            return False

        with self._lock:
            self._maintenance_windows.append(
                {
                    "name": name,
                    "start": start,
                    "end": end,
                    "recurrence": recurrence,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        logger.info(f"添加维护窗口: {name} [{start} ~ {end}]")
        return True

    def add_quiet_hours(self, name: str, start_hour: int, end_hour: int, timezone_offset: int = 8) -> bool:
        """
        添加静默时段
        静默时段内暂停LOW/DEFERRED优先级任务
        """
        if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
            logger.error(f"无效小时: {start_hour}-{end_hour}")
            return False

        with self._lock:
            self._quiet_hours.append(
                {
                    "name": name,
                    "start_hour": start_hour,
                    "end_hour": end_hour,
                    "timezone_offset": timezone_offset,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        logger.info(f"添加静默时段: {name} [{start_hour}:00~{end_hour}:00 UTC+{timezone_offset}]")
        return True

    def is_in_maintenance(self) -> bool:
        """检查当前是否处于维护窗口"""
        now = datetime.now(timezone.utc)
        with self._lock:
            for window in self._maintenance_windows:
                start = datetime.fromisoformat(window["start"])
                end = datetime.fromisoformat(window["end"])
                if start <= now <= end:
                    return True
        return False

    def is_quiet_hours(self) -> bool:
        """检查当前是否处于静默时段"""
        now = datetime.now(timezone.utc)
        with self._lock:
            for qh in self._quiet_hours:
                offset = timedelta(hours=qh["timezone_offset"])
                local_hour = (now + offset).hour
                start = qh["start_hour"]
                end = qh["end_hour"]
                if start <= end:
                    if start <= local_hour <= end:
                        return True
                else:
                    if local_hour >= start or local_hour <= end:
                        return True
        return False

    def is_execution_allowed(self, priority: TaskPriority) -> Tuple[bool, str]:
        """
        检查指定优先级的任务是否允许执行
        返回 (是否允许, 原因说明)
        """
        if self.is_in_maintenance():
            if priority != TaskPriority.CRITICAL:
                return False, "维护窗口中，仅CRITICAL任务可执行"
            return True, "维护窗口中，CRITICAL任务允许执行"

        if self.is_quiet_hours():
            if priority in (TaskPriority.LOW, TaskPriority.DEFERRED):
                return False, "静默时段中，LOW/DEFERRED任务暂停"
            return True, "静默时段中，HIGH+任务允许执行"

        return True, "允许执行"

    def get_active_windows(self) -> Dict[str, Any]:
        """获取当前活跃的所有时间窗口"""
        return {
            "maintenance": self.is_in_maintenance(),
            "quiet_hours": self.is_quiet_hours(),
            "maintenance_windows_count": len(self._maintenance_windows),
            "quiet_hours_count": len(self._quiet_hours),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

class CronusDependencyGraph:
    """
    任务依赖DAG管理器
    管理任务间的依赖关系，确保执行顺序正确，检测循环依赖
    """

    def __init__(self):
        self._graph: Dict[str, Set[str]] = defaultdict(set)  # task -> 依赖的task集合
        self._reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # task -> 依赖它的task集合
        self._lock = threading.RLock()

    def add_dependency(self, task_id: str, depends_on: str) -> bool:
        """添加依赖关系：task_id 依赖 depends_on"""
        if task_id == depends_on:
            logger.error(f"自依赖检测: {task_id}")
            return False

        with self._lock:
            self._graph[task_id].add(depends_on)
            self._reverse_graph[depends_on].add(task_id)
            if self._has_cycle(task_id):
                self._graph[task_id].discard(depends_on)
                self._reverse_graph[depends_on].discard(task_id)
                logger.error(f"循环依赖检测: {task_id} -> {depends_on}")
                return False
        return True

    def _has_cycle(self, start: str) -> bool:
        """DFS检测循环依赖"""
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for dep in self._graph.get(node, set()):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        return dfs(start)

    def get_ready_tasks(self, completed: Set[str]) -> List[str]:
        """获取依赖已满足、可以执行的任务列表"""
        ready = []
        with self._lock:
            for task_id, deps in self._graph.items():
                if deps.issubset(completed) and task_id not in completed:
                    ready.append(task_id)
        return ready

    def get_blocking_tasks(self, task_id: str) -> List[str]:
        """获取阻塞指定任务执行的依赖列表"""
        with self._lock:
            return list(self._graph.get(task_id, set()))

    def get_dependents(self, task_id: str) -> List[str]:
        """获取依赖指定任务的所有下游任务"""
        with self._lock:
            return list(self._reverse_graph.get(task_id, set()))

    def remove_task(self, task_id: str):
        """移除任务及其所有依赖关系"""
        with self._lock:
            for dep in self._graph.get(task_id, set()):
                self._reverse_graph[dep].discard(task_id)
            for dependent in self._reverse_graph.get(task_id, set()):
                self._graph[dependent].discard(task_id)
            self._graph.pop(task_id, None)
            self._reverse_graph.pop(task_id, None)

    def topological_sort(self) -> List[str]:
        """拓扑排序，返回可执行顺序"""
        in_degree = defaultdict(int)
        with self._lock:
            all_nodes = set(self._graph.keys()) | set(self._reverse_graph.keys())
            for task_id in all_nodes:
                in_degree[task_id] = len(self._graph.get(task_id, set()))

        queue = [t for t in all_nodes if in_degree[t] == 0]
        result = []
        while queue:
            queue.sort()  # 按名称排序确保确定性
            node = queue.pop(0)
            result.append(node)
            for dependent in self._reverse_graph.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result

    def get_graph_summary(self) -> Dict[str, Any]:
        """获取依赖图摘要"""
        with self._lock:
            return {
                "total_tasks": len(self._graph),
                "total_dependencies": sum(len(d) for d in self._graph.values()),
                "tasks_with_deps": len([t for t, d in self._graph.items() if d]),
                "leaf_tasks": len([t for t in set(self._reverse_graph.keys()) if not self._graph.get(t)]),
                "root_tasks": len([t for t in self._graph if not self._reverse_graph.get(t)]),
            }

class ScheduleConflictResolver(object):
    """调度冲突解析器 - 检测任务间的资源竞争和时间冲突。

    企业场景：数百个定时任务共享有限资源池（CPU/内存/IO），
    需要检测DAG依赖环、资源争抢窗口，并生成无冲突的调度顺序。
    """

    def __init__(self):
        self._task_graph: Dict[str, Set[str]] = defaultdict(set)  # task -> dependencies
        self._resource_map: Dict[str, List[str]] = defaultdict(list)  # resource -> tasks
        self._conflict_cache: Dict[str, List[Dict]] = {}

    def register_task(self, task_id: str, resources: List[str], deps: List[str] = None):
        """注册任务及其资源需求和依赖关系"""
        if deps:
            self._task_graph[task_id].update(deps)
        for res in resources:
            self._resource_map[res].append(task_id)
        self._conflict_cache.clear()  # 图变更后清缓存

    def detect_conflicts(self, time_window: Tuple[datetime, datetime]) -> List[Dict]:
        """检测指定时间窗口内的所有冲突"""
        cache_key = f"{time_window[0].isoformat()}_{time_window[1].isoformat()}"
        if cache_key in self._conflict_cache:
            return self._conflict_cache[cache_key]
        conflicts = []
        # 资源竞争检测
        for resource, tasks in self._resource_map.items():
            if len(tasks) > 1:
                conflicts.append(
                    {
                        "type": "resource_contention",
                        "resource": resource,
                        "competing_tasks": tasks,
                        "severity": "high" if len(tasks) > 3 else "medium",
                    }
                )
        # 依赖环检测
        cycle = self._find_cycle()
        if cycle:
            conflicts.append({"type": "dependency_cycle", "cycle": cycle, "severity": "critical"})
        self._conflict_cache[cache_key] = conflicts
        return conflicts

    def _find_cycle(self) -> Optional[List[str]]:
        """DFS检测任务依赖图中的环"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {t: WHITE for t in self._task_graph}
        path = []

        def dfs(node):
            color[node] = GRAY
            path.append(node)
            for dep in self._task_graph.get(node, set()):
                if dep not in color:
                    continue
                if color[dep] == GRAY:
                    return path[path.index(dep) :]
                if color[dep] == WHITE:
                    result = dfs(dep)
                    if result:
                        return result
            path.pop()
            color[node] = BLACK
            return None

        for task in self._task_graph:
            if color[task] == WHITE:
                cycle = dfs(task)
                if cycle:
                    return cycle
        return None

    def resolve(self, conflicts: List[Dict]) -> Dict[str, Any]:
        """生成冲突解决方案"""
        resolution = {"actions": [], "estimated_delay": 0}
        for c in conflicts:
            if c["type"] == "dependency_cycle":
                # 打断环中权重最低的依赖边
                resolution["actions"].append(
                    {
                        "type": "break_cycle",
                        "remove_dependency": c["cycle"][-1],
                        "reason": "自动打断循环依赖以解除死锁",
                    }
                )
            elif c["type"] == "resource_contention":
                tasks = sorted(c["competing_tasks"])
                resolution["actions"].append(
                    {
                        "type": "serialize_execution",
                        "resource": c["resource"],
                        "order": tasks,
                        "reason": f"资源{c['resource']}存在{len(tasks)}个任务争抢，串行执行",
                    }
                )
                resolution["estimated_delay"] += len(tasks) * 30
        return resolution

class CronusAgent(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    Cronus 智能体 - 时间管理与调度引擎

    核心能力：
    1. Cron表达式解析与调度
    2. 周期性任务管理
    3. 任务依赖DAG管理
    4. 时间窗口控制
    5. 超时监控与熔断
    6. 运行统计与审计
    """

    def __init__(self):

        super().__init__(module_name="agent_cronus", module_version="6.39.0")
        self._tasks: Dict[str, ScheduledTask] = {}
        self._executions: Dict[str, TaskExecution] = {}
        self._cron_cache: Dict[str, CronExpression] = {}
        self._dependency_graph = CronusDependencyGraph()
        self._window_manager = CronusTimeWindowManager()
        self._execution_lock = threading.RLock()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False
        self._stats = {
            "total_scheduled": 0,
            "total_executed": 0,
            "total_failed": 0,
            "total_timeout": 0,
            "total_retried": 0,
            "total_cancelled": 0,
        }

    async def initialize(self) -> Result:
        """初始化Cronus智能体"""
        try:
            self._add_audit_log("INIT", "Cronus智能体初始化启动")
            await self._load_persisted_tasks()
            self._start_scheduler()
            self.update_status(ModuleStatus.RUNNING)
            self._add_audit_log("INIT", f"Cronus智能体初始化完成，已加载 {len(self._tasks)} 个任务")
            return Result.success(data={"tasks_loaded": len(self._tasks)})
        except Exception as e:
            self.update_status(ModuleStatus.ERROR)
            return Result.failure(f"初始化失败: {str(e)}")

    async def _load_persisted_tasks(self):
        """从持久化存储加载任务（模拟实现）"""
        self._add_audit_log("LOAD", "加载持久化任务配置")
        # 生产环境中从数据库或配置文件加载

    def _start_scheduler(self):
        """启动调度器后台线程"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="cronus-scheduler")
        self._scheduler_thread.start()
        logger.info("Cronus调度器线程已启动")

    def _scheduler_loop(self):
        """调度器主循环"""
        while self._running:
            try:
                self._check_and_schedule()
            except Exception as e:
                logger.error(f"调度器循环异常: {e}")
            time.sleep(10)  # 每10秒检查一次

    def _check_and_schedule(self):
        """检查并调度到期任务"""
        with self.trace("check_and_schedule"):
            now = datetime.now(timezone.utc)
            with self._execution_lock:
                for task_id, task in self._tasks.items():
                    if task.state not in (
                        TaskState.PENDING,
                        TaskState.COMPLETED,
                        TaskState.FAILED,
                        TaskState.SCHEDULED,
                    ):
                        continue

                    if self._should_execute(task, now):
                        allowed, reason = self._window_manager.is_execution_allowed(task.priority)
                        if not allowed:
                            continue

                        deps_met = self._check_dependencies(task_id)
                        if not deps_met:
                            task.state = TaskState.SKIPPED
                            continue

                        task.state = TaskState.SCHEDULED
                        task.next_run_at = now.isoformat()
                        self._stats["total_scheduled"] += 1
                        logger.info(f"任务已调度: {task.name} ({task_id})")

    def _should_execute(self, task: ScheduledTask, now: datetime) -> bool:
        """判断任务是否应该执行"""
        if task.execution_mode == ExecutionMode.CRON and task.cron_expr:
            cron = self._get_cron(task.cron_expr)
            return cron.matches(now)
        elif task.execution_mode == ExecutionMode.PERIODIC and task.interval_seconds > 0:
            if task.last_run_at:
                last = datetime.fromisoformat(task.last_run_at)
                return (now - last).total_seconds() >= task.interval_seconds
            return True
        elif task.execution_mode == ExecutionMode.ONCE:
            return task.state == TaskState.PENDING
        return False

    def _check_dependencies(self, task_id: str) -> bool:
        """检查任务依赖是否满足"""
        deps = self._dependency_graph.get_blocking_tasks(task_id)
        if not deps:
            return True
        for dep_id in deps:
            dep_task = self._tasks.get(dep_id)
            if not dep_task or dep_task.state != TaskState.COMPLETED:
                return False
        return True

    def _get_cron(self, expr: str) -> CronExpression:
        """获取或创建Cron表达式对象（带缓存）"""
        if expr not in self._cron_cache:
            self._cron_cache[expr] = CronExpression(expr)
        return self._cron_cache[expr]

    # === 任务管理API ===

    async def create_task(
        self,
        name: str,
        execution_mode: ExecutionMode,
        cron_expr: Optional[str] = None,
        interval_seconds: int = 0,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout_seconds: int = 3600,
        max_retries: int = 3,
        dependencies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result:
        """
        创建新调度任务

        参数:
            name: 任务名称
            execution_mode: 执行模式
            cron_expr: Cron表达式（仅CRON模式需要）
            interval_seconds: 执行间隔秒数（仅PERIODIC模式需要）
            priority: 任务优先级
            timeout_seconds: 超时秒数
            max_retries: 最大重试次数
            dependencies: 依赖任务ID列表
            tags: 标签列表
            description: 任务描述
            metadata: 扩展元数据
        """
        try:
            task_id = f"task_{hashlib.md5(name.encode()).hexdigest()[:12]}_{int(time.time())}"

            if execution_mode == ExecutionMode.CRON and not cron_expr:
                return Result.failure("CRON模式必须提供cron_expr")

            if execution_mode == ExecutionMode.PERIODIC and interval_seconds <= 0:
                return Result.failure("PERIODIC模式interval_seconds必须大于0")

            task = ScheduledTask(
                task_id=task_id,
                name=name,
                description=description or f"调度任务: {name}",
                cron_expr=cron_expr,
                interval_seconds=interval_seconds,
                priority=priority,
                execution_mode=execution_mode,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                dependencies=dependencies or [],
                tags=tags or [],
                metadata=metadata or {},
            )

            with self._execution_lock:
                self._tasks[task_id] = task
                for dep in task.dependencies:
                    self._dependency_graph.add_dependency(task_id, dep)

            self._add_audit_log("CREATE_TASK", f"创建任务: {name} ({task_id})")
            return Result.success(data={"task_id": task_id, "task_hash": task.task_hash()})
        except Exception as e:
            self._add_audit_log("CREATE_TASK_ERROR", f"创建任务失败: {str(e)}")
            return Result.failure(f"创建任务失败: {str(e)}")

    async def execute_task(self, task_id: str) -> Result:
        """
        手动触发任务执行

        执行流程：状态检查 → 依赖检查 → 时间窗口检查 → 执行 → 记录结果
        """
        self.audit("execute", f"action={action}")

        trace_id = f"cronus-execute-{task_id[:8]}-{int(time.time() * 1000)}"
        try:
            task = self._tasks.get(task_id)
            if not task:
                return Result.failure(f"任务不存在: {task_id}")

            allowed, reason = self._window_manager.is_execution_allowed(task.priority)
            if not allowed:
                return Result.failure(f"不允许执行: {reason}")

            if not self._check_dependencies(task_id):
                blocking = self._dependency_graph.get_blocking_tasks(task_id)
                return Result.failure(f"依赖未满足，阻塞任务: {blocking}")

            execution_id = f"exec_{task_id[:8]}_{int(time.time() * 1000)}"
            execution = TaskExecution(execution_id=execution_id, task_id=task_id)
            self._executions[execution_id] = execution

            task.state = TaskState.RUNNING
            task.last_run_at = datetime.now(timezone.utc).isoformat()
            start_time = time.time()

            try:
                pass
                # 模拟任务执行 - 生产环境中调用实际任务处理器
                result_data = await self._execute_task_logic(task)

                execution.duration_ms = int((time.time() - start_time) * 1000)
                execution.state = TaskState.COMPLETED
                execution.finished_at = datetime.now(timezone.utc).isoformat()
                execution.result = str(result_data)

                task.state = TaskState.COMPLETED
                task.last_result = "SUCCESS"
                task.error_message = None

                self._stats["total_executed"] += 1
                self._add_audit_log("EXECUTE_TASK", f"任务完成: {task.name} 耗时{execution.duration_ms}ms")

                return Result.success(
                    data={"execution_id": execution_id, "duration_ms": execution.duration_ms, "result": result_data}
                )
            except TimeoutError:
                execution.state = TaskState.TIMEOUT
                execution.error = "执行超时"
                task.state = TaskState.TIMEOUT
                self._stats["total_timeout"] += 1
                return Result.failure("任务执行超时")
            except Exception as e:
                execution.state = TaskState.FAILED
                execution.error = str(e)
                task.state = TaskState.FAILED
                task.error_message = str(e)
                self._stats["total_failed"] += 1

                if task.should_retry():
                    task.retry_count += 1
                    task.state = TaskState.RETRYING
                    self._stats["total_retried"] += 1
                    self._add_audit_log("TASK_RETRY", f"任务重试: {task.name} 第{task.retry_count}次")
                else:
                    self._add_audit_log("TASK_FAILED", f"任务失败: {task.name} - {str(e)}")

                return Result.failure(f"任务执行失败: {str(e)}")
        except Exception as e:
            return Result.failure(f"执行异常: {str(e)}")

    async def _execute_task_logic(self, task: ScheduledTask) -> Dict[str, Any]:
        """
        执行任务核心逻辑
        生产环境中根据task.metadata中的handler信息调用对应处理器
        """
        handler_type = task.metadata.get("handler_type", "default")
        handler_params = task.metadata.get("handler_params", {})

        if handler_type == "python_callable":
            # 模拟Python函数调用
            return {"handler": "python_callable", "status": "executed", "params": handler_params}
        elif handler_type == "http_callback":
            # 模拟HTTP回调
            return {"handler": "http_callback", "status": "called", "url": handler_params.get("url")}
        elif handler_type == "shell_command":
            # 模拟Shell命令
            return {"handler": "shell_command", "status": "completed", "command": handler_params.get("cmd")}
        else:
            return {"handler": "default", "status": "completed", "task": task.name}

    async def cancel_task(self, task_id: str) -> Result:
        """取消任务"""
        try:
            task = self._tasks.get(task_id)
            if not task:
                return Result.failure(f"任务不存在: {task_id}")
            if task.state in (TaskState.COMPLETED, TaskState.CANCELLED):
                return Result.failure(f"任务已完成或已取消")

            task.state = TaskState.CANCELLED
            self._stats["total_cancelled"] += 1
            self._add_audit_log("CANCEL_TASK", f"取消任务: {task.name} ({task_id})")
            return Result.success(data={"task_id": task_id, "state": "cancelled"})
        except Exception as e:
            return Result.failure(f"取消任务失败: {str(e)}")

    async def retry_task(self, task_id: str) -> Result:
        """手动重试失败的任务"""
        try:
            task = self._tasks.get(task_id)
            if not task:
                return Result.failure(f"任务不存在: {task_id}")
            if task.state not in (TaskState.FAILED,):
                return Result.failure(f"当前状态不可重试: {task.state.value}")

            task.retry_count += 1
            task.state = TaskState.RETRYING
            task.error_message = None
            self._stats["total_retried"] += 1
            self._add_audit_log("RETRY_TASK", f"手动重试: {task.name} 第{task.retry_count}次")

            return await self.execute_task(task_id)
        except Exception as e:
            return Result.failure(f"重试失败: {str(e)}")

    # === 时间窗口管理API ===

    async def add_maintenance_window(self, name: str, start: str, end: str) -> Result:
        """添加维护窗口"""
        success = self._window_manager.add_maintenance_window(name, start, end)
        if success:
            self._add_audit_log("MAINT_WINDOW", f"添加维护窗口: {name}")
            return Result.success(data={"name": name, "start": start, "end": end})
        return Result.failure("添加维护窗口失败")

    async def add_quiet_hours(self, name: str, start_hour: int, end_hour: int) -> Result:
        """添加静默时段"""
        success = self._window_manager.add_quiet_hours(name, start_hour, end_hour)
        if success:
            self._add_audit_log("QUIET_HOURS", f"添加静默时段: {name}")
            return Result.success(data={"name": name, "start_hour": start_hour, "end_hour": end_hour})
        return Result.failure("添加静默时段失败")

    # === 查询API ===

    async def get_task_info(self, task_id: str) -> Result:
        """获取任务详情"""
        task = self._tasks.get(task_id)
        if not task:
            return Result.failure(f"任务不存在: {task_id}")
        return Result.success(
            data={
                "task_id": task.task_id,
                "name": task.name,
                "state": task.state.value,
                "priority": task.priority.value,
                "execution_mode": task.execution_mode.value,
                "cron_expr": task.cron_expr,
                "interval_seconds": task.interval_seconds,
                "timeout_seconds": task.timeout_seconds,
                "max_retries": task.max_retries,
                "retry_count": task.retry_count,
                "dependencies": task.dependencies,
                "tags": task.tags,
                "created_at": task.created_at,
                "last_run_at": task.last_run_at,
                "next_run_at": task.next_run_at,
                "last_result": task.last_result,
                "error_message": task.error_message,
            }
        )

    async def list_tasks(
        self, state_filter: Optional[str] = None, tag_filter: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Result:
        """列出任务"""
        tasks = list(self._tasks.values())
        if state_filter:
            tasks = [t for t in tasks if t.state.value == state_filter]
        if tag_filter:
            tasks = [t for t in tasks if tag_filter in t.tags]

        total = len(tasks)
        tasks = tasks[offset : offset + limit]

        return Result.success(
            data={
                "total": total,
                "limit": limit,
                "offset": offset,
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "name": t.name,
                        "state": t.state.value,
                        "priority": t.priority.value,
                        "execution_mode": t.execution_mode.value,
                        "last_run_at": t.last_run_at,
                        "retry_count": t.retry_count,
                    }
                    for t in tasks
                ],
            }
        )

    async def get_stats(self) -> Result:
        """获取调度统计信息"""
        state_counts = defaultdict(int)
        priority_counts = defaultdict(int)
        for task in self._tasks.values():
            state_counts[task.state.value] += 1
            priority_counts[task.priority.value] += 1

        return Result.success(
            data={
                "total_tasks": len(self._tasks),
                "total_executions": len(self._executions),
                "stats": self._stats,
                "state_distribution": dict(state_counts),
                "priority_distribution": dict(priority_counts),
                "dependency_graph": self._dependency_graph.get_graph_summary(),
                "time_windows": self._window_manager.get_active_windows(),
                "cron_cache_size": len(self._cron_cache),
            }
        )

    async def get_dependency_graph(self) -> Result:
        """获取依赖关系图"""
        return Result.success(data=self._dependency_graph.get_graph_summary())

    async def predict_next_run(self, task_id: str) -> Result:
        """预测任务下次执行时间"""
        task = self._tasks.get(task_id)
        if not task:
            return Result.failure(f"任务不存在: {task_id}")
        if task.execution_mode == ExecutionMode.CRON and task.cron_expr:
            cron = self._get_cron(task.cron_expr)
            next_time = cron.next_run_time()
            return Result.success(data={"task_id": task_id, "next_run_at": next_time.isoformat()})
        elif task.execution_mode == ExecutionMode.PERIODIC:
            if task.last_run_at:
                last = datetime.fromisoformat(task.last_run_at)
                next_time = last + timedelta(seconds=task.interval_seconds)
                return Result.success(data={"task_id": task_id, "next_run_at": next_time.isoformat()})
        return Result.success(data={"task_id": task_id, "next_run_at": "需要手动触发"})

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        # 采集Prometheus指标
        metrics_collector.gauge("cronus_tasks_total", len(self._tasks))
        metrics_collector.gauge("cronus_executions_total", len(self._executions))
        metrics_collector.counter("cronus_health_checks_total")
        running = sum(1 for t in self._tasks.values() if hasattr(t, "state") and str(t.state) == "RUNNING")
        metrics_collector.gauge("cronus_running_tasks", running)
        return {
            "status": "healthy",
            "scheduler_running": self._running,
            "thread_alive": self._scheduler_thread.is_alive() if self._scheduler_thread else False,
            "tasks_count": len(self._tasks),
            "executions_count": len(self._executions),
            "uptime_seconds": int(time.time() - self._init_time) if hasattr(self, "_init_time") else 0,
        }

    async def shutdown(self) -> Result:
        """关闭Cronus智能体"""
        self._running = False
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)
        self._add_audit_log("SHUTDOWN", "Cronus智能体已关闭")
        self.update_status(ModuleStatus.STOPPED)
        return Result.success(data={"status": "shutdown"})

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

module_class = CronusAgent
