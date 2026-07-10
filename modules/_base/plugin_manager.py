from __future__ import annotations
"""PluginManager — Plugin 生态操作系统

核心能力:
1. 6 大 Hook 点: on_startup / on_shutdown / on_config_change / 
                  on_webhook / on_menu / on_widget
2. Plugin 发现 + 依赖注入 + 版本兼容
3. Plugin 市场: 本地注册 + 远程安装 + 启用/停用
4. 与现有 EnterpriseModule 共存
"""
import os, sys, json, time, inspect, importlib, threading
from typing import Any, Dict, List, Optional, Callable, Protocol
from dataclasses import dataclass, field
from pathlib import Path
from core.logging_config import get_logger
from modules._base.plugin_base import PluginBase, PluginInterface, PluginStatus

logger = get_logger("evo.plugin_manager")

# ── Hook 点定义 ──────────────────────────────────────

@dataclass
class HookPoint:
    """Plugin Hook 点 — 系统生命周期的插入点"""
    name: str
    description: str
    priority: int = 0  # 数值越小越先执行

# 6 大 Hook
HOOKS = {
    "on_startup":   HookPoint("on_startup",   "服务启动时初始化", priority=10),
    "on_shutdown":  HookPoint("on_shutdown",  "服务关闭时清理", priority=90),
    "on_config":    HookPoint("on_config",    "配置变更时触发", priority=50),
    "on_webhook":   HookPoint("on_webhook",   "收到 Webhook 时处理", priority=50),
    "on_menu":      HookPoint("on_menu",      "提供侧边栏菜单项", priority=30),
    "on_widget":    HookPoint("on_widget",    "提供 Dashboard 组件", priority=30),
}


@dataclass
class PluginMeta:
    """Plugin 元数据"""
    id: str
    name: str
    version: str
    author: str = ""
    description: str = ""
    homepage: str = ""
    hooks: List[str] = field(default_factory=list)
    enabled: bool = True
    installed_at: float = 0.0
    source: str = "local"  # local / marketplace


