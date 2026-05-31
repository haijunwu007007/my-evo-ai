"""兼容层 — 将 CircuitBreakerMixin 和 RateLimiterMixin 统一导出。
部分模块使用 from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin，
此文件保持向后兼容。
"""

from .circuit_breaker import CircuitBreakerMixin
from .rate_limiter import RateLimiterMixin

__all__ = ["CircuitBreakerMixin", "RateLimiterMixin"]
