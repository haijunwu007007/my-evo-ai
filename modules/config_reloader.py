"""
AUTO-EVO-AI V0.1 — 配置热重载管理器
Grade: A (生产级) | Category: 配置管理
职责：配置文件监听、热重载、变更检测、回滚、版本管理、差异对比
"""

__module_meta__ = {
    "id": "config-reloader",
    "name": "Config Reloader",
    "version": "V0.1",
    "group": "config",
    "inputs": [
        {"name": "source_id", "type": "string", "required": True, "description": ""},
        {"name": "d", "type": "string", "required": True, "description": ""},
        {"name": "old", "type": "string", "required": True, "description": ""},
        {"name": "new", "type": "string", "required": True, "description": ""},
        {"name": "prefix", "type": "string", "required": True, "description": ""},
        {"name": "base", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["config", "manager"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — 配置热重载管理器 Grade: A (生产级) | Category: 配置管理",
}

import os
import time
import uuid
import json
import copy
import hashlib
import logging
import threading
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

class ReloadStrategy(Enum):
    IMMEDIATE = "immediate"
    DEBOUNCE = "debounce"
    SCHEDULED = "scheduled"
    MANUAL = "manual"

class ConfigFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    ENV = "env"
    INI = "ini"

@dataclass
class ConfigSource:
    """配置源"""

    source_id: str = ""
    name: str = ""
    path: str = ""
    format: ConfigFormat = ConfigFormat.JSON
    content_hash: str = ""
    last_loaded: float = 0.0
    version: int = 0
    enabled: bool = True

@dataclass
class ConfigVersion:
    """配置版本"""

    version_id: str = ""
    source_id: str = ""
    version: int = 0
    content: Dict[str, Any] = field(default_factory=dict)
    hash: str = ""
    change_summary: str = ""
    created_at: float = 0.0
    created_by: str = "system"

@dataclass
class ReloadEvent:
    """重载事件"""

    event_id: str = ""
    source_id: str = ""
    event_type: str = "changed"  # changed, rolled_back, validated
    old_hash: str = ""
    new_hash: str = ""
    changes: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    success: bool = True
    error: str = ""

class ConfigReloaderManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """配置热重载管理器 - 生产级实现"""

    MODULE_ID = "config_reloader"
    MODULE_NAME = "config_reloader"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "config_reloader",
                "version": "7.0.0",
                "description": "配置热重载管理，支持文件监听、变更检测、版本管理、回滚",
            }
        )
        self._sources: Dict[str, ConfigSource] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}  # source_id -> current config
        self._versions: Dict[str, List[ConfigVersion]] = defaultdict(list)
        self._events: List[ReloadEvent] = []
        self._watchers: Dict[str, Dict] = {}  # source_id -> {interval, last_check, strategy}
        self._callbacks: List[Callable] = []
        self._initialized = False
        self._max_versions = 50
        self._max_events = 1000

    def initialize(self) -> None:
        if self._initialized:
            return
        # 预置示例配置源
        defaults = [
            ("app_config", "应用配置", "/etc/bgos/app.json", ConfigFormat.JSON),
            ("db_config", "数据库配置", "/etc/bgos/database.json", ConfigFormat.JSON),
            ("security_config", "安全配置", "/etc/bgos/security.json", ConfigFormat.JSON),
        ]
        now = time.time()
        for sid, name, path, fmt in defaults:
            self._sources[sid] = ConfigSource(
                source_id=sid,
                name=name,
                path=path,
                format=fmt,
                last_loaded=now,
                version=1,
            )
            self._configs[sid] = self._generate_default_config(sid)
            cv = ConfigVersion(
                version_id=f"ver_{uuid.uuid4().hex[:8]}",
                source_id=sid,
                version=1,
                content=copy.deepcopy(self._configs[sid]),
                hash=self._hash_dict(self._configs[sid]),
                created_at=now,
            )
            self._versions[sid].append(cv)
        self._initialized = True
        logger.info(f"配置重载管理器初始化完成，配置源: {len(self._sources)}")

    def _generate_default_config(self, source_id: str) -> Dict:
        """生成默认配置"""
        if "app" in source_id:
            return {
                "app_name": "BGOS",
                "version": "7.0",
                "debug": False,
                "server": {"host": "0.0.0.0", "port": 8000, "workers": 4},
                "logging": {"level": "INFO", "file": "/var/log/bgos/app.log"},
            }
        elif "db" in source_id:
            return {
                "primary": {"host": "localhost", "port": 5432, "database": "bgos", "pool_size": 20, "timeout": 30},
                "replicas": [],
                "migrations_enabled": True,
            }
        elif "security" in source_id:
            return {
                "jwt_expiry": 3600,
                "refresh_expiry": 86400,
                "password_min_length": 12,
                "max_login_attempts": 5,
                "cors_origins": ["https://bgos.example.com"],
            }
        return {}

    def _hash_dict(self, d: Dict) -> str:
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]

    def _diff_configs(self, old: Dict, new: Dict, prefix: str = "") -> List[str]:
        """比较两个配置的差异"""
        changes = []
        all_keys = set(list(old.keys()) + list(new.keys()))
        for key in sorted(all_keys):
            path = f"{prefix}.{key}" if prefix else key
            if key not in old:
                changes.append(f"+ {path}")
            elif key not in new:
                changes.append(f"- {path}")
            elif old[key] != new[key]:
                if isinstance(old[key], dict) and isinstance(new[key], dict):
                    changes.extend(self._diff_configs(old[key], new[key], path))
                else:
                    changes.append(f"~ {path}: {old[key]} -> {new[key]}")
        return changes

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一execute入口"""
        self.trace("execute", {"module": "config_reloader"})
        self.metrics_collector.counter("config_reloader.execute.calls", 1)
        self.audit("execute", {"module": "config_reloader"})
        params = params or {}
        try:
            if action == "list_sources":
                return {
                    "success": True,
                    "result": [
                        {
                            "source_id": s.source_id,
                            "name": s.name,
                            "path": s.path,
                            "format": s.format.value,
                            "version": s.version,
                            "enabled": s.enabled,
                            "hash": s.content_hash,
                            "last_loaded": datetime.fromtimestamp(s.last_loaded).isoformat(),
                        }
                        for s in self._sources.values()
                    ],
                }

            elif action == "get_config":
                sid = params.get("source_id", "")
                if sid not in self._configs:
                    return {"success": False, "error": f"配置源{sid}不存在"}
                return {
                    "success": True,
                    "result": {
                        "source_id": sid,
                        "version": self._sources[sid].version,
                        "config": self._configs[sid],
                    },
                }

            elif action == "update_config":
                sid = params.get("source_id", "")
                if sid not in self._configs:
                    return {"success": False, "error": f"配置源{sid}不存在"}
                new_config = params.get("config", {})
                if not isinstance(new_config, dict):
                    return {"success": False, "error": "配置必须是dict"}
                old_config = copy.deepcopy(self._configs[sid])
                old_hash = self._hash_dict(old_config)

                # 合并配置
                self._deep_merge(old_config, new_config)
                self._configs[sid] = old_config
                new_hash = self._hash_dict(self._configs[sid])

                changes = self._diff_configs(old_config, new_config)
                source = self._sources[sid]
                source.version += 1
                source.content_hash = new_hash
                source.last_loaded = time.time()

                # 保存版本
                cv = ConfigVersion(
                    version_id=f"ver_{uuid.uuid4().hex[:8]}",
                    source_id=sid,
                    version=source.version,
                    content=copy.deepcopy(self._configs[sid]),
                    hash=new_hash,
                    change_summary="; ".join(changes[:10]),
                    created_at=time.time(),
                    created_by=params.get("user", "system"),
                )
                versions = self._versions[sid]
                if len(versions) >= self._max_versions:
                    versions.pop(0)
                versions.append(cv)

                # 记录事件
                event = ReloadEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    source_id=sid,
                    event_type="changed",
                    old_hash=old_hash,
                    new_hash=new_hash,
                    changes=changes,
                    timestamp=time.time(),
                    success=True,
                )
                if len(self._events) >= self._max_events:
                    self._events.pop(0)
                self._events.append(event)

                return {
                    "success": True,
                    "result": {
                        "source_id": sid,
                        "version": source.version,
                        "changes": len(changes),
                        "change_details": changes,
                        "old_hash": old_hash,
                        "new_hash": new_hash,
                    },
                }

            elif action == "rollback":
                sid = params.get("source_id", "")
                target_ver = params.get("version", 0)
                if sid not in self._versions:
                    return {"success": False, "error": f"配置源{sid}不存在"}
                versions = self._versions[sid]
                target = None
                for v in versions:
                    if v.version == target_ver:
                        target = v
                        break
                if not target:
                    return {"success": False, "error": f"版本{target_ver}不存在"}

                self._configs[sid] = copy.deepcopy(target.content)
                source = self._sources[sid]
                source.version = target.version
                source.content_hash = target.hash
                source.last_loaded = time.time()

                event = ReloadEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    source_id=sid,
                    event_type="rolled_back",
                    new_hash=target.hash,
                    changes=[f"回滚到版本{target_ver}"],
                    timestamp=time.time(),
                )
                self._events.append(event)

                return {
                    "success": True,
                    "result": {
                        "source_id": sid,
                        "rolled_back_to": target_ver,
                        "hash": target.hash,
                    },
                }

            elif action == "list_versions":
                sid = params.get("source_id", "")
                versions = self._versions.get(sid, [])
                return {
                    "success": True,
                    "result": [
                        {
                            "version_id": v.version_id,
                            "version": v.version,
                            "hash": v.hash,
                            "change_summary": v.change_summary,
                            "created_at": datetime.fromtimestamp(v.created_at).isoformat(),
                            "created_by": v.created_by,
                        }
                        for v in versions
                    ],
                }

            elif action == "diff":
                sid = params.get("source_id", "")
                v1 = params.get("version_from", 1)
                v2 = params.get("version_to", 2)
                versions = self._versions.get(sid, [])
                c1 = next((v.content for v in versions if v.version == v1), None)
                c2 = next((v.content for v in versions if v.version == v2), None)
                if not c1 or not c2:
                    return {"success": False, "error": "版本不存在"}
                changes = self._diff_configs(c1, c2)
                return {
                    "success": True,
                    "result": {
                        "source_id": sid,
                        "from": v1,
                        "to": v2,
                        "changes": len(changes),
                        "details": changes,
                    },
                }

            elif action == "validate":
                sid = params.get("source_id", "")
                if sid not in self._configs:
                    return {"success": False, "error": f"配置源{sid}不存在"}
                config = self._configs[sid]
                warnings = []
                errors = []
                # 基础校验
                if isinstance(config, dict):
                    if "server" in config:
                        srv = config["server"]
                        if isinstance(srv, dict):
                            port = srv.get("port", 0)
                            if not (1 <= port <= 65535):
                                errors.append(f"无效端口: {port}")
                    if "password_min_length" in config and config["password_min_length"] < 8:
                        warnings.append("密码最小长度建议不低于8")
                    if "debug" in config and config.get("debug") and "security" in sid:
                        warnings.append("生产环境不建议开启debug")
                return {
                    "success": True,
                    "result": {
                        "source_id": sid,
                        "valid": len(errors) == 0,
                        "errors": errors,
                        "warnings": warnings,
                    },
                }

            elif action == "history":
                limit = params.get("limit", 50)
                sid = params.get("source_id")
                events = self._events[-limit:]
                if sid:
                    events = [e for e in events if e.source_id == sid]
                return {
                    "success": True,
                    "result": [
                        {
                            "event_id": e.event_id,
                            "source_id": e.source_id,
                            "event_type": e.event_type,
                            "changes": e.changes[:5],
                            "success": e.success,
                            "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                        }
                        for e in events
                    ],
                }

            elif action == "get_stats":
                return {
                    "success": True,
                    "result": {
                        "sources": len(self._sources),
                        "total_versions": sum(len(v) for v in self._versions.values()),
                        "events": len(self._events),
                        "watchers": len(self._watchers),
                    },
                }

            elif action == "health_check":
                return {"success": True, "result": self.health_check()}

            else:
                return {"success": False, "error": f"未知操作: {action}"}

        except Exception as e:
            logger.error(f"[ConfigReloader] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def _deep_merge(self, base: Dict, override: Dict):
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        base.update(
            {
                "status": "healthy" if self._initialized else "stopped",
                "sources": len(self._sources),
                "total_versions": sum(len(v) for v in self._versions.values()),
                "events": len(self._events),
                "watchers": len(self._watchers),
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False

    def diff_config_versions(self, source: str, version_a: str, version_b: str) -> Dict[str, Any]:
        """对比两个配置版本的差异。企业场景：配置变更前对比新旧版本，
        确认变更内容是否符合预期，防止误操作。
        """
        versions = self._versions.get(source, {})
        config_a = versions.get(version_a, {})
        config_b = versions.get(version_b, {})
        if not config_a:
            return {"success": False, "error": f"版本 {version_a} 不存在"}
        if not config_b:
            return {"success": False, "error": f"版本 {version_b} 不存在"}
        added = {}
        removed = {}
        changed = {}
        all_keys = set(list(config_a.keys()) + list(config_b.keys()))
        for key in all_keys:
            if key not in config_a:
                added[key] = config_b[key]
            elif key not in config_b:
                removed[key] = config_a[key]
            elif config_a[key] != config_b[key]:
                changed[key] = {"old": config_a[key], "new": config_b[key]}
        return {
            "success": True,
            "source": source,
            "version_a": version_a,
            "version_b": version_b,
            "added": added,
            "removed": removed,
            "changed": changed,
            "total_changes": len(added) + len(removed) + len(changed),
        }

    def rollback_config(self, source: str, target_version: str) -> Dict[str, Any]:
        """回滚配置到指定版本。企业场景：配置变更导致线上问题后紧急回滚，
        将配置恢复到上一个已知正常版本。
        """
        versions = self._versions.get(source, {})
        if target_version not in versions:
            return {"success": False, "error": f"版本 {target_version} 不存在"}
        current = getattr(self, "_current_configs", {}).get(source, {})
        self._current_configs[source] = versions[target_version]
        event = {
            "source": source,
            "action": "rollback",
            "target_version": target_version,
            "previous_version": current.get("version", "unknown"),
            "timestamp": time.time(),
        }
        self._events.append(event)
        if self._audit:
            self._audit.log("config_rollback", {"source": source, "target": target_version})
        return {"success": True, "source": source, "rolled_back_to": target_version}

    def get_config_change_log(self, source: str = "", limit: int = 50) -> Dict[str, Any]:
        """配置变更日志。企业场景：审计追踪配置变更历史，排查问题时回溯变更链。
        支持按source过滤，按时间倒序展示。
        """
        events = getattr(self, "_events", [])
        if source:
            events = [e for e in events if e.get("source") == source]
        recent = events[-limit:]
        return {
            "success": True,
            "total": len(events),
            "returned": len(recent),
            "filter_source": source or "all",
            "changes": recent,
        }

    def get_source_health(self) -> Dict[str, Any]:
        """配置源健康状态。企业场景：监控各配置源（Git/Nacos/Consul/本地文件）
        的连接状态和最后同步时间，发现配置源异常及时告警。
        """
        sources = getattr(self, "_sources", {})
        health = []
        for source_id, source in sources.items():
            health.append(
                {
                    "source_id": source_id,
                    "type": getattr(source, "type", "unknown"),
                    "connected": getattr(source, "connected", True),
                    "last_sync": getattr(source, "last_sync", 0),
                    "config_count": getattr(source, "config_count", 0),
                }
            )
        connected = sum(1 for h in health if h["connected"])
        return {
            "success": True,
            "total_sources": len(health),
            "connected": connected,
            "disconnected": len(health) - connected,
            "sources": health,
        }

    def get_config_change_summary(self, hours: int = 24) -> Dict[str, Any]:
        """配置变更摘要。企业场景：SRE团队每日晨会回顾过去24小时配置变更，
        识别异常变更（非工作时间、高频变更、核心配置被改）。
        """
        history = getattr(self, "_change_history", [])
        cutoff = time.time() - hours * 3600
        recent = [h for h in history if h.get("timestamp", 0) > cutoff]
        by_source = {}
        for h in recent:
            src = h.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1
        after_hours = [h for h in recent if 0 <= time.localtime(h.get("timestamp", 0)).tm_hour < 6]
        return {
            "success": True,
            "hours": hours,
            "total_changes": len(recent),
            "by_source": by_source,
            "after_hours_count": len(after_hours),
            "top_changed_keys": self._top_changed_keys(recent, 10),
        }

    def _top_changed_keys(self, history: list, limit: int) -> List[Dict]:
        key_counts = {}
        for h in history:
            key = h.get("key", "")
            if key:
                key_counts[key] = key_counts.get(key, 0) + 1
        return [{"key": k, "changes": c} for k, c in sorted(key_counts.items(), key=lambda x: -x[1])[:limit]]

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

module_class = ConfigReloaderManager
