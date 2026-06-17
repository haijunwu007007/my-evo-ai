"""
AUTO-EVO-AI V0.1 — 模块包入口
==============================
modules/ 包含 455+ 个模块文件，注册到全局 Registry。
通过 _base/ 基础设施层提供 EnterpriseModule 基类支持。

用法：
    from modules import EnterpriseModule, ModuleRegistry
    from modules._base import TracingContext, get_tracer
"""

from modules._base import (
    EnterpriseModule,
    ModuleStats,
    HealthReport,
    Result,
    ModuleStatus,
    ModuleRegistry,
)

__all__ = [
    "EnterpriseModule",
    "ModuleStats",
    "HealthReport",
    "Result",
    "ModuleStatus",
    "ModuleRegistry",
]
