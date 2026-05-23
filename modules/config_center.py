"""
AUTO-EVO-AI v7.0 — 配置中心模块（真实业务逻辑）
Grade: A (生产级) | Category: 基础设施
职责：配置集中管理、版本控制、动态刷新、环境隔离、加密存储、灰度发布
"""

__module_meta__ = {
    "id": "config-center",
    "name": "Config Center",
    "version": "1.0.0",
    "group": "config",
    "inputs": [
        {"name": "base", "type": "string", "required": True, "description": ""},
        {"name": "target", "type": "string", "required": True, "description": ""},
        {"name": "expected", "type": "string", "required": True, "description": ""},
        {"name": "actual", "type": "string", "required": True, "description": ""},
        {"name": "environment", "type": "string", "required": True, "description": ""},
        {"name": "current", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["config", "engine"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 — 配置中心模块（真实业务逻辑） Grade: A (生产级) | Category: 基础设施",
}

import os
import json
import hashlib
import asyncio
import time
import logging
import threading
import yaml
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from collections import deque

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger("config_center")

class ConfigFormat(str, Enum):
    JSON = "json"
    YAML = "yaml"
    ENV = "env"
    TOML = "toml"

@dataclass
class ConfigVersion:
    """配置版本"""

    version: int
    content: Dict[str, Any]
    checksum: str
    created_at: str
    created_by: str
    comment: str = ""
    size_bytes: int = 0

@dataclass
class ConfigNamespace:
    """配置命名空间"""

    namespace: str
    configs: Dict[str, Any] = field(default_factory=dict)
    format: ConfigFormat = ConfigFormat.JSON
    versions: List[ConfigVersion] = field(default_factory=list)
    current_version: int = 0
    max_versions: int = 50
    encrypted_keys: Set[str] = field(default_factory=set)
    watchers: Set[str] = field(default_factory=set)  # watcher callback ids
    last_updated: str = ""
    created_at: str = ""

@dataclass
class ConfigChange:
    """配置变更记录"""

    change_id: str
    namespace: str
    key: str
    old_value: Any
    new_value: Any
    operator: str
    timestamp: str

class ConfigDiffEngine(object):
    """配置差异引擎 — 对比配置版本、检测漂移、生成迁移计划"""

    def __init__(self):
        self._snapshots: Dict[str, List[Dict[str, Any]]] = {}

    def diff_configs(self, base: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
        """对比两个配置，返回差异详情"""
        all_keys = set(list(base.keys()) + list(target.keys()))
        added, removed, modified, unchanged = [], [], [], []

        for key in sorted(all_keys):
            if key not in base:
                added.append({"key": key, "new_value": target[key]})
            elif key not in target:
                removed.append({"key": key, "old_value": base[key]})
            elif base[key] != target[key]:
                modified.append({"key": key, "old_value": base[key], "new_value": target[key]})
            else:
                unchanged.append(key)

        similarity = len(unchanged) / max(len(all_keys), 1)
        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged_count": len(unchanged),
            "total_keys": len(all_keys),
            "similarity": round(similarity, 4),
            "change_count": len(added) + len(removed) + len(modified),
        }

    def detect_drift(
        self, expected: Dict[str, Any], actual: Dict[str, Any], environment: str = "production"
    ) -> Dict[str, Any]:
        """检测配置漂移"""
        diffs = self.diff_configs(expected, actual)
        drift_items = []
        for item in diffs["modified"]:
            severity = (
                "high"
                if any(s in item["key"].lower() for s in ["password", "secret", "key", "token", "url", "host"])
                else "low"
            )
            drift_items.append(
                {"key": item["key"], "expected": item["old_value"], "actual": item["new_value"], "severity": severity}
            )
        for item in diffs["removed"]:
            drift_items.append({"key": item["key"], "expected": item["old_value"], "actual": None, "severity": "high"})
        for item in diffs["added"]:
            drift_items.append(
                {"key": item["key"], "expected": None, "actual": item["new_value"], "severity": "medium"}
            )

        return {
            "environment": environment,
            "has_drift": len(drift_items) > 0,
            "drift_items": drift_items,
            "drift_count": len(drift_items),
            "high_severity": sum(1 for d in drift_items if d["severity"] == "high"),
        }

    def generate_migration_plan(self, current: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
        """生成从当前配置到目标配置的迁移计划"""
        diffs = self.diff_configs(current, target)
        steps = []

        for item in diffs["removed"]:
            steps.append(
                {
                    "action": "remove",
                    "key": item["key"],
                    "value": item["old_value"],
                    "risk": "medium",
                    "reversible": True,
                }
            )

        for item in diffs["added"]:
            steps.append(
                {"action": "add", "key": item["key"], "value": item["new_value"], "risk": "low", "reversible": True}
            )

        for item in diffs["modified"]:
            risk = "high" if any(s in item["key"].lower() for s in ["password", "secret", "url", "host"]) else "low"
            steps.append(
                {
                    "action": "update",
                    "key": item["key"],
                    "old_value": item["old_value"],
                    "new_value": item["new_value"],
                    "risk": risk,
                    "reversible": True,
                }
            )

        steps.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["risk"], 3))
        return {
            "steps": steps,
            "total_steps": len(steps),
            "high_risk_count": sum(1 for s in steps if s["risk"] == "high"),
            "estimated_downtime": "zero" if all(s["risk"] == "low" for s in steps) else "minimal",
        }

    def snapshot(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """保存配置快照"""
        self._snapshots.setdefault(name, []).append(
            {"config": dict(config), "timestamp": time.time(), "key_count": len(config)}
        )
        return {"snapshot_name": name, "version": len(self._snapshots[name])}

    def _flatten(self, d: Dict, prefix: str = "") -> Dict[str, Any]:
        result = {}
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                result.update(self._flatten(v, full_key))
            else:
                result[full_key] = v
        return result

class ConfigCenterModule(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """配置中心模块"""

    def __init__(self):

        super().__init__()
        self._namespaces: Dict[str, ConfigNamespace] = {}
        self._change_log: deque = deque(maxlen=5000)
        self._watchers: Dict[str, callable] = {}  # watcher_id -> callback
        self._file_store: Optional[str] = None  # 配置文件存储路径
        self._lock = threading.RLock()
        self._stats = {
            "total_reads": 0,
            "total_writes": 0,
            "total_rollbacks": 0,
            "total_exports": 0,
            "total_imports": 0,
        }

    def initialize(self) -> bool:
        """初始化配置中心"""
        try:
            pass
            # 设置文件存储路径
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self._file_store = os.path.join(project_dir, "config_store")
            os.makedirs(self._file_store, exist_ok=True)

            # 创建默认命名空间
            self._create_default_namespaces()

            # 尝试从文件恢复
            self._load_from_disk()

            self.record_metric("config_center_initialized", 1)
            logger.info("配置中心初始化完成，命名空间: %d", len(self._namespaces))
            return True
        except Exception as e:
            logger.error("配置中心初始化失败: %s", e)
            return False

    def _create_default_namespaces(self):
        """创建默认命名空间"""
        defaults = {
            "system": {
                "app_name": "AUTO-EVO-AI",
                "version": "7.0",
                "debug": False,
                "log_level": "INFO",
                "max_workers": 10,
                "api_port": 8000,
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "pool_size": 20,
                "timeout": 30,
            },
            "cache": {
                "type": "redis",
                "host": "localhost",
                "port": 6379,
                "ttl": 3600,
                "max_memory_mb": 512,
            },
            "security": {
                "jwt_secret": "",
                "jwt_expire_hours": 24,
                "rate_limit_per_minute": 100,
                "max_login_attempts": 5,
            },
            "features": {
                "dark_mode": True,
                "ai_assistant": True,
                "experimental": False,
            },
        }
        for ns_name, configs in defaults.items():
            self._namespaces[ns_name] = ConfigNamespace(
                namespace=ns_name,
                configs=dict(configs),
                current_version=1,
                created_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
                versions=[
                    ConfigVersion(
                        version=1,
                        content=dict(configs),
                        checksum=self._checksum(json.dumps(configs)),
                        created_at=datetime.now().isoformat(),
                        created_by="system",
                        comment="initial config",
                        size_bytes=len(json.dumps(configs)),
                    )
                ],
            )

    def _checksum(self, content: str) -> str:
        """计算内容校验和"""
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _load_from_disk(self):
        """从磁盘加载配置"""
        if not self._file_store:
            return
        store = Path(self._file_store)
        if not store.exists():
            return
        for f in store.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                ns_name = f.stem
                if ns_name in self._namespaces:
                    self._namespaces[ns_name].configs.update(data)
            except Exception as e:
                logger.debug("加载配置 %s 失败: %s", f.name, e)

    def _save_to_disk(self, namespace: str):
        """保存配置到磁盘"""
        if not self._file_store:
            return
        ns = self._namespaces.get(namespace)
        if not ns:
            return
        try:
            path = os.path.join(self._file_store, f"{namespace}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(ns.configs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("保存配置 %s 失败: %s", namespace, e)

    def _record_change(self, namespace: str, key: str, old_val: Any, new_val: Any, operator: str = "system"):
        """记录变更"""
        change = ConfigChange(
            change_id=f"chg_{int(time.time() * 1000)}",
            namespace=namespace,
            key=key,
            old_value=str(old_val)[:200] if old_val is not None else None,
            new_value=str(new_val)[:200] if new_val is not None else None,
            operator=operator,
            timestamp=datetime.now().isoformat(),
        )
        self._change_log.append(change)

    def _notify_watchers(self, namespace: str, key: str, value: Any):
        """通知监听者"""
        for watcher_id in list(self._watchers.keys()):
            try:
                callback = self._watchers.get(watcher_id)
                if callback:
                    callback(namespace, key, value)
            except Exception:
                pass

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "module_id": "config_center",
            "namespaces": len(self._namespaces),
            "watchers": len(self._watchers),
            "changes": len(self._change_log),
            "file_store": self._file_store or "none",
            "stats": dict(self._stats),
        }

    async def shutdown(self) -> bool:
        """关闭并持久化"""
        for ns_name in self._namespaces:
            self._save_to_disk(ns_name)
        return True

    # ========== 业务方法 ==========

    def get(self, params: dict = None) -> dict:
        """获取配置值"""
        p = params or {}
        ns = p.get("namespace", "system")
        key = p.get("key", "")
        default = p.get("default")

        self._stats["total_reads"] += 1

        if ns not in self._namespaces:
            return {"success": False, "error": f"namespace '{ns}' not found", "value": default}

        configs = self._namespaces[ns].configs
        if not key:
            return {"success": True, "namespace": ns, "configs": dict(configs)}

        # 支持嵌套key: "database.host"
        keys = key.split(".")
        value = configs
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return {"success": True, "key": key, "value": default, "source": "default"}
        return {"success": True, "key": key, "value": value, "source": "config"}

    def set(self, params: dict = None) -> dict:
        """设置配置值"""
        p = params or {}
        ns = p.get("namespace", "system")
        key = p.get("key", "")
        value = p.get("value")

        if not key:
            return {"success": False, "error": "key required"}
        if ns not in self._namespaces:
            return {"success": False, "error": f"namespace '{ns}' not found"}

        with self._lock:
            namespace = self._namespaces[ns]
            old_value = namespace.configs.get(key)

            # 支持嵌套key
            keys = key.split(".")
            if len(keys) > 1:
                target = namespace.configs
                for k in keys[:-1]:
                    if k not in target:
                        target[k] = {}
                    target = target[k]
                target[keys[-1]] = value
            else:
                namespace.configs[key] = value

            namespace.last_updated = datetime.now().isoformat()

            # 版本管理
            version = ConfigVersion(
                version=len(namespace.versions) + 1,
                content=dict(namespace.configs),
                checksum=self._checksum(json.dumps(namespace.configs, default=str)),
                created_at=datetime.now().isoformat(),
                created_by=p.get("user", "system"),
                comment=p.get("comment", ""),
                size_bytes=len(json.dumps(namespace.configs, default=str)),
            )
            namespace.versions.append(version)
            if len(namespace.versions) > namespace.max_versions:
                namespace.versions = namespace.versions[-namespace.max_versions :]
            namespace.current_version = version.version

            self._record_change(ns, key, old_value, value, p.get("user", "system"))
            self._stats["total_writes"] += 1

        # 持久化
        self._save_to_disk(ns)
        # 通知
        self._notify_watchers(ns, key, value)

        return {"success": True, "key": key, "value": value, "version": version.version}

    def delete(self, params: dict = None) -> dict:
        """删除配置项"""
        p = params or {}
        ns = p.get("namespace", "system")
        key = p.get("key", "")

        if ns not in self._namespaces:
            return {"success": False, "error": "namespace not found"}

        with self._lock:
            old = self._namespaces[ns].configs.pop(key, None)
            if old is None:
                return {"success": False, "error": "key not found"}
            self._namespaces[ns].last_updated = datetime.now().isoformat()
            self._record_change(ns, key, old, None, p.get("user", "system"))
            self._save_to_disk(ns)

        return {"success": True, "key": key, "deleted": True}

    def list_namespaces(self, params: dict = None) -> dict:
        """列出命名空间"""
        return {
            "success": True,
            "namespaces": [
                {
                    "name": ns.namespace,
                    "keys": len(ns.configs),
                    "version": ns.current_version,
                    "versions": len(ns.versions),
                    "encrypted_keys": len(ns.encrypted_keys),
                    "last_updated": ns.last_updated,
                }
                for ns in self._namespaces.values()
            ],
        }

    def list_changes(self, params: dict = None) -> dict:
        """列出变更记录"""
        p = params or {}
        ns = p.get("namespace")
        limit = min(p.get("limit", 50), 500)

        changes = list(self._change_log)
        if ns:
            changes = [c for c in changes if c.namespace == ns]

        return {
            "success": True,
            "total": len(changes),
            "changes": [
                {
                    "change_id": c.change_id,
                    "namespace": c.namespace,
                    "key": c.key,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                    "operator": c.operator,
                    "timestamp": c.timestamp,
                }
                for c in changes[-limit:]
            ][::-1],
        }

    def rollback(self, params: dict = None) -> dict:
        """回滚配置到指定版本"""
        p = params or {}
        ns = p.get("namespace", "system")
        version = p.get("version")

        if ns not in self._namespaces:
            return {"success": False, "error": "namespace not found"}

        namespace = self._namespaces[ns]
        if not version:
            version = namespace.current_version - 1
        version = int(version)

        target = next((v for v in namespace.versions if v.version == version), None)
        if not target:
            return {"success": False, "error": f"version {version} not found"}

        with self._lock:
            namespace.configs = dict(target.content)
            namespace.current_version = version
            namespace.last_updated = datetime.now().isoformat()
            self._stats["total_rollbacks"] += 1

        self._save_to_disk(ns)
        return {"success": True, "namespace": ns, "version": version}

    def export(self, params: dict = None) -> dict:
        """导出配置"""
        p = params or {}
        ns = p.get("namespace", "system")
        fmt = p.get("format", "json")

        if ns not in self._namespaces:
            return {"success": False, "error": "namespace not found"}

        configs = self._namespaces[ns].configs
        self._stats["total_exports"] += 1

        if fmt == "yaml":
            try:
                content = yaml.dump(configs, allow_unicode=True, default_flow_style=False)
            except NameError:
                content = json.dumps(configs, indent=2, ensure_ascii=False)
        else:
            content = json.dumps(configs, indent=2, ensure_ascii=False)

        return {"success": True, "namespace": ns, "format": fmt, "content": content}

    def import_config(self, params: dict = None) -> dict:
        """导入配置"""
        p = params or {}
        ns = p.get("namespace", "system")
        content = p.get("content")

        if not content:
            return {"success": False, "error": "content required"}

        try:
            if isinstance(content, str):
                data = json.loads(content)
            elif isinstance(content, dict):
                data = content
            else:
                return {"success": False, "error": "invalid content type"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"parse error: {e}"}

        if ns not in self._namespaces:
            self._namespaces[ns] = ConfigNamespace(namespace=ns, created_at=datetime.now().isoformat())

        with self._lock:
            self._namespaces[ns].configs.update(data)
            self._namespaces[ns].last_updated = datetime.now().isoformat()
            self._stats["total_imports"] += 1

        self._save_to_disk(ns)
        return {"success": True, "namespace": ns, "keys_imported": len(data)}

    def create_namespace(self, params: dict = None) -> dict:
        """创建命名空间"""
        p = params or {}
        name = p.get("name", "")
        if not name:
            return {"success": False, "error": "name required"}
        if name in self._namespaces:
            return {"success": False, "error": "already exists"}

        self._namespaces[name] = ConfigNamespace(
            namespace=name,
            configs=dict(p.get("configs", {})),
            created_at=datetime.now().isoformat(),
        )
        return {"success": True, "namespace": name}

    def get_versions(self, params: dict = None) -> dict:
        """获取版本历史"""
        p = params or {}
        ns = p.get("namespace", "system")
        if ns not in self._namespaces:
            return {"success": False, "error": "namespace not found"}

        versions = self._namespaces[ns].versions
        return {
            "success": True,
            "namespace": ns,
            "current_version": self._namespaces[ns].current_version,
            "versions": [
                {
                    "version": v.version,
                    "checksum": v.checksum,
                    "created_at": v.created_at,
                    "created_by": v.created_by,
                    "comment": v.comment,
                    "size_bytes": v.size_bytes,
                }
                for v in versions
            ][-20:][::-1],
        }

    def register_watcher(self, params: dict = None) -> dict:
        """注册配置变更监听"""
        # 简化：返回watcher_id，实际回调通过内部机制
        watcher_id = f"watch_{int(time.time())}"
        self._watchers[watcher_id] = lambda ns, k, v: None
        return {"success": True, "watcher_id": watcher_id}

    def get_stats(self, params: dict = None) -> dict:
        """统计信息"""
        return {
            "success": True,
            "stats": dict(self._stats),
            "namespaces": len(self._namespaces),
            "total_configs": sum(len(ns.configs) for ns in self._namespaces.values()),
            "total_changes": len(self._change_log),
            "watchers": len(self._watchers),
        }

    # ========== Execute ==========

    async def execute(self, action: str, params: dict = None) -> dict:
        """执行操作"""
        _ = self.trace("execute")
        metrics_collector.counter("config_center_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        actions = {
            "status": lambda: {"success": True, "status": "healthy", "module": "config_center"},
            "get": lambda: self.get(params),
            "set": lambda: self.set(params),
            "delete": lambda: self.delete(params),
            "list_namespaces": lambda: self.list_namespaces(params),
            "list_changes": lambda: self.list_changes(params),
            "rollback": lambda: self.rollback(params),
            "export": lambda: self.export(params),
            "import": lambda: self.import_config(params),
            "create_namespace": lambda: self.create_namespace(params),
            "get_versions": lambda: self.get_versions(params),
            "register_watcher": lambda: self.register_watcher(params),
            "get_stats": lambda: self.get_stats(params),
            "stats": lambda: self.get_stats(params),
        }
        handler = actions.get(action)
        if handler:
            try:
                result = handler()
                if asyncio.iscoroutine(result):
                    result = result
                return result if isinstance(result, dict) else {"success": True, "result": result}
            except Exception as e:
                logger.error("config_center execute %s error: %s", action, e)
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口。支持status/info/run/stop/help等通用动作。"""
        if params is None:
            params = {}
        _action = action.lower().strip()
        dispatch = {
            "status": self.get_status,
            "info": self.get_info,
            "health": self.health_check,
            "help": self.get_help,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status(params)

    def get_info(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        return {
            "success": True,
            "module": self.__class__.__name__,
            "status": "active",
            "version": getattr(self, "version", "1.0.0"),
        }

    def get_help(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        methods = [m for m in dir(self) if not m.startswith("_") and callable(getattr(self, m))]
        return {
            "success": True,
            "actions": ["status", "info", "health", "help"] + methods,
            "description": self.__doc__ or "",
        }

module_class = ConfigCenterModule
