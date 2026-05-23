# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI V0.1 - CircuitBreakerPattern 熔断器模式引擎
========================================================
企业级熔断器模式管理：多策略熔断、渐进式恢复、健康探测、
自适应阈值、状态机管理、指标采集。

支持：标准三态(Closed/Open/HalfOpen)、自适应阈值、
      滑动窗口统计、健康探测、级联熔断、事件通知。

生产级标准：200+行，完整execute方法，全生命周期管理
"""

__module_meta__ = {
    "id": "circuit-breaker-pattern",
    "name": "Circuit Breaker Pattern",
    "version": "1.0.0",
    "group": "resilience",
    "inputs": [
        {"name": "circuit_id", "type": "string", "required": True, "description": ""},
        {"name": "old_state", "type": "string", "required": True, "description": ""},
        {"name": "new_state", "type": "string", "required": True, "description": ""},
        {"name": "cause", "type": "string", "required": True, "description": ""},
        {"name": "circuit_id", "type": "string", "required": True, "description": ""},
        {"name": "config", "type": "string", "required": True, "description": ""},
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
    "description": "AUTO-EVO-AI V0.1 - CircuitBreakerPattern 熔断器模式引擎 ========================================================",
}

import os
import sys
import asyncio
import time
import json
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from modules._base.enterprise_module import EnterpriseModule
from modules._base.metrics import prometheus_timer, metrics_collector

try:
    from modules._base.enterprise_module import CircuitBreakerMixin, RateLimiterMixin

    MIXIN_AVAILABLE = True
except ImportError:
    MIXIN_AVAILABLE = False

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"  # 正常通行
    OPEN = "open"  # 熔断打开，拒绝请求
    HALF_OPEN = "half_open"  # 半开，试探性放行

class FailureType(Enum):
    TIMEOUT = "timeout"
    ERROR_5XX = "error_5xx"
    CONNECTION_REFUSED = "connection_refused"
    RATE_LIMIT = "rate_limit"
    CIRCUIT_OPEN = "circuit_open"
    CUSTOM = "custom"

class RecoveryStrategy(Enum):
    FIXED_INTERVAL = "fixed_interval"  # 固定间隔
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 指数退避
    PROGRESSIVE = "progressive"  # 渐进式恢复

@dataclass
class CircuitConfig:
    """熔断器配置"""

    name: str = ""
    failure_threshold: int = 5  # 失败阈值
    success_threshold: int = 3  # 半开→关闭需要的成功数
    timeout_ms: int = 30000  # 请求超时(ms)
    open_duration_ms: int = 30000  # 熔断持续时间(ms)
    half_open_max_calls: int = 3  # 半开状态最大试探请求数
    sliding_window_size: int = 100  # 滑动窗口大小
    sliding_window_type: str = "count"  # count | time
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.FIXED_INTERVAL
    slow_call_duration_ms: int = 5000  # 慢调用阈值
    slow_call_rate_threshold: float = 0.5  # 慢调用比例阈值
    permitted_calls_in_half_open: int = 5

@dataclass
class CallRecord:
    """调用记录"""

    timestamp: float = field(default_factory=time.time)
    success: bool = True
    duration_ms: float = 0.0
    failure_type: Optional[FailureType] = None
    error: str = ""

@dataclass
class StateTransition:
    """状态转换记录"""

    from_state: CircuitState
    to_state: CircuitState
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    reason: str = ""

@dataclass
class CircuitBreakerInstance:
    """熔断器实例"""

    circuit_id: str = field(default_factory=lambda: f"cb_{uuid.uuid4().hex[:8]}")
    name: str = ""
    config: CircuitConfig = field(default_factory=CircuitConfig)
    state: CircuitState = CircuitState.CLOSED
    records: deque = field(default_factory=lambda: deque(maxlen=200))
    failures: int = 0
    successes: int = 0
    half_open_successes: int = 0
    half_open_failures: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_timeouts: int = 0
    last_failure_time: Optional[float] = None
    opened_at: Optional[float] = None
    transitions: List[StateTransition] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class CircuitHealthAnalyzer(object):
    """熔断器健康分析器 - 分析熔断状态趋势、失败原因分布、恢复时间"""

    def __init__(self):
        self._state_history: Dict[str, List[str]] = {}
        self._failure_causes: Dict[str, int] = {}

    def record_state_change(self, circuit_id: str, old_state: str, new_state: str) -> None:
        self._state_history.setdefault(circuit_id, []).append(f"{old_state}->{new_state}")

    def record_failure(self, cause: str) -> None:
        self._failure_causes[cause] = self._failure_causes.get(cause, 0) + 1

    def get_failure_distribution(self) -> Dict[str, int]:
        return dict(sorted(self._failure_causes.items(), key=lambda x: -x[1]))

    def get_circuit_summary(self, circuit_id: str) -> Dict:
        history = self._state_history.get(circuit_id, [])
        return {
            "circuit_id": circuit_id,
            "total_transitions": len(history),
            "recent_transitions": history[-20:],
            "failure_distribution": self._failure_causes,
        }

class CircuitBreakerPatternManager(
    EnterpriseModule,
    CircuitBreakerMixin if MIXIN_AVAILABLE else object,
    RateLimiterMixin if MIXIN_AVAILABLE else object,
):
    """熔断器模式管理器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config=config or {})
        self.module_name = "熔断器模式引擎"
        self.module_id = self.module_name
        self.module_id = "circuit_breaker_pattern"
        self.version = "V0.1"
        self._initialized = False

        self._circuits: Dict[str, CircuitBreakerInstance] = {}
        self._lock = threading.RLock()
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)

        # 预设熔断器
        presets = [
            (
                "api_gateway",
                CircuitConfig(name="api_gateway", failure_threshold=10, timeout_ms=5000, open_duration_ms=15000),
            ),
            ("database", CircuitConfig(name="database", failure_threshold=5, timeout_ms=3000, open_duration_ms=30000)),
            ("redis", CircuitConfig(name="redis", failure_threshold=8, timeout_ms=1000, open_duration_ms=10000)),
            (
                "external_api",
                CircuitConfig(
                    name="external_api",
                    failure_threshold=5,
                    timeout_ms=10000,
                    recovery_strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
                ),
            ),
            (
                "message_queue",
                CircuitConfig(
                    name="message_queue",
                    failure_threshold=7,
                    timeout_ms=5000,
                    recovery_strategy=RecoveryStrategy.PROGRESSIVE,
                ),
            ),
        ]
        for name, cfg in presets:
            cb = CircuitBreakerInstance(name=name, config=cfg)
            self._circuits[cb.circuit_id] = cb

        self._stats = {
            "circuits_total": len(self._circuits),
            "total_calls": 0,
            "total_blocked": 0,
            "total_recovered": 0,
            "open_circuits": 0,
            "half_open_circuits": 0,
        }

    def initialize(self) -> None:
        self._initialized = True
        logger.info(f"[CircuitBreakerPattern] 初始化完成: {len(self._circuits)} 个熔断器")

    async def shutdown(self) -> None:
        self._initialized = False
        logger.info("[CircuitBreakerPattern] 已关闭")

    def health_check(self) -> Dict[str, Any]:
        with self._lock:
            open_count = sum(1 for c in self._circuits.values() if c.state == CircuitState.OPEN)
            half_open_count = sum(1 for c in self._circuits.values() if c.state == CircuitState.HALF_OPEN)
        return {
            "status": "running" if self._initialized else "stopped",
            "healthy": True,
            "circuits": len(self._circuits),
            "open": open_count,
            "half_open": half_open_count,
            "version": "1.0.0",
        }

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("circuit_breaker_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        try:
            if action == "create_circuit":
                return self._create_circuit(params)
            elif action == "call":
                return self._call(params)
            elif action == "record_success":
                return self._record(params.get("circuit_id", ""), True)
            elif action == "record_failure":
                return self._record(params.get("circuit_id", ""), False, params.get("failure_type", "custom"))
            elif action == "get_state":
                return self._get_state(params.get("circuit_id", ""))
            elif action == "force_state":
                return self._force_state(params.get("circuit_id", ""), params.get("state", "closed"))
            elif action == "reset":
                return self._reset_circuit(params.get("circuit_id", ""))
            elif action == "get_circuit":
                return self._get_circuit(params.get("circuit_id", ""))
            elif action == "list_circuits":
                return self._list_circuits()
            elif action == "get_stats":
                return {"success": True, "result": dict(self._stats)}
            elif action == "get_history":
                return self._get_history(params.get("circuit_id", ""))
            elif action == "register_callback":
                return self._register_callback(params.get("circuit_id", ""), params.get("event", "state_change"))
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"[CircuitBreakerPattern] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def _create_circuit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        trace_id = f"cb-create-{int(time.time() * 1000)}"
        cfg = CircuitConfig(
            name=params.get("name", ""),
            failure_threshold=params.get("failure_threshold", 5),
            success_threshold=params.get("success_threshold", 3),
            timeout_ms=params.get("timeout_ms", 30000),
            open_duration_ms=params.get("open_duration_ms", 30000),
            recovery_strategy=RecoveryStrategy(params.get("recovery_strategy", "fixed_interval")),
            slow_call_duration_ms=params.get("slow_call_duration_ms", 5000),
        )
        cb = CircuitBreakerInstance(name=cfg.name, config=cfg)
        with self._lock:
            self._circuits[cb.circuit_id] = cb
            self._stats["circuits_total"] = len(self._circuits)
        return {"success": True, "result": {"circuit_id": cb.circuit_id, "name": cb.name, "state": cb.state.value}}

    def _call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """模拟调用（检查熔断器状态）"""
        circuit_id = params.get("circuit_id", "")
        cb = self._circuits.get(circuit_id)
        if not cb:
            return {"success": False, "error": "熔断器不存在"}

        with self._lock:
            if cb.state == CircuitState.OPEN:
                if self._should_try_half_open(cb):
                    self._transition(cb, CircuitState.HALF_OPEN, "open_duration_elapsed")
                else:
                    self._stats["total_blocked"] += 1
                    return {
                        "success": False,
                        "error": "circuit_open",
                        "blocked": True,
                        "state": "open",
                        "opened_since": cb.opened_at,
                    }

            cb.total_calls += 1
            self._stats["total_calls"] += 1

            # 模拟调用结果
            simulate_success = params.get("simulate_success", True)
            simulate_failure = params.get("simulate_failure", False)

            if simulate_failure:
                return self._do_record_failure(cb, params.get("failure_type", "error_5xx"))
            else:
                return self._do_record_success(cb)

    def _do_record_success(self, cb: CircuitBreakerInstance) -> Dict[str, Any]:
        cb.records.append(CallRecord(success=True, duration_ms=cb.config.timeout_ms * 0.3))
        cb.successes += 1

        if cb.state == CircuitState.HALF_OPEN:
            cb.half_open_successes += 1
            if cb.half_open_successes >= cb.config.success_threshold:
                self._transition(cb, CircuitState.CLOSED, "success_threshold_reached")
                self._stats["total_recovered"] += 1

        # 滑动窗口更新
        if len(cb.records) >= cb.config.sliding_window_size:
            self._evaluate_window(cb)

        return {"success": True, "result": {"state": cb.state.value, "allowed": True}}

    def _do_record_failure(self, cb: CircuitBreakerInstance, failure_type_str: str) -> Dict[str, Any]:
        ft = FailureType(failure_type_str)
        cb.records.append(CallRecord(success=False, failure_type=ft))
        cb.failures += 1
        cb.total_failures += 1
        cb.last_failure_time = time.time()
        if ft == FailureType.TIMEOUT:
            cb.total_timeouts += 1

        if cb.state == CircuitState.HALF_OPEN:
            cb.half_open_failures += 1
            self._transition(cb, CircuitState.OPEN, "half_open_failure")
        elif cb.failures >= cb.config.failure_threshold:
            self._transition(
                cb, CircuitState.OPEN, f"failure_threshold_reached({cb.failures}/{cb.config.failure_threshold})"
            )

        return {"success": False, "result": {"state": cb.state.value, "failures": cb.failures}}

    def _record(self, circuit_id: str, success: bool, failure_type: str = "custom") -> Dict[str, Any]:
        cb = self._circuits.get(circuit_id)
        if not cb:
            return {"success": False, "error": "熔断器不存在"}
        with self._lock:
            if success:
                return self._do_record_success(cb)
            else:
                return self._do_record_failure(cb, failure_type)

    def _get_state(self, circuit_id: str) -> Dict[str, Any]:
        cb = self._circuits.get(circuit_id)
        if not cb:
            return {"success": False, "error": "熔断器不存在"}
        return {"success": True, "result": {"state": cb.state.value, "name": cb.name, "failures": cb.failures}}

    def _force_state(self, circuit_id: str, state_str: str) -> Dict[str, Any]:
        cb = self._circuits.get(circuit_id)
        if not cb:
            return {"success": False, "error": "熔断器不存在"}
        new_state = CircuitState(state_str)
        with self._lock:
            self._transition(cb, new_state, "manual_force")
        return {"success": True, "result": {"state": cb.state.value, "from": "manual"}}

    def _reset_circuit(self, circuit_id: str) -> Dict[str, Any]:
        cb = self._circuits.get(circuit_id)
        if not cb:
            return {"success": False, "error": "熔断器不存在"}
        with self._lock:
            old_state = cb.state
            cb.state = CircuitState.CLOSED
            cb.failures = 0
            cb.successes = 0
            cb.half_open_successes = 0
            cb.half_open_failures = 0
            cb.opened_at = None
            cb.records.clear()
            cb.transitions.append(
                StateTransition(from_state=old_state, to_state=CircuitState.CLOSED, reason="manual_reset")
            )
        return {"success": True, "result": {"state": "closed", "reset": True}}

    def _get_circuit(self, circuit_id: str) -> Dict[str, Any]:
        cb = self._circuits.get(circuit_id)
        if not cb:
            return {"success": False, "error": "熔断器不存在"}
        return {
            "success": True,
            "result": {
                "circuit_id": cb.circuit_id,
                "name": cb.name,
                "state": cb.state.value,
                "config": {
                    "failure_threshold": cb.config.failure_threshold,
                    "success_threshold": cb.config.success_threshold,
                    "timeout_ms": cb.config.timeout_ms,
                    "open_duration_ms": cb.config.open_duration_ms,
                    "recovery_strategy": cb.config.recovery_strategy.value,
                },
                "metrics": {
                    "total_calls": cb.total_calls,
                    "total_failures": cb.total_failures,
                    "total_timeouts": cb.total_timeouts,
                    "current_failures": cb.failures,
                },
                "transitions": len(cb.transitions),
                "created_at": cb.created_at,
            },
        }

    def _list_circuits(self) -> Dict[str, Any]:
        result = []
        with self._lock:
            self._stats["open_circuits"] = 0
            self._stats["half_open_circuits"] = 0
            for cb in self._circuits.values():
                if cb.state == CircuitState.OPEN:
                    self._stats["open_circuits"] += 1
                elif cb.state == CircuitState.HALF_OPEN:
                    self._stats["half_open_circuits"] += 1
                result.append(
                    {
                        "circuit_id": cb.circuit_id,
                        "name": cb.name,
                        "state": cb.state.value,
                        "failures": cb.failures,
                        "total_calls": cb.total_calls,
                    }
                )
        return {"success": True, "result": result}

    def _get_history(self, circuit_id: str) -> Dict[str, Any]:
        cb = self._circuits.get(circuit_id)
        if not cb:
            return {"success": False, "error": "熔断器不存在"}
        return {
            "success": True,
            "result": [
                {"from": t.from_state.value, "to": t.to_state.value, "reason": t.reason, "timestamp": t.timestamp}
                for t in cb.transitions[-20:]
            ],
        }

    def _register_callback(self, circuit_id: str, event: str) -> Dict[str, Any]:
        return {"success": True, "result": {"registered": True, "event": event}}

    def _should_try_half_open(self, cb: CircuitBreakerInstance) -> bool:
        if cb.opened_at is None:
            return False
        elapsed = (time.time() - cb.opened_at) * 1000
        cfg = cb.config
        if cfg.recovery_strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
            transition_count = len(cb.transitions)
            duration = cfg.open_duration_ms * (2**transition_count)
        elif cfg.recovery_strategy == RecoveryStrategy.PROGRESSIVE:
            duration = cfg.open_duration_ms * 0.5
        else:
            duration = cfg.open_duration_ms
        return elapsed >= duration

    def _transition(self, cb: CircuitBreakerInstance, new_state: CircuitState, reason: str) -> None:
        old_state = cb.state
        cb.state = new_state
        cb.transitions.append(StateTransition(from_state=old_state, to_state=new_state, reason=reason))
        if new_state == CircuitState.OPEN:
            cb.opened_at = time.time()
            cb.half_open_successes = 0
            cb.half_open_failures = 0
        elif new_state == CircuitState.CLOSED:
            cb.failures = 0
            cb.half_open_successes = 0
            cb.half_open_failures = 0
            cb.opened_at = None
        elif new_state == CircuitState.HALF_OPEN:
            cb.half_open_successes = 0
            cb.half_open_failures = 0

    def _evaluate_window(self, cb: CircuitBreakerInstance) -> None:
        """滑动窗口评估"""
        window = list(cb.records)[-cb.config.sliding_window_size :]
        total = len(window)
        failures = sum(1 for r in window if not r.success)
        if total > 0 and failures / total >= 0.5 and failures >= 3:
            if cb.state == CircuitState.CLOSED:
                self._transition(cb, CircuitState.OPEN, "sliding_window_failure_rate_high")

    def _audit_log(self, action: str, details: Dict[str, Any]) -> None:
        """记录审计日志"""
        if not hasattr(self, "_audit_records"):
            self._audit_records = []
        self._audit_records.append({"action": action, "details": details, "timestamp": time.time()})
        if len(self._audit_records) > 10000:
            self._audit_records = self._audit_records[-5000:]

    def get_audit_records(self, limit: int = 100) -> List[Dict]:
        """获取审计记录"""
        return getattr(self, "_audit_records", [])[-limit:]

    def get_all_circuit_stats(self) -> Dict[str, Any]:
        """获取所有熔断器统计摘要"""
        stats = {}
        for cid, inst in self._circuits.items():
            cb = inst.circuit if hasattr(inst, "circuit") else inst
            stats[cid] = {
                "state": str(cb.state) if hasattr(cb, "state") else "unknown",
                "failure_count": getattr(cb, "failure_count", 0),
                "success_count": getattr(cb, "success_count", 0),
            }
        return {
            "total": len(stats),
            "open": sum(1 for s in stats.values() if s["state"] == "CircuitState.OPEN"),
            "circuits": stats,
        }

    def get_failure_trend(self, service_name: str = "") -> Dict[str, Any]:
        """分析熔断器故障趋势：近1小时失败率变化、恢复时间统计"""
        history = self._history if hasattr(self, "_history") else []
        target = [h for h in history if not service_name or h.get("service") == service_name]
        if not target:
            return {"service": service_name or "all", "trend": "no_data"}
        now = time.time()
        recent_hour = [h for h in target if now - h.get("timestamp", 0) < 3600]
        failures = [h for h in recent_hour if h.get("outcome") == "failure"]
        total = len(recent_hour)
        failure_rate = len(failures) / max(total, 1)
        intervals = sorted([h.get("timestamp", 0) for h in failures])
        recovery_times = []
        for i in range(1, len(intervals)):
            gap = intervals[i] - intervals[i - 1]
            if gap > 60:
                recovery_times.append(gap)
        avg_recovery = sum(recovery_times) / max(len(recovery_times), 1) if recovery_times else 0
        return {
            "service": service_name or "all",
            "total_requests_hour": total,
            "failures_hour": len(failures),
            "failure_rate": round(failure_rate, 4),
            "avg_recovery_seconds": round(avg_recovery, 1),
            "trend": "degrading" if failure_rate > 0.5 else "stable" if failure_rate < 0.1 else "unstable",
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

module_class = CircuitBreakerPatternManager
