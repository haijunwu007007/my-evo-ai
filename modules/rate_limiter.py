# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 通用限流器（A级）— Token Bucket + Sliding Window 真实实现"""
# Grade: A

import time
import uuid
import logging
import threading
from collections import deque
from typing import Any, Dict, Optional, Tuple

from modules._base.enterprise_module import (
    EnterpriseModule, ModuleStatus, HealthReport,
    CircuitBreakerMixin, RateLimiterMixin,
)

logger = logging.getLogger("evo.rate-limiter-mod")

__module_meta__ = {
    "id": "rate-limiter-mod",
    "name": "Rate Limiter",
    "version": "V0.1",
    "group": "system",
    "grade": "A",
    "tags": ["system", "rate-limit", "throttle", "token-bucket", "sliding-window"],
    "description": "通用限流器 — Token Bucket + Sliding Window 双策略",
}


# ======================================================================
# Token Bucket 算法
# ======================================================================

class TokenBucket:
    """令牌桶限流器。

    以固定速率向桶中添加令牌，请求消耗令牌；
    令牌不足时请求被拒绝，直到桶中重新积累足够令牌。
    """

    def __init__(self, capacity: float, fill_rate: float, initial_tokens: Optional[float] = None) -> None:
        """
        Args:
            capacity: 桶最大容量（峰值突发请求数）
            fill_rate: 令牌补充速率（每秒添加的令牌数）
            initial_tokens: 初始令牌数，默认填满
        """
        self.capacity = max(capacity, 1)
        self.fill_rate = max(fill_rate, 0.001)
        self._tokens = initial_tokens if initial_tokens is not None else self.capacity
        self._last_time = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """按时间间隔补充令牌。"""
        now = time.monotonic()
        elapsed = now - self._last_time
        if elapsed > 0:
            new_tokens = elapsed * self.fill_rate
            self._tokens = min(self.capacity, self._tokens + new_tokens)
            self._last_time = now

    def allow_request(self, tokens: float = 1.0) -> Tuple[bool, float]:
        """检查是否允许请求消耗 tokens 个令牌。

        Returns:
            (allowed, remaining_tokens)
        """
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True, self._tokens
            return False, self._tokens

    def wait_if_needed(self, tokens: float = 1.0, timeout: Optional[float] = None) -> bool:
        """阻塞直到获取到令牌或超时。

        Returns:
            True 表示成功获取，False 表示超时
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            allowed, _ = self.allow_request(tokens)
            if allowed:
                return True
            if deadline is not None and time.monotonic() >= deadline:
                return False
            # 等待一个令牌产生的时间
            time.sleep(1.0 / self.fill_rate)

    @property
    def tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens


# ======================================================================
# Sliding Window 算法
# ======================================================================

class SlidingWindow:
    """滑动窗口限流器。

    在固定时间窗口内限制最大请求数，窗口随时间滑动。
    使用 deque 记录请求时间戳，精确到毫秒级。
    """

    def __init__(self, window_size: float, max_requests: int) -> None:
        """
        Args:
            window_size: 窗口大小（秒）
            max_requests: 窗口内允许的最大请求数
        """
        self.window_size = max(window_size, 0.1)
        self.max_requests = max(max_requests, 1)
        self._timestamps: deque = deque()
        self._lock = threading.Lock()

    def _trim(self, now: float) -> None:
        """移除窗口外的过期时间戳。"""
        cutoff = now - self.window_size
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def allow_request(self) -> Tuple[bool, int]:
        """检查是否允许请求。

        Returns:
            (allowed, remaining_slots)
        """
        with self._lock:
            now = time.monotonic()
            self._trim(now)
            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(now)
                return True, self.max_requests - len(self._timestamps)
            return False, 0

    def wait_if_needed(self, timeout: Optional[float] = None) -> bool:
        """阻塞直到窗口有空位或超时。"""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            allowed, _ = self.allow_request()
            if allowed:
                return True
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(max(self.window_size / self.max_requests, 0.01))

    @property
    def current_count(self) -> int:
        with self._lock:
            self._trim(time.monotonic())
            return len(self._timestamps)


# ======================================================================
# 模块主类
# ======================================================================

class RateLimiter(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """通用限流器模块，封装 TokenBucket 和 SlidingWindow 两种策略。"""

    MODULE_ID = "rate-limiter-mod"
    MODULE_NAME = "通用限流器"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict] = None) -> None:
        super().__init__(config)
        self._buckets: Dict[str, TokenBucket] = {}
        self._windows: Dict[str, SlidingWindow] = {}
        self._lock = threading.Lock()
        self._configs: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING
        self.logger.info("RateLimiter initialized (token-bucket + sliding-window)")

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value,
            healthy=True,
            module_id=self.MODULE_ID,
            checks={
                "buckets": len(self._buckets),
                "windows": len(self._windows),
                "configs": len(self._configs),
            },
        )

    async def execute(self, action: str, params: Optional[Dict] = None) -> Any:
        return await self._safe_execute(action, params, handler=self._dispatch)

    async def shutdown(self) -> None:
        self._buckets.clear()
        self._windows.clear()
        self.status = ModuleStatus.STOPPED
        self.logger.info("RateLimiter shut down")

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def get_token_bucket(self, key: str, capacity: float = 20.0, fill_rate: float = 10.0) -> TokenBucket:
        """获取或创建指定 key 的 TokenBucket。"""
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(capacity=capacity, fill_rate=fill_rate)
                self.logger.debug("Created token bucket '%s': cap=%s rate=%s", key, capacity, fill_rate)
            return self._buckets[key]

    def get_sliding_window(self, key: str, window_size: float = 60.0, max_requests: int = 100) -> SlidingWindow:
        """获取或创建指定 key 的 SlidingWindow。"""
        with self._lock:
            if key not in self._windows:
                self._windows[key] = SlidingWindow(window_size=window_size, max_requests=max_requests)
                self.logger.debug("Created sliding window '%s': window=%ss limit=%s", key, window_size, max_requests)
            return self._windows[key]

    def allow_request(self, key: str, method: str = "token_bucket", **kwargs) -> Dict:
        """统一接口：检查是否允许请求。

        Args:
            key: 限流键
            method: "token_bucket" 或 "sliding_window"
            **kwargs: 传递给对应限流器的参数

        Returns:
            {"allowed": bool, "remaining": float/int, "key": str}
        """
        if method == "token_bucket":
            capacity = float(kwargs.get("capacity", 20))
            fill_rate = float(kwargs.get("fill_rate", 10))
            tokens = float(kwargs.get("tokens", 1.0))
            bucket = self.get_token_bucket(key, capacity, fill_rate)
            allowed, remaining = bucket.allow_request(tokens)
            return {"allowed": allowed, "remaining": round(remaining, 2), "key": key}

        elif method == "sliding_window":
            window_size = float(kwargs.get("window_size", 60))
            max_requests = int(kwargs.get("max_requests", 100))
            sw = self.get_sliding_window(key, window_size, max_requests)
            allowed, remaining = sw.allow_request()
            return {"allowed": allowed, "remaining": remaining, "key": key}

        else:
            raise ValueError(f"Unknown method: {method}")

    # ------------------------------------------------------------------
    # Dispatch（保持向后兼容）
    # ------------------------------------------------------------------

    def _dispatch(self, p: Dict) -> Dict:
        action = {"check": "token_bucket", "stats": "config_list"}.get(
            p.get("action", "status"), p.get("action", "status")
        )

        if action == "token_bucket":
            key = p.get("key", "default")
            rate = float(p.get("rate", 10))
            burst = int(p.get("burst", 20))
            result = self.allow_request(key, method="token_bucket", capacity=burst, fill_rate=rate, tokens=1.0)
            return {"success": True, **result}

        if action == "sliding_window":
            key = p.get("key", "default")
            limit = int(p.get("limit", 100))
            window = int(p.get("window", 60))
            result = self.allow_request(key, method="sliding_window", max_requests=limit, window_size=window)
            return {"success": True, **result}

        if action == "config":
            key = p.get("key", "default")
            rate = float(p.get("rate", 10))
            burst = int(p.get("burst", 20))
            window = int(p.get("window", 60))
            limit = int(p.get("limit", 100))
            method = p.get("method", "token_bucket")
            self._configs[key] = {
                "rate": rate, "burst": burst,
                "window": window, "limit": limit,
                "method": method,
            }
            return {"success": True, "key": key, "config": self._configs[key]}

        if action == "config_list":
            return {"success": True, "configs": self._configs}

        if action == "clear":
            key = p.get("key", "")
            with self._lock:
                if key:
                    self._buckets.pop(key, None)
                    self._windows.pop(key, None)
                else:
                    self._buckets.clear()
                    self._windows.clear()
            return {"success": True, "cleared": True}

        if action == "blocklist":
            return {
                "success": True,
                "keys": list(self._buckets.keys()) + list(self._windows.keys()),
                "total_buckets": len(self._buckets),
                "total_windows": len(self._windows),
            }

        if action == "stats":
            return {
                "buckets": len(self._buckets),
                "windows": {
                    k: sw.current_count for k, sw in self._windows.items()
                },
                "configs": len(self._configs),
                "methods": ["token_bucket", "sliding_window"],
            }

        return {"error": f"unknown:{action}"}


module_class = RateLimiter
