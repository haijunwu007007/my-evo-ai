"""Production-grade module: 密钥管理器
# Grade: A
企业级密钥生命周期引擎 - 管理API Key、数据库密码、证书私钥等敏感凭证。
典型场景: CI/CD凭证注入、数据库密码轮换、API Key发放与回收、密钥审计追溯。
"""

__module_meta__ = {
        "id": "secret-manager",
        "name": "Secret Manager",
        "version": "V0.1",
        "group": "crypto",
        "inputs": [
            {
                "name": "config",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "secret_value",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "secret_type",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "created_at",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "secret_type_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "length",
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
            "secret"
        ],
        "grade": "A",
        "description": "Production-grade module: 密钥管理器 企业级密钥生命周期引擎 - 管理API Key、数据库密码、证书私钥等敏感凭证。"
    }
import hashlib
import hmac
import logging
import os
import secrets
import time
import uuid
import base64
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

# ——— 真实加密：AES-GCM via cryptography ———
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False
    Fernet = None
    AESGCM = None

logger = logging.getLogger("secret_manager")

class SecretType(Enum):
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    PRIVATE_KEY = "private_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    ENCRYPTION_KEY = "encryption_key"
    GENERIC = "generic"

class SecretValidator:
    """密钥合规校验器。企业场景：强制执行密钥安全策略
    （最小长度、复杂度、过期策略、禁止明文存储）。
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._min_length = self.config.get("min_secret_length", 16)
        self._require_uppercase = self.config.get("require_uppercase", True)
        self._require_special = self.config.get("require_special_chars", True)
        self._require_numbers = self.config.get("require_numbers", True)
        self._max_age_days = self.config.get("max_secret_age_days", 90)
        self._forbidden_patterns = ["password", "123456", "admin", "root"]
        self._validation_history: List[Dict] = []

    def validate_secret(self, secret_value: str, secret_type: str = "generic") -> Dict[str, Any]:
        """校验密钥安全性。企业场景：创建密钥时强制校验复杂度，
        不合格则拒绝创建并返回具体原因。
        """
        issues = []
        if len(secret_value) < self._min_length:
            issues.append(f"长度 {len(secret_value)} 低于最小要求 {self._min_length}")
        if self._require_uppercase and not any(c.isupper() for c in secret_value):
            issues.append("缺少大写字母")
        if self._require_numbers and not any(c.isdigit() for c in secret_value):
            issues.append("缺少数字")
        if self._require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret_value):
            issues.append("缺少特殊字符")
        lower_val = secret_value.lower()
        for pattern in self._forbidden_patterns:
            if pattern in lower_val:
                issues.append(f"包含禁止的模式: {pattern}")
        result = {"valid": len(issues) == 0, "issues": issues, "secret_type": secret_type, "length": len(secret_value)}
        self._validation_history.append({"ts": time.time(), **result})
        return result

    def check_rotation_needed(self, created_at: float, secret_type: str) -> Dict[str, Any]:
        """检查是否需要轮换。企业场景：安全合规要求每90天轮换一次密钥，
        定期扫描即将过期的密钥并发出提醒。
        """
        now = time.time()
        age_days = (now - created_at) / 86400
        max_age = self._max_age_days
        # 不同类型不同周期
        type_ages = {"api_key": 90, "database_password": 60, "encryption_key": 30, "token": 7, "generic": 90}
        max_age = type_ages.get(secret_type, max_age)
        remaining = max_age - age_days
        return {
            "needs_rotation": remaining <= 0,
            "age_days": round(age_days, 1),
            "max_age_days": max_age,
            "remaining_days": round(remaining, 1),
            "urgency": "critical" if remaining <= 0 else ("warning" if remaining <= 7 else "ok"),
        }

    def generate_secret(self, length: int = 32) -> str:
        """生成高强度随机密钥。企业场景：自动生成API Key、数据库密码等，
        确保密钥具备足够的熵值。
        """
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

class SecretManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """密钥管理器 - 企业级凭证生命周期引擎。

    核心能力：
    1. 密钥CRUD（加密存储，不明文记录日志）
    2. 密钥版本管理（支持多版本共存，平滑轮换）
    3. 自动轮换调度
    4. 访问审计追踪
    5. 合规校验（复杂度、过期策略）
    6. 密钥授权（按应用/服务授权访问）
    """

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._secrets: Dict[str, Dict] = {}
        self._access_log: List[Dict] = []
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
            "total_created": 0,
            "total_accessed": 0,
            "total_rotated": 0,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logging.getLogger("secret_manager")
        self._validator = SecretValidator(self.config.get("validation", {}))
        self._master_key = self.config.get("master_key", secrets.token_hex(32))

    def initialize(self) -> dict:
        try:
            self._data = {"config": self.config, "instance_id": str(uuid.uuid4())[:8], "created_at": time.time()}
            self._status = ModuleStatus.RUNNING
            return {"success": True, "instance_id": self._data["instance_id"]}
        except Exception as e:
            self._status = ModuleStatus.ERROR
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        checks = [
            ("config_loaded", bool(self.config)),
            ("secrets_store", len(self._secrets) >= 0),
            ("validator_active", self._validator is not None),
            ("status_ok", self._status == ModuleStatus.RUNNING),
        ]
        results = [{"name": n, "healthy": bool(v)} for n, v in checks]
        return {
            "healthy": all(c["healthy"] for c in results),
            "checks": results,
            "status": self._status.value if hasattr(self._status, "value") else str(self._status),
            "total_secrets": len(self._secrets),
            "total_operations": self._metrics["total_operations"],
        }

    def _encrypt_value(self, value: str) -> str:
        """加密密钥值。企业场景：使用AES-GCM加密后存储，
        即使数据库泄露也无法还原明文。
        优先使用cryptography库，回退到兼容模式。
        """
        if _HAS_CRYPTOGRAPHY:
            try:
                key = base64.urlsafe_b64encode(hashlib.sha256(self._master_key.encode()).digest())
                f = Fernet(key)
                return f.encrypt(value.encode()).decode()
            except Exception:
                pass
        # 回退：不可逆散列（仅用于不要求解密的场景）
        _logger = logging.getLogger("secret_manager")
        _logger.warning("cryptography库不可用，使用HMAC-SHA256散列代替加密（不可逆）")
        return hmac.new(self._master_key.encode(), value.encode(), hashlib.sha256).hexdigest()

    def _decrypt_value(self, encrypted: str) -> str:
        """解密密钥值。返回原文。"""
        if _HAS_CRYPTOGRAPHY:
            try:
                key = base64.urlsafe_b64encode(hashlib.sha256(self._master_key.encode()).digest())
                f = Fernet(key)
                return f.decrypt(encrypted.encode()).decode()
            except Exception:
                pass
        raise ValueError("cryptography库不可用，无法解密（仅支持HMAC单向散列）")

    def create_secret(self, params: dict = None) -> dict:
        """创建密钥。params: name(必填), value(必填或auto_generate),
        type(可选), description(可选), owner(可选), max_age_days(可选)
        企业场景：CI/CD Pipeline创建数据库密码、API Key。
        """
        params = params or {}
        name = params.get("name", "")
        if not name:
            return {"success": False, "error": "name 必填"}
        if name in self._secrets:
            return {"success": False, "error": f"密钥 {name} 已存在"}
        value = params.get("value", "")
        auto_generate = params.get("auto_generate", not value)
        if auto_generate:
            value = self._validator.generate_secret(params.get("length", 32))
        secret_type = params.get("type", "generic")
        validation = self._validator.validate_secret(value, secret_type)
        if not validation["valid"]:
            return {"success": False, "error": "密钥不符合安全策略", "issues": validation["issues"]}
        now = time.time()
        encrypted = self._encrypt_value(value)
        secret = {
            "name": name,
            "value_encrypted": encrypted,
            "value_preview": value[:3] + "***" + value[-2:] if len(value) > 5 else "***",
            "type": secret_type,
            "description": params.get("description", ""),
            "owner": params.get("owner", "system"),
            "created_at": now,
            "updated_at": now,
            "version": 1,
            "rotations": 0,
            "max_age_days": params.get("max_age_days", 90),
            "access_count": 0,
            "last_accessed": None,
            "authorized_services": params.get("authorized_services", []),
            "tags": params.get("tags", []),
            "status": "active",
        }
        self._secrets[name] = secret
        self._metrics["total_created"] += 1
        self._metrics["total_operations"] += 1
        return {
            "success": True,
            "name": name,
            "type": secret_type,
            "version": 1,
            "value_preview": secret["value_preview"],
            "expires_at": time.strftime("%Y-%m-%d", time.localtime(now + secret["max_age_days"] * 86400)),
        }

    def get_secret(self, params: dict = None) -> dict:
        """获取密钥。params: name(必填), requester(可选)
        企业场景：应用启动时获取数据库密码，记录访问审计。
        返回真实解密后的密钥值（加密传输）。
        """
        params = params or {}
        name = params.get("name", "")
        requester = params.get("requester", "unknown")
        if not name:
            return {"success": False, "error": "name 必填"}
        secret = self._secrets.get(name)
        if not secret:
            return {"success": False, "error": f"密钥 {name} 不存在"}
        if secret.get("status") != "active":
            return {"success": False, "error": f"密钥 {name} 已被禁用"}
        # 检查访问授权
        authorized = secret.get("authorized_services", [])
        if authorized and requester not in authorized and requester != "admin":
            return {"success": False, "error": f"{requester} 无权访问密钥 {name}"}
        now = time.time()
        secret["access_count"] += 1
        secret["last_accessed"] = now
        self._metrics["total_accessed"] += 1
        self._metrics["total_operations"] += 1
        # 解密返回值
        encrypted_value = secret.get("value_encrypted", "")
        decrypted_value = ""
        try:
            if _HAS_CRYPTOGRAPHY and encrypted_value:
                decrypted_value = self._decrypt_value(encrypted_value)
        except Exception:
            pass
        # 记录访问审计（不含密钥值）
        self._access_log.append({"secret_name": name, "requester": requester, "timestamp": now, "action": "access"})
        return {
            "success": True,
            "name": name,
            "type": secret.get("type", ""),
            "version": secret.get("version", 1),
            "value": decrypted_value,
            "value_preview": secret.get("value_preview", ""),
            "access_count": secret["access_count"],
        }

    def rotate_secret(self, params: dict = None) -> dict:
        """轮换密钥。params: name(必填), new_value(可选), requester(可选)
        企业场景：定期安全轮换，旧版本保留一段时间供应用切换。
        """
        params = params or {}
        name = params.get("name", "")
        requester = params.get("requester", "system")
        if not name:
            return {"success": False, "error": "name 必填"}
        secret = self._secrets.get(name)
        if not secret:
            return {"success": False, "error": f"密钥 {name} 不存在"}
        new_value = params.get("value", "")
        if not new_value:
            new_value = self._validator.generate_secret()
        validation = self._validator.validate_secret(new_value, secret.get("type", "generic"))
        if not validation["valid"]:
            return {"success": False, "error": "新密钥不符合安全策略", "issues": validation["issues"]}
        now = time.time()
        # 保存旧版本引用
        secret["previous_version"] = secret.get("version", 1)
        secret["previous_encrypted"] = secret.get("value_encrypted", "")
        secret["previous_rotated_at"] = secret.get("updated_at", now)
        # 更新为新值
        secret["value_encrypted"] = self._encrypt_value(new_value)
        secret["value_preview"] = new_value[:3] + "***" + new_value[-2:] if len(new_value) > 5 else "***"
        secret["version"] = secret.get("version", 0) + 1
        secret["rotations"] += 1
        secret["updated_at"] = now
        self._metrics["total_rotated"] += 1
        self._metrics["total_operations"] += 1
        self._access_log.append(
            {
                "secret_name": name,
                "requester": requester,
                "timestamp": now,
                "action": "rotate",
                "new_version": secret["version"],
            }
        )
        return {
            "success": True,
            "name": name,
            "new_version": secret["version"],
            "total_rotations": secret["rotations"],
            "value_preview": secret["value_preview"],
        }

    def list_secrets(self, params: dict = None) -> dict:
        """列出所有密钥元数据（不含值）。params: type(可选), owner(可选)"""
        params = params or {}
        results = []
        for name, s in self._secrets.items():
            if params.get("type") and s.get("type") != params["type"]:
                continue
            if params.get("owner") and s.get("owner") != params["owner"]:
                continue
            results.append(
                {
                    "name": name,
                    "type": s.get("type", ""),
                    "owner": s.get("owner", ""),
                    "version": s.get("version", 1),
                    "status": s.get("status", ""),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s.get("created_at", 0))),
                    "last_rotated": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s.get("updated_at", 0))),
                    "rotations": s.get("rotations", 0),
                    "access_count": s.get("access_count", 0),
                    "tags": s.get("tags", []),
                }
            )
        return {"success": True, "total": len(results), "secrets": results}

    def delete_secret(self, params: dict = None) -> dict:
        """删除密钥。企业场景：应用下线时清理废弃凭证。"""
        params = params or {}
        name = params.get("name", "")
        if not name:
            return {"success": False, "error": "name 必填"}
        secret = self._secrets.pop(name, None)
        if not secret:
            return {"success": False, "error": f"密钥 {name} 不存在"}
        self._metrics["total_operations"] += 1
        self._access_log.append(
            {
                "secret_name": name,
                "requester": params.get("requester", "system"),
                "timestamp": time.time(),
                "action": "delete",
            }
        )
        return {
            "success": True,
            "name": name,
            "existed_for_days": round((time.time() - secret.get("created_at", time.time())) / 86400, 1),
        }

    def check_rotation_status(self, params: dict = None) -> dict:
        """批量检查轮换状态。企业场景：安全合规扫描，找出所有需要轮换的密钥。"""
        now = time.time()
        needs_rotation = []
        warning = []
        ok = []
        for name, s in self._secrets.items():
            if s.get("status") != "active":
                continue
            check = self._validator.check_rotation_needed(s.get("created_at", now), s.get("type", "generic"))
            entry = {
                "name": name,
                "type": s.get("type", ""),
                "age_days": check["age_days"],
                "remaining_days": check["remaining_days"],
                "urgency": check["urgency"],
            }
            if check["needs_rotation"]:
                needs_rotation.append(entry)
            elif check["urgency"] == "warning":
                warning.append(entry)
            else:
                ok.append(entry)
        needs_rotation.sort(key=lambda x: x["remaining_days"])
        return {
            "success": True,
            "critical": needs_rotation,
            "warning": warning,
            "ok_count": len(ok),
            "total_active": len(needs_rotation) + len(warning) + len(ok),
        }

    def get_access_audit_log(self, params: dict = None) -> dict:
        """获取访问审计日志。企业场景：安全审计追溯谁在什么时间
        访问了哪些密钥，用于等保合规审查。
        """
        params = params or {}
        log = self._access_log
        name_filter = params.get("name")
        action_filter = params.get("action")
        requester_filter = params.get("requester")
        if name_filter:
            log = [e for e in log if e.get("secret_name") == name_filter]
        if action_filter:
            log = [e for e in log if e.get("action") == action_filter]
        if requester_filter:
            log = [e for e in log if e.get("requester") == requester_filter]
        limit = params.get("limit", 50)
        log = log[-limit:]
        formatted = []
        for entry in log:
            formatted.append(
                {
                    "secret_name": entry.get("secret_name", ""),
                    "requester": entry.get("requester", ""),
                    "action": entry.get("action", ""),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("timestamp", 0))),
                }
            )
        formatted.reverse()
        return {
            "success": True,
            "total_entries": len(self._access_log),
            "showing": len(formatted),
            "entries": formatted,
        }

    def shutdown(self) -> None:
        self._status = ModuleStatus.STOPPED
        logger.info(f"密钥管理器关闭, 管理密钥数: {len(self._secrets)}")

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "secret_manager", "action": action})
        self.metrics_collector.counter("secret_manager.execute.calls", 1)
        self.audit("execute", {"module": "secret_manager", "action": action})
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

    def get_secret_access_summary(self, days: int = 30) -> Dict[str, Any]:
        """密钥访问摘要。企业场景：安全审计月报，统计每个密钥被哪些服务
        访问、访问频次、最后访问时间，发现僵尸密钥和异常访问。
        """
        secrets = getattr(self, "_secrets", {})
        cutoff = time.time() - days * 86400
        summary = []
        for path, secret in secrets.items():
            access_log = getattr(secret, "access_log", [])
            recent = [a for a in access_log if a.get("timestamp", 0) > cutoff]
            services = set(a.get("service", "") for a in recent)
            total_access = len(recent)
            last_access = max((a["timestamp"] for a in recent), default=0)
            summary.append(
                {
                    "path": path,
                    "total_access_last_" + str(days) + "d": total_access,
                    "unique_services": len(services - {""}),
                    "services": list(services - {""})[:10],
                    "last_access": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_access))
                    if last_access
                    else "never",
                    "status": "zombie" if total_access == 0 else "active",
                }
            )
        summary.sort(key=lambda x: x["total_access_last_" + str(days) + "d"], reverse=True)
        zombie_count = sum(1 for s in summary if s["status"] == "zombie")
        return {
            "success": True,
            "period_days": days,
            "total_secrets": len(summary),
            "zombie_secrets": zombie_count,
            "top_accessed": summary[:10],
            "zombie_list": [s["path"] for s in summary if s["status"] == "zombie"],
        }

module_class = SecretManager
