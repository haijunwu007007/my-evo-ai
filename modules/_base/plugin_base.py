from __future__ import annotations
"""AUTO-EVO-AI V0.1 — Plugin 架构基类

PluginInterface → PluginBase → EnterpriseModule(兼容)
新模块应继承 PluginBase，旧模块继续保持 EnterpriseModule 继承。
"""
import time, os, json
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from enum import Enum


class PluginStatus(str, Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    ERROR = "error"


@runtime_checkable
class PluginInterface(Protocol):
    """Plugin 核心接口 — 6 个必需方法"""

    plugin_id: str
    plugin_name: str
    plugin_version: str

    def initialize(self) -> Dict[str, Any]: ...
    def health_check(self) -> Dict[str, Any]: ...
    def get_status(self) -> Dict[str, Any]: ...
    def get_actions(self) -> List[Dict[str, str]]: ...
    async def execute(self, action: str, params: Optional[Dict] = None) -> Dict[str, Any]: ...
    def shutdown(self) -> None: ...


class PluginBase:
    """Plugin 基类 — 提供 48 个 EnterpriseModule 方法中的默认实现"""

    plugin_id: str = "unknown"
    plugin_name: str = "Unknown"
    plugin_version: str = "V0.1"
    plugin_group: str = "core"

    def __init__(self, config: Dict[str, Any] = None):
        self._start_time = time.time()
        self._status = PluginStatus.UNINITIALIZED
        self._config = config or {}
        self._metrics: Dict[str, List[float]] = {}
        self._init_logger()

    def _init_logger(self):
        from core.logging_config import get_logger
        self.logger = get_logger(f"evo.plugin.{self.plugin_id}")

    # ── Core lifecycle ──

    def initialize(self) -> Dict[str, Any]:
        self._status = PluginStatus.RUNNING
        return {"success": True, "plugin": self.plugin_id}

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok" if self._status == PluginStatus.RUNNING else "error",
                "healthy": self._status == PluginStatus.RUNNING,
                "plugin": self.plugin_id}

    def get_status(self) -> Dict[str, Any]:
        return {"plugin_id": self.plugin_id, "plugin_name": self.plugin_name,
                "status": self._status.value, "version": self.plugin_version,
                "uptime": round(time.time() - self._start_time, 1)}

    def get_actions(self) -> List[Dict[str, str]]:
        return [{"name": "status", "desc": "获取状态"},
                {"name": "health", "desc": "健康检查"}]

    async def execute(self, action: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        if action == "status":
            return self.get_status()
        if action == "health":
            return self.health_check()
        return {"success": False, "error": f"Unknown action: {action}"}

    def shutdown(self) -> None:
        self._status = PluginStatus.STOPPED

    # ── Metrics ──

    def record_metric(self, name: str, value: float = 1.0):
        self._metrics.setdefault(name, []).append(value)
        if len(self._metrics[name]) > 1000:
            self._metrics[name] = self._metrics[name][-500:]

    def get_metrics(self) -> Dict[str, Any]:
        result = {}
        for k, v in self._metrics.items():
            if v:
                result[k] = {"count": len(v), "avg": round(sum(v) / len(v), 3), "last": v[-1]}
        return result

    # ── Logging helpers ──

    def info(self, msg: str, **kwargs):
        self.logger.info(f"[{self.plugin_id}] {msg}", **kwargs)

    def warning(self, msg: str, **kwargs):
        self.logger.warning(f"[{self.plugin_id}] {msg}", **kwargs)

    def error(self, msg: str, **kwargs):
        self.logger.error(f"[{self.plugin_id}] {msg}", **kwargs)

    def debug(self, msg: str, **kwargs):
        self.logger.debug(f"[{self.plugin_id}] {msg}", **kwargs)


# ── Backward-compatible EnterpriseModule ──

class EnterpriseModuleV2(PluginBase):
    """EnterpriseModule V2 — 继承 PluginBase，保持向后兼容"""

    MODULE_ID: str = ""
    MODULE_NAME: str = ""
    MODULE_VERSION: str = "V0.1"
    ModuleStatus = PluginStatus

    def __init__(self, module_id: str = "", module_name: str = "", config: Dict = None):
        self.plugin_id = module_id or self.MODULE_ID
        self.plugin_name = module_name or self.MODULE_NAME
        self.plugin_version = self.MODULE_VERSION
        super().__init__(config)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, val):
        self._status = val

    def get_available_actions(self) -> List[Dict[str, str]]:
        return self.get_actions()
