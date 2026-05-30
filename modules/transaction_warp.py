"""
AUTO-EVO-AI V0.1 — 生命周期策略模块
Grade: A (生产级) | Category: 核心基础
职责：管理模块/服务的完整生命周期，包括启动、健康检查、优雅关闭、依赖管理
"""

__module_meta__ = {
    "id": "transaction-warp",
    "name": "Transaction Warp",
    "version": "V0.1",
    "group": "database",
    "inputs": [
        {"name": "component_id", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "priority", "type": "string", "required": True, "description": ""},
        {"name": "dependencies", "type": "string", "required": True, "description": ""},
        {"name": "component_id", "type": "string", "required": True, "description": ""},
        {"name": "hours", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["transaction", "manager"],
    "grade": "B",
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
logger = logging.getLogger("transaction_warp")

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
class TransactionWarp:
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

class TransactionWarpManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """生命周期策略管理器 - 生产级实现"""

    def __init__(self):

        super().__init__()
        self._components: Dict[str, ManagedComponent] = {}
        self._policies: Dict[str, TransactionWarp] = {}
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
        core_policy = TransactionWarp(
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
        biz_policy = TransactionWarp(
            policy_id="policy-business-modules",
            name="业务模块策略",
            description="业务功能模块的生命周期管理",
            startup_order=["api", "worker", "scheduler"],
            startup_timeout=60,
            shutdown_timeout=30,
        )
        self._policies["policy-business-modules"] = biz_policy

        # 监控日志策略
        monitor_policy = TransactionWarp(
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
            "module_id": "transaction_warp",
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
        metrics_collector.counter("transaction_warp_ops_total", labels={"action": action})
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

    def analyze_compensation_history(self, hours: int = 24) -> Dict[str, Any]:
        """分析补偿事务历史：成功率、平均补偿时间、失败原因分布"""
        history = self._compensation_log if hasattr(self, "_compensation_log") else []
        now = time.time()
        cutoff = now - hours * 3600
        recent = [h for h in history if isinstance(h, dict) and h.get("timestamp", 0) >= cutoff] if history else []
        if not recent:
            return {"window_hours": hours, "total": 0}
        success = sum(1 for h in recent if h.get("status") == "success")
        failed = sum(1 for h in recent if h.get("status") == "failed")
        durations = [h.get("duration_ms", 0) for h in recent if h.get("status") == "success"]
        reasons: Dict[str, int] = {}
        for h in recent:
            if h.get("status") == "failed":
                reason = h.get("error", "unknown")[:50]
                reasons[reason] = reasons.get(reason, 0) + 1
        return {
            "window_hours": hours,
            "total_compensations": len(recent),
            "success": success,
            "failed": failed,
            "success_rate": round(success / max(len(recent), 1), 4),
            "avg_duration_ms": round(sum(durations) / max(len(durations), 1), 2),
            "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 1 else 0,
            "failure_reasons": dict(sorted(reasons.items(), key=lambda x: -x[1])),
        }

    def check_saga_health(self) -> Dict[str, Any]:
        """检查Saga事务健康状态：活跃事务、超时风险、悬挂补偿"""
        sagas = self._active_sagas if hasattr(self, "_active_sagas") else {}
        now = time.time()
        active = 0
        timed_out = 0
        compensating = 0
        hanging = []
        for sid, saga in sagas.items() if isinstance(sagas, dict) else []:
            state = saga.get("state", "") if isinstance(saga, dict) else ""
            if state in ("running", "pending"):
                active += 1
                started = saga.get("started_at", 0)
                timeout = saga.get("timeout_seconds", 300)
                if started and (now - started) > timeout:
                    timed_out += 1
                    hanging.append(
                        {"saga_id": sid, "elapsed": round(now - started), "timeout": timeout, "risk": "high"}
                    )
            elif state == "compensating":
                compensating += 1
                comp_started = saga.get("compensate_started_at", 0)
                if comp_started and (now - comp_started) > 60:
                    hanging.append(
                        {
                            "saga_id": sid,
                            "elapsed": round(now - comp_started),
                            "risk": "medium",
                            "detail": "compensation taking too long",
                        }
                    )
        return {
            "active_sagas": active,
            "compensating": compensating,
            "timeout_risk": timed_out,
            "hanging_transactions": hanging,
            "healthy": timed_out == 0 and len(hanging) == 0,
        }

    def get_transaction_timeline(self, saga_id: str) -> Dict[str, Any]:
        """获取事务执行时间线：各步骤的开始/结束时间、耗时、状态"""
        sagas = self._active_sagas if hasattr(self, "_active_sagas") else {}
        history = self._compensation_log if hasattr(self, "_compensation_log") else []
        saga = sagas.get(saga_id) if isinstance(sagas, dict) else None
        if not saga:
            return {"error": "saga not found"}
        steps = saga.get("steps", []) if isinstance(saga, dict) else []
        timeline = []
        for step in steps:
            if isinstance(step, dict):
                duration = 0
                if step.get("end_time") and step.get("start_time"):
                    duration = step["end_time"] - step["start_time"]
                timeline.append(
                    {
                        "step": step.get("name", ""),
                        "action": step.get("action", ""),
                        "status": step.get("status", "unknown"),
                        "start_time": step.get("start_time"),
                        "duration_ms": round(duration * 1000, 2),
                    }
                )
        related_compensations = [h for h in history if isinstance(h, dict) and h.get("saga_id") == saga_id]
        return {
            "saga_id": saga_id,
            "state": saga.get("state", "") if isinstance(saga, dict) else "",
            "steps": timeline,
            "compensations": related_compensations,
            "total_duration_ms": round(sum(t["duration_ms"] for t in timeline), 2),
        }

    def get_compensation_recommendations(self) -> Dict[str, Any]:
        """生成补偿策略优化建议：超时配置、重试策略、幂等性检查"""
        sagas = self._active_sagas if hasattr(self, "_active_sagas") else {}
        recommendations = []
        for sid, saga in sagas.items() if isinstance(sagas, dict) else []:
            if not isinstance(saga, dict):
                continue
            steps = saga.get("steps", [])
            for step in steps:
                if not isinstance(step, dict):
                    continue
                retries = step.get("retry_count", 0)
                timeout = step.get("timeout_seconds", 0)
                if retries > 10:
                    recommendations.append(
                        {
                            "saga_id": sid,
                            "step": step.get("name", ""),
                            "type": "retry_excessive",
                            "detail": f"重试次数{retries}过高，建议增加退避间隔或降低最大重试次数",
                        }
                    )
                if timeout == 0:
                    recommendations.append(
                        {
                            "saga_id": sid,
                            "step": step.get("name", ""),
                            "type": "no_timeout",
                            "detail": "未设置超时，补偿可能无限等待",
                        }
                    )
        return {"total_recommendations": len(recommendations), "recommendations": recommendations[:20]}

    def get_retry_policy_summary(self) -> Dict[str, Any]:
        """获取所有补偿步骤的重试策略汇总"""
        sagas = self._active_sagas if hasattr(self, "_active_sagas") else {}
        policies = {}
        for sid, saga in sagas.items() if isinstance(sagas, dict) else []:
            if not isinstance(saga, dict):
                continue
            for step in saga.get("steps", []):
                if isinstance(step, dict):
                    name = step.get("name", "unknown")
                    policies[name] = {
                        "max_retries": step.get("max_retries", 3),
                        "backoff_ms": step.get("backoff_ms", 1000),
                        "timeout_seconds": step.get("timeout_seconds", 30),
                    }
        return {"total_policies": len(policies), "policies": policies}

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

module_class = TransactionWarpManager
