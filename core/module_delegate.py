"""
AUTO-EVO-AI V0.1 — Module Delegate 模式
=========================================
核心思想：模块不直接 import 引擎服务，而是通过 Delegate 单例调用。
所有方法都有 Noop 兜底，确保不会因为服务未注册而崩溃。
"""
import time
from core.logging_config import get_logger
from typing import Any, Dict, Optional

logger = get_logger("evo.delegate")


class _ServiceWrapper:
    """服务装饰器：计时 + 错误捕获 + 日志"""

    def __init__(self, service_obj):
        self._obj = service_obj

    def __getattr__(self, name):
        attr = getattr(self._obj, name, None)
        if attr is None:
            def noop(*args, **kwargs):
                logger.debug("delegate noop: %s.%s", type(self._obj).__name__, name)
                return {"success": False, "delegate_noop": True, "service": type(self._obj).__name__, "method": name}
            return noop
        if not callable(attr):
            return attr

        def wrapper(*args, **kwargs):
            t0 = time.time()
            try:
                result = attr(*args, **kwargs)
                elapsed = time.time() - t0
                if elapsed > 1.0:
                    logger.warning("delegate slow call: %s.%s took %.2fs", type(self._obj).__name__, name, elapsed)
                return result
            except Exception as e:
                logger.error("delegate error: %s.%s -> %s", type(self._obj).__name__, name, e)
                return {"success": False, "error": str(e), "delegate_error": True}
        return wrapper


class _NoopService:
    """空服务兜底"""
    def __getattr__(self, name):
        def noop(*args, **kwargs):
            return {"success": False, "delegate_noop": True, "service": type(self).__name__, "method": name}
        return noop


class ModuleDelegate:
    """模块委托 - 单例，注册引擎服务供模块调用"""

    _instance = None
    _services: dict[str, _ServiceWrapper] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, name: str, service) -> None:
        """注册一个引擎服务"""
        self._services[name] = _ServiceWrapper(service)
        logger.info("delegate registered: %s -> %s", name, type(service).__name__)

    def __getattr__(self, name: str) -> _ServiceWrapper:
        if name.startswith("_"):
            raise AttributeError(name)
        svc = self._services.get(name)
        if svc is not None:
            return svc
        logger.debug("delegate service not found: %s (using noop)", name)
        noop = _NoopService()
        self._services[name] = _ServiceWrapper(noop)
        return self._services[name]


# 单例快捷方式
_delegate = ModuleDelegate.get_instance()
