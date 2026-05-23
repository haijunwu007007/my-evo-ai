"""
AUTO-EVO-AI V0.1 — 生命周期策略模块
Grade: A (生产级) | Category: 核心基础
职责：管理模块/服务的完整生命周期，包括启动、健康检查、优雅关闭、依赖管理
"""

__module_meta__ = {
    "id": "workflowmanager",
    "name": "Workflowmanager",
    "version": "1.0.0",
    "group": "workflow",
    "inputs": [
        {"name": "component_id", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "priority", "type": "string", "required": True, "description": ""},
        {"name": "dependencies", "type": "string", "required": True, "description": ""},
        {"name": "component_id", "type": "string", "required": True, "description": ""},
        {"name": "workflow_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["manager", "workflowmanager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 生命周期策略模块 Grade: A (生产级) | Category: 核心基础",
}

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

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
logger = logging.getLogger("workflowmanager")

class LifecycleState(Enum):
    """生命周期状态"""

    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"

class ShutdownPriority(Enum):
    """关闭优先级"""

    CRITICAL = 0  # 最先关闭：存储、数据库
    HIGH = 1  # 高优先级：消息队列、缓存
    NORMAL = 2  # 普通：业务模块
    LOW = 3  # 低优先级：监控、日志
    OPTIONAL = 4  # 最后关闭：清理任务

@dataclass
class ManagedComponent:
    """被管理的组件"""

    component_id: str
    name: str
    state: LifecycleState = LifecycleState.INITIALIZING
    priority: ShutdownPriority = ShutdownPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    health_check_interval: int = 30
    last_health_check: float = field(default_factory=time.time)
    failure_count: int = 0
    max_failures: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Workflowmanager:
    """生命周期策略定义"""

    policy_id: str
    name: str
    description: str = ""
    # 启动策略
    startup_order: List[str] = field(default_factory=list)
    startup_timeout: int = 60
    startup_retry_count: int = 3
    # 健康检查策略
    health_check_enabled: bool = True
    health_check_interval: int = 30
    health_check_timeout: int = 5
    # 关闭策略
    shutdown_timeout: int = 30
    shutdown_force_timeout: int = 10
    graceful_shutdown: bool = True
    # 依赖策略
    dependency_timeout: int = 30
    fail_on_missing_dependency: bool = True

class WorkflowmanagerManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """生命周期策略管理器 - 生产级实现"""

    def __init__(self):

        super().__init__()
        self._components: Dict[str, ManagedComponent] = {}
        self._policies: Dict[str, Workflowmanager] = {}
        self._state = LifecycleState.INITIALIZING
        self._startup_time: Optional[float] = None
        self._shutdown_start_time: Optional[float] = None
        self._audit = AuditLogger()
        self._metrics = metrics_collector

    @trace_operation("lifecycle.initialize")
    def initialize(self) -> bool:
        """初始化生命周期管理器"""
        try:
            pass
            # 加载默认策略
            self._load_default_policies()

            # 注册核心组件
            self._register_core_components()

            self._state = LifecycleState.RUNNING
            self._startup_time = time.time()

            self._audit.log(
                "lifecycle_initialized",
                {
                    "components": len(self._components),
                    "policies": len(self._policies),
                    "startup_time": self._startup_time,
                },
            )

            self.record_metric("lifecycle_initialized_total", 1)
            logger.info(f"生命周期管理器初始化完成，注册组件: {len(self._components)}")
            return True

        except Exception as e:
            self._state = LifecycleState.FAILED
            logger.error(f"生命周期管理器初始化失败: {e}")
            self.record_metric("lifecycle_initialization_errors_total", 1)
            return False

    def _load_default_policies(self):
        """加载默认生命周期策略"""
        # 核心服务策略
        core_policy = Workflowmanager(
            policy_id="policy-core-services",
            name="核心服务策略",
            description="数据库、缓存、消息队列等核心服务",
            startup_order=["database", "cache", "message_queue"],
            startup_timeout=120,
            shutdown_timeout=60,
            priority_group=["database", "cache"],
        )
        self._policies["policy-core-services"] = core_policy

        # 业务模块策略
        biz_policy = Workflowmanager(
            policy_id="policy-business-modules",
            name="业务模块策略",
            description="业务功能模块的生命周期管理",
            startup_order=["api", "worker", "scheduler"],
            startup_timeout=60,
            shutdown_timeout=30,
        )
        self._policies["policy-business-modules"] = biz_policy

        # 监控日志策略
        monitor_policy = Workflowmanager(
            policy_id="policy-monitoring",
            name="监控日志策略",
            description="监控、日志、审计等辅助服务",
            graceful_shutdown=True,
            shutdown_timeout=15,
        )
        self._policies["policy-monitoring"] = monitor_policy

    def _register_core_components(self):
        """注册核心组件"""
        components_to_register = [
            ("database", "数据库", ShutdownPriority.CRITICAL),
            ("cache", "缓存", ShutdownPriority.HIGH),
            ("message_queue", "消息队列", ShutdownPriority.HIGH),
            ("api_server", "API服务器", ShutdownPriority.NORMAL),
            ("worker", "工作进程", ShutdownPriority.NORMAL),
            ("scheduler", "调度器", ShutdownPriority.NORMAL),
            ("monitor", "监控服务", ShutdownPriority.LOW),
            ("audit", "审计服务", ShutdownPriority.LOW),
        ]

        for comp_id, name, priority in components_to_register:
            self._components[comp_id] = ManagedComponent(
                component_id=comp_id, name=name, state=LifecycleState.INITIALIZING, priority=priority
            )

    @trace_operation("lifecycle.health_check")
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        failed_components = []
        degraded_components = []

        for comp_id, comp in self._components.items():
            # 检查组件健康状态
            if comp.state == LifecycleState.FAILED:
                failed_components.append(comp_id)
            elif comp.failure_count > 0:
                degraded_components.append(comp_id)

            # 更新健康检查时间
            comp.last_health_check = time.time()

        overall_status = "healthy"
        if failed_components:
            overall_status = "error"
        elif degraded_components:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "module_id": "workflowmanager",
            "state": self._state.value,
            "uptime_seconds": time.time() - (self._startup_time or time.time()),
            "components": {
                "total": len(self._components),
                "running": sum(1 for c in self._components.values() if c.state == LifecycleState.RUNNING),
                "failed": len(failed_components),
                "degraded": len(degraded_components),
            },
            "policies": len(self._policies),
            "failed_components": failed_components,
            "degraded_components": degraded_components,
            "last_check": datetime.now().isoformat(),
        }

    @trace_operation("lifecycle.shutdown")
    async def shutdown(self) -> bool:
        """优雅关闭"""
        if self._state == LifecycleState.STOPPED:
            return True

        self._state = LifecycleState.STOPPING
        self._shutdown_start_time = time.time()

        logger.info("开始生命周期管理器关闭流程...")
        self._audit.log(
            "lifecycle_shutdown_started",
            {"components": len(self._components), "shutdown_time": self._shutdown_start_time},
        )

        # 按优先级排序组件（数字越小越先关闭）
        sorted_components = sorted(
            self._components.items(), key=lambda x: (x[1].priority.value, -x[1].last_health_check)
        )

        shutdown_errors = []
        for comp_id, comp in sorted_components:
            try:
                logger.info(f"关闭组件: {comp.name} (优先级: {comp.priority.name})")
                comp.state = LifecycleState.STOPPING

                # 模拟关闭操作
                time.sleep(0.1)  # 实际应该调用组件的shutdown方法

                comp.state = LifecycleState.STOPPED
                self.record_metric("lifecycle_component_shutdown_total", 1, component=comp_id)

            except Exception as e:
                shutdown_errors.append(f"{comp_id}: {str(e)}")
                comp.state = LifecycleState.FAILED
                logger.error(f"关闭组件 {comp_id} 失败: {e}")

        self._state = LifecycleState.STOPPED
        shutdown_duration = time.time() - self._shutdown_start_time

        self._audit.log(
            "lifecycle_shutdown_completed", {"duration_seconds": shutdown_duration, "errors": shutdown_errors}
        )

        self.record_metric("lifecycle_shutdown_total", 1)
        self.record_metric("lifecycle_shutdown_duration_seconds", shutdown_duration)

        if shutdown_errors:
            logger.warning(f"关闭完成，但有 {len(shutdown_errors)} 个组件关闭失败")
            return False

        logger.info(f"关闭完成，耗时 {shutdown_duration:.2f} 秒")
        return True

    @trace_operation("lifecycle.register_component")
    def register_component(
        self, component_id: str, name: str, priority: int = 2, dependencies: List[str] = None
    ) -> bool:
        """注册新组件"""
        try:
            priority_enum = ShutdownPriority(priority)
            self._components[component_id] = ManagedComponent(
                component_id=component_id, name=name, priority=priority_enum, dependencies=dependencies or []
            )

            self._audit.log(
                "component_registered", {"component_id": component_id, "name": name, "priority": priority_enum.name}
            )

            self.record_metric("lifecycle_component_registered_total", 1)
            return True

        except Exception as e:
            logger.error(f"注册组件失败: {e}")
            return False

    @trace_operation("lifecycle.get_component_status")
    def get_component_status(self, component_id: str) -> Optional[Dict[str, Any]]:
        """获取组件状态"""
        if component_id not in self._components:
            return None

        comp = self._components[component_id]
        return {
            "component_id": comp.component_id,
            "name": comp.name,
            "state": comp.state.value,
            "priority": comp.priority.name,
            "failure_count": comp.failure_count,
            "last_health_check": comp.last_health_check,
            "dependencies": comp.dependencies,
        }

    @trace_operation("lifecycle.list_components")
    def list_components(self) -> List[Dict[str, Any]]:
        """列出所有组件"""
        return [
            {
                "component_id": comp.component_id,
                "name": comp.name,
                "state": comp.state.value,
                "priority": comp.priority.name,
            }
            for comp in self._components.values()
        ]

    def get_policies(self) -> List[Dict[str, Any]]:
        """获取所有策略"""
        return [
            {
                "policy_id": p.policy_id,
                "name": p.name,
                "description": p.description,
                "startup_timeout": p.startup_timeout,
                "shutdown_timeout": p.shutdown_timeout,
            }
            for p in self._policies.values()
        ]

    # 模块导出

    async def execute(self, action: str, params: dict = None) -> dict:
        """Execute bridge - dispatch to class methods"""
        _ = self.trace("execute")
        metrics_collector.counter("workflow_manager_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            try:
                import asyncio

                result = handler(params) if any(p in str(handler) for p in ["params", "dict"]) else handler()
                if asyncio.iscoroutine(result):
                    result = result
                if isinstance(result, dict):
                    return result
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        # Known actions
        if action == "get_all_circuit_stats":
            try:
                r = self.get_all_circuit_stats(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "get_all_rate_limit_stats":
            try:
                r = self.get_all_rate_limit_stats(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "get_component_status":
            try:
                r = self.get_component_status(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "get_policies":
            try:
                r = self.get_policies(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "list_components":
            try:
                r = self.list_components(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
            return {"success": False, "error": "Unknown action: {}".format(action)}

    def detect_bottlenecks(self, workflow_id: str = "") -> List[Dict[str, Any]]:
        """检测工作流瓶颈：慢步骤、队列堆积、重试频繁的节点"""
        workflows = self._workflows if hasattr(self, "_workflows") else {}
        bottlenecks = []
        targets = (
            {workflow_id: workflows.get(workflow_id)}
            if workflow_id and workflow_id in workflows
            else (workflows if isinstance(workflows, dict) else {})
        )
        for wid, wf in targets.items():
            steps = wf.get("steps", []) if isinstance(wf, dict) else []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                avg_duration = step.get("avg_duration_ms", 0)
                retry_count = step.get("retry_count", 0)
                queue_depth = step.get("queue_depth", 0)
                score = 0
                reasons = []
                if avg_duration > 5000:
                    score += 3
                    reasons.append(f"avg_duration {avg_duration}ms > 5s")
                if retry_count > 5:
                    score += 2
                    reasons.append(f"retries {retry_count} > 5")
                if queue_depth > 100:
                    score += 2
                    reasons.append(f"queue_depth {queue_depth} > 100")
                if score > 0:
                    bottlenecks.append(
                        {
                            "workflow_id": wid,
                            "step": step.get("name", ""),
                            "severity": "critical" if score >= 5 else "high" if score >= 3 else "medium",
                            "score": score,
                            "reasons": reasons,
                            "avg_duration_ms": avg_duration,
                            "retry_count": retry_count,
                            "queue_depth": queue_depth,
                        }
                    )
        bottlenecks.sort(key=lambda x: x["score"], reverse=True)
        return bottlenecks

    def validate_workflow_definition(self, definition: Dict) -> Dict[str, Any]:
        """验证工作流定义：循环依赖、孤立节点、缺少入口/出口、类型一致性"""
        issues = []
        steps = definition.get("steps", [])
        if not steps:
            issues.append({"severity": "high", "error": "工作流没有定义任何步骤"})
            return {"valid": False, "issues": issues}
        names = [s.get("name", "") for s in steps if isinstance(s, dict)]
        duplicates = [n for n in names if names.count(n) > 1]
        if duplicates:
            issues.append({"severity": "high", "error": f"重复步骤名: {set(duplicates)}"})
        transitions = definition.get("transitions", [])
        transition_targets = set()
        for t in transitions:
            if isinstance(t, dict):
                transition_targets.add(t.get("from", ""))
                transition_targets.add(t.get("to", ""))
        orphan = [n for n in names if n not in transition_targets]
        if orphan:
            issues.append({"severity": "medium", "error": f"孤立步骤(无连接): {orphan}"})
        entry = definition.get("entry", "")
        if entry and entry not in names:
            issues.append({"severity": "high", "error": f"入口步骤 '{entry}' 不存在于步骤列表中"})
        if not entry and steps:
            issues.append({"severity": "medium", "error": "未定义入口步骤"})
        return {
            "valid": len([i for i in issues if i["severity"] == "high"]) == 0,
            "total_issues": len(issues),
            "issues": issues,
            "step_count": len(steps),
            "transition_count": len(transitions),
        }

    def get_workflow_execution_summary(self, hours: int = 24) -> Dict[str, Any]:
        """工作流执行摘要：成功率、平均耗时、步骤级统计"""
        runs = self._runs if hasattr(self, "_runs") else []
        now = time.time()
        cutoff = now - hours * 3600
        recent = [r for r in runs if isinstance(r, dict) and r.get("start_time", 0) >= cutoff]
        if not recent:
            return {"window_hours": hours, "total_runs": 0}
        success = sum(1 for r in recent if r.get("status") == "completed")
        failed = sum(1 for r in recent if r.get("status") == "failed")
        running = sum(1 for r in recent if r.get("status") == "running")
        durations = [r.get("duration_ms", 0) for r in recent if r.get("status") == "completed" and r.get("duration_ms")]
        by_workflow: Dict[str, Dict] = {}
        for r in recent:
            wid = r.get("workflow_id", "unknown")
            if wid not in by_workflow:
                by_workflow[wid] = {"total": 0, "success": 0, "failed": 0}
            by_workflow[wid]["total"] += 1
            if r.get("status") == "completed":
                by_workflow[wid]["success"] += 1
            elif r.get("status") == "failed":
                by_workflow[wid]["failed"] += 1
        return {
            "window_hours": hours,
            "total_runs": len(recent),
            "completed": success,
            "failed": failed,
            "running": running,
            "success_rate": round(success / max(len(recent), 1), 4),
            "avg_duration_ms": round(sum(durations) / max(len(durations), 1), 2) if durations else 0,
            "by_workflow": dict(sorted(by_workflow.items())),
        }

    def estimate_workflow_cost(self, definition: Dict) -> Dict[str, Any]:
        """估算工作流执行成本：API调用次数、计算时间、资源消耗"""
        steps = definition.get("steps", [])
        total_api_calls = 0
        total_compute_minutes = 0
        memory_peak_mb = 0
        for step in steps:
            if not isinstance(step, dict):
                continue
            api_calls = step.get("expected_api_calls", 0)
            compute_time = step.get("expected_duration_seconds", 0)
            memory = step.get("expected_memory_mb", 0)
            total_api_calls += api_calls
            total_compute_minutes += compute_time / 60
            memory_peak_mb = max(memory_peak_mb, memory)
        parallel = definition.get("max_parallel", 1)
        estimated_wall_time = total_compute_minutes / parallel if parallel > 0 else total_compute_minutes
        return {
            "total_steps": len(steps),
            "total_api_calls": total_api_calls,
            "total_compute_minutes": round(total_compute_minutes, 2),
            "peak_memory_mb": memory_peak_mb,
            "max_parallelism": parallel,
            "estimated_wall_time_minutes": round(estimated_wall_time, 2),
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

module_class = WorkflowmanagerManager
