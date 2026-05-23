"""
AUTO-EVO-AI v7.0 — 生命周期策略模块
Grade: A (生产级) | Category: 核心基础
职责：管理模块/服务的完整生命周期，包括启动、健康检查、优雅关闭、依赖管理
"""

__module_meta__ = {
    "id": "agent-athena",
    "name": "Agent Athena",
    "version": "1.0.0",
    "group": "agent",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "component_id", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "priority", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [{"type": "event", "config": {"on": "agent_athena.task.request"}}],
    "depends_on": [],
    "tags": ["engine", "manager", "multi-agent", "agent"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 — 生命周期策略模块 Grade: A (生产级) | Category: 核心基础",
}

import os
import asyncio
import time
import time as tmod
import logging
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModulenterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import prometheus_timer, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("agent_athena")

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
class LifecyclePolicy:
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

class AgentAthenaManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """生命周期策略管理器 - 生产级实现"""

    MODULE_ID = "agent_athena"
    MODULE_NAME = "生命周期策略管理"
    VERSION = "7.0.0"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._components: Dict[str, ManagedComponent] = {}
        self._policies: Dict[str, LifecyclePolicy] = {}
        self._state = LifecycleState.INITIALIZING
        self._startup_time: Optional[float] = None
        self._shutdown_start_time: Optional[float] = None
        self._audit = None
        self._metrics = metrics_collector

    def initialize(self) -> None:
        """初始化生命周期管理器"""
        try:
            pass
            # 加载默认策略
            self._load_default_policies()

            # 注册核心组件
            self._register_core_components()

            self._state = LifecycleState.RUNNING
            self._startup_time = time.time()

            if self._audit:
                self._audit.log(
                    "lifecycle_initialized",
                    {
                        "components": len(self._components),
                        "policies": len(self._policies),
                        "startup_time": self._startup_time,
                    },
                )

            self.stats.success_count += 1
            logger.info(f"生命周期管理器初始化完成，注册组件: {len(self._components)}")

        except Exception as e:
            self._state = LifecycleState.FAILED
            logger.error(f"生命周期管理器初始化失败: {e}")
            self.stats.error_count += 1
            raise

    def _load_default_policies(self):
        """加载默认生命周期策略"""
        # 核心服务策略
        core_policy = LifecyclePolicy(
            policy_id="policy-core-services",
            name="核心服务策略",
            description="数据库、缓存、消息队列等核心服务",
            startup_order=["database", "cache", "message_queue"],
            startup_timeout=120,
            shutdown_timeout=60,
        )
        self._policies["policy-core-services"] = core_policy

        # 业务模块策略
        biz_policy = LifecyclePolicy(
            policy_id="policy-business-modules",
            name="业务模块策略",
            description="业务功能模块的生命周期管理",
            startup_order=["api", "worker", "scheduler"],
            startup_timeout=60,
            shutdown_timeout=30,
        )
        self._policies["policy-business-modules"] = biz_policy

        # 监控日志策略
        monitor_policy = LifecyclePolicy(
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

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        metrics_collector.counter("agent_athena_ops_total", labels={"action": action})
        """执行生命周期管理动作"""
        params = params or {}
        start_time = time.time()
        success = False
        error_msg = None

        with self.trace("execute"):
            try:
                if action == "register_component":
                    component_id = params.get("component_id")
                    name = params.get("name")
                    priority = params.get("priority", 2)
                    if not all([component_id, name]):
                        error_msg = "Missing params: component_id, name"
                        return {"success": False, "error": error_msg}
                    result = self.register_component(component_id, name, priority)
                    success = True
                    return {"success": True, "result": {"registered": result}}
                elif action == "get_component_status":
                    component_id = params.get("component_id")
                    if not component_id:
                        error_msg = "Missing param: component_id"
                        return {"success": False, "error": error_msg}
                    result = self.get_component_status(component_id)
                    success = True
                    return {"success": True, "result": result}
                elif action == "list_components":
                    result = self.list_components()
                    success = True
                    return {"success": True, "result": result}
                elif action == "list_policies":
                    result = self.get_policies()
                    success = True
                    return {"success": True, "result": result}
                elif action == "health_check_components":
                    self._perform_health_checks()
                    result = self.health_check()
                    success = True
                    return {"success": True, "result": result}
                else:
                    error_msg = f"Unknown action: {action}"
                    return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Execute error: {e}", exc_info=True)
                return {"success": False, "error": error_msg}
            finally:
                duration_ms = (time.time() - start_time) * 1000
            self.stats.record_request(duration_ms, success, error_msg)

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        self.audit("execute", f"action={action}")

        failed_components = []
        degraded_components = []

        for comp_id, comp in self._components.items():
            if comp.state == LifecycleState.FAILED:
                failed_components.append(comp_id)
            elif comp.failure_count > 0:
                degraded_components.append(comp_id)

            # 更新健康检查时间
            comp.last_health_check = time.time()

        # 判断整体状态
        if failed_components:
            status = "unhealthy"
        elif degraded_components or self._state == LifecycleState.DEGRADED:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "module_id": self.module_id,
            "module_level": self.module_level,
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
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        }

    def _perform_health_checks(self):
        """执行健康检查（模拟）"""
        for comp_id, comp in self._components.items():
            # 模拟健康检查 - 50%概率成功
            import time as tmod

            if (int(tmod.time()*1000000)%1000000/1000000) > 0.5:
                comp.state = LifecycleState.RUNNING
                comp.failure_count = 0
            else:
                comp.failure_count += 1
                if comp.failure_count >= comp.max_failures:
                    comp.state = LifecycleState.FAILED

    def shutdown(self) -> None:
        """优雅关闭"""
        if self._state == LifecycleState.STOPPED:
            return

        self._state = LifecycleState.STOPPING
        self._shutdown_start_time = time.time()

        logger.info("开始生命周期管理器关闭流程...")

        if self._audit:
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
                self.stats.success_count += 1

            except Exception as e:
                shutdown_errors.append(f"{comp_id}: {str(e)}")
                comp.state = LifecycleState.FAILED
                logger.error(f"关闭组件 {comp_id} 失败: {e}")

        self._state = LifecycleState.STOPPED
        shutdown_duration = time.time() - self._shutdown_start_time

        if self._audit:
            self._audit.log(
                "lifecycle_shutdown_completed", {"duration_seconds": shutdown_duration, "errors": shutdown_errors}
            )

        if shutdown_errors:
            logger.warning(f"关闭完成，但有 {len(shutdown_errors)} 个组件关闭失败")
        else:
            logger.info(f"关闭完成，耗时 {shutdown_duration:.2f} 秒")

    def register_component(
        self, component_id: str, name: str, priority: int = 2, dependencies: Optional[List[str]] = None
    ) -> bool:
        """注册新组件"""
        try:
            priority_enum = ShutdownPriority(priority)
            self._components[component_id] = ManagedComponent(
                component_id=component_id, name=name, priority=priority_enum, dependencies=dependencies or []
            )

            if self._audit:
                self._audit.log(
                    "component_registered", {"component_id": component_id, "name": name, "priority": priority_enum.name}
                )

            self.stats.success_count += 1
            return True

        except Exception as e:
            logger.error(f"注册组件失败: {e}")
            self.stats.error_count += 1
            return False

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

module_class = AgentAthenaManager

class AnalysisEngine(object):
    """数据分析引擎 - 多维分析、趋势检测、异常识别"""

    def __init__(self):
        self._datasets: Dict[str, List[Dict]] = {}
        self._analysis_cache: Dict[str, Dict] = {}
        self._trend_models: Dict[str, Dict] = {}

    def ingest(self, dataset_id: str, records: List[Dict]) -> int:
        """导入数据集"""
        if dataset_id not in self._datasets:
            self._datasets[dataset_id] = []
        self._datasets[dataset_id].extend(records)
        self._analysis_cache.pop(dataset_id, None)
        return len(self._datasets[dataset_id])

    def get_statistics(self, dataset_id: str, field: str) -> Dict[str, Any]:
        """计算字段统计"""
        data = self._datasets.get(dataset_id, [])
        values = [r.get(field) for r in data if isinstance(r.get(field), (int, float))]
        if not values:
            return {"field": field, "count": 0}
        n = len(values)
        mean = sum(values) / n
        sorted_vals = sorted(values)
        median = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        variance = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
        std = variance**0.5
        return {
            "field": field,
            "count": n,
            "mean": round(mean, 4),
            "median": round(median, 4),
            "std": round(std, 4),
            "min": min(values),
            "max": max(values),
            "q1": sorted_vals[n // 4],
            "q3": sorted_vals[3 * n // 4],
        }

    def detect_anomalies(self, dataset_id: str, field: str, threshold: float = 2.0) -> List[Dict]:
        """异常值检测"""
        stats = self.get_statistics(dataset_id, field)
        if stats["count"] == 0:
            return []
        mean = stats["mean"]
        std = stats["std"]
        anomalies = []
        data = self._datasets.get(dataset_id, [])
        for i, r in enumerate(data):
            v = r.get(field)
            if isinstance(v, (int, float)):
                z = abs(v - mean) / max(std, 1e-8)
                if z > threshold:
                    anomalies.append({"index": i, "value": v, "z_score": round(z, 4)})
        return anomalies

    def detect_trend(self, dataset_id: str, field: str) -> Dict[str, Any]:
        """简单趋势检测"""
        data = self._datasets.get(dataset_id, [])
        values = [r.get(field) for r in data if isinstance(r.get(field), (int, float))]
        if len(values) < 3:
            return {"trend": "insufficient_data", "values": len(values)}
        first_half = values[: len(values) // 2]
        second_half = values[len(values) // 2 :]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        change = (avg_second - avg_first) / max(abs(avg_first), 1e-8) * 100
        direction = "up" if change > 5 else "down" if change < -5 else "stable"
        return {
            "trend": direction,
            "change_pct": round(change, 2),
            "first_avg": round(avg_first, 4),
            "second_avg": round(avg_second, 4),
        }

    def group_by(self, dataset_id: str, field: str) -> Dict[str, int]:
        """分组统计"""
        data = self._datasets.get(dataset_id, [])
        groups: Dict[str, int] = {}
        for r in data:
            key = str(r.get(field, "unknown"))
            groups[key] = groups.get(key, 0) + 1
        return dict(sorted(groups.items(), key=lambda x: -x[1]))

    def get_dataset_info(self, dataset_id: str) -> Dict[str, Any]:
        data = self._datasets.get(dataset_id, [])
        if not data:
            return {"dataset_id": dataset_id, "records": 0}
        fields = list(data[0].keys()) if data else []
        return {"dataset_id": dataset_id, "records": len(data), "fields": fields}

    def list_datasets(self) -> List[str]:
        return list(self._datasets.keys())

    def correlate(self, dataset_id: str, field_a: str, field_b: str) -> Dict[str, Any]:
        """计算两字段相关性"""
        data = self._datasets.get(dataset_id, [])
        pairs = [
            (r.get(field_a), r.get(field_b))
            for r in data
            if isinstance(r.get(field_a), (int, float)) and isinstance(r.get(field_b), (int, float))
        ]
        if len(pairs) < 2:
            return {"correlation": 0.0, "pairs": len(pairs)}
        n = len(pairs)
        sum_a = sum(p[0] for p in pairs)
        sum_b = sum(p[1] for p in pairs)
        sum_ab = sum(p[0] * p[1] for p in pairs)
        sum_a2 = sum(p[0] ** 2 for p in pairs)
        sum_b2 = sum(p[1] ** 2 for p in pairs)
        denom = ((n * sum_a2 - sum_a**2) * (n * sum_b2 - sum_b**2)) ** 0.5
        corr = (n * sum_ab - sum_a * sum_b) / max(denom, 1e-8)
        return {"correlation": round(corr, 4), "pairs": n, "field_a": field_a, "field_b": field_b}

    def top_values(self, dataset_id: str, field: str, n: int = 10) -> List[Dict]:
        """获取字段Top N值"""
        data = self._datasets.get(dataset_id, [])
        counter: Dict[str, int] = {}
        for r in data:
            v = str(r.get(field, ""))
            counter[v] = counter.get(v, 0) + 1
        sorted_items = sorted(counter.items(), key=lambda x: -x[1])
        return [{"value": k, "count": v} for k, v in sorted_items[:n]]

    def assess_data_quality(self, dataset_id: str) -> Dict[str, Any]:
        """评估数据集质量: 完整性、一致性、唯一性"""
        data = self._datasets.get(dataset_id, [])
        if not data:
            return {"error": "dataset not found", "quality_score": 0}
        total_rows = len(data)
        if total_rows == 0:
            return {"total_rows": 0, "quality_score": 1.0}
        fields = list(data[0].keys()) if data else []
        null_counts: Dict[str, int] = {}
        for row in data:
            for field in fields:
                if row.get(field) is None or str(row.get(field, "")).strip() == "":
                    null_counts[field] = null_counts.get(field, 0) + 1
        completeness = sum(1 for row in data for f in fields if row.get(f) is not None)
        max_possible = total_rows * max(len(fields), 1)
        completeness_rate = completeness / max_possible
        unique_sets = {f: len(set(str(r.get(f, "")) for r in data)) for f in fields}
        uniqueness = min(unique_sets.values()) / max(total_rows, 1) if unique_sets else 0
        score = round((completeness_rate * 0.5 + uniqueness * 0.5) * 100, 1)
        return {
            "total_rows": total_rows,
            "fields": len(fields),
            "completeness_rate": round(completeness_rate, 4),
            "uniqueness_rate": round(uniqueness, 4),
            "null_counts": null_counts,
            "quality_score": score,
        }