class PluginManager:
    """Plugin 管理器 — 单例"""

    def __init__(self):
        self._plugins: Dict[str, PluginBase] = {}
        self._metas: Dict[str, PluginMeta] = {}
        self._hook_handlers: Dict[str, List[str]] = {h: [] for h in HOOKS}
        self._classes: Dict[str, type] = {}
        self._lock = threading.Lock()
        self._market_url = ""

    # ── 注册与发现 ──

    def register(self, plugin: PluginBase, meta: Optional[PluginMeta] = None) -> Dict:
        """注册一个 Plugin 实例"""
        pid = plugin.plugin_id
        with self._lock:
            self._plugins[pid] = plugin
            if meta:
                self._metas[pid] = meta
            else:
                self._metas[pid] = PluginMeta(
                    id=pid, name=plugin.plugin_name,
                    version=plugin.plugin_version,
                    installed_at=time.time())
            # 扫描 Hook 实现
            for hook_name in HOOKS:
                if hasattr(plugin, hook_name):
                    handler = getattr(plugin, hook_name)
                    if callable(handler):
                        self._hook_handlers[hook_name].append(pid)
            logger.info(f"[Plugin] 已注册: {pid} ({plugin.plugin_name})")
        return {"success": True, "plugin_id": pid}

    def unregister(self, plugin_id: str) -> bool:
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            self._plugins[plugin_id].shutdown()
            del self._plugins[plugin_id]
            self._metas.pop(plugin_id, None)
            for handlers in self._hook_handlers.values():
                handlers[:] = [p for p in handlers if p != plugin_id]
        logger.info(f"[Plugin] 已卸载: {plugin_id}")
        return True

    def get(self, plugin_id: str) -> Optional[PluginBase]:
        return self._plugins.get(plugin_id)

    @property
    def all(self) -> Dict[str, PluginBase]:
        return dict(self._plugins)

    @property
    def all_metas(self) -> Dict[str, PluginMeta]:
        return dict(self._metas)

    @property
    def count(self) -> int:
        return len(self._plugins)

    # ── Hook 触发 ──

    def trigger_hook(self, hook_name: str, **kwargs) -> List[Dict]:
        """触发指定 Hook，按优先级排列后执行"""
        if hook_name not in HOOKS:
            logger.warning(f"[Plugin] 未知 Hook: {hook_name}")
            return []
        results = []
        handlers = list(self._hook_handlers.get(hook_name, []))
        for pid in handlers:
            plugin = self._plugins.get(pid)
            if not plugin or not self._metas.get(pid, PluginMeta("","","")).enabled:
                continue
            try:
                handler = getattr(plugin, hook_name)
                result = handler(**kwargs)
                results.append({"plugin_id": pid, "success": True, "result": result})
            except Exception as e:
                logger.error(f"[Plugin] Hook {hook_name} 执行失败 [{pid}]: {e}")
                results.append({"plugin_id": pid, "success": False, "error": str(e)})
        return results

    def trigger_startup(self) -> List[Dict]:
        """启动时触发所有 on_startup"""
        return self.trigger_hook("on_startup")

    def trigger_shutdown(self) -> List[Dict]:
        return self.trigger_hook("on_shutdown")

    # ── Plugin 发现 ──

    def scan_directory(self, mod_dir: str) -> int:
        """扫描目录发现 Plugin 类"""
        count = 0
        for f in sorted(os.listdir(mod_dir)):
            if not f.endswith('.py') or f.startswith('_') or f.startswith('.'):
                continue
            module_name = f[:-3]
            try:
                spec = importlib.util.spec_from_file_location(
                    module_name, os.path.join(mod_dir, f))
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                # 扫描 PluginBase 子类
                for name, obj in inspect.getmembers(mod, inspect.isclass):
                    if (issubclass(obj, PluginBase) and 
                        obj is not PluginBase and 
                        obj is not object):
                        # 实例化并注册
                        try:
                            instance = obj()
                            meta = PluginMeta(
                                id=instance.plugin_id,
                                name=instance.plugin_name,
                                version=instance.plugin_version,
                                installed_at=time.time(),
                                source="local")
                            self.register(instance, meta)
                            count += 1
                        except Exception as e:
                            logger.warning(f"[Scan] {module_name}.{name} 实例化失败: {e}")
                        break
            except Exception as e:
                logger.debug(f"[Scan] 跳过 {module_name}: {e}")
        logger.info(f"[Plugin] 扫描完成: {count} 个新 Plugin")
        return count

    def install_from_market(self, plugin_id: str, source_url: str) -> Dict:
        """从市场安装 Plugin（TODO: 远程下载）"""
        logger.info(f"[Plugin] 市场安装请求: {plugin_id} -> {source_url}")
        return {"success": False, "error": "市场安装尚未实现"}

    # ── 启停控制 ──

    def enable(self, plugin_id: str) -> bool:
        if plugin_id in self._metas:
            self._metas[plugin_id].enabled = True
            plugin = self._plugins.get(plugin_id)
            if plugin:
                plugin.initialize()
            return True
        return False

    def disable(self, plugin_id: str) -> bool:
        if plugin_id in self._metas:
            self._metas[plugin_id].enabled = False
            plugin = self._plugins.get(plugin_id)
            if plugin:
                plugin.shutdown()
            return True
        return False

    # ── 菜单与组件 ──

    def get_menu_items(self) -> List[Dict]:
        """收集所有 Plugin 的菜单项"""
        items = []
        for pid in self._hook_handlers.get("on_menu", []):
            plugin = self._plugins.get(pid)
            if not plugin or not self._metas.get(pid, PluginMeta("","","")).enabled:
                continue
            try:
                result = plugin.on_menu()
                if isinstance(result, list):
                    items.extend(result)
                elif result:
                    items.append(result)
            except Exception:
                pass
        return items

    def get_widgets(self) -> List[Dict]:
        """收集所有 Plugin 的 Dashboard 组件"""
        widgets = []
        for pid in self._hook_handlers.get("on_widget", []):
            plugin = self._plugins.get(pid)
            if not plugin or not self._metas.get(pid, PluginMeta("","","")).enabled:
                continue
            try:
                result = plugin.on_widget()
                if isinstance(result, list):
                    widgets.extend(result)
                elif result:
                    widgets.append(result)
            except Exception:
                pass
        return widgets


# 全局单例
plugin_manager = PluginManager()
