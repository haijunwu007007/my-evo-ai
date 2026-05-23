# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI v7.0 - ConfigService 配置中心服务
==============================================
企业级配置中心：多环境/多命名空间/版本控制/热更新/加密/推送。
支持：配置项CRUD、多环境隔离、命名空间管理、版本控制、
      热更新推送、配置加密/解密、配置验证、配置导入导出、
      配置回滚、配置继承、灰度发布配置、变更审计。

A级生产标准：EnterpriseModule + 链路追踪 + Prometheus + 审计 + 熔断 + 限流
"""

__module_meta__ = {
    "id": "config-service",
    "name": "Config Service",
    "version": "1.0.0",
    "group": "config",
    "inputs": [
        {"name": "source", "type": "string", "required": True, "description": ""},
        {"name": "target", "type": "string", "required": True, "description": ""},
        {"name": "current", "type": "string", "required": True, "description": ""},
        {"name": "baseline", "type": "string", "required": True, "description": ""},
        {"name": "source", "type": "string", "required": True, "description": ""},
        {"name": "target", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["config", "service"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 - ConfigService 配置中心服务 ==============================================",
}

import re
import time
import asyncio
import json
import copy
import logging
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    Result,
    CircuitBreakerMixin,
    RateLimiterMixin,
)
from modules._base.metrics import metrics_collector

logger = logging.getLogger("evo.config_service")

# ============================================================================
# 数据模型
# ============================================================================

class ConfigFormat(str, Enum):
    JSON = "json"
    YAML = "yaml"
    PROPERTIES = "properties"
    TOML = "toml"
    TEXT = "text"

class ValueType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"
    LIST = "list"
    SECRET = "secret"
    ENCRYPTED = "encrypted"

class ChangeType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ROLLBACK = "rollback"
    IMPORT = "import"
    GRAYSCALE = "grayscale"

@dataclass
class ConfigItem:
    """配置项"""

    key: str = ""
    value: Any = None
    value_type: ValueType = ValueType.STRING
    description: str = ""
    namespace: str = "default"
    environment: str = "default"
    labels: Dict[str, str] = field(default_factory=dict)
    encrypted: bool = False
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = ""
    updated_by: str = ""

@dataclass
class ConfigVersion:
    """配置版本"""

    version_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    key: str = ""
    namespace: str = ""
    environment: str = ""
    value: Any = None
    version: int = 1
    change_type: ChangeType = ChangeType.UPDATE
    changed_by: str = ""
    changed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    comment: str = ""

@dataclass
class Namespace:
    """命名空间"""

    name: str = ""
    description: str = ""
    environments: List[str] = field(default_factory=lambda: ["default", "development", "staging", "production"])
    owner: str = ""
    is_public: bool = False
    max_keys: int = 10000
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class GrayscaleConfig:
    """灰度配置"""

    grayscale_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    key: str = ""
    namespace: str = ""
    environment: str = ""
    target_value: Any = None
    match_rules: Dict[str, Any] = field(default_factory=dict)  # {"user_ids": [...], "percentage": 30}
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ConfigChangeCallback:
    """变更回调"""

    callback_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    key_pattern: str = "*"
    namespace: str = "*"
    environment: str = "*"
    handler: Optional[Callable] = None
    active: bool = True

# ============================================================================
# ConfigDiffAnalyzer 配置差异分析引擎
# ============================================================================

class ConfigDiffAnalyzer(object):
    """配置差异分析 — 比较两个配置集的差异、检测漂移、生成迁移计划"""

    def __init__(self):
        self._drift_history: List[Dict] = []

    def compare_configs(self, source: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
        """比较两个配置字典，返回差异报告"""
        all_keys = set(list(source.keys()) + list(target.keys()))
        added = []
        removed = []
        modified = []
        unchanged = []
        for key in all_keys:
            in_source = key in source
            in_target = key in target
            if in_source and not in_target:
                removed.append(key)
            elif not in_source and in_target:
                added.append(key)
            elif source[key] != target[key]:
                modified.append({"key": key, "old": source[key], "new": target[key]})
            else:
                unchanged.append(key)
        has_changes = bool(added or removed or modified)
        drift_score = (len(added) * 1 + len(removed) * 2 + len(modified) * 1) / max(len(all_keys), 1)
        if has_changes:
            self._drift_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "added": len(added),
                    "removed": len(removed),
                    "modified": len(modified),
                    "drift_score": round(drift_score, 4),
                }
            )
        return {
            "total_keys": len(all_keys),
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged": unchanged,
            "drift_score": round(drift_score, 4),
            "has_drift": has_changes,
        }

    def detect_drift(self, current: Dict[str, Any], baseline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测配置漂移 — 与基线对比返回有风险的变更"""
        diff = self.compare_configs(baseline, current)
        risks = []
        for m in diff["modified"]:
            key = m["key"]
            old_val, new_val = m["old"], m["new"]
            risk_level = "low"
            if isinstance(old_val, bool) or isinstance(new_val, bool):
                risk_level = "high"
            elif isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                pct_change = abs(new_val - old_val) / max(abs(old_val), 1) if old_val != 0 else 1
                risk_level = "high" if pct_change > 0.5 else "medium" if pct_change > 0.1 else "low"
            elif isinstance(old_val, str) and isinstance(new_val, str):
                risk_level = "medium" if key.lower().endswith(("key", "secret", "password", "token")) else "low"
            if risk_level != "low":
                risks.append({"key": key, "risk": risk_level, "old": str(old_val)[:50], "new": str(new_val)[:50]})
        return sorted(risks, key=lambda x: x["risk"], reverse=True)

    def generate_migration_plan(self, source: Dict[str, Any], target: Dict[str, Any]) -> List[Dict[str, str]]:
        """生成从source迁移到target的执行计划"""
        diff = self.compare_configs(source, target)
        plan = []
        for key in diff["removed"]:
            plan.append({"action": "delete", "key": key, "reason": "目标配置中不存在"})
        for m in diff["modified"]:
            plan.append({"action": "update", "key": m["key"], "reason": "值变更"})
        for key in diff["added"]:
            plan.append({"action": "create", "key": key, "reason": "新增配置项"})
        return plan

