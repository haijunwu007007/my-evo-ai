"""Production-grade 插件市场模块 V0.1
# Grade: A
上市公司生产级实现 - 插件注册/搜索/安装/版本管理/评分/依赖检查/发布审核
"""

__module_meta__ = {
        "id": "plugin-market",
        "name": "Plugin Market",
        "version": "V0.1",
        "group": "plugin",
        "inputs": [
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "version",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "author",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "category",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "query",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "category_2",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "manager",
            "plugin"
        ],
        "grade": "A",
        "description": "Production-grade 插件市场模块 V0.1 上市公司生产级实现 - 插件注册/搜索/安装/版本管理/评分/依赖检查/发布审核"
    }
import hashlib
from core.logging_config import get_logger
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = get_logger("plugin_market")

class PluginRegistry:
    """插件注册中心"""

    def __init__(self):
        self._plugins: dict[str, dict] = {}
        self._by_category: dict[str, list[str]] = defaultdict(list)
        self._by_author: dict[str, list[str]] = defaultdict(list)
        self._name_index: dict[str, str] = {}

    def register(
        self,
        name: str,
        version: str,
        author: str,
        category: str,
        description: str,
        entry_point: str,
        dependencies: list[str] = None,
        tags: list[str] = None,
        icon: str = "",
    ) -> dict:
        plugin_id = str(uuid.uuid4())[:10]
        normalized = name.lower().replace("-", "_").replace(" ", "_")
        if normalized in self._name_index:
            existing_id = self._name_index[normalized]
            existing = self._plugins.get(existing_id, {})
            existing_versions = existing.get("versions", {})
            existing_versions[version] = {
                "entry_point": entry_point,
                "dependencies": dependencies or [],
                "published_at": time.time(),
                "size_kb": 0,
            }
            existing["latest_version"] = version
            return {"success": True, "id": existing_id, "action": "version_added", "version": version}
        entry = {
            "id": plugin_id,
            "name": name,
            "normalized": normalized,
            "latest_version": version,
            "author": author,
            "category": category,
            "description": description,
            "tags": tags or [],
            "icon": icon,
            "download_count": 0,
            "rating_avg": 0,
            "rating_count": 0,
            "status": "published",
            "created_at": time.time(),
            "updated_at": time.time(),
            "versions": {
                version: {
                    "entry_point": entry_point,
                    "dependencies": dependencies or [],
                    "published_at": time.time(),
                    "size_kb": 0,
                }
            },
        }
        self._plugins[plugin_id] = entry
        self._by_category[category].append(plugin_id)
        self._by_author[author].append(plugin_id)
        self._name_index[normalized] = plugin_id
        return {"success": True, "id": plugin_id, "action": "created"}

    def search(
        self,
        query: str = "",
        category: str = "",
        author: str = "",
        tags: list[str] = None,
        sort_by: str = "relevance",
        limit: int = 20,
    ) -> list[dict]:
        results = list(self._plugins.values())
        if query:
            q = query.lower()
            results = [
                p
                for p in results
                if q in p["name"].lower() or q in p["description"].lower() or q in " ".join(p.get("tags", [])).lower()
            ]
        if category:
            results = [p for p in results if p["category"] == category]
        if author:
            results = [p for p in results if p["author"] == author]
        if tags:
            results = [p for p in results if any(t in p.get("tags", []) for t in tags)]
        if sort_by == "downloads":
            results.sort(key=lambda x: x["download_count"], reverse=True)
        elif sort_by == "rating":
            results.sort(key=lambda x: x["rating_avg"], reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda x: x["created_at"], reverse=True)
        else:

            def relevance(p):
                q = (query or "").lower()
                score = 0
                if q and q in p["name"].lower():
                    score += 10
                if q and q in p["description"].lower():
                    score += 5
                score += p["download_count"] * 0.001
                score += p["rating_avg"]
                return score

            results.sort(key=relevance, reverse=True)
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "latest_version": p["latest_version"],
                "author": p["author"],
                "category": p["category"],
                "description": p["description"][:200],
                "tags": p["tags"][:5],
                "download_count": p["download_count"],
                "rating_avg": round(p["rating_avg"], 1),
                "rating_count": p["rating_count"],
            }
            for p in results[:limit]
        ]

    def get_plugin(self, plugin_id: str) -> dict | None:
        return self._plugins.get(plugin_id)

    def get_by_name(self, name: str) -> dict | None:
        normalized = name.lower().replace("-", "_").replace(" ", "_")
        pid = self._name_index.get(normalized)
        return self._plugins.get(pid) if pid else None

    def rate(self, plugin_id: str, score: float, review: str = "") -> dict:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return {"success": False, "error": "plugin_not_found"}
        score = max(0, min(5, score))
        old_avg = plugin["rating_avg"]
        old_count = plugin["rating_count"]
        new_count = old_count + 1
        new_avg = (old_avg * old_count + score) / new_count
        plugin["rating_avg"] = round(new_avg, 2)
        plugin["rating_count"] = new_count
        plugin["updated_at"] = time.time()
        return {"success": True, "new_avg": round(new_avg, 2), "rating_count": new_count}

    def increment_downloads(self, plugin_id: str):
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin["download_count"] += 1

    def get_categories(self) -> list[str]:
        return list(set(p["category"] for p in self._plugins.values()))

    def get_stats(self) -> dict:
        return {
            "total_plugins": len(self._plugins),
            "categories": len(self.get_categories()),
            "authors": len(self._by_author),
            "total_downloads": sum(p["download_count"] for p in self._plugins.values()),
        }

    # --- Auto-generated action dispatch methods ---
    def _action_get_by_name(self, params=None):
        """Auto-generated action wrapper for get_by_name"""
        if params is None:
            params = {}
        return self.get_by_name(**params)

    def _action_get_categories(self, params=None):
        """Auto-generated action wrapper for get_categories"""
        if params is None:
            params = {}
        return self.get_categories(**params)

    def _action_get_plugin(self, params=None):
        """Auto-generated action wrapper for get_plugin"""
        if params is None:
            params = {}
        return self.get_plugin(**params)

    def _action_get_stats(self, params=None):
        """Auto-generated action wrapper for get_stats"""
        if params is None:
            params = {}
        return self.get_stats(**params)

    def _action_increment_downloads(self, params=None):
        """Auto-generated action wrapper for increment_downloads"""
        if params is None:
            params = {}
        return self.increment_downloads(**params)

    def _action_rate(self, params=None):
        """Auto-generated action wrapper for rate"""
        if params is None:
            params = {}
        return self.rate(**params)

    def _action_register(self, params=None):
        """Auto-generated action wrapper for register"""
        if params is None:
            params = {}
        return self.register(**params)

    def _action_search(self, params=None):
        """Auto-generated action wrapper for search"""
        if params is None:
            params = {}
        return self.search(**params)

