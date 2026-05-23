# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 - 熔断器 Mixin
=================================
基于断路器模式（Circuit Breaker Pattern）的故障保护。
防止级联故障，保护外部调用。

三种状态：
  CLOSED（关闭/正常）→ 调用正常通过
  OPEN（打开/熔断）→ 快速失败，不调用下游
  HALF_OPEN（半开）→ 尝试少量请求，探测恢复

配置参数：
  failure_threshold: 失败次数阈值（默认5）
  recovery_timeout: 熔断恢复超时（默认30秒）
  half_open_max: 半开状态最大试探次数（默认3）

使用方式:
  class MyModule(CircuitBreakerMixin, EnterpriseModule):
      async def call_external(self, url):
          return await self.circuit_breaker_call(
              "api_call", lambda: self.http_get(url),
              timeout=10
          )
"""

import time
import logging
import asyncio
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Awaitable

logger = logging.getLogger("evo.circuit_breaker")


class CircuitState(str, Enum):
    CLOSED = "closed"  # 正常通行
    OPEN = "open"  # 熔断，快速失败
    HALF_OPEN = "half_open"  # 探测中


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 5  # 连续失败次数触发熔断
    success_threshold: int = 3  # 半开状态连续成功恢复
    recovery_timeout: float = 30.0  # 熔断恢复等待时间（秒）
    timeout: float = 10.0  # 单次调用超时（秒）
    half_open_max_calls: int = 3  # 半开状态最大试探次数


@dataclass
class CircuitStats:
    """熔断器统计"""

    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_failures: int = 0
    total_successes: int = 0
    total_rejected: int = 0  # 熔断期间拒绝的请求
    last_failure_time: Optional[float] = None
    last_state_change: Optional[float] = None
    half_open_calls: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "total_rejected": self.total_rejected,
            "last_failure_time": self.last_failure_time,
            "last_state_change": self.last_state_change,
        }


class CircuitBreaker:
    """单个熔断器实例"""

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._stats = CircuitStats()
        self._stats.last_state_change = time.time()
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """获取当前状态（自动检查恢复）"""
        with self._lock:
            if self._stats.state == CircuitState.OPEN:
                elapsed = time.time() - (self._stats.last_failure_time or 0)
                if elapsed >= self.config.recovery_timeout:
                    self._transition(CircuitState.HALF_OPEN)
            return self._stats.state

    def _transition(self, new_state: CircuitState):
        """状态转换"""
        old = self._stats.state
        if old != new_state:
            logger.warning(f"[熔断器:{self.name}] {old.value} → {new_state.value}")
            self._stats.state = new_state
            self._stats.last_state_change = time.time()
            if new_state == CircuitState.HALF_OPEN:
                self._stats.half_open_calls = 0

    def allow_request(self) -> bool:
        """判断是否允许请求通过"""
        state = self.state
        with self._lock:
            if state == CircuitState.CLOSED:
                return True
            elif state == CircuitState.OPEN:
                self._stats.total_rejected += 1
                return False
            elif state == CircuitState.HALF_OPEN:
                if self._stats.half_open_calls < self.config.half_open_max_calls:
                    self._stats.half_open_calls += 1
                    return True
                self._stats.total_rejected += 1
                return False
        return False

    def record_success(self):
        """记录成功"""
        with self._lock:
            self._stats.total_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.consecutive_successes += 1
            if (
                self._stats.state == CircuitState.HALF_OPEN
                and self._stats.consecutive_successes >= self.config.success_threshold
            ):
                self._transition(CircuitState.CLOSED)

    def record_failure(self):
        """记录失败"""
        with self._lock:
            self._stats.total_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.consecutive_failures += 1
            self._stats.last_failure_time = time.time()
            if (
                self._stats.state == CircuitState.HALF_OPEN
                or self._stats.consecutive_failures >= self.config.failure_threshold
            ):
                self._transition(CircuitState.OPEN)

    def get_stats(self) -> Dict[str, Any]:
        return {"name": self.name, **self._stats.to_dict()}

    def reset(self):
        """手动重置"""
        with self._lock:
            self._stats = CircuitStats()
            self._stats.last_state_change = time.time()


class CircuitBreakerMixin:
    """
    熔断器混入类
    与EnterpriseModule配合使用，为模块提供熔断保护能力。

    使用方式:
        class MyModule(CircuitBreakerMixin, EnterpriseModule):
            async def initialize(self):
                self._circuits = {}

            async def call_api(self, url):
                return await self.circuit_breaker_call(
                    "external_api", lambda: self._http_get(url)
                )
    """

    _circuits: Dict[str, CircuitBreaker] = {}

    def _get_circuit(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name, config)
        return self._circuits[name]

    async def circuit_breaker_call(
        self,
        name: str,
        func: Callable[[], Awaitable[Any]],
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Any = None,
    ) -> Any:
        """
        通过熔断器执行异步调用

        Args:
            name: 熔断器名称
            func: 异步函数（无参数）
            config: 熔断器配置
            fallback: 熔断时的降级返回值
        """
        cb = self._get_circuit(name, config)

        if not cb.allow_request():
            logger.warning(f"[{name}] 熔断中，执行降级策略")
            return fallback

        try:
            result = await asyncio.wait_for(func(), timeout=self._get_circuit(name, config).config.timeout)
            cb.record_success()
            return result
        except asyncio.TimeoutError:
            cb.record_failure()
            logger.warning(f"[{name}] 调用超时")
            return fallback
        except Exception as e:
            cb.record_failure()
            logger.error(f"[{name}] 调用失败: {e}")
            return fallback

    def get_all_circuit_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有熔断器状态"""
        return {name: cb.get_stats() for name, cb in self._circuits.items()}

    def reset_all_circuits(self):
        """重置所有熔断器"""
        for cb in self._circuits.values():
            cb.reset()