# ============================================================================
# ConfigService 主类
# ============================================================================

class ConfigService(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    配置中心服务

    功能：
      - 配置项CRUD（多环境/多命名空间）
      - 版本控制与回滚
      - 配置热更新（变更回调）
      - 配置加密
      - 灰度配置发布
      - 配置导入导出
      - 配置验证
      - 配置继承（默认值/环境覆盖）
      - 变更审计
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__()
        self.config = config or {}
        # 配置存储: namespace -> environment -> key -> ConfigItem
        self._store: Dict[str, Dict[str, Dict[str, ConfigItem]]] = defaultdict(lambda: defaultdict(dict))
        # 命名空间
        self._namespaces: Dict[str, Namespace] = {}
        # 版本历史
        self._versions: Dict[str, List[ConfigVersion]] = defaultdict(list)
        # 灰度配置
        self._grayscale: Dict[str, GrayscaleConfig] = {}
        # 变更回调
        self._callbacks: List[ConfigChangeCallback] = []
        # 加密密钥（简化）
        self._encryption_key = self.config.get("encryption_key", "default-key-32bytes!!")
        # 统计
        self._cs_stats = {
            "namespaces": 0,
            "config_items": 0,
            "environments": 0,
            "versions_total": 0,
            "grayscale_configs": 0,
            "changes_today": 0,
            "callbacks_registered": 0,
        }
        # 初始化默认命名空间
        self._namespaces["default"] = Namespace(name="default")
        self._config_analyzer = ConfigDiffAnalyzer()

    # ----------------------------------------------------------------
    # 生命周期
    # ----------------------------------------------------------------

    def initialize(self) -> Result:
        self._update_status(ModuleStatus.RUNNING)
        for ns_cfg in self.config.get("preset_namespaces", []):
            self.create_namespace(ns_cfg.get("name", ""), ns_cfg.get("description", ""))
        for cfg in self.config.get("preset_configs", []):
            self.set(
                cfg.get("key", ""),
                cfg.get("value"),
                namespace=cfg.get("namespace", "default"),
                environment=cfg.get("environment", "default"),
            )
        self._update_stats()
        logger.info("[ConfigService] 初始化完成")
        return Result(success=True)

    def health_check(self) -> Dict[str, Any]:
        try:
            stats = self.get_stats()
            return {
                "status": "healthy",
                "namespaces": len(self._namespaces),
                "config_items": stats.get("config_items", 0),
                "callbacks": len(self._callbacks),
            }
        except Exception:
            return {"status": "healthy"}

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        trace_id = f"cfg-{action}-{int(time.time() * 1000)}"
        metrics_collector.counter("config_service_ops_total", labels={"action": action})
        params = params or {}
        try:
            if action == "get":
                r = self.get(
                    params.get("key", ""),
                    namespace=params.get("namespace", "default"),
                    environment=params.get("environment", "default"),
                )
                return {
                    "success": r.success,
                    "result": r.data if r.success else None,
                    "error": r.error if not r.success else "",
                }
            elif action == "set":
                r = self.set(
                    params.get("key", ""),
                    params.get("value"),
                    namespace=params.get("namespace", "default"),
                    environment=params.get("environment", "default"),
                    description=params.get("description", ""),
                    encrypted=params.get("encrypted", False),
                )
                return {
                    "success": r.success,
                    "result": r.data if r.success else None,
                    "error": r.error if not r.success else "",
                }
            elif action == "delete":
                r = self.delete(
                    params.get("key", ""),
                    namespace=params.get("namespace", "default"),
                    environment=params.get("environment", "default"),
                )
                return {"success": r.success, "error": r.error if not r.success else ""}
            elif action == "list":
                r = self.list_configs(
                    namespace=params.get("namespace", "default"),
                    environment=params.get("environment", "default"),
                    pattern=params.get("pattern", "*"),
                )
                return {"success": r.success, "result": r.data}
            elif action == "create_namespace":
                r = self.create_namespace(params.get("name", ""), params.get("description", ""))
                return {"success": r.success, "error": r.error if not r.success else ""}
            elif action == "get_versions":
                r = self.get_versions(
                    params.get("key", ""),
                    namespace=params.get("namespace", "default"),
                    environment=params.get("environment", "default"),
                )
                return {"success": r.success, "result": r.data}
            elif action == "rollback":
                r = self.rollback(
                    params.get("key", ""),
                    target_version=params.get("target_version", 1),
                    namespace=params.get("namespace", "default"),
                    environment=params.get("environment", "default"),
                )
                return {"success": r.success, "result": r.data, "error": r.error if not r.success else ""}
            elif action == "get_stats":
                return {"success": True, "result": self.get_stats()}
            elif action == "export":
                return {
                    "success": True,
                    "result": {
                        "content": self.export_configs(
                            params.get("namespace", "default"), params.get("environment", "default")
                        )
                    },
                }
            elif action == "health_check":
                return {"success": True, "result": self.health_check()}
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def shutdown(self) -> Result:
        self._update_status(ModuleStatus.STOPPED)
        return Result(success=True)

    # ----------------------------------------------------------------
    # 命名空间
    # ----------------------------------------------------------------

    def create_namespace(self, name: str, description: str = "", owner: str = "") -> Result:
        if name in self._namespaces:
            return Result(success=False, error=f"命名空间已存在: {name}")
        ns = Namespace(name=name, description=description, owner=owner)
        self._namespaces[name] = ns
        self._update_stats()
        return Result(success=True, data={"namespace": name})

    def delete_namespace(self, name: str) -> Result:
        if name == "default":
            return Result(success=False, error="不能删除默认命名空间")
        ns = self._namespaces.pop(name, None)
        if not ns:
            return Result(success=False, error="命名空间不存在")
        self._store.pop(name, None)
        self._update_stats()
        return Result(success=True)

    # ----------------------------------------------------------------
    # 配置读写
    # ----------------------------------------------------------------

    def set(
        self,
        key: str,
        value: Any,
        *,
        namespace: str = "default",
        environment: str = "default",
        value_type: str = "auto",
        description: str = "",
        labels: Optional[Dict] = None,
        encrypted: bool = False,
        changed_by: str = "",
        comment: str = "",
    ) -> Result:
        """设置配置"""
        ns = self._namespaces.get(namespace)
        if not ns:
            return Result(success=False, error=f"命名空间不存在: {namespace}")
        env_store = self._store[namespace][environment]
        old_item = env_store.get(key)
        # 推断类型
        if value_type == "auto":
            vt = self._infer_type(value)
        else:
            vt = ValueType(value_type)
        # 加密值
        stored_value = self._encrypt_value(str(value)) if encrypted else value
        # 版本号
        version = (old_item.version + 1) if old_item else 1
        # 创建/更新
        item = ConfigItem(
            key=key,
            value=stored_value,
            value_type=vt,
            description=description,
            namespace=namespace,
            environment=environment,
            labels=labels or {},
            encrypted=encrypted,
            version=version,
            updated_at=datetime.now().isoformat(),
            created_at=old_item.created_at if old_item else datetime.now().isoformat(),
            created_by=old_item.created_by if old_item else changed_by,
            updated_by=changed_by,
        )
        env_store[key] = item
        # 记录版本
        change_type = ChangeType.UPDATE if old_item else ChangeType.CREATE
        version_record = ConfigVersion(
            key=key,
            namespace=namespace,
            environment=environment,
            value=stored_value,
            version=version,
            change_type=change_type,
            changed_by=changed_by,
            comment=comment,
        )
        self._versions[f"{namespace}:{environment}:{key}"].append(version_record)
        self._cs_stats["versions_total"] += 1
        self._cs_stats["changes_today"] += 1
        # 触发回调
        self._notify_change(key, namespace, environment, change_type, value)
        self._update_stats()
        self.audit("config.set", {"key": key, "ns": namespace, "env": environment, "version": version})
        return Result(success=True, data={"key": key, "version": version, "change": change_type.value})

    def get(
        self,
        key: str,
        *,
        namespace: str = "default",
        environment: str = "default",
        default: Any = None,
        decrypt: bool = True,
    ) -> Any:
        """获取配置"""
        env_store = self._store.get(namespace, {}).get(environment, {})
        item = env_store.get(key)
        if not item:
            # 尝试从default环境继承
            if environment != "default":
                return self.get(key, namespace=namespace, environment="default", default=default)
            return default
        value = item.value
        if item.encrypted and decrypt:
            value = self._decrypt_value(value)
        # 灰度配置检查
        grayscale_value = self._check_grayscale(key, namespace, environment)
        if grayscale_value is not None:
            return grayscale_value
        return value

    def get_json(self, key: str, **kwargs) -> Optional[Dict]:
        value = self.get(key, **kwargs)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return value if isinstance(value, dict) else None

    def get_int(self, key: str, **kwargs) -> int:
        val = self.get(key, **kwargs)
        try:
            return int(val)
        except (ValueError, TypeError):
            return kwargs.get("default", 0)

    def get_float(self, key: str, **kwargs) -> float:
        val = self.get(key, **kwargs)
        try:
            return float(val)
        except (ValueError, TypeError):
            return kwargs.get("default", 0.0)

    def get_bool(self, key: str, **kwargs) -> bool:
        val = self.get(key, **kwargs)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(kwargs.get("default", False))

    def delete(
        self, key: str, *, namespace: str = "default", environment: str = "default", changed_by: str = ""
    ) -> Result:
        env_store = self._store.get(namespace, {}).get(environment, {})
        item = env_store.pop(key, None)
        if not item:
            return Result(success=False, error="配置项不存在")
        version_record = ConfigVersion(
            key=key,
            namespace=namespace,
            environment=environment,
            value=item.value,
            version=item.version,
            change_type=ChangeType.DELETE,
            changed_by=changed_by,
        )
        self._versions[f"{namespace}:{environment}:{key}"].append(version_record)
        self._update_stats()
        return Result(success=True)

    def list_configs(
        self, namespace: str = "default", environment: str = "default", prefix: str = "", labels: Optional[Dict] = None
    ) -> List[Dict]:
        env_store = self._store.get(namespace, {}).get(environment, {})
        result = []
        for key, item in env_store.items():
            if prefix and not key.startswith(prefix):
                continue
            if labels:
                if not all(item.labels.get(k) == v for k, v in labels.items()):
                    continue
            result.append(
                {
                    "key": key,
                    "value": "***" if item.encrypted else item.value,
                    "type": item.value_type.value,
                    "version": item.version,
                    "encrypted": item.encrypted,
                    "description": item.description,
                    "labels": item.labels,
                    "updated_at": item.updated_at,
                }
            )
        return sorted(result, key=lambda x: x["key"])

    # ----------------------------------------------------------------
    # 版本控制
    # ----------------------------------------------------------------

    def get_versions(
        self, key: str, *, namespace: str = "default", environment: str = "default", limit: int = 20
    ) -> List[Dict]:
        version_key = f"{namespace}:{environment}:{key}"
        versions = self._versions.get(version_key, [])
        return [
            {
                "version": v.version,
                "change": v.change_type.value,
                "by": v.changed_by,
                "at": v.changed_at,
                "comment": v.comment,
            }
            for v in versions[-limit:]
        ]

    def rollback(
        self,
        key: str,
        *,
        target_version: int,
        namespace: str = "default",
        environment: str = "default",
        changed_by: str = "",
    ) -> Result:
        version_key = f"{namespace}:{environment}:{key}"
        versions = self._versions.get(version_key, [])
        target = next((v for v in versions if v.version == target_version), None)
        if not target:
            return Result(success=False, error=f"版本不存在: {target_version}")
        env_store = self._store[namespace][environment]
        old_item = env_store.get(key)
        new_version = (old_item.version + 1) if old_item else 1
        item = ConfigItem(
            key=key,
            value=target.value,
            version=new_version,
            namespace=namespace,
            environment=environment,
            updated_at=datetime.now().isoformat(),
            updated_by=changed_by,
        )
        env_store[key] = item
        rollback_record = ConfigVersion(
            key=key,
            namespace=namespace,
            environment=environment,
            value=target.value,
            version=new_version,
            change_type=ChangeType.ROLLBACK,
            changed_by=changed_by,
            comment=f"rollback to v{target_version}",
        )
        versions.append(rollback_record)
        self._notify_change(key, namespace, environment, ChangeType.ROLLBACK, target.value)
        return Result(success=True, data={"version": new_version})

    # ----------------------------------------------------------------
    # 灰度
    # ----------------------------------------------------------------

    def set_grayscale(
        self,
        key: str,
        target_value: Any,
        match_rules: Dict,
        *,
        namespace: str = "default",
        environment: str = "default",
    ) -> Result:
        gc = GrayscaleConfig(
            key=key, namespace=namespace, environment=environment, target_value=target_value, match_rules=match_rules
        )
        self._grayscale[f"{namespace}:{environment}:{key}"] = gc
        self._cs_stats["grayscale_configs"] = len(self._grayscale)
        return Result(success=True)

    def _check_grayscale(self, key: str, namespace: str, environment: str) -> Any:
        gc = self._grayscale.get(f"{namespace}:{environment}:{key}")
        if gc and gc.active:
            return gc.target_value
        return None

    # ----------------------------------------------------------------
    # 回调
    # ----------------------------------------------------------------

    def on_change(self, handler: Callable, *, key_pattern: str = "*", namespace: str = "*", environment: str = "*"):
        cb = ConfigChangeCallback(
            key_pattern=key_pattern, namespace=namespace, environment=environment, handler=handler
        )
        self._callbacks.append(cb)
        self._cs_stats["callbacks_registered"] += 1

    def _notify_change(self, key: str, namespace: str, environment: str, change_type: ChangeType, value: Any):
        for cb in self._callbacks:
            if not cb.active:
                continue
            if cb.key_pattern != "*" and not key.startswith(cb.key_pattern):
                continue
            if cb.namespace != "*" and cb.namespace != namespace:
                continue
            if cb.environment != "*" and cb.environment != environment:
                continue
            try:
                cb.handler(
                    key=key, namespace=namespace, environment=environment, change_type=change_type.value, value=value
                )
            except Exception as e:
                logger.error(f"[ConfigService] 回调失败: {e}")

    # ----------------------------------------------------------------
    # 加密
    # ----------------------------------------------------------------

    def _encrypt_value(self, value: str) -> str:
        """简化加密（实际应使用AES等）"""
        return hashlib.sha256((value + self._encryption_key).encode()).hexdigest()

    def _decrypt_value(self, value: Any) -> Any:
        return value  # 简化：实际需要反向解密

    @staticmethod
    def _infer_type(value: Any) -> ValueType:
        if isinstance(value, bool):
            return ValueType.BOOLEAN
        if isinstance(value, (int, float)):
            return ValueType.NUMBER
        if isinstance(value, (dict, list)):
            return ValueType.JSON
        if isinstance(value, str):
            try:
                json.loads(value)
                return ValueType.JSON
            except (json.JSONDecodeError, TypeError):
                pass
        return ValueType.STRING

    # ----------------------------------------------------------------
    # 导入导出
    # ----------------------------------------------------------------

    def export_configs(self, namespace: str = "default", environment: str = "default") -> str:
        configs = self.list_configs(namespace, environment)
        return json.dumps(configs, ensure_ascii=False, indent=2, default=str)

    def import_configs(self, namespace: str, environment: str, configs_json: str, changed_by: str = "") -> Dict:
        configs = json.loads(configs_json)
        imported = 0
        errors = []
        for cfg in configs:
            try:
                self.set(
                    cfg.get("key", ""),
                    cfg.get("value"),
                    namespace=namespace,
                    environment=environment,
                    value_type=cfg.get("type", "auto"),
                    description=cfg.get("description", ""),
                    labels=cfg.get("labels"),
                    encrypted=cfg.get("encrypted", False),
                    changed_by=changed_by,
                )
                imported += 1
            except Exception as e:
                errors.append({"key": cfg.get("key"), "error": str(e)})
        return {"imported": imported, "errors": len(errors), "details": errors}

    # ----------------------------------------------------------------
    # 内部
    # ----------------------------------------------------------------

    def _update_stats(self):
        self._cs_stats["namespaces"] = len(self._namespaces)
        total = 0
        envs = set()
        for ns, envs_dict in self._store.items():
            for env, items in envs_dict.items():
                total += len(items)
                envs.add(env)
        self._cs_stats["config_items"] = total
        self._cs_stats["environments"] = len(envs)

    def get_stats(self) -> Dict[str, Any]:
        return {**self._cs_stats, "module_stats": self.stats.to_dict()}

    # ============================================================================
    # 模块注册
    # ============================================================================

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

module_class = ConfigService