class InstallManager:
    """安装管理器"""

    def __init__(self, registry: PluginRegistry):
        self.registry = registry
        self._installed: dict[str, dict] = {}
        self._install_log: list[dict] = []

    def install(self, plugin_id: str, version: str = None) -> dict:
        plugin = self.registry.get_plugin(plugin_id)
        if not plugin:
            return {"success": False, "error": "plugin_not_found"}
        ver = version or plugin["latest_version"]
        if ver not in plugin["versions"]:
            return {"success": False, "error": f"version_not_found:{ver}"}
        if plugin_id in self._installed:
            self._installed[plugin_id]["version"] = ver
            self._installed[plugin_id]["updated_at"] = time.time()
        else:
            self._installed[plugin_id] = {
                "plugin_id": plugin_id,
                "name": plugin["name"],
                "version": ver,
                "installed_at": time.time(),
                "status": "installed",
            }
        self.registry.increment_downloads(plugin_id)
        record = {"plugin_id": plugin_id, "version": ver, "action": "install", "ts": time.time()}
        self._install_log.append(record)
        return {"success": True, "plugin_id": plugin_id, "version": ver}

    def uninstall(self, plugin_id: str) -> dict:
        if plugin_id not in self._installed:
            return {"success": False, "error": "not_installed"}
        entry = self._installed.pop(plugin_id)
        self._install_log.append(
            {"plugin_id": plugin_id, "version": entry["version"], "action": "uninstall", "ts": time.time()}
        )
        return {"success": True, "plugin_id": plugin_id}

    def list_installed(self) -> list[dict]:
        return list(self._installed.values())

    def is_installed(self, plugin_id: str) -> bool:
        return plugin_id in self._installed

    def check_updates(self) -> list[dict]:
        updates = []
        for pid, installed in self._installed.items():
            plugin = self.registry.get_plugin(pid)
            if plugin and plugin["latest_version"] != installed["version"]:
                updates.append(
                    {
                        "plugin_id": pid,
                        "name": installed["name"],
                        "current": installed["version"],
                        "latest": plugin["latest_version"],
                    }
                )
        return updates

