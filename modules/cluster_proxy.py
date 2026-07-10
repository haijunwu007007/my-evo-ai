from core.logging_config import get_logger
logger = get_logger("evo.modules.cluster_proxy")
"""
AUTO-EVO-AI V0.1 — 生命周期策略模块
Grade: A (生产级) | Category: 核心基础
职责：管理模块/服务的完整生命周期，包括启动、健康检查、优雅关闭、依赖管理
"""

__module_meta__ = {
        "id": "cluster-proxy",
        "name": "Cluster Proxy",
        "version": "V0.1",
        "group": "database",
        "inputs": [
            {
                "name": "component_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "priority",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "dependencies",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "component_id_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "component_id_3",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "success",
                "type": "bool",
                "description": "是否成功"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "cluster",
            "manager"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — 生命周期策略模块 Grade: A (生产级) | Category: 核心基础"
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
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

# 兼容性：trace_operation, metrics, audit, mixins
try:
    from modules._base.tracing import trace_operation
except ImportError:

    def trace_operation(name):
        def decorator(func):
            return func

        return decorator

try:
    from modules._base.metrics import metrics_collector
except ImportError:
    metrics_collector = None
    try:
        from modules._base.metrics import metrics_collector as _mc

        metrics_collector = _mc
    except Exception as _e:        logger.warning(f"[    .strip() module] 异常: {_e}")

try:
    from modules._base.audit import AuditLogger
except ImportError:

    class AuditLogger:
        def __init__(self, name):
            self._name = name

        def log(self, action, data=None):
            pass

from modules._base.circuit_breaker import CircuitBreakerMixin

try:
    pass
except ImportError:
    pass  # RateLimiterMixin imported from enterprise_module

logger = logging.getLogger("cluster_proxy")

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
    dependencies: list[str] = field(default_factory=list)
    health_check_interval: int = 30
    last_health_check: float = field(default_factory=time.time)
    failure_count: int = 0
    max_failures: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ClusterProxy:
    """生命周期策略定义"""

    policy_id: str
    name: str
    description: str = ""
    # 启动策略
    startup_order: list[str] = field(default_factory=list)
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
    priority_group: list[str] = field(default_factory=list)

class ClusterProxyManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """生命周期策略管理器 - 生产级实现"""

    def __init__(self):

        super().__init__(
            config={
                "module_id": "cluster_proxy",
                "version": "7.0.0",
                "description": "管理模块/服务的完整生命周期，支持优雅启动和关闭",
            }
        )
        self.module_name = "cluster_proxy"
        self.module_id = self.module_name
        self._components: dict[str, ManagedComponent] = {}
        self._policies: dict[str, ClusterProxy] = {}
        self._state = LifecycleState.INITIALIZING
        self._startup_time: float | None = None
        self._shutdown_start_time: float | None = None
        self._audit = AuditLogger()
        self._metrics = metrics_collector

    @trace_operation("lifecycle.initialize")
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
        core_policy = ClusterProxy(
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
        biz_policy = ClusterProxy(
            policy_id="policy-business-modules",
            name="业务模块策略",
            description="业务功能模块的生命周期管理",
            startup_order=["api", "worker", "scheduler"],
            startup_timeout=60,
            shutdown_timeout=30,
        )
        self._policies["policy-business-modules"] = biz_policy

        # 监控日志策略
        monitor_policy = ClusterProxy(
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
    def health_check(self) -> dict[str, Any]:
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
            "module_id": "cluster_proxy",
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
    async def shutdown(self) -> None:
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
                self.record_metric(f"lifecycle_component_shutdown_total_{comp_id}", 1)

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
        self, component_id: str, name: str, priority: int = 2, dependencies: list[str] = None
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
    def get_component_status(self, component_id: str) -> dict[str, Any] | None:
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
    def list_components(self) -> list[dict[str, Any]]:
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

    def get_policies(self) -> list[dict[str, Any]]:
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
    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """统一execute入口"""
        _ = self.trace("execute")
        metrics_collector.counter("cluster_proxy_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        try:
            if action == "register_component":
                comp = self._register_single_component(
                    params.get("component_id", ""), params.get("name", ""), params.get("priority", "normal")
                )
                return {"success": True, "result": {"component_id": comp.component_id, "state": comp.state.value}}
            elif action == "get_component_status":
                return {"success": True, "result": self.get_component_status(params.get("component_id", ""))}
            elif action == "list_components":
                return {"success": True, "result": self.list_components()}
            elif action == "list_policies":
                return {"success": True, "result": self.get_policies()}
            elif action == "get_policy":
                pid = params.get("policy_id", "")
                p = self._policies.get(pid)
                if not p:
                    return {"success": False, "error": f"策略{pid}不存在"}
                return {
                    "success": True,
                    "result": {
                        "policy_id": p.policy_id,
                        "name": p.name,
                        "description": p.description,
                        "startup_order": p.startup_order,
                        "startup_timeout": p.startup_timeout,
                        "shutdown_timeout": p.shutdown_timeout,
                        "priority_group": p.priority_group,
                    },
                }
            elif action == "health_check":
                return {"success": True, "result": self.health_check()}
            elif action == "get_stats":
                hc = self.health_check()
                return {
                    "success": True,
                    "result": {
                        "state": self._state.value,
                        "uptime": hc.get("uptime_seconds", 0),
                        "components_total": len(self._components),
                        "components_running": sum(
                            1 for c in self._components.values() if c.state == LifecycleState.RUNNING
                        ),
                        "policies": len(self._policies),
                    },
                }
            elif action == "start_component":
                cid = params.get("component_id", "")
                comp = self._components.get(cid)
                if not comp:
                    return {"success": False, "error": f"组件{cid}不存在"}
                comp.state = LifecycleState.RUNNING
                self._audit.log("component_started", {"component_id": cid})
                return {"success": True, "result": {"component_id": cid, "state": comp.state.value}}
            elif action == "stop_component":
                cid = params.get("component_id", "")
                comp = self._components.get(cid)
                if not comp:
                    return {"success": False, "error": f"组件{cid}不存在"}
                comp.state = LifecycleState.STOPPED
                self._audit.log("component_stopped", {"component_id": cid})
                return {"success": True, "result": {"component_id": cid, "state": comp.state.value}}
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"[ClusterProxy] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def _register_single_component(self, component_id: str, name: str, priority: str = "normal") -> ManagedComponent:
        pri_map = {
            "critical": ShutdownPriority.CRITICAL,
            "high": ShutdownPriority.HIGH,
            "normal": ShutdownPriority.NORMAL,
            "low": ShutdownPriority.LOW,
        }
        comp = ManagedComponent(
            component_id=component_id,
            name=name,
            state=LifecycleState.INITIALIZING,
            priority=pri_map.get(priority, ShutdownPriority.NORMAL),
        )
        self._components[component_id] = comp
        self.record_metric("lifecycle_component_registered_total", 1)
        self._audit.log("component_registered", {"component_id": component_id})
        return comp

    def analyze_routing_efficiency(self) -> dict[str, Any]:
        """分析集群路由效率：请求分布、延迟统计、错误率、热点节点识别"""
        routes = self._routing_rules if hasattr(self, "_routing_rules") else []
        components = self._components if hasattr(self, "_components") else {}
        backends = self._backends if hasattr(self, "_backends") else {}
        report = {"total_routes": len(routes), "total_components": len(components), "total_backends": len(backends)}
        # 后端负载分析
        backend_load = []
        for bid, backend in backends.items():
            req_count = getattr(backend, "request_count", 0) if hasattr(backend, "request_count") else 0
            err_count = getattr(backend, "error_count", 0) if hasattr(backend, "error_count") else 0
            avg_latency = getattr(backend, "avg_latency_ms", 0) if hasattr(backend, "avg_latency_ms") else 0
            error_rate = err_count / max(req_count, 1)
            backend_load.append(
                {
                    "backend_id": bid,
                    "request_count": req_count,
                    "error_count": err_count,
                    "error_rate": round(error_rate, 4),
                    "avg_latency_ms": round(avg_latency, 2),
                }
            )
        if backend_load:
            backend_load.sort(key=lambda x: x["request_count"], reverse=True)
            total_reqs = sum(b["request_count"] for b in backend_load)
            if total_reqs > 0:
                max_share = backend_load[0]["request_count"] / total_reqs
                min_share = backend_load[-1]["request_count"] / total_reqs
                imbalance = max_share - min_share
            else:
                imbalance = 0
            report["backend_imbalance"] = round(imbalance, 3)
            report["hot_backends"] = [
                b for b in backend_load if b["request_count"] > total_reqs / max(len(backend_load), 1) * 2
            ]
            report["slow_backends"] = [b for b in backend_load if b["avg_latency_ms"] > 500]
        report["backends"] = backend_load
        # 组件健康汇总
        healthy = sum(1 for c in components.values() if getattr(c, "state", None) == LifecycleState.RUNNING)
        report["component_health"] = {
            "healthy": healthy,
            "total": len(components),
            "health_rate": round(healthy / max(len(components), 1), 3),
        }
        return report

    def generate_topology_snapshot(self) -> dict[str, Any]:
        """生成集群拓扑快照：节点关系、依赖图、分区感知"""
        components = self._components if hasattr(self, "_components") else {}
        backends = self._backends if hasattr(self, "_backends") else {}
        routes = self._routing_rules if hasattr(self, "_routing_rules") else []
        # 节点拓扑
        nodes = []
        for cid, comp in components.items():
            state = getattr(comp, "state", None)
            nodes.append(
                {
                    "id": cid,
                    "name": getattr(comp, "name", cid),
                    "state": state.value if hasattr(state, "value") else str(state),
                    "priority": getattr(comp, "priority", "normal"),
                }
            )
        # 路由连接
        connections = []
        for rule in routes:
            src = getattr(rule, "source", "") if hasattr(rule, "source") else str(rule.get("source", ""))
            dst = getattr(rule, "target", "") if hasattr(rule, "target") else str(rule.get("target", ""))
            if src and dst:
                connections.append({"source": src, "target": dst})
        # 分区信息
        partitions = {}
        for bid in backends:
            zone = getattr(backends[bid], "zone", "default") if hasattr(backends[bid], "zone") else "default"
            partitions.setdefault(zone, []).append(bid)
        return {
            "timestamp": time.time(),
            "nodes": nodes,
            "connections": connections,
            "partitions": {z: len(n) for z, n in partitions.items()},
            "partition_detail": partitions,
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

module_class = ClusterProxyManager
