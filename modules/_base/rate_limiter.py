# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI v7.0 - 限流器 Mixin
================================
基于令牌桶算法的请求限流器。
保护系统不被突发流量击垮。

算法：令牌桶（Token Bucket）
  - 以固定速率向桶中放入令牌
  - 每次请求消耗一个令牌
  - 桶满时丢弃多余令牌
  - 桶空时请求被限流

配置：
  rate: 每秒补充令牌数（默认10）
  burst: 桶最大容量（默认20）
  per: 限流维度（module/action/ip）

使用方式:
  class MyModule(RateLimiterMixin, EnterpriseModule):
      async def execute(self, action, params):


if not self.rate_limit_check("execute"):
              return Result(success=False, error="rate_limited")
          ...
"""

import time
import logging
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("evo.rate_limiter")


@dataclass
class RateLimitConfig:
    """限流配置"""

    rate: float = 10.0  # 每秒令牌补充速率
    burst: int = 20  # 桶最大容量
    window: float = 1.0  # 滑动窗口大小（秒）
    max_wait: float = 5.0  # 最大等待时间（秒）


class TokenBucket:
    """令牌桶限流器"""

    def __init__(self, name: str, config: Optional[RateLimitConfig] = None):
        self.name = name
        self.config = config or RateLimitConfig()
        self._tokens: float = self.config.burst
        self._last_refill: float = time.time()
        self._lock = threading.Lock()
        # 统计
        self._total_allowed = 0
        self._total_rejected = 0
        self._total_waited = 0

    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self._last_refill
        new_tokens = elapsed * self.config.rate
        self._tokens = min(self.config.burst, self._tokens + new_tokens)
        self._last_refill = now

    def acquire(self, tokens: int = 1, blocking: bool = False) -> bool:
        """
        获取令牌

        Args:
            tokens: 需要的令牌数
            blocking: 是否阻塞等待
        Returns:
            是否获取成功
        """
        with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                self._total_allowed += 1
                return True

            if not blocking:
                self._total_rejected += 1
                return False

            # 阻塞等待
            wait_time = (tokens - self._tokens) / self.config.rate
            if wait_time > self.config.max_wait:
                self._total_rejected += 1
                return False

            self._total_waited += 1
            return True  # 调用方需自行 sleep

    def get_wait_time(self, tokens: int = 1) -> float:
        """获取需要等待的时间"""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                return 0.0
            return (tokens - self._tokens) / self.config.rate

    @property
    def available_tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens

    def get_stats(self) -> Dict[str, any]:
        return {
            "name": self.name,
            "available_tokens": round(self.available_tokens, 1),
            "rate": self.config.rate,
            "burst": self.config.burst,
            "total_allowed": self._total_allowed,
            "total_rejected": self._total_rejected,
            "total_waited": self._total_waited,
        }


class SlidingWindowCounter:
    """滑动窗口计数器 — 用于统计窗口内请求数"""

    def __init__(self, window: float = 60.0):
        self.window = window
        self._timestamps: List[float] = []
        self._lock = threading.Lock()

    def record(self):
        """记录一次请求"""
        now = time.time()
        with self._lock:
            self._timestamps.append(now)
            # 清理过期记录
            cutoff = now - self.window
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.pop(0)

    def count(self) -> int:
        """当前窗口内请求数"""
        now = time.time()
        cutoff = now - self.window
        with self._lock:
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.pop(0)
            return len(self._timestamps)


class RateLimiterMixin:
    """
    限流器混入类
    与EnterpriseModule配合使用，为模块提供限流保护能力。

    使用方式:
        class MyModule(RateLimiterMixin, EnterpriseModule):
            async def initialize(self):
                self._setup_rate_limit(rate=100, burst=200)

            async def execute(self, action, params):
                if not self.rate_limit_check("execute"):
                    return Result(success=False, error="请求过于频繁，请稍后重试")
                ...
    """

    _buckets: Dict[str, TokenBucket] = {}
    _windows: Dict[str, SlidingWindowCounter] = {}
    _rate_limit_config: Optional[RateLimitConfig] = None

    def _setup_rate_limit(
        self,
        rate: float = 10.0,
        burst: int = 20,
        window: float = 60.0,
        max_wait: float = 5.0,
    ):
        """初始化限流配置"""
        self._rate_limit_config = RateLimitConfig(rate=rate, burst=burst, window=window, max_wait=max_wait)

    def _get_bucket(self, key: str) -> TokenBucket:
        """获取或创建令牌桶"""
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(f"{self.module_id}:{key}", self._rate_limit_config)
        return self._buckets[key]

    def _get_window(self, key: str) -> SlidingWindowCounter:
        """获取或创建滑动窗口"""
        if key not in self._windows:
            window_size = self._rate_limit_config.window if self._rate_limit_config else 60.0
            self._windows[key] = SlidingWindowCounter(window_size)
        return self._windows[key]

    def rate_limit_check(self, key: str = "default", tokens: int = 1) -> bool:
        """
        检查是否被限流（非阻塞）

        Args:
            key: 限流维度（如 "execute", "query_api"）
            tokens: 消耗令牌数
        Returns:
            True = 允许通过，False = 被限流
        """
        bucket = self._get_bucket(key)
        allowed = bucket.acquire(tokens, blocking=False)
        if allowed:
            window = self._get_window(key)
            window.record()
        return allowed

    def rate_limit_wait_time(self, key: str = "default", tokens: int = 1) -> float:
        """获取需要等待的时间（秒）"""
        bucket = self._get_bucket(key)
        return bucket.get_wait_time(tokens)

    def get_all_rate_limit_stats(self) -> Dict[str, Dict[str, any]]:
        """获取所有限流器状态"""
        bucket_stats = {name: b.get_stats() for name, b in self._buckets.items()}
        window_stats = {name: {"count": w.count(), "window": w.window} for name, w in self._windows.items()}
        return {"buckets": bucket_stats, "windows": window_stats}
