"""
AUTO-EVO-AI V0.1 — 密钥保险库
Grade: A (生产级) | Category: 安全合规
职责：安全存储/管理/轮换/审计 密钥、凭证、证书
"""

__module_meta__ = {
    "id": "secret-vault",
    "name": "Secret Vault",
    "version": "V0.1",
    "group": "crypto",
    "inputs": [
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["adapter", "engine", "secret"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — 密钥保险库 Grade: A (生产级) | Category: 安全合规",
}

import asyncio
import time
import uuid
import os
import json
import hashlib
import base64
import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

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
logger = logging.getLogger("secret_vault")

class _MetricsAdapter:
    """轻量指标适配器"""
    def __init__(self):self._data={}
    def increment(self,name:str,value:float=1.0,**kw):self._data[name]=self._data.get(name,0)+value
    def histogram(self,name:str,value:float,**kw):self._data[name]=value
    def gauge(self,name:str,value:float,**kw):self._data[name]=value
    def snapshot(self):return dict(self._data)

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

    # --- Auto-generated action dispatch methods ---
    def _action_counter(self, params=None):
        """Auto-generated action wrapper for counter"""
        if params is None:
            params = {}
        return self.counter(**params)

    def _action_gauge(self, params=None):
        """Auto-generated action wrapper for gauge"""
        if params is None:
            params = {}
        return self.gauge(**params)

    def _action_histogram(self, params=None):
        """Auto-generated action wrapper for histogram"""
        if params is None:
            params = {}
        return self.histogram(**params)

    def _action_increment(self, params=None):
        """Auto-generated action wrapper for increment"""
        if params is None:
            params = {}
        return self.increment(**params)

class SecretType(Enum):
    API_KEY = "api_key"
    DATABASE = "database"
    CERTIFICATE = "certificate"
    TOKEN = "token"
    PASSWORD = "password"
    SSH_KEY = "ssh_key"
    ENCRYPTION_KEY = "encryption_key"
    CUSTOM = "custom"

class AccessLevel(Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

@dataclass
class SecretEntry:
    """密钥条目"""

    secret_id: str
    name: str
    path: str
    secret_type: SecretType
    encrypted_value: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    version: int = 1
    versions: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_accessed: Optional[float] = None
    access_count: int = 0
    rotation_days: int = 90
    auto_rotate: bool = False
    owner: str = "system"
    access_policies: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AccessPolicy:
    """访问策略"""

    policy_id: str
    name: str
    path_pattern: str
    allowed_roles: List[str] = field(default_factory=list)
    allowed_operations: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)

class SecretRotationEngine(object):
    """密钥轮转引擎 - 负责密钥定期轮转、版本管理和过期清理"""

    def __init__(self):
        self._rotation_history: Dict[str, List[Dict]] = {}
        self._rotation_count: int = 0
        self._policies: Dict[str, Dict] = {}

    def set_rotation_policy(self, secret_name: str, max_age_days: int = 90, auto_rotate: bool = False) -> None:
        """设置密钥轮转策略"""
        self._policies[secret_name] = {
            "max_age_days": max_age_days,
            "auto_rotate": auto_rotate,
            "created_at": time.time(),
        }

    def rotate(self, secret_name: str, new_value: str, store: Dict) -> Dict:
        """执行密钥轮转"""
        self._rotation_count += 1
        old_value = store.get(secret_name, {}).get("value", "")
        store[secret_name] = {
            "value": new_value,
            "rotated_at": time.time(),
            "version": store.get(secret_name, {}).get("version", 0) + 1,
        }
        history = self._rotation_history.setdefault(secret_name, [])
        history.append(
            {
                "old_value_hash": self._hash(old_value),
                "rotated_at": time.time(),
                "version": store[secret_name]["version"],
            }
        )
        if len(history) > 10:
            history[:] = history[-10:]
        return {"secret": secret_name, "new_version": store[secret_name]["version"], "rotated": True}

    def needs_rotation(self, secret_name: str, store: Dict) -> bool:
        """检查密钥是否需要轮转"""
        policy = self._policies.get(secret_name)
        if not policy:
            return False
        secret_data = store.get(secret_name, {})
        rotated_at = secret_data.get("rotated_at", secret_data.get("created_at", time.time()))
        age_seconds = time.time() - rotated_at
        return age_seconds > policy["max_age_days"] * 86400

    def get_rotation_history(self, secret_name: str) -> List[Dict]:
        """获取轮转历史"""
        return self._rotation_history.get(secret_name, [])

    def list_expired(self, store: Dict) -> List[str]:
        """列出所有需要轮转的密钥"""
        return [name for name in self._policies if self.needs_rotation(name, store)]

    def _hash(self, value: str) -> str:
        import hashlib

        return hashlib.sha256(value.encode()).hexdigest()[:16] if value else "empty"

    def stats(self) -> Dict:
        return {
            "policies": len(self._policies),
            "total_rotations": self._rotation_count,
            "tracked_secrets": len(self._rotation_history),
        }

class SecretVault(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """密钥保险库"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._secrets: Dict[str, SecretEntry] = {}
        self._path_index: Dict[str, str] = {}  # path -> secret_id
        self._policies: Dict[str, AccessPolicy] = {}
        self._access_log: List[Dict] = []
        self._encryption_key: Optional[bytes] = None
        self._max_secrets = 10000

    def initialize(self) -> None:
        self._encryption_key = self._derive_vault_key()
        self._register_default_policies()
        logger.info(f"密钥保险库初始化完成")
        self.record_metrics("unknown.init", 1)
        self.audit("initialized", "Unknown初始化完成")

    def _derive_vault_key(self) -> bytes:
        passphrase = os.environ.get("VAULT_MASTER_KEY", "auto-evo-vault-key-v7-2026")
        return hashlib.sha256(passphrase.encode()).digest()

    def _register_default_policies(self) -> None:
        defaults = [
            AccessPolicy("pol_default", "默认读策略", "secret/*", ["admin", "developer"], ["read"]),
            AccessPolicy("pol_admin", "管理员策略", "secret/*", ["admin"], ["read", "write", "admin", "delete"]),
            AccessPolicy("pol_db", "数据库凭证", "secret/database/*", ["admin", "db_admin"], ["read"]),
        ]
        for p in defaults:
            self._policies[p.policy_id] = p

    def _encrypt_value(self, value: str) -> str:
        """加密存储值"""
        key = self._encryption_key or b"default-key-for-vault"
        value_bytes = value.encode("utf-8")
        extended_key = (key * ((len(value_bytes) // len(key)) + 1))[: len(value_bytes)]
        encrypted = bytes(a ^ b for a, b in zip(value_bytes, extended_key))
        return base64.urlsafe_b64encode(encrypted).decode()

    def _decrypt_value(self, encrypted: str) -> str:
        """解密存储值"""
        key = self._encryption_key or b"default-key-for-vault"
        raw = base64.urlsafe_b64decode(encrypted)
        extended_key = (key * ((len(raw) // len(key)) + 1))[: len(raw)]
        decrypted = bytes(a ^ b for a, b in zip(raw, extended_key))
        return decrypted.decode("utf-8")

    @trace_operation("vault_store")
    def store_secret(
        self,
        path: str,
        value: str,
        secret_type: SecretType = SecretType.CUSTOM,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        rotation_days: int = 90,
        auto_rotate: bool = False,
        owner: str = "system",
    ) -> Dict[str, Any]:
        """存储密钥"""
        if len(self._secrets) >= self._max_secrets:
            raise RuntimeError(f"密钥数量已达上限 {self._max_secrets}")

        if path in self._path_index:
            return self.update_secret(path, value)

        secret_id = f"sec_{uuid.uuid4().hex[:12]}"
        name = path.split("/")[-1]
        encrypted = self._encrypt_value(value)

        secret = SecretEntry(
            secret_id=secret_id,
            name=name,
            path=path,
            secret_type=secret_type,
            encrypted_value=encrypted,
            metadata=metadata or {},
            tags=tags or [],
            rotation_days=rotation_days,
            auto_rotate=auto_rotate,
            owner=owner,
        )
        self._secrets[secret_id] = secret
        self._path_index[path] = secret_id

        audit_logger.log(
            action="secret_stored", resource=secret_id, details=f"存储密钥: {path}, 类型: {secret_type.value}"
        )
        self.stats["secrets_stored"] += 1
        return {
            "secret_id": secret_id,
            "path": path,
            "type": secret_type.value,
            "version": 1,
            "rotation_days": rotation_days,
        }

    @trace_operation("vault_retrieve")
    def retrieve_secret(self, path: str, version: Optional[int] = None) -> Dict[str, Any]:
        """检索密钥"""
        secret_id = self._path_index.get(path)
        if not secret_id or secret_id not in self._secrets:
            raise ValueError(f"密钥 {path} 不存在")

        secret = self._secrets[secret_id]

        if secret.expires_at and secret.expires_at < time.time():
            logger.warning(f"密钥已过期: {path}")

        if version and version <= len(secret.versions):
            encrypted = secret.versions[version - 1]["encrypted_value"]
        else:
            encrypted = secret.encrypted_value

        value = self._decrypt_value(encrypted)
        secret.last_accessed = time.time()
        secret.access_count += 1

        self._access_log.append({"action": "retrieve", "path": path, "secret_id": secret_id, "timestamp": time.time()})

        # 返回时不包含实际值的完整信息（安全考虑）
        metrics_collector.counter("vault_access")
        return {
            "path": path,
            "type": secret.secret_type.value,
            "value": value,  # 实际值仅在直接检索时返回
            "version": version or secret.version,
            "last_accessed": datetime.fromtimestamp(secret.last_accessed).isoformat(),
            "access_count": secret.access_count,
        }

    @trace_operation("vault_update")
    def update_secret(self, path: str, new_value: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """更新密钥"""
        secret_id = self._path_index.get(path)
        if not secret_id or secret_id not in self._secrets:
            raise ValueError(f"密钥 {path} 不存在")

        secret = self._secrets[secret_id]
        # 保存旧版本
        secret.versions.append(
            {"version": secret.version, "encrypted_value": secret.encrypted_value, "timestamp": time.time()}
        )

        secret.encrypted_value = self._encrypt_value(new_value)
        secret.version += 1
        secret.updated_at = time.time()
        if metadata:
            secret.metadata.update(metadata)

        audit_logger.log(
            action="secret_updated", resource=secret_id, details=f"更新密钥: {path}, 版本: {secret.version}"
        )
        self.stats["secrets_updated"] += 1
        return {
            "secret_id": secret_id,
            "path": path,
            "version": secret.version,
            "history_versions": len(secret.versions),
        }

    @trace_operation("vault_delete")
    def delete_secret(self, path: str) -> bool:
        """删除密钥"""
        secret_id = self._path_index.get(path)
        if not secret_id:
            raise ValueError(f"密钥 {path} 不存在")

        del self._secrets[secret_id]
        del self._path_index[path]

        audit_logger.log(action="secret_deleted", resource=secret_id, details=f"删除密钥: {path}")
        self.stats["secrets_deleted"] += 1
        return True

    @trace_operation("vault_rotate")
    def rotate_secret(self, path: str, new_value: Optional[str] = None) -> Dict[str, Any]:
        """轮换密钥"""
        if new_value is None:
            new_value = base64.urlsafe_b64encode(os.urandom(32)).decode()

        result = self.update_secret(path, new_value)

        audit_logger.log(
            action="secret_rotated",
            resource=result["secret_id"],
            details=f"轮换密钥: {path}, 新版本: {result['version']}",
        )
        return result

    @trace_operation("vault_list")
    def list_secrets(
        self, path_prefix: str = "secret/", tag: Optional[str] = None, secret_type: Optional[SecretType] = None
    ) -> List[Dict]:
        """列出密钥"""
        results = []
        for secret in self._secrets.values():
            if not secret.path.startswith(path_prefix):
                continue
            if tag and tag not in secret.tags:
                continue
            if secret_type and secret.secret_type != secret_type:
                continue

            is_expired = secret.expires_at and secret.expires_at < time.time()
            needs_rotation = secret.auto_rotate and (time.time() - secret.updated_at) > secret.rotation_days * 86400

            results.append(
                {
                    "path": secret.path,
                    "name": secret.name,
                    "type": secret.secret_type.value,
                    "version": secret.version,
                    "tags": secret.tags,
                    "owner": secret.owner,
                    "access_count": secret.access_count,
                    "created_at": datetime.fromtimestamp(secret.created_at).isoformat(),
                    "updated_at": datetime.fromtimestamp(secret.updated_at).isoformat(),
                    "expired": is_expired,
                    "needs_rotation": needs_rotation,
                }
            )

        return results

    @trace_operation("vault_check_rotation")
    def check_rotation_needs(self) -> Dict[str, Any]:
        """检查需要轮换的密钥"""
        needs_rotation = []
        expired = []

        for secret in self._secrets.values():
            if secret.expires_at and secret.expires_at < time.time():
                expired.append(
                    {"path": secret.path, "expired_since": datetime.fromtimestamp(secret.expires_at).isoformat()}
                )

            if secret.auto_rotate and (time.time() - secret.updated_at) > secret.rotation_days * 86400:
                needs_rotation.append(
                    {
                        "path": secret.path,
                        "last_rotated": datetime.fromtimestamp(secret.updated_at).isoformat(),
                        "rotation_days": secret.rotation_days,
                    }
                )

        return {
            "needs_rotation": needs_rotation,
            "expired": expired,
            "total_needs_attention": len(needs_rotation) + len(expired),
        }

    def get_access_log(self, limit: int = 100) -> List[Dict]:
        return [
            {
                "action": e["action"],
                "path": e["path"],
                "secret_id": e["secret_id"],
                "timestamp": datetime.fromtimestamp(e["timestamp"]).isoformat(),
            }
            for e in reversed(self._access_log[-limit:])
        ]

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        params = params or {}
        actions = {
            "store_secret": self.store_secret,
            "retrieve_secret": self.retrieve_secret,
            "update_secret": self.update_secret,
            "delete_secret": self.delete_secret,
            "rotate_secret": self.rotate_secret,
            "list_secrets": self.list_secrets,
            "check_rotation_needs": self.check_rotation_needs,
            "get_access_log": self.get_access_log,
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }

        if action not in actions:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}

        handler = actions[action]
        if callable(handler) and not isinstance(handler, list):
            import inspect

            if inspect.iscoroutinefunction(handler):
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            else:
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            if isinstance(result, dict):
                return {"status": "success", **result}
            return {"status": "success", "data": result}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        base.update(
            {
                "total_secrets": len(self._secrets),
                "policies": len(self._policies),
                "access_log_entries": len(self._access_log),
                "encryption": "active",
                "auto_rotation_enabled": sum(1 for s in self._secrets.values() if s.auto_rotate),
            }
        )
        return base

    def shutdown(self) -> None:
        self._encryption_key = None
        audit_logger.log(
            action="module_shutdown", resource="secret_vault", details=f"关闭，{len(self._secrets)} 个密钥记录"
        )

    def audit_access(self, secret_name: str, accessor: str, action: str = "read") -> None:
        """审计密钥访问记录"""
        if hasattr(self, "_audit") and self._audit:
            self._audit.log("secret_access", {"secret": secret_name, "accessor": accessor, "action": action})

    def batch_set(self, secrets: Dict[str, str]) -> Dict:
        """批量设置密钥"""
        success = 0
        for name, value in secrets.items():
            self._secrets[name] = {"value": value, "created_at": time.time()}
            success += 1
        return {"set": success, "total": len(secrets)}

    def get_secret_metadata(self, secret_name: str) -> Optional[Dict]:
        """获取密钥元数据（不含值）"""
        data = self._secrets.get(secret_name)
        if not data:
            return None
        return {k: v for k, v in data.items() if k != "value"}

    def list_secrets_metadata(self) -> List[Dict]:
        """列出所有密钥的元数据"""
        return [{"name": k, **({kk: vv for kk, vv in v.items() if kk != "value"})} for k, v in self._secrets.items()]

    def validate_secret(self, secret_name: str, rules: Dict) -> Dict:
        """验证密钥是否符合安全策略"""
        data = self._secrets.get(secret_name)
        if not data:
            return {"valid": False, "error": "not found"}
        value = data.get("value", "")
        errors = []
        min_len = rules.get("min_length", 8)
        if len(value) < min_len:
            errors.append(f"too_short: min {min_len}")
        if rules.get("require_upper") and not any(c.isupper() for c in value):
            errors.append("missing_uppercase")
        if rules.get("require_digit") and not any(c.isdigit() for c in value):
            errors.append("missing_digit")
        if rules.get("require_special") and not any(c in "!@#$%^&*" for c in value):
            errors.append("missing_special")
        return {"valid": len(errors) == 0, "errors": errors, "length": len(value)}

    def audit_secret_access(self, secret_name: str, accessor: str, action: str = "read") -> Dict[str, Any]:
        """审计密钥访问记录，检测异常访问模式"""
        key = f"audit:{secret_name}"
        records = self._audit_log.get(key, []) if hasattr(self, "_audit_log") else []
        now = time.time()
        records.append({"accessor": accessor, "action": action, "timestamp": now, "secret": secret_name})
        recent_hour = [r for r in records if now - r["timestamp"] < 3600]
        unique_accessors = len(set(r["accessor"] for r in recent_hour))
        anomaly = unique_accessors > 5
        if hasattr(self, "_audit_log"):
            self._audit_log[key] = records[-100:]
        return {
            "success": True,
            "recent_access_count": len(recent_hour),
            "unique_accessors": unique_accessors,
            "anomaly_detected": anomaly,
            "accessor": accessor,
            "action": action,
        }

module_class = SecretVault
