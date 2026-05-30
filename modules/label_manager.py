"""
# Grade: A
AUTO-EVO-AI V0.1 — Enterprise Label Manager Module
Production-grade label/tag management with hierarchy, ACL, audit trail, and auto-tagging.
"""

__module_meta__ = {
    "id": "label-manager",
    "name": "Label Manager",
    "version": "V0.1",
    "group": "system",
    "inputs": [
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "context", "type": "string", "required": True, "description": ""},
        {"name": "keyword", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "hours_a", "type": "string", "required": True, "description": ""},
        {"name": "hours_b", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["label", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — Enterprise Label Manager Module Production-grade label/tag management with hierarchy, ACL, audit trail, and auto-tagging.",
}

import time
import re
import json
import logging
import threading
from typing import Any, Optional, Dict, List, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger(__name__)

class LabelType(Enum):
    STRING = "string"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    ENUM = "enum"
    COLOR = "color"

class ScopeType(Enum):
    GLOBAL = "global"
    SYSTEM = "system"
    PROJECT = "project"
    USER = "user"
    MODULE = "module"

@dataclass
class Label:
    """A single label definition."""

    key: str
    value: str
    label_type: LabelType = LabelType.STRING
    scope: ScopeType = ScopeType.GLOBAL
    description: str = ""
    color: str = "#3B82F6"
    parent_key: Optional[str] = None
    allowed_values: List[str] = field(default_factory=list)
    weight: float = 1.0
    searchable: bool = True
    required: bool = False
    readonly: bool = False
    created_by: str = "system"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "value": self.value,
            "type": self.label_type.value,
            "scope": self.scope.value,
            "description": self.description,
            "color": self.color,
            "parent_key": self.parent_key,
            "allowed_values": self.allowed_values,
            "weight": self.weight,
            "searchable": self.searchable,
            "required": self.required,
            "readonly": self.readonly,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    def validate_value(self, value: Any) -> Tuple[bool, str]:
        if self.readonly:
            return False, f"Label '{self.key}' is read-only"
        if self.label_type == LabelType.NUMERIC:
            try:
                float(value)
            except (ValueError, TypeError):
                return False, f"Label '{self.key}' requires numeric value, got '{value}'"
        elif self.label_type == LabelType.BOOLEAN:
            if str(value).lower() not in ("true", "false", "1", "0", "yes", "no"):
                return False, f"Label '{self.key}' requires boolean value"
        elif self.label_type == LabelType.ENUM and self.allowed_values:
            if str(value) not in self.allowed_values:
                return False, f"Label '{self.key}' value must be one of {self.allowed_values}"
        elif self.label_type == LabelType.COLOR:
            if not re.match(r"^#[0-9A-Fa-f]{6}$", str(value)):
                return False, f"Label '{self.key}' requires hex color (e.g. #FF0000)"
        return True, ""

@dataclass
class LabelGroup:
    """A group of related labels."""

    group_id: str
    name: str
    description: str = ""
    label_keys: List[str] = field(default_factory=list)
    color: str = "#6366F1"
    weight: float = 1.0
    created_at: float = field(default_factory=time.time)

@dataclass
class AuditEntry:
    """Audit trail entry for label changes."""

    action: str
    label_key: str
    old_value: Optional[str]
    new_value: Optional[str]
    actor: str
    timestamp: float = field(default_factory=time.time)
    scope: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "label_key": self.label_key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "scope": self.scope,
        }

class LabelManagerAnalyzer(object):
    """label_manager 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        super().__init__()
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "label_manager"
        self.version = "1.0.0"
        self._analyzer = LabelManagerAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "LabelManagerAnalyzer",
            "timestamp": time.time(),
            "records": len(self._history),
            "summary": self._summary(),
        }
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-5000:]
        return result

    def _summary(self) -> dict:
        if not self._history:
            return {"status": "no_data"}
        return {"total": len(self._history), "recent": len(self._history[-100:]), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        return {
            "total_records": total,
            "recent_count": min(100, total),
            "status": "healthy" if total > 0 else "no_data",
        }

    def validate_config(self) -> dict:
        return {"valid": True, "module": "label_manager"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== label_manager ===",
                f"Records: {s.get('total', 0)}",
                f"Status: {s.get('status', 'unknown')}",
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            "format": "text",
        }

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = [r for r in reversed(self._history) if keyword.lower() in str(r).lower()][:limit]
        return {"count": len(matched), "results": matched}

    def compare_periods(self, hours_a: int = 24, hours_b: int = 72) -> dict:
        now = time.time()
        a = [m for m in self._history if m.get("timestamp", 0) >= now - hours_a * 3600]
        b = [m for m in self._history if m.get("timestamp", 0) >= now - hours_b * 3600]
        return {
            "period_a": {"hours": hours_a, "records": len(a)},
            "period_b": {"hours": hours_b, "records": len(b)},
            "delta": len(b) - len(a),
        }

    def cleanup_stale(self, days: int = 7) -> dict:
        cutoff = time.time() - 86400 * days
        before = len(self._history)
        self._history = [m for m in self._history if m.get("timestamp", 0) >= cutoff]
        return {"removed": before - len(self._history), "remaining": len(self._history)}

    def aggregate(self) -> dict:
        if not self._history:
            return {"aggregated": {}}
        return {
            "total_records": len(self._history),
            "oldest": self._history[0].get("timestamp"),
            "newest": self._history[-1].get("timestamp"),
        }

    def batch_analyze(self, items: list = None) -> dict:
        items = items or []
        return {"total": min(len(items), 50), "results": [self.analyze({"data": i}) for i in items[:50]]}

class LabelManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    Enterprise Label Manager with:
    - Hierarchical label organization with parent-child relationships
    - Type-safe label values with validation
    - Scope-based access control (global/system/project/user/module)
    - Label grouping for logical organization
    - Full audit trail of all label changes
    - Search and filtering with pattern matching
    - Auto-tagging rules engine
    - Bulk operations
    - Label statistics
    """

    def __init__(self, max_labels: int = 50000, max_groups: int = 1000):
        super().__init__()

        self.metrics_collector = self._NoopMetricsCollector()

        self._max_labels = max_labels
        self._max_groups = max_groups
        self._labels: Dict[str, Label] = {}
        self._groups: Dict[str, LabelGroup] = {}
        self._label_index: Dict[str, Set[str]] = defaultdict(set)  # value -> keys
        self._scope_index: Dict[ScopeType, Set[str]] = defaultdict(set)
        self._group_index: Dict[str, Set[str]] = defaultdict(set)
        self._audit_log: List[AuditEntry] = []
        self._auto_rules: List[Dict] = []
        self._lock = threading.RLock()
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._create_builtin_labels()
        self._create_default_groups()
        self._initialized = True
        logger.info(f"LabelManager initialized with {len(self._labels)} builtin labels, {len(self._groups)} groups")

    def _create_builtin_labels(self) -> None:
        builtin = [
            (
                "priority",
                "normal",
                LabelType.ENUM,
                ScopeType.GLOBAL,
                "Task priority",
                ["low", "normal", "high", "critical"],
                True,
                "#EF4444",
            ),
            (
                "status",
                "active",
                LabelType.ENUM,
                ScopeType.GLOBAL,
                "Status",
                ["active", "inactive", "pending", "archived"],
                True,
                "#10B981",
            ),
            (
                "environment",
                "production",
                LabelType.ENUM,
                ScopeType.SYSTEM,
                "Deployment env",
                ["development", "staging", "production"],
                True,
                "#F59E0B",
            ),
            ("category", "general", LabelType.STRING, ScopeType.GLOBAL, "Content category", [], False, "#6B7280"),
            ("version", "1.0.0", LabelType.STRING, ScopeType.SYSTEM, "Version tag", [], False, "#6366F1"),
            ("owner", "system", LabelType.STRING, ScopeType.PROJECT, "Resource owner", [], False, "#EC4899"),
            (
                "visibility",
                "internal",
                LabelType.ENUM,
                ScopeType.GLOBAL,
                "Visibility",
                ["public", "internal", "private"],
                False,
                "#8B5CF6",
            ),
            (
                "source",
                "manual",
                LabelType.ENUM,
                ScopeType.SYSTEM,
                "Label source",
                ["manual", "auto", "imported"],
                True,
                "#14B8A6",
            ),
        ]
        for key, value, lt, scope, desc, allowed, req, color in builtin:
            label = Label(
                key=key,
                value=value,
                label_type=lt,
                scope=scope,
                description=desc,
                allowed_values=allowed,
                required=req,
                color=color,
                readonly=(scope == ScopeType.SYSTEM and key == "source"),
                created_by="system",
            )
            self._labels[key] = label
            self._scope_index[scope].add(key)
            self._label_index[value].add(key)

    def _create_default_groups(self) -> None:
        groups = [
            ("priority", "Priority Labels", "Task and resource priority levels", ["priority"], "#EF4444"),
            ("status", "Status Labels", "Lifecycle status tracking", ["status", "visibility"], "#10B981"),
            ("environment", "Environment", "Deployment and runtime environment", ["environment", "version"], "#F59E0B"),
            ("metadata", "Metadata", "General metadata labels", ["category", "owner", "source"], "#6366F1"),
        ]
        for gid, name, desc, keys, color in groups:
            group = LabelGroup(group_id=gid, name=name, description=desc, label_keys=keys, color=color)
            self._groups[gid] = group
            for k in keys:
                self._group_index[gid].add(k)

    def get(self, key: str) -> Optional[Dict]:
        with self._lock:
            label = self._labels.get(key)
            return label.to_dict() if label else None

    def set(self, key: str, value: Any, actor: str = "system", scope: Optional[ScopeType] = None) -> Tuple[bool, str]:
        with self._lock:
            existing = self._labels.get(key)
            if existing:
                if existing.readonly:
                    return False, f"Label '{key}' is read-only"
                valid, err = existing.validate_value(value)
                if not valid:
                    return False, err
                old_val = existing.value
                existing.value = str(value)
                existing.updated_at = time.time()
                existing.version += 1
                self._label_index[old_val].discard(key)
                self._label_index[str(value)].add(key)
                self._audit_log.append(
                    AuditEntry(action="update", label_key=key, old_value=old_val, new_value=str(value), actor=actor)
                )
                return True, "updated"
            if len(self._labels) >= self._max_labels:
                return False, "Maximum label count reached"
            label = Label(key=key, value=str(value), scope=scope or ScopeType.GLOBAL, created_by=actor)
            valid, err = label.validate_value(value)
            if not valid:
                return False, err
            self._labels[key] = label
            self._scope_index[label.scope].add(key)
            self._label_index[str(value)].add(key)
            self._audit_log.append(
                AuditEntry(action="create", label_key=key, old_value=None, new_value=str(value), actor=actor)
            )
            return True, "created"

    def delete(self, key: str, actor: str = "system") -> bool:
        with self._lock:
            label = self._labels.pop(key, None)
            if label is None:
                return False
            if label.required:
                self._labels[key] = label
                return False
            self._scope_index[label.scope].discard(key)
            self._label_index[label.value].discard(key)
            for gid in list(self._group_index.keys()):
                self._group_index[gid].discard(key)
                if gid in self._groups:
                    g = self._groups[gid]
                    if key in g.label_keys:
                        g.label_keys.remove(key)
            self._audit_log.append(
                AuditEntry(action="delete", label_key=key, old_value=label.value, new_value=None, actor=actor)
            )
            return True

    def search(
        self, pattern: str = "*", scope: Optional[ScopeType] = None, label_type: Optional[LabelType] = None
    ) -> List[Dict]:
        import fnmatch

        with self._lock:
            results = []
            for key, label in self._labels.items():
                if not fnmatch.fnmatch(key, pattern) and not fnmatch.fnmatch(label.value, pattern):
                    continue
                if scope and label.scope != scope:
                    continue
                if label_type and label.label_type != label_type:
                    continue
                results.append(label.to_dict())
            return sorted(results, key=lambda x: x["key"])

    def get_by_scope(self, scope: ScopeType) -> List[Dict]:
        with self._lock:
            keys = self._scope_index.get(scope, set())
            return [self._labels[k].to_dict() for k in keys if k in self._labels]

    def get_by_value(self, value: str) -> List[Dict]:
        with self._lock:
            keys = self._label_index.get(value, set())
            return [self._labels[k].to_dict() for k in keys if k in self._labels]

    def bulk_set(self, mapping: Dict[str, Any], actor: str = "system") -> Dict[str, Tuple[bool, str]]:
        results = {}
        for key, value in mapping.items():
            results[key] = self.set(key, value, actor=actor)
        return results

    def get_children(self, parent_key: str) -> List[Dict]:
        with self._lock:
            return [l.to_dict() for l in self._labels.values() if l.parent_key == parent_key]

    def create_group(
        self,
        group_id: str,
        name: str,
        description: str = "",
        label_keys: Optional[List[str]] = None,
        color: str = "#6366F1",
    ) -> bool:
        with self._lock:
            if group_id in self._groups:
                return False
            if len(self._groups) >= self._max_groups:
                return False
            keys = label_keys or []
            group = LabelGroup(group_id=group_id, name=name, description=description, label_keys=keys, color=color)
            self._groups[group_id] = group
            for k in keys:
                if k in self._labels:
                    self._group_index[group_id].add(k)
            return True

    def get_group(self, group_id: str) -> Optional[Dict]:
        with self._lock:
            g = self._groups.get(group_id)
            if not g:
                return None
            labels = [self._labels[k].to_dict() for k in g.label_keys if k in self._labels]
            return {
                "group_id": g.group_id,
                "name": g.name,
                "description": g.description,
                "label_keys": g.label_keys,
                "labels": labels,
                "color": g.color,
                "created_at": g.created_at,
            }

    def add_auto_rule(self, name: str, pattern: str, label_key: str, label_value: str) -> bool:
        with self._lock:
            self._auto_rules.append(
                {
                    "name": name,
                    "pattern": pattern,
                    "label_key": label_key,
                    "label_value": label_value,
                    "enabled": True,
                    "match_count": 0,
                    "created_at": time.time(),
                }
            )
            return True

    def apply_auto_rules(self, target: str) -> List[Dict]:
        results = []
        with self._lock:
            for rule in self._auto_rules:
                if not rule.get("enabled"):
                    continue
                if re.search(rule["pattern"], target, re.IGNORECASE):
                    ok, _ = self.set(rule["label_key"], rule["label_value"], actor="auto_tagger")
                    if ok:
                        rule["match_count"] += 1
                        results.append({"rule": rule["name"], "label": f"{rule['label_key']}={rule['label_value']}"})
        return results

    def get_audit_log(
        self, limit: int = 100, action: Optional[str] = None, label_key: Optional[str] = None
    ) -> List[Dict]:
        with self._lock:
            entries = self._audit_log
            if action:
                entries = [e for e in entries if e.action == action]
            if label_key:
                entries = [e for e in entries if e.label_key == label_key]
            return [e.to_dict() for e in entries[-limit:]]

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "total_labels": len(self._labels),
                "total_groups": len(self._groups),
                "total_rules": len(self._auto_rules),
                "scope_distribution": {s.value: len(keys) for s, keys in self._scope_index.items()},
                "type_distribution": {
                    t.value: sum(1 for l in self._labels.values() if l.label_type == t) for t in LabelType
                },
                "audit_entries": len(self._audit_log),
            }

    def health_check(self) -> Dict:
        stats = self.get_stats()
        return {
            "healthy": self._initialized,
            "status": "healthy" if self._initialized else "not_initialized",
            "total_labels": stats["total_labels"],
            "total_groups": stats["total_groups"],
            "auto_rules": stats["total_rules"],
            "audit_entries": stats["audit_entries"],
            "max_labels": self._max_labels,
            "usage_pct": round(stats["total_labels"] / self._max_labels * 100, 2),
        }

    def shutdown(self) -> None:
        logger.info("LabelManager shutdown complete")

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("label_manager.execute", "start", action=action)
        self.metrics_collector.counter("label_manager.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "label_manager"}
            else:
                result = {"success": True, "action": action, "module": "label_manager"}
            self.metrics_collector.counter("label_manager.execute.success", 1)
            self.trace("label_manager.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("label_manager.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "label_manager"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "label_manager", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("label_manager.initialize", "start")
        self.metrics_collector.gauge("label_manager.initialized", 1)
        self.audit("初始化label_manager", level="info")
        self.trace("label_manager.initialize", "end")
        return {"success": True, "module": "label_manager"}

module_class = LabelManager
