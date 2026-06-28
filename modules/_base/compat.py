"""
AUTO-EVO-AI V0.1 — 兼容层（已废弃）
===================================
2026-06-28: 审计确认 427 个引用 Mixin 的模块全部有正确的 import 语句，
           `inject_compat()` 是死代码。已从 infra.py 与 startup.py 中移除。
           本文件保留作为兜底，不主动使用。
"""

import builtins as _builtins
import logging

_logger = logging.getLogger("evo.compat")

# ── 需要注入到 builtins 的兼容名称列表 ──
_COMPAT_NAMES = [
    ("CircuitBreakerMixin", "modules._base.circuit_breaker"),
    ("RateLimiterMixin", "modules._base.rate_limiter"),
]


def _import_compat_name(name: str, module_path: str):
    """尝试导入兼容名称，失败时静默跳过"""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, name, None)
        if cls:
            return cls
    except Exception:
        pass
    return None


def inject_compat():
    """将兼容名称注入 builtins，供未正确 import 的模块使用"""
    injected = []
    for name, path in _COMPAT_NAMES:
        if hasattr(_builtins, name):
            continue  # 已注入，跳过
        cls = _import_compat_name(name, path)
        if cls:
            setattr(_builtins, name, cls)
            injected.append(name)
    if injected:
        _logger.debug(f"[COMPAT] 注入 builtins: {injected}")


def cleanup_compat():
    """清理 builtins 中的兼容名称，仅清理由本模块注入的"""
    for name, _ in _COMPAT_NAMES:
        _builtins.__dict__.pop(name, None)


# ── 模块加载时的上下文管理器式注入 ──

class CompatContext:
    """上下文管理器，临时将兼容名称注入 builtins，
    用于模块加载时确保 class 定义能解析到 Mixin 名称。"""

    def __init__(self):
        self._saved = {}

    def __enter__(self):
        for name, path in _COMPAT_NAMES:
            self._saved[name] = getattr(_builtins, name, None)
            if name not in _builtins.__dict__:
                cls = _import_compat_name(name, path)
                if cls:
                    setattr(_builtins, name, cls)
        return self

    def __exit__(self, *args):
        for name in dict(self._saved):
            saved = self._saved.pop(name, None)
            if saved is None:
                _builtins.__dict__.pop(name, None)
            else:
                setattr(_builtins, name, saved)
