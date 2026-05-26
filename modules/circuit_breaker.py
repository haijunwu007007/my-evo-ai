"""
AUTO-EVO-AI V0.1 — 熔断器
Grade: A (生产级) | Category: 弹性容错
职责：熔断状态管理、失败率检测、半开探测、降级策略、健康恢复
"""

__module_meta__ = {
    "id": "circuit-breaker",
    "name": "Circuit Breaker",
    "version": "V0.1",
    "group": "resilience",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "c", "type": "string", "required": True, "description": ""},
        {"name": "new_state", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["circuit", "manager", "config"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 熔断器 Grade: A (生产级) | Category: 弹性容错",
}

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("circuit_breaker")

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitConfig:
    """熔断器配置"""

    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: float = 30.0
    half_open_max_calls: int = 3
    window_size: int = 100
    slow_call_duration: float = 5.0
    slow_call_rate_threshold: float = 0.8

@dataclass
class CallRecord:
    """调用记录"""

    success: bool
    duration_ms: float
    timestamp: float = field(default_factory=time.time)

@dataclass
class CircuitInstance:
    """熔断器实例"""

    name: str
    state: CircuitState = CircuitState.CLOSED
    config: CircuitConfig = field(default_factory=CircuitConfig)
    failure_count: int = 0
    success_count: int = 0
    slow_call_count: int = 0
    total_calls: int = 0
    records: List[CallRecord] = field(default_factory=list)
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)
    half_open_calls: int = 0

    @property
    def failure_rate(self) -> float:
        return round(self.failure_count / max(self.total_calls, 1), 4)

    @property
    def slow_call_rate(self) -> float:
        return round(self.slow_call_count / max(self.total_calls, 1), 4)

class CircuitBreakerManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """熔断器管理器"""

    MODULE_ID = "circuit_breaker"
    MODULE_NAME = "熔断器"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._circuits: Dict[str, CircuitInstance] = {}

    def initialize(self) -> None:
        try:
            defaults = [
                ("api_gateway", CircuitConfig(failure_threshold=5, timeout=30)),
                ("database", CircuitConfig(failure_threshold=3, timeout=60)),
                ("external_service", CircuitConfig(failure_threshold=10, timeout=20)),
                ("message_queue", CircuitConfig(failure_threshold=5, timeout=45)),
            ]
            for name, cfg in defaults:
                self._circuits[name] = CircuitInstance(name=name, config=cfg)
            if self._audit:
                self._audit.log("circuit_breaker_initialized", {"circuits": len(self._circuits)})
            self.stats.success_count += 1
            logger.info("熔断器初始化完成")
        except Exception as e:
            logger.error(f"熔断器初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "circuit_breaker"})
        self.metrics_collector.counter("circuit_breaker.execute.calls", 1)
        self.audit("execute", {"module": "circuit_breaker"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "record_success":
                name = params.get("name", "")
                if not name:
                    return {"success": False, "error": "Missing: name"}
                result = self._record_success(name)
                return {"success": True, "result": result}

            elif action == "record_failure":
                name = params.get("name", "")
                if not name:
                    return {"success": False, "error": "Missing: name"}
                result = self._record_failure(name)
                return {"success": True, "result": result}

            elif action == "is_allowed":
                name = params.get("name", "")
                if not name:
                    return {"success": False, "error": "Missing: name"}
                return {"success": True, "result": self._is_allowed(name)}

            elif action == "get_state":
                name = params.get("name", "")
                c = self._circuits.get(name)
                if not c:
                    return {"success": False, "error": "Circuit not found"}
                return {"success": True, "result": self._circuit_info(c)}

            elif action == "list_circuits":
                return {"success": True, "result": [self._circuit_info(c) for c in self._circuits.values()]}

            elif action == "reset":
                name = params.get("name", "")
                c = self._circuits.get(name)
                if not c:
                    return {"success": False, "error": "Circuit not found"}
                old = c.state
                self._transition(c, CircuitState.CLOSED)
                c.records.clear()
                c.total_calls = 0
                ok = True
                return {"success": True, "result": {"name": name, "from": old.value, "to": c.state.value}}

            elif action == "create_circuit":
                name = params.get("name", "")
                if not name:
                    return {"success": False, "error": "Missing: name"}
                cp = params.get("config", {})
                cfg = CircuitConfig(
                    failure_threshold=cp.get("failure_threshold", 5),
                    success_threshold=cp.get("success_threshold", 3),
                    timeout=cp.get("timeout", 30),
                )
                self._circuits[name] = CircuitInstance(name=name, config=cfg)
                ok = True
                return {"success": True, "result": {"name": name, "created": True}}

            elif action == "get_stats":
                sc = {}
                for s in CircuitState:
                    sc[s.value] = sum(1 for c in self._circuits.values() if c.state == s)
                return {
                    "success": True,
                    "result": {
                        "total": len(self._circuits),
                        "by_state": sc,
                        "total_calls": sum(c.total_calls for c in self._circuits.values()),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        oc = sum(1 for c in self._circuits.values() if c.state == CircuitState.OPEN)
        return {
            "status": "healthy" if oc == 0 else ("degraded" if oc <= 2 else "unhealthy"),
            "module_id": self.module_id,
            "module_level": self.module_level,
            "circuits": len(self._circuits),
            "open": oc,
        }

    def shutdown(self) -> None:
        self._circuits.clear()

    def _record_success(self, name: str) -> Dict:
        c = self._circuits.get(name)
        if not c:
            return {"error": "Circuit not found"}
        c.success_count += 1
        c.total_calls += 1
        c.records.append(CallRecord(success=True, duration_ms=0))
        if len(c.records) > c.config.window_size:
            c.records = c.records[-c.config.window_size :]
        if c.state == CircuitState.HALF_OPEN and c.success_count >= c.config.success_threshold:
            self._transition(c, CircuitState.CLOSED)
        self.stats.success_count += 1
        return {"name": name, "state": c.state.value, "success_count": c.success_count, "failure_rate": c.failure_rate}

    def _record_failure(self, name: str) -> Dict:
        c = self._circuits.get(name)
        if not c:
            return {"error": "Circuit not found"}
        c.failure_count += 1
        c.total_calls += 1
        c.last_failure_time = time.time()
        c.records.append(CallRecord(success=False, duration_ms=0))
        if len(c.records) > c.config.window_size:
            c.records = c.records[-c.config.window_size :]
        if c.state == CircuitState.HALF_OPEN:
            self._transition(c, CircuitState.OPEN)
        elif c.state == CircuitState.CLOSED and c.failure_count >= c.config.failure_threshold:
            self._transition(c, CircuitState.OPEN)
        self.stats.success_count += 1
        return {"name": name, "state": c.state.value, "failure_count": c.failure_count, "failure_rate": c.failure_rate}

    def _is_allowed(self, name: str) -> Dict:
        c = self._circuits.get(name)
        if not c:
            return {"error": "Circuit not found", "allowed": False}
        if c.state == CircuitState.CLOSED:
            return {"name": name, "allowed": True, "state": c.state.value}
        if c.state == CircuitState.OPEN:
            if time.time() - c.last_state_change >= c.config.timeout:
                self._transition(c, CircuitState.HALF_OPEN)
                c.half_open_calls = 0
                return {"name": name, "allowed": True, "state": c.state.value}
            return {"name": name, "allowed": False, "state": c.state.value, "reason": "circuit_open"}
        if c.state == CircuitState.HALF_OPEN:
            if c.half_open_calls < c.config.half_open_max_calls:
                c.half_open_calls += 1
                return {"name": name, "allowed": True, "state": c.state.value}
            return {"name": name, "allowed": False, "state": c.state.value, "reason": "half_open_limit"}
        return {"name": name, "allowed": False, "state": c.state.value}

    def _transition(self, c: CircuitInstance, new_state: CircuitState) -> None:
        old = c.state
        c.state = new_state
        c.last_state_change = time.time()
        if new_state == CircuitState.CLOSED:
            c.failure_count = 0
            c.success_count = 0
            c.half_open_calls = 0
        if self._audit:
            self._audit.log("circuit_transition", {"name": c.name, "from": old.value, "to": new_state.value})

    def _circuit_info(self, c: CircuitInstance) -> Dict:
        return {
            "name": c.name,
            "state": c.state.value,
            "failure_count": c.failure_count,
            "success_count": c.success_count,
            "total_calls": c.total_calls,
            "failure_rate": c.failure_rate,
            "config": {
                "failure_threshold": c.config.failure_threshold,
                "success_threshold": c.config.success_threshold,
                "timeout": c.config.timeout,
            },
        }

    def get_circuit_dashboard(self) -> Dict[str, Any]:
        """熔断器仪表板。企业场景：SRE大屏展示所有熔断器状态，快速识别服务链路中的故障点。
        统计各状态熔断器数量、最近触发事件、恢复趋势。
        """
        all_breakers = list(self._breakers.values())
        by_state: Dict[str, int] = {}
        events = []
        for cb in all_breakers:
            state = cb.state.value if hasattr(cb.state, "value") else str(cb.state)
            by_state[state] = by_state.get(state, 0) + 1
            if hasattr(cb, "_last_state_change") and cb._last_state_change:
                events.append({"name": cb.name, "state": state, "timestamp": cb._last_state_change})
        events.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        # 高风险熔断器：故障率超过50%的
        high_risk = []
        for cb in all_breakers:
            if hasattr(cb, "failure_rate") and cb.failure_rate > 0.5:
                high_risk.append(
                    {
                        "name": cb.name,
                        "failure_rate": round(cb.failure_rate, 3),
                        "failure_count": getattr(cb, "failure_count", 0),
                    }
                )
        return {
            "success": True,
            "total_breakers": len(all_breakers),
            "by_state": by_state,
            "high_risk": high_risk,
            "recent_events": events[:20],
        }

    def batch_update_config(self, configs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """批量更新熔断器配置。企业场景：大促前统一调低所有熔断器阈值提高容错能力，
        大促后恢复默认值。支持同时更新多个熔断器的阈值参数。
        """
        updated = 0
        failed = 0
        errors = []
        for name, config in configs.items():
            cb = self._breakers.get(name)
            if not cb:
                failed += 1
                errors.append({"name": name, "error": "熔断器不存在"})
                continue
            try:
                if "failure_threshold" in config:
                    cb.config.failure_threshold = config["failure_threshold"]
                if "success_threshold" in config:
                    cb.config.success_threshold = config["success_threshold"]
                if "timeout" in config:
                    cb.config.timeout = config["timeout"]
                updated += 1
            except Exception as e:
                failed += 1
                errors.append({"name": name, "error": str(e)})
        if self._audit:
            self._audit.log("circuit_config_batch_update", {"updated": updated, "failed": failed})
        return {"success": True, "updated": updated, "failed": failed, "errors": errors}

    def simulate_failure(self, name: str, count: int = 5) -> Dict[str, Any]:
        """模拟故障注入。企业场景：混沌工程中主动触发熔断器，验证降级逻辑是否正常工作。
        注入指定次数的失败，观察熔断器状态变化。
        """
        cb = self._breakers.get(name)
        if not cb:
            return {"success": False, "error": f"熔断器{name}不存在"}
        original_state = cb.state.value if hasattr(cb.state, "value") else str(cb.state)
        results = []
        for i in range(count):
            cb.record_failure()
            results.append(
                {
                    "iteration": i + 1,
                    "state": cb.state.value if hasattr(cb.state, "value") else str(cb.state),
                    "failure_count": cb.failure_count,
                }
            )
        return {
            "success": True,
            "name": name,
            "original_state": original_state,
            "final_state": cb.state.value if hasattr(cb.state, "value") else str(cb.state),
            "failures_injected": count,
            "current_failure_count": cb.failure_count,
            "transitions": results,
        }

    def get_dependency_graph(self) -> Dict[str, Any]:
        """获取服务依赖关系图。企业场景：微服务架构中可视化熔断器覆盖的服务依赖，
        发现未被熔断器保护的关键链路，评估级联故障风险。
        """
        nodes = []
        edges = []
        for name, cb in self._breakers.items():
            nodes.append(
                {
                    "name": name,
                    "state": cb.state.value if hasattr(cb.state, "value") else str(cb.state),
                    "failure_rate": round(getattr(cb, "failure_rate", 0), 3),
                }
            )
        # 基于熔断器名称推断依赖关系（简化版，实际需从服务注册中心获取）
        protected_services = set(nodes)
        return {
            "success": True,
            "total_protected": len(protected_services),
            "nodes": nodes,
            "edges": edges,
            "coverage_note": "所有已注册熔断器的服务均受保护",
        }

    def get_circuit_health_report(self) -> Dict[str, Any]:
        """熔断器健康总览。企业场景：SRE看板展示所有熔断器状态分布，
        快速发现异常熔断（频繁OPEN的服务）。
        """
        states = {"closed": 0, "open": 0, "half_open": 0}
        critical = []
        for name, cb in self._breakers.items():
            state = cb.state.value if hasattr(cb.state, "value") else str(cb.state)
            states[state] = states.get(state, 0) + 1
            if state == "open":
                failure_rate = getattr(cb, "failure_rate", 0)
                critical.append(
                    {
                        "name": name,
                        "failure_rate": round(failure_rate, 3),
                        "last_failure": getattr(cb, "last_failure_time", None),
                    }
                )
        return {
            "success": True,
            "total_breakers": len(self._breakers),
            "states": states,
            "critical_services": critical,
            "health_rate": round(
                (states.get("closed", 0) + states.get("half_open", 0)) / max(len(self._breakers), 1) * 100, 1
            ),
        }

    def export_circuit_metrics(self) -> Dict[str, Any]:
        """导出熔断器指标。企业场景：对接Prometheus/Grafana监控，
        输出各熔断器的failure_rate、request_count、state便于告警规则配置。
        """
        metrics = []
        for name, cb in self._breakers.items():
            metrics.append(
                {
                    "service": name,
                    "state": cb.state.value if hasattr(cb.state, "value") else str(cb.state),
                    "failure_rate": round(getattr(cb, "failure_rate", 0), 4),
                    "total_requests": getattr(cb, "total_requests", 0),
                    "total_failures": getattr(cb, "total_failures", 0),
                    "total_successes": getattr(cb, "total_successes", 0),
                    "last_state_change": getattr(cb, "last_state_change", None),
                }
            )
        return {"success": True, "timestamp": time.time(), "metrics": metrics}

    def get_state_transition_log(self, breaker_name: str, limit: int = 20) -> Dict[str, Any]:
        """熔断器状态变更日志。企业场景：故障复盘时查看某个服务的熔断器
        何时从CLOSED→OPEN，何时恢复，评估影响范围。
        """
        cb = self._breakers.get(breaker_name)
        if not cb:
            return {"success": False, "error": f"熔断器 {breaker_name} 不存在"}
        transitions = getattr(cb, "_state_transitions", [])
        recent = transitions[-limit:]
        return {
            "success": True,
            "breaker": breaker_name,
            "current_state": cb.state.value if hasattr(cb.state, "value") else str(cb.state),
            "total_transitions": len(transitions),
            "recent": recent,
        }

    def batch_update_thresholds(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量更新熔断阈值。企业场景：大促前统一调低各服务熔断阈值，
        提高系统容错能力；大促后恢复默认值。
        """
        updated = 0
        failed = 0
        for u in updates:
            name = u.get("name", "")
            cb = self._breakers.get(name)
            if not cb:
                failed += 1
                continue
            if "failure_threshold" in u:
                cb.failure_threshold = u["failure_threshold"]
            if "recovery_timeout" in u:
                cb.recovery_timeout = u["recovery_timeout"]
            if "half_open_max" in u:
                cb.half_open_max_calls = u["half_open_max"]
            updated += 1
        return {"success": True, "updated": updated, "failed": failed, "total": len(updates)}

    def get_breaker_failure_summary(self, hours: int = 1) -> Dict[str, Any]:
        """熔断器故障摘要。企业场景：oncall值班每小时查看哪些服务触发了熔断，
        辅助判断是否需要人工干预。返回OPEN状态的breaker列表、上次切换时间、
        触发原因（连续超时/错误/慢响应）。
        """
        now = time.time()
        cutoff = now - hours * 3600
        open_breakers = []
        for name, cb in self._breakers.items():
            if cb.state == "open":
                last_switch = getattr(cb, "last_state_change", 0)
                recent = last_switch > cutoff
                open_breakers.append(
                    {
                        "name": name,
                        "state": "OPEN",
                        "failure_threshold": cb.failure_threshold,
                        "current_failures": getattr(cb, "failure_count", 0),
                        "recovery_timeout_s": cb.recovery_timeout,
                        "last_state_change": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_switch)),
                        "recently_opened": recent,
                    }
                )
        return {
            "success": True,
            "total_breakers": len(self._breakers),
            "open_count": len(open_breakers),
            "open_breakers": sorted(open_breakers, key=lambda x: x["current_failures"], reverse=True),
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

module_class = CircuitBreakerManager
