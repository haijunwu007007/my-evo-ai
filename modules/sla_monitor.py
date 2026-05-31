"""
AUTO-EVO-AI V0.1 — 生命周期策略模块
Grade: A (生产级) | Category: 核心基础
职责：管理模块/服务的完整生命周期，包括启动、健康检查、优雅关闭、依赖管理
"""

__module_meta__ = {
        "id": "sla-monitor",
        "name": "Sla Monitor",
        "version": "V0.1",
        "group": "monitor",
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
                "name": "hours",
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
        "triggers": [
            {
                "type": "schedule",
                "config": {
                    "cron": "0 */4 * * *"
                }
            },
            {
                "type": "event",
                "config": {
                    "on": "sla_monitor.scan.request"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "monitor",
            "sla",
            "manager"
        ],
        "grade": "B",
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
logger = logging.getLogger("sla_monitor")

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
class SlaMonitor:
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

class SlaMonitorManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """生命周期策略管理器 - 生产级实现"""

    def __init__(self):

        super().__init__()
        self._components: Dict[str, ManagedComponent] = {}
        self._policies: Dict[str, SlaMonitor] = {}
        self._state = LifecycleState.INITIALIZING
        self._startup_time: Optional[float] = None
        self._shutdown_start_time: Optional[float] = None
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
            # return None

        except Exception as e:
            self._state = LifecycleState.FAILED
            logger.error(f"生命周期管理器初始化失败: {e}")
            self.record_metric("lifecycle_initialization_errors_total", 1)
            return False

    def _load_default_policies(self):
        """加载默认生命周期策略"""
        # 核心服务策略
        core_policy = SlaMonitor(
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
        biz_policy = SlaMonitor(
            policy_id="policy-business-modules",
            name="业务模块策略",
            description="业务功能模块的生命周期管理",
            startup_order=["api", "worker", "scheduler"],
            startup_timeout=60,
            shutdown_timeout=30,
        )
        self._policies["policy-business-modules"] = biz_policy

        # 监控日志策略
        monitor_policy = SlaMonitor(
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
        """统一execute入口"""
        _ = self.trace("execute")
        metrics_collector.counter("sla_monitor_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        try:
            if action == "register_component":
                comp = self.register_component(
                    params.get("component_id", ""), params.get("name", ""), params.get("priority", 2)
                )
                return {"success": True, "result": {"component_id": comp.component_id, "state": comp.state.value}}
            elif action == "get_component_status":
                st = self.get_component_status(params.get("component_id", ""))
                if not st:
                    return {"success": False, "error": "组件不存在"}
                return {"success": True, "result": st}
            elif action == "list_components":
                return {"success": True, "result": self.list_components()}
            elif action == "list_policies":
                return {"success": True, "result": self.get_policies()}
            elif action == "get_stats":
                hc = self.health_check()
                return {
                    "success": True,
                    "result": {"state": self._state.value, "components": len(self._components), **hc},
                }
            elif action == "health_check":
                return {"success": True, "result": self.health_check()}
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

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
            "module_id": "sla_monitor",
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
            return

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
        # return None

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
            # return None

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

    def compute_sla_compliance(self, hours: int = 24) -> Dict[str, Any]:
        """计算SLA合规率：按策略统计可用性、违规次数、累计中断时长"""
        policies = self._policies if hasattr(self, "_policies") else {}
        incidents = self._incidents if hasattr(self, "_incidents") else []
        cutoff = time.time() - hours * 3600
        recent_incidents = [i for i in incidents if isinstance(i, dict) and i.get("timestamp", 0) >= cutoff]
        results = {}
        total_target_uptime = hours * 3600
        for pid, policy in policies.items():
            name = getattr(policy, "name", "") or policy.get("name", pid) if isinstance(policy, dict) else pid
            target = getattr(policy, "availability_target", 99.9) or policy.get("availability_target", 99.9)
            policy_incidents = [i for i in recent_incidents if isinstance(i, dict) and i.get("policy_id", "") == pid]
            total_downtime = sum(i.get("duration_seconds", 0) for i in policy_incidents)
            actual_uptime = max(0, total_target_uptime - total_downtime)
            availability = (actual_uptime / total_target_uptime) * 100
            violation_count = len([i for i in policy_incidents if i.get("is_violation", False)])
            results[pid] = {
                "name": name,
                "target_availability": target,
                "actual_availability": round(availability, 4),
                "met_sla": availability >= target,
                "violation_count": violation_count,
                "total_incidents": len(policy_incidents),
                "total_downtime_seconds": total_downtime,
                "total_downtime_minutes": round(total_downtime / 60, 1),
                "window_hours": hours,
            }
        return {"window_hours": hours, "policies": results}

    def generate_breach_alert(self, policy_id: str) -> Dict[str, Any]:
        """生成SLA违规告警：包含违规详情、影响评估、修复建议"""
        policies = self._policies if hasattr(self, "_policies") else {}
        policy = policies.get(policy_id)
        if not policy:
            return {"error": "policy not found", "policy_id": policy_id}
        name = getattr(policy, "name", policy_id)
        target = getattr(policy, "availability_target", 99.9)
        # 最近24h合规情况
        compliance = self.compute_sla_compliance(hours=24)
        policy_data = compliance.get("policies", {}).get(policy_id, {})
        actual = policy_data.get("actual_availability", 100)
        gap = target - actual
        # 影响评估
        if gap > 5:
            severity = "P1"
            impact = "严重影响业务连续性，可能导致合同违约和经济损失"
        elif gap > 1:
            severity = "P2"
            impact = "SLA未达标，需要紧急干预以防止进一步恶化"
        elif gap > 0:
            severity = "P3"
            impact = "SLA接近阈值，需要关注趋势并预防违规"
        else:
            severity = "OK"
            impact = "SLA达标，当前无违规风险"
        # 修复建议
        if severity == "P1":
            suggestion = "立即启动应急响应：1)识别根因 2)切换备用服务 3)通知利益相关方"
        elif severity == "P2":
            suggestion = "在2小时内完成根因分析并启动修复，考虑临时增加冗余"
        elif severity == "P3":
            suggestion = "加强监控频率，检查是否存在性能退化趋势，准备应急预案"
        else:
            suggestion = "继续保持当前运维策略"
        return {
            "policy_id": policy_id,
            "name": name,
            "severity": severity,
            "target": target,
            "actual": actual,
            "gap": round(gap, 4),
            "impact": impact,
            "suggestion": suggestion,
            "incidents_count": policy_data.get("total_incidents", 0),
            "total_downtime_minutes": policy_data.get("total_downtime_minutes", 0),
            "timestamp": time.time(),
        }

    def analyze_incident_trends(self, days: int = 7) -> Dict[str, Any]:
        """分析SLA事件趋势：按日/按策略统计，识别恶化或改善趋势"""
        incidents = self._incidents if hasattr(self, "_incidents") else []
        cutoff = time.time() - days * 86400
        recent = [i for i in incidents if isinstance(i, dict) and i.get("timestamp", 0) >= cutoff]
        # 按日分组
        daily_counts: Dict[str, int] = {}
        daily_violations: Dict[str, int] = {}
        for inc in recent:
            ts = inc.get("timestamp", 0)
            day_key = time.strftime("%Y-%m-%d", time.localtime(ts))
            daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
            if inc.get("is_violation", False):
                daily_violations[day_key] = daily_violations.get(day_key, 0) + 1
        # 按策略分组
        policy_counts: Dict[str, int] = {}
        for inc in recent:
            pid = inc.get("policy_id", "unknown")
            policy_counts[pid] = policy_counts.get(pid, 0) + 1
        # 趋势判断
        daily_list = sorted(daily_counts.values()) if daily_counts else [0]
        if len(daily_list) >= 4:
            first_half_avg = sum(daily_list[: len(daily_list) // 2]) / (len(daily_list) // 2)
            second_half_avg = sum(daily_list[len(daily_list) // 2 :]) / (len(daily_list) - len(daily_list) // 2)
            if second_half_avg > first_half_avg * 1.5:
                trend = "worsening"
            elif second_half_avg < first_half_avg * 0.7:
                trend = "improving"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        return {
            "period_days": days,
            "total_incidents": len(recent),
            "total_violations": sum(daily_violations.values()),
            "daily_incidents": daily_counts,
            "daily_violations": daily_violations,
            "incidents_by_policy": policy_counts,
            "trend": trend,
            "top_policy": max(policy_counts.items(), key=lambda x: x[1])[0] if policy_counts else None,
        }

    def export_compliance_report(self, period_days: int = 30) -> Dict[str, Any]:
        """导出SLA合规报告：月度汇总、达标率、罚金风险估算"""
        compliance = self.compute_sla_compliance(hours=period_days * 24)
        policies = compliance.get("policies", {})
        total_policies = len(policies)
        met_count = sum(1 for p in policies.values() if p.get("met_sla", False))
        # 计算加权平均可用性
        weighted_availability = 0
        for p in policies.values():
            target = p.get("target_availability", 99.9)
            actual = p.get("actual_availability", 100)
            weight = 1.0 / max(target, 0.01)
            weighted_availability += actual * weight
        if total_policies > 0:
            avg_availability = weighted_availability / (
                sum(1.0 / max(p.get("target_availability", 99.9), 0.01) for p in policies.values())
            )
        else:
            avg_availability = 100
        # 罚金风险估算（假设每低1%扣$1000/天）
        worst_gap = max(
            (p.get("target_availability", 99.9) - p.get("actual_availability", 100) for p in policies.values()),
            default=0,
        )
        penalty_days = max(0, worst_gap * period_days / 100)
        estimated_penalty = round(penalty_days * 1000, 2) if worst_gap > 0 else 0
        return {
            "report_period_days": period_days,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_policies": total_policies,
            "policies_met_sla": met_count,
            "overall_compliance_rate": round(met_count / max(total_policies, 1) * 100, 1),
            "weighted_avg_availability": round(avg_availability, 4),
            "worst_policy_gap": round(worst_gap, 4),
            "estimated_penalty_risk_usd": estimated_penalty,
            "policy_details": policies,
        }

    # 模块导出

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

module_class = SlaMonitorManager
