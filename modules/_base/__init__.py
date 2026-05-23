# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 基础设施层
==========================
EnterpriseModule基类 + 链路追踪 + Prometheus指标 + 审计日志 + 熔断器 + 限流器 + 模块注册器

所有生产级模块必须继承 EnterpriseModule 基类，获得：
  - 标准化生命周期管理（initialize / health_check / shutdown）
  - 分布式链路追踪（trace_id 贯穿）
  - Prometheus 指标自动采集
  - 审计日志自动记录
  - 熔断器保护（外部调用）
  - 限流器控制（请求频率）
  - 模块自注册到全局 Registry
"""

from .enterprise_module import (
    EnterpriseModule,
    ModuleStats,
    HealthReport,
    Result,
    ModuleStatus,
)
from .registry import ModuleRegistry
from .tracing import TracingContext, get_tracer
from .metrics import MetricsCollector, get_metrics
from .audit import AuditLogger, get_audit_logger
from .circuit_breaker import CircuitBreakerMixin
from .rate_limiter import RateLimiterMixin

__all__ = [
    "EnterpriseModule",
    "ModuleStats",
    "HealthReport",
    "Result",
    "ModuleStatus",
    "ModuleRegistry",
    "TracingContext",
    "get_tracer",
    "MetricsCollector",
    "get_metrics",
    "AuditLogger",
    "get_audit_logger",
    "CircuitBreakerMixin",
    "RateLimiterMixin",
]
