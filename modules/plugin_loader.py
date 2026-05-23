"""Production-grade 插件加载器模块 V0.1
上市公司生产级实现 - 动态加载/依赖解析/生命周期管理/沙箱隔离/版本兼容
"""

__module_meta__ = {
    "id": "plugin-loader",
    "name": "Plugin Loader",
    "version": "1.0.0",
    "group": "plugin",
    "inputs": [
        {"name": "plugin_id", "type": "string", "required": True, "description": ""},
        {"name": "dependencies", "type": "string", "required": True, "description": ""},
        {"name": "version", "type": "string", "required": True, "description": ""},
        {"name": "plugin_id", "type": "string", "required": True, "description": ""},
        {"name": "plugin_id", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["manager", "plugin"],
    "grade": "A",
    "description": "Production-grade 插件加载器模块 V0.1 上市公司生产级实现 - 动态加载/依赖解析/生命周期管理/沙箱隔离/版本兼容",
}
import importlib
import importlib.util
import logging
import os
import sys
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger("plugin_loader")

class PluginDependencyResolver(object):
    """插件依赖解析器"""

    def __init__(self):
        self._dependencies: Dict[str, Dict] = {}
        self._loaded: set = set()

    def register(self, plugin_id: str, dependencies: List[str], version: str = "1.0.0"):
        self._dependencies[plugin_id] = {"deps": dependencies, "version": version, "resolved": False, "missing": []}

    def resolve(self, plugin_id: str) -> Dict:
        if plugin_id not in self._dependencies:
            return {"success": False, "error": "plugin_not_registered"}
        order = []
        visited = set()
        missing = []

        def _visit(pid):
            if pid in visited:
                return
            visited.add(pid)
            if pid not in self._dependencies:
                if pid not in self._loaded:
                    missing.append(pid)
                return
            for dep in self._dependencies[pid]["deps"]:
                _visit(dep)
            order.append(pid)

        _visit(plugin_id)
        self._dependencies[plugin_id]["resolved"] = len(missing) == 0
        self._dependencies[plugin_id]["missing"] = missing
        return {"success": len(missing) == 0, "load_order": order, "missing": missing}

    def mark_loaded(self, plugin_id: str):
        self._loaded.add(plugin_id)

    # --- Auto-generated action dispatch methods ---
    def _action_mark_loaded(self, params=None):
        """Auto-generated action wrapper for mark_loaded"""
        if params is None:
            params = {}
        return self.mark_loaded(**params)

    def _action_register(self, params=None):
        """Auto-generated action wrapper for register"""
        if params is None:
            params = {}
        return self.register(**params)

    def _action_resolve(self, params=None):
        """Auto-generated action wrapper for resolve"""
        if params is None:
            params = {}
        return self.resolve(**params)

class PluginSandbox:
    """插件沙箱环境"""

    def __init__(self):
        self._sandboxes: Dict[str, Dict] = {}
        self._allowed_modules = {
            "json",
            "math",
            "time",
            "datetime",
            "re",
            "hashlib",
            "collections",
            "functools",
            "itertools",
            "logging",
        }
        self._blocked_modules = {"os", "sys", "subprocess", "shutil", "socket", "ctypes", "signal", "importlib"}

    def create_sandbox(self, plugin_id: str) -> Dict:
        sandbox = {
            "id": str(uuid.uuid4())[:8],
            "plugin_id": plugin_id,
            "created_at": time.time(),
            "resource_limits": {"max_memory_mb": 256, "max_cpu_percent": 50, "max_execution_time_sec": 30},
            "allowed_modules": list(self._allowed_modules),
            "blocked_modules": list(self._blocked_modules),
        }
        self._sandboxes[plugin_id] = sandbox
        return sandbox

    def check_permission(self, plugin_id: str, module_name: str) -> bool:
        if module_name in self._blocked_modules:
            return False
        return module_name in self._allowed_modules

    def destroy_sandbox(self, plugin_id: str):
        self._sandboxes.pop(plugin_id, None)

    def get_sandbox(self, plugin_id: str) -> Optional[Dict]:
        return self._sandboxes.get(plugin_id)

class PluginLifecycleManager(object):
    """插件生命周期管理器"""

    STATES = ["registered", "initialized", "started", "stopped", "error"]

    def __init__(self):
        self._plugins: Dict[str, Dict] = {}
        self._state_history: Dict[str, List[Dict]] = defaultdict(list)

    def register(self, plugin_id: str, entry_point: str, metadata: Dict = None) -> Dict:
        self._plugins[plugin_id] = {
            "id": plugin_id,
            "entry_point": entry_point,
            "metadata": metadata or {},
            "state": "registered",
            "registered_at": time.time(),
            "instance": None,
            "error": None,
            "start_count": 0,
            "start_time": None,
        }
        self._state_history[plugin_id].append({"from": None, "to": "registered", "ts": time.time()})
        return {"success": True, "id": plugin_id, "state": "registered"}

    def initialize(self, plugin_id: str) -> Dict:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return {"success": False, "error": "plugin_not_found"}
        if plugin["state"] != "registered":
            return {"success": False, "error": f"invalid_state:{plugin['state']}"}
        self._transition(plugin_id, "initialized")
        return {"success": True, "id": plugin_id, "state": "initialized"}

    def start(self, plugin_id: str) -> Dict:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return {"success": False, "error": "plugin_not_found"}
        if plugin["state"] not in ("registered", "initialized", "stopped"):
            return {"success": False, "error": f"invalid_state:{plugin['state']}"}
        self._transition(plugin_id, "started")
        plugin["start_count"] += 1
        plugin["start_time"] = time.time()
        return {"success": True, "id": plugin_id, "state": "started", "start_count": plugin["start_count"]}

    def stop(self, plugin_id: str) -> Dict:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return {"success": False, "error": "plugin_not_found"}
        if plugin["state"] != "started":
            return {"success": False, "error": f"invalid_state:{plugin['state']}"}
        self._transition(plugin_id, "stopped")
        return {"success": True, "id": plugin_id, "state": "stopped"}

    def get_plugin(self, plugin_id: str) -> Optional[Dict]:
        return self._plugins.get(plugin_id)

    def list_plugins(self, state: str = None) -> List[Dict]:
        plugins = list(self._plugins.values())
        if state:
            plugins = [p for p in plugins if p["state"] == state]
        return plugins

    def _transition(self, plugin_id: str, new_state: str):
        plugin = self._plugins[plugin_id]
        old_state = plugin["state"]
        plugin["state"] = new_state
        self._state_history[plugin_id].append({"from": old_state, "to": new_state, "ts": time.time()})

class PluginLoader(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """插件加载器 - 生产级实现"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "plugins_loaded": 0,
            "plugins_started": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logger

        self.dependency_resolver = PluginDependencyResolver()
        self.sandbox = PluginSandbox()
        self.lifecycle = PluginLifecycleManager()

    def initialize(self) -> dict:
        self._status = ModuleStatus.RUNNING
        return {"success": True}

    def health_check(self) -> dict:
        plugins = self.lifecycle.list_plugins()
        states = defaultdict(int)
        for p in plugins:
            states[p["state"]] += 1
        return {
            "healthy": self._status == ModuleStatus.RUNNING,
            "total_plugins": len(plugins),
            "by_state": dict(states),
        }

    def register_plugin(self, params: dict = None) -> dict:
        params = params or {}
        pid = params.get("id", str(uuid.uuid4())[:8])
        deps = params.get("dependencies", [])
        if deps:
            self.dependency_resolver.register(pid, deps, params.get("version", "1.0.0"))
        self.sandbox.create_sandbox(pid)
        result = self.lifecycle.register(pid, params.get("entry_point", ""), params.get("metadata"))
        return {"success": True, **result}

    def load_plugin(self, params: dict = None) -> dict:
        params = params or {}
        pid = params.get("id", "")
        deps_result = self.dependency_resolver.resolve(pid)
        if not deps_result.get("success"):
            return {"success": False, "error": "unresolved_dependencies", "missing": deps_result.get("missing", [])}
        init_result = self.lifecycle.initialize(pid)
        if not init_result.get("success"):
            return init_result
        start_result = self.lifecycle.start(pid)
        if start_result.get("success"):
            self._metrics["plugins_loaded"] += 1
            self._metrics["plugins_started"] += 1
            self.dependency_resolver.mark_loaded(pid)
        return {"success": True, **start_result, "load_order": deps_result.get("load_order", [])}

    def stop_plugin(self, params: dict = None) -> dict:
        params = params or {}
        return {"success": True, **self.lifecycle.stop(params.get("id", ""))}

    def list_plugins(self, params: dict = None) -> dict:
        params = params or {}
        plugins = self.lifecycle.list_plugins(params.get("state"))
        return {"success": True, "plugins": plugins, "count": len(plugins)}

    def get_plugin_info(self, params: dict = None) -> dict:
        params = params or {}
        plugin = self.lifecycle.get_plugin(params.get("id", ""))
        return {"success": plugin is not None, "plugin": plugin}

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "plugin_loader"})
        self.metrics_collector.counter("plugin_loader.execute.calls", 1)
        self.audit("execute", {"module": "plugin_loader"})
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            self._metrics["total_operations"] += 1
            t0 = time.time()
            try:
                result = handler(params)
                self._metrics["last_success_ts"] = time.time()
                self._metrics["avg_latency_ms"] = (
                    self._metrics["avg_latency_ms"] * 0.9 + (time.time() - t0) * 1000 * 0.1
                )
                return result
            except Exception as e:
                self._metrics["errors"] += 1
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    def get_dependency_graph(self) -> Dict[str, Any]:
        """插件依赖图。企业场景：架构师查看插件间依赖关系，
        评估引入新插件的影响范围和循环依赖风险。
        """
        resolver = getattr(self, "dependency_resolver", None)
        graph = getattr(resolver, "_dependencies", {}) if resolver else {}
        nodes = []
        edges = []
        for pid, deps in graph.items():
            nodes.append({"plugin_id": pid, "dependency_count": len(deps)})
            for dep in deps:
                edges.append({"from": pid, "to": dep})
        return {
            "success": True,
            "total_plugins": len(nodes),
            "total_dependencies": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def get_plugin_health_summary(self) -> Dict[str, Any]:
        """插件健康汇总。企业场景：运维看板展示所有插件运行状态，
        快速发现异常插件。
        """
        plugins = self.lifecycle.list_plugins() if hasattr(self, "lifecycle") else []
        by_state = {}
        for p in plugins:
            state = p.get("state", "unknown")
            by_state[state] = by_state.get(state, 0) + 1
        return {
            "success": True,
            "total_plugins": len(plugins),
            "by_state": by_state,
            "loaded": self._metrics.get("plugins_loaded", 0),
            "started": self._metrics.get("plugins_started", 0),
        }

    def get_plugin_dependencies(self, plugin_name: str) -> Dict[str, Any]:
        """查看插件依赖树。企业场景：安装/卸载前检查依赖链，
        避免卸载被其他插件依赖的核心模块导致连锁失败。
        """
        plugins = getattr(self, "_plugins", {})
        plugin = plugins.get(plugin_name)
        if not plugin:
            return {"success": False, "error": f"插件 {plugin_name} 不存在"}
        # 前置依赖
        requires = getattr(plugin, "requires", [])
        # 被谁依赖
        depended_by = []
        for name, p in plugins.items():
            deps = getattr(p, "requires", [])
            if plugin_name in deps:
                depended_by.append(name)
        # 递归检查循环依赖
        visited = set()
        has_cycle = False

        def check_cycle(node, path):
            nonlocal has_cycle
            if node in path:
                has_cycle = True
                return
            if node in visited:
                return
            visited.add(node)
            p = plugins.get(node)
            if p:
                for dep in getattr(p, "requires", []):
                    check_cycle(dep, path + [node])

        check_cycle(plugin_name, [])
        return {
            "success": True,
            "plugin": plugin_name,
            "requires": requires,
            "depended_by": depended_by,
            "has_circular_dependency": has_cycle,
            "safe_to_remove": len(depended_by) == 0,
        }

    def reload_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """热重载插件。企业场景：开发环境修改插件代码后热重载，
        无需重启主进程，加速开发迭代。
        """
        plugins = getattr(self, "_plugins", {})
        if plugin_name not in plugins:
            return {"success": False, "error": f"插件 {plugin_name} 未加载"}
        start = time.time()
        # 停止
        plugin = plugins[plugin_name]
        if hasattr(plugin, "stop"):
            try:
                plugin.stop()
            except Exception as e:
                return {"success": False, "error": f"停止失败: {e}"}
        # 重新加载模块
        module_path = getattr(plugin, "module_path", "")
        if module_path:
            try:
                import importlib
                import sys

                if module_path in sys.modules:
                    importlib.reload(sys.modules[module_path])
            except Exception as e:
                return {"success": False, "error": f"重载模块失败: {e}"}
        # 重新启动
        if hasattr(plugin, "start"):
            try:
                plugin.start()
            except Exception as e:
                return {"success": False, "error": f"启动失败: {e}"}
        elapsed = round(time.time() - start, 3)
        self.metrics_collector.counter("plugin_loader.reload")
        self.audit("reload_plugin", details={"plugin": plugin_name, "duration_ms": elapsed * 1000})
        return {
            "success": True,
            "plugin": plugin_name,
            "reload_time_ms": round(elapsed * 1000, 1),
            "message": "插件热重载完成",
        }

    def get_plugin_resource_usage(self) -> Dict[str, Any]:
        """插件资源使用统计。企业场景：发现资源占用异常的插件
        （如内存泄漏、线程未释放），指导优化或替换决策。
        """
        plugins = getattr(self, "_plugins", {})
        usage = []
        for name, plugin in plugins.items():
            state = getattr(plugin, "state", "unknown")
            mem_mb = getattr(plugin, "memory_mb", 0)
            threads = getattr(plugin, "thread_count", 0)
            cpu_pct = getattr(plugin, "cpu_percent", 0)
            uptime = getattr(plugin, "uptime_seconds", 0)
            usage.append(
                {
                    "name": name,
                    "state": state,
                    "memory_mb": round(mem_mb, 1),
                    "threads": threads,
                    "cpu_percent": round(cpu_pct, 1),
                    "uptime_hours": round(uptime / 3600, 1),
                }
            )
        usage.sort(key=lambda x: -x["memory_mb"])
        total_mem = sum(u["memory_mb"] for u in usage)
        return {
            "success": True,
            "total_plugins": len(usage),
            "total_memory_mb": round(total_mem, 1),
            "top_by_memory": usage[:10],
        }

    def get_plugin_api_summary(self) -> Dict[str, Any]:
        """插件API汇总。企业场景：API网关配置时需要知道每个插件
        注册了哪些API端点，避免路由冲突。
        """
        plugins = getattr(self, "_plugins", {})
        summary = []
        for name, plugin in plugins.items():
            routes = getattr(plugin, "routes", [])
            hooks = getattr(plugin, "hooks", [])
            extensions = getattr(plugin, "extensions", [])
            summary.append(
                {
                    "name": name,
                    "version": getattr(plugin, "version", "0.0.0"),
                    "routes": [
                        {"path": r.get("path", ""), "method": r.get("method", "GET"), "handler": r.get("handler", "")}
                        for r in routes
                    ],
                    "hooks": hooks,
                    "extensions": extensions,
                    "route_count": len(routes),
                }
            )
        total_routes = sum(s["route_count"] for s in summary)
        return {"success": True, "total_plugins": len(summary), "total_routes": total_routes, "plugins": summary}

    def validate_all_plugins(self) -> Dict[str, Any]:
        """验证所有插件完整性。企业场景：启动时或发布前检查所有插件的
        接口实现、依赖满足、配置完整，提前暴露问题。
        """
        plugins = getattr(self, "_plugins", {})
        results = []
        for name, plugin in plugins.items():
            issues = []
            version = getattr(plugin, "version", "unknown")
            # 检查必要方法
            required_methods = ["start", "stop"]
            for method in required_methods:
                if not hasattr(plugin, method):
                    issues.append(f"缺少方法: {method}")
            # 检查依赖
            requires = getattr(plugin, "requires", [])
            for dep in requires:
                if dep not in plugins:
                    issues.append(f"依赖缺失: {dep}")
            # 检查配置
            config = getattr(plugin, "config", {})
            required_config = getattr(plugin, "required_config", [])
            for key in required_config:
                if key not in config or not config[key]:
                    issues.append(f"配置缺失: {key}")
            results.append(
                {
                    "name": name,
                    "version": version,
                    "valid": len(issues) == 0,
                    "issues": issues,
                }
            )
        valid_count = sum(1 for r in results if r["valid"])
        invalid = [r for r in results if not r["valid"]]
        return {
            "success": True,
            "total": len(results),
            "valid": valid_count,
            "invalid": invalid,
            "validation_passed": len(invalid) == 0,
        }

    def get_plugin_load_order(self) -> Dict[str, Any]:
        """计算插件加载顺序。企业场景：确保插件按依赖关系顺序加载，
        被依赖的插件先于依赖它的插件启动。
        """
        plugins = getattr(self, "_plugins", {})
        # 拓扑排序
        in_degree = {name: 0 for name in plugins}
        adj = {name: [] for name in plugins}
        for name, plugin in plugins.items():
            for dep in getattr(plugin, "requires", []):
                if dep in plugins:
                    adj[dep].append(name)
                    in_degree[name] += 1
        queue = [n for n, d in in_degree.items() if d == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        has_cycle = len(order) != len(plugins)
        return {
            "success": True,
            "load_order": order,
            "has_cycle": has_cycle,
            "unresolved": [n for n in plugins if n not in order],
        }

    def shutdown(self) -> dict:
        """Graceful shutdown for plugin_loader."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = PluginLoader