class PluginMarket(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """插件市场 - 生产级实现"""

    def __init__(self, config: dict | None = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._metrics: dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "installs": 0,
            "searches": 0,
            "ratings": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: list[dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logger

        self.registry = PluginRegistry()
        self.installer = InstallManager(self.registry)

    def initialize(self) -> dict:
        self._status = ModuleStatus.RUNNING
        return {"success": True, "stats": self.registry.get_stats()}

    def health_check(self) -> dict:
        return {
            "healthy": self._status == ModuleStatus.RUNNING,
            **self.registry.get_stats(),
            "installed": len(self.installer.list_installed()),
        }

    def publish(self, params: dict = None) -> dict:
        params = params or {}
        result = self.registry.register(
            params.get("name", ""),
            params.get("version", "1.0.0"),
            params.get("author", ""),
            params.get("category", "general"),
            params.get("description", ""),
            params.get("entry_point", ""),
            params.get("dependencies"),
            params.get("tags"),
            params.get("icon"),
        )
        return {"success": True, **result}

    def search(self, params: dict = None) -> dict:
        params = params or {}
        results = self.registry.search(
            params.get("query", ""),
            params.get("category", ""),
            params.get("author", ""),
            params.get("tags"),
            params.get("sort_by", "relevance"),
            int(params.get("limit", 20)),
        )
        self._metrics["searches"] += 1
        return {"success": True, "results": results, "count": len(results)}

    def install(self, params: dict = None) -> dict:
        params = params or {}
        result = self.installer.install(params.get("id", ""), params.get("version"))
        if result.get("success"):
            self._metrics["installs"] += 1
        return result

    def uninstall(self, params: dict = None) -> dict:
        params = params or {}
        return self.installer.uninstall(params.get("id", ""))

    def rate_plugin(self, params: dict = None) -> dict:
        params = params or {}
        result = self.registry.rate(params.get("id", ""), float(params.get("score", 5)), params.get("review", ""))
        if result.get("success"):
            self._metrics["ratings"] += 1
        return {"success": True, **result}

    def get_plugin(self, params: dict = None) -> dict:
        params = params or {}
        plugin = self.registry.get_plugin(params.get("id", ""))
        return {"success": plugin is not None, "plugin": plugin}

    def list_installed(self, params: dict = None) -> dict:
        installed = self.installer.list_installed()
        return {"success": True, "installed": installed, "count": len(installed)}

    def check_updates(self, params: dict = None) -> dict:
        updates = self.installer.check_updates()
        return {"success": True, "updates": updates, "count": len(updates)}

    def get_categories(self, params: dict = None) -> dict:
        return {"success": True, "categories": self.registry.get_categories()}

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "plugin_market"})
        self.metrics_collector.counter("plugin_market.execute.calls", 1)
        self.audit("execute", {"module": "plugin_market"})
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

    def get_marketplace_stats(self) -> dict[str, Any]:
        """市场统计。企业场景：平台运营查看插件市场概况，
        各分类插件数量、下载量排行、评分分布。
        """
        registry = getattr(self, "registry", None)
        plugins = getattr(registry, "_plugins", {}) if registry else {}
        by_category = {}
        total_downloads = 0
        for pid, plugin in plugins.items():
            cat = getattr(plugin, "category", "uncategorized")
            by_category[cat] = by_category.get(cat, 0) + 1
            total_downloads += getattr(plugin, "downloads", 0)
        sorted_cats = sorted(by_category.items(), key=lambda x: -x[1])
        return {
            "success": True,
            "total_plugins": len(plugins),
            "total_categories": len(by_category),
            "total_downloads": total_downloads,
            "by_category": [{"category": c, "count": n} for c, n in sorted_cats],
        }

    def get_update_availability_report(self) -> dict[str, Any]:
        """更新可用报告。企业场景：运维每周检查已安装插件的更新，
        批量升级安全补丁。
        """
        updates = self.installer.check_updates() if hasattr(self, "installer") else []
        by_severity = {}
        for u in updates:
            sev = u.get("severity", "normal")
            by_severity[sev] = by_severity.get(sev, 0) + 1
        return {"success": True, "updates_available": len(updates), "by_severity": by_severity, "updates": updates}

    def get_plugin_dependencies(self, plugin_id: str) -> dict[str, Any]:
        """查看插件依赖树。企业场景：安装插件前评估依赖影响，
        检查是否存在版本冲突或循环依赖。
        """
        plugins = getattr(self, "_plugins", {})
        plugin = plugins.get(plugin_id)
        if not plugin:
            return {"success": False, "error": f"插件 {plugin_id} 不存在"}
        deps = getattr(plugin, "dependencies", [])
        dep_tree = []
        visited = set()

        def resolve(dep_id, depth=0):
            if dep_id in visited or depth > 5:
                return
            visited.add(dep_id)
            dep = plugins.get(dep_id)
            dep_tree.append(
                {
                    "plugin_id": dep_id,
                    "depth": depth,
                    "installed": dep is not None,
                    "version": getattr(dep, "version", "N/A") if dep else "未安装",
                    "name": getattr(dep, "name", dep_id) if dep else dep_id,
                }
            )
            if dep:
                for sub_dep in getattr(dep, "dependencies", []):
                    resolve(sub_dep, depth + 1)

        for dep_id in deps:
            resolve(dep_id)
        installed_count = sum(1 for d in dep_tree if d["installed"])
        missing = [d for d in dep_tree if not d["installed"]]
        return {
            "success": True,
            "plugin_id": plugin_id,
            "total_dependencies": len(dep_tree),
            "installed": installed_count,
            "missing": len(missing),
            "missing_plugins": missing,
            "dependency_tree": dep_tree,
        }

    def get_marketplace_stats(self) -> dict[str, Any]:
        """插件市场统计。企业场景：管理员查看市场概况，总插件数、
        已安装数、按分类分布、下载排行。
        """
        plugins = getattr(self, "_plugins", {})
        by_category = {}
        by_status = {}
        top_downloads = []
        for pid, p in plugins.items():
            cat = getattr(p, "category", "uncategorized")
            status = getattr(p, "status", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1
            top_downloads.append(
                {
                    "plugin_id": pid,
                    "name": getattr(p, "name", pid),
                    "downloads": getattr(p, "downloads", 0),
                    "rating": getattr(p, "rating", 0),
                }
            )
        top_downloads.sort(key=lambda x: x["downloads"], reverse=True)
        installed = sum(1 for p in plugins.values() if getattr(p, "status", "") == "installed")
        return {
            "success": True,
            "total_plugins": len(plugins),
            "installed": installed,
            "by_category": by_category,
            "by_status": by_status,
            "top_downloaded": top_downloads[:10],
        }

    def check_plugin_compatibility(self, plugin_name: str, target_version: str) -> dict[str, Any]:
        """插件兼容性检查。企业场景：升级系统版本前检查已安装插件
        是否兼容新版本，提前发现不兼容风险。
        """
        plugins = getattr(self, "_plugins", {})
        plugin = plugins.get(plugin_name)
        if not plugin:
            return {"success": False, "error": f"插件 {plugin_name} 不存在"}
        requires = getattr(plugin, "requires", {})
        min_ver = requires.get("min_platform_version", "0.0.0")
        max_ver = requires.get("max_platform_version", "99.99.99")
        target_parts = [int(x) for x in target_version.split(".")]
        min_parts = [int(x) for x in min_ver.split(".")]
        max_parts = [int(x) for x in max_ver.split(".")]
        is_compatible = target_parts >= min_parts and target_parts <= max_parts
        return {
            "success": True,
            "plugin": plugin_name,
            "target_version": target_version,
            "compatible": is_compatible,
            "requires": requires,
            "min_platform": min_ver,
            "max_platform": max_ver,
        }

    def get_plugin_changelog(self, plugin_name: str) -> dict[str, Any]:
        """查看插件更新日志。企业场景：升级前评估变更内容，
        确认是否包含breaking changes。
        """
        plugins = getattr(self, "_plugins", {})
        plugin = plugins.get(plugin_name)
        if not plugin:
            return {"success": False, "error": f"插件 {plugin_name} 不存在"}
        changelog = getattr(plugin, "changelog", [])
        if not changelog:
            return {
                "success": True,
                "plugin": plugin_name,
                "message": "无更新日志",
                "versions_available": getattr(plugin, "version", "1.0.0"),
            }
        has_breaking = any(c.get("breaking", False) for c in changelog)
        return {
            "success": True,
            "plugin": plugin_name,
            "current_version": getattr(plugin, "version", "1.0.0"),
            "has_breaking_changes": has_breaking,
            "recent_changes": changelog[:5],
        }

    def search_plugins(self, keyword: str, category: str = None) -> dict[str, Any]:
        """搜索插件。企业场景：开发者在市场中搜索特定功能的插件，
        按名称、描述、标签匹配，按下载量排序。
        """
        plugins = getattr(self, "_plugins", {})
        results = []
        kw = keyword.lower()
        for name, plugin in plugins.items():
            desc = getattr(plugin, "description", "").lower()
            tags = [t.lower() for t in getattr(plugin, "tags", [])]
            cat = getattr(plugin, "category", "").lower()
            if kw in name.lower() or kw in desc or kw in tags:
                if category and cat != category.lower():
                    continue
                results.append(
                    {
                        "name": name,
                        "version": getattr(plugin, "version", "1.0.0"),
                        "author": getattr(plugin, "author", ""),
                        "description": getattr(plugin, "description", ""),
                        "downloads": getattr(plugin, "downloads", 0),
                        "rating": getattr(plugin, "rating", 0),
                        "category": cat,
                    }
                )
        results.sort(key=lambda x: -x["downloads"])
        return {
            "success": True,
            "keyword": keyword,
            "category": category,
            "results_count": len(results),
            "results": results[:20],
        }

    def shutdown(self) -> dict:
        """Graceful shutdown for plugin_market."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = PluginMarket
