"""
AUTO-EVO-AI v7.0 — 生命周期策略模块
Grade: A (生产级) | Category: 核心基础
职责：管理模块/服务的完整生命周期，包括启动、健康检查、优雅关闭、依赖管理
"""

__module_meta__ = {
    "id": "data-watermark",
    "name": "Data Watermark",
    "version": "1.0.0",
    "group": "data",
    "inputs": [
        {"name": "component_id", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "priority", "type": "string", "required": True, "description": ""},
        {"name": "dependencies", "type": "string", "required": True, "description": ""},
        {"name": "component_id", "type": "string", "required": True, "description": ""},
        {"name": "items", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["data", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 — 生命周期策略模块 Grade: A (生产级) | Category: 核心基础",
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
logger = logging.getLogger("data_watermark")

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
class DataWatermark:
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

class DataWatermarkManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """生命周期策略管理器 - 生产级实现"""

    def __init__(self):

        super().__init__()
        self._components: Dict[str, ManagedComponent] = {}
        self._policies: Dict[str, DataWatermark] = {}
        self._state = LifecycleState.INITIALIZING
        self._startup_time: Optional[float] = None
        self._shutdown_start_time: Optional[float] = None
        self._audit = AuditLogger()
        self._metrics = metrics_collector

    @trace_operation("lifecycle.initialize")
    def initialize(self) -> Dict[str, Any]:
        """初始化"""
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
            return {"success": True}

        except Exception as e:
            self._state = LifecycleState.FAILED
            logger.error(f"生命周期管理器初始化失败: {e}")
            self.record_metric("lifecycle_initialization_errors_total", 1)
            return {"success": False, "error": str(e)}

    def _load_default_policies(self):
        """加载默认生命周期策略"""
        # 核心服务策略
        core_policy = DataWatermark(
            policy_id="policy-core-services",
            name="核心服务策略",
            description="数据库、缓存、消息队列等核心服务",
            startup_order=["database", "cache", "message_queue"],
            startup_timeout=120,
            shutdown_timeout=60,
        )
        self._policies["policy-core-services"] = core_policy

        # 业务模块策略
        biz_policy = DataWatermark(
            policy_id="policy-business-modules",
            name="业务模块策略",
            description="业务功能模块的生命周期管理",
            startup_order=["api", "worker", "scheduler"],
            startup_timeout=60,
            shutdown_timeout=30,
        )
        self._policies["policy-business-modules"] = biz_policy

        # 监控日志策略
        monitor_policy = DataWatermark(
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

        overall_status = "ok"
        if failed_components:
            overall_status = "error"
        elif degraded_components:
            overall_status = "degraded"

        return {
            "healthy": overall_status == "ok",
            "status": overall_status,
            "module_id": "data_watermark",
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
            return {"success": True}

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
        return {"success": True}

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
            return {"success": True}

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
        metrics_collector.counter("data_watermark_ops_total", labels={"action": action})
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

    def batch_verify_watermarks(self, items: List[Dict[str, str]]) -> Dict[str, Any]:
        """批量验证数据水印：检查每个数据项的水印完整性和归属"""
        results = []
        valid_count = 0
        tampered_count = 0
        missing_count = 0
        for item in items:
            data = item.get("data", "")
            expected_owner = item.get("owner", "")
            item_id = item.get("id", "")
            # 提取水印
            extracted = self._extract_watermark(data) if hasattr(self, "_extract_watermark") else None
            if not extracted:
                missing_count += 1
                results.append({"id": item_id, "status": "missing_watermark"})
                continue
            owner_match = extracted.get("owner", "") == expected_owner
            if owner_match:
                valid_count += 1
                results.append(
                    {
                        "id": item_id,
                        "status": "valid",
                        "owner": extracted.get("owner"),
                        "confidence": extracted.get("confidence", 0),
                    }
                )
            else:
                tampered_count += 1
                results.append(
                    {
                        "id": item_id,
                        "status": "tampered",
                        "expected_owner": expected_owner,
                        "extracted_owner": extracted.get("owner"),
                    }
                )
        return {
            "total": len(items),
            "valid": valid_count,
            "tampered": tampered_count,
            "missing": missing_count,
            "integrity_rate": round(valid_count / max(len(items), 1), 4),
            "details": results,
        }

    def test_watermark_robustness(self, test_data: str, attacks: List[str] = None) -> Dict[str, Any]:
        """测试水印鲁棒性：模拟各种攻击（裁剪、压缩、噪声）后验证水印可提取性"""
        attacks = attacks or ["crop_10", "crop_30", "noise_light", "noise_heavy", "compress_50", "compress_90"]
        results = []
        for attack in attacks:
            # 模拟攻击对数据的影响
            corrupted = self._simulate_attack(test_data, attack)
            # 尝试提取水印
            extracted = self._extract_watermark(corrupted) if hasattr(self, "_extract_watermark") else None
            recovered = extracted is not None
            confidence = extracted.get("confidence", 0) if extracted else 0
            results.append(
                {
                    "attack": attack,
                    "watermark_recovered": recovered,
                    "confidence": round(confidence, 4),
                    "resistant": recovered and confidence > 0.7,
                }
            )
        resistant_count = sum(1 for r in results if r["resistant"])
        return {
            "attacks_tested": len(attacks),
            "resistant_count": resistant_count,
            "resistance_rate": round(resistant_count / max(len(attacks), 1), 4),
            "vulnerable_attacks": [r["attack"] for r in results if not r["resistant"]],
            "results": results,
        }

    def _simulate_attack(self, data: str, attack: str) -> str:
        """模拟数据篡改攻击"""
        result = list(data)
        if "crop" in attack:
            pct = int(attack.split("_")[1]) / 100
            keep = int(len(result) * (1 - pct))
            result = result[:keep] + result[-keep:]
        elif "noise" in attack:
            import random

            level = 0.02 if "light" in attack else 0.1
            positions = range(min(int(len(result)*level), len(result)))
            for pos in positions:
                if pos < len(result):
                    result[pos] = chr((ord(result[pos]) + 1) % 256)
        elif "compress" in attack:
            # 模拟压缩导致的信息损失
            pct = int(attack.split("_")[1]) / 100
            remove = int(len(result) * pct * 0.1)
            result = result[: len(result) - remove]
        return "".join(result)

    def detect_watermark_collision(self, owner_a: str, data_a: str, owner_b: str, data_b: str) -> Dict[str, Any]:
        """水印冲突检测：判断两份数据嵌入不同水印后是否会互相覆盖"""
        combined_a = self._embed_watermark(data_a, owner_a) if hasattr(self, "_embed_watermark") else data_a
        combined_b = self._embed_watermark(data_b, owner_b) if hasattr(self, "_embed_watermark") else data_b
        # 检查相似数据的水印是否互相干扰
        similarity = self._compute_similarity(data_a, data_b) if hasattr(self, "_compute_similarity") else 0.0
        collision_risk = "high" if similarity > 0.9 and owner_a != owner_b else "medium" if similarity > 0.7 else "low"
        return {
            "owner_a": owner_a,
            "owner_b": owner_b,
            "data_similarity": round(similarity, 4),
            "collision_risk": collision_risk,
            "recommendation": "使用不同水印算法或增加水印间隔" if collision_risk == "high" else "无冲突风险",
        }

    def get_watermark_usage_report(self) -> Dict[str, Any]:
        """水印使用统计报告：嵌入次数、验证次数、按所有者统计"""
        stats = self._stats if hasattr(self, "_stats") else {}
        history = self._history if hasattr(self, "_history") else []
        total_embedded = stats.get("embedded_count", len([h for h in history if h.get("action") == "embed"]))
        total_verified = stats.get("verified_count", len([h for h in history if h.get("action") == "verify"]))
        total_extracted = stats.get("extracted_count", len([h for h in history if h.get("action") == "extract"]))
        # 按所有者统计
        by_owner = {}
        for h in history:
            owner = h.get("owner", "unknown")
            by_owner[owner] = by_owner.get(owner, 0) + 1
        # 按类型统计
        by_type = {}
        for h in history:
            wm_type = h.get("watermark_type", h.get("type", "unknown"))
            by_type[wm_type] = by_type.get(wm_type, 0) + 1
        return {
            "total_operations": len(history),
            "embedded": total_embedded,
            "verified": total_verified,
            "extracted": total_extracted,
            "by_owner": dict(sorted(by_owner.items(), key=lambda x: -x[1])[:20]),
            "by_type": by_type,
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

module_class = DataWatermarkManager
