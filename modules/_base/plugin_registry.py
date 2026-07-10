from __future__ import annotations
"""AUTO-EVO-AI V0.1 — Plugin Registry

管理所有 Plugin 的发现、注册、生命周期。
支持向后兼容: 新 Plugin 和旧 EnterpriseModule 共存。
"""
import os, sys, time, inspect, importlib
from typing import Any, Dict, List, Optional, Type
from core.logging_config import get_logger
from modules._base.plugin_base import PluginInterface, PluginBase, EnterpriseModuleV2

logger = get_logger("evo.plugin_registry")


class PluginRegistry:
    """Plugin 注册表 — 统一管理所有 Plugin 实例"""

    def __init__(self):
        self._plugins: Dict[str, PluginBase] = {}
        self._classes: Dict[str, type] = {}
        self._pending: List[str] = []
        self._scan_time: float = 0

    # ── Registration ──

    def register(self, plugin_id: str, plugin: PluginBase) -> Dict[str, Any]:
        self._plugins[plugin_id] = plugin
        logger.info(f"[Plugin] 注册: {plugin_id}")
        return {"success": True, "plugin_id": plugin_id}

    def unregister(self, plugin_id: str) -> bool:
        if plugin_id in self._plugins:
            self._plugins[plugin_id].shutdown()
            del self._plugins[plugin_id]
            return True
        return False

    def get(self, plugin_id: str) -> Optional[PluginBase]:
        return self._plugins.get(plugin_id)

    @property
    def all(self) -> Dict[str, PluginBase]:
        return dict(self._plugins)

    @property
    def count(self) -> int:
        return len(self._plugins)

    # ── Health / Status ──

    def get_all_health(self) -> Dict[str, Dict]:
        result = {}
        for pid, plugin in self._plugins.items():
            try:
                result[pid] = plugin.health_check()
            except Exception:
                result[pid] = {"status": "error", "healthy": False}
        return result

    def get_all_status(self) -> Dict[str, Dict]:
        return {pid: p.get_status() for pid, p in self._plugins.items()}

    def initialize_all(self) -> Dict[str, Any]:
        ok, fail = 0, 0
        for pid, plugin in self._plugins.items():
            try:
                plugin.initialize()
                ok += 1
            except Exception as e:
                logger.error(f"[Plugin] {pid} 初始化失败: {e}")
                fail += 1
        return {"success": ok + fail > 0, "ok": ok, "failed": fail}

    # ── Discovery (scan modules directory) ──

    def scan_directory(self, mod_dir: str, recursive: bool = True) -> List[str]:
        discovered = []
        for f in sorted(os.listdir(mod_dir)):
            if not f.endswith('.py') or f.startswith('_') or f.startswith('.'):
                continue
            module_name = f[:-3]
            try:
                spec = importlib.util.spec_from_file_location(module_name, os.path.join(mod_dir, f))
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                # Try EnterpriseModule pattern first
                if hasattr(mod, 'module_class'):
                    cls = mod.module_class
                    self._classes[module_name] = cls
                    discovered.append(module_name)
                    logger.debug(f"[Scan] 发现 EnterpriseModule: {module_name}")
                    continue

                # Try PluginBase subclass
                for name, obj in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(obj, PluginBase) and obj is not PluginBase and obj is not EnterpriseModuleV2:
                        self._classes[module_name] = obj
                        discovered.append(module_name)
                        logger.debug(f"[Scan] 发现 Plugin: {module_name}")
                        break
            except Exception as e:
                logger.debug(f"[Scan] 跳过 {module_name}: {e}")
        self._scan_time = time.time()
        return discovered


# 全局单例
plugin_registry = PluginRegistry()
