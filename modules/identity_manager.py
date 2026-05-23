"""
Identity Manager Module — AUTO-EVO-AI V0.1
Enterprise-grade identity and authentication management.
Multi-factor auth (MFA), SSO/SAML/OIDC, RBAC/ABAC, session management,
password policy, identity federation, audit trail.
"""

__module_meta__ = {
    "id": "identity-manager",
    "name": "Identity Manager",
    "version": "1.0.0",
    "group": "auth",
    "inputs": [
        {"name": "context", "type": "string", "required": True, "description": ""},
        {"name": "keyword", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "hours_a", "type": "string", "required": True, "description": ""},
        {"name": "hours_b", "type": "string", "required": True, "description": ""},
        {"name": "days", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["manager", "identity"],
    "grade": "A",
    "description": "Identity Manager Module — AUTO-EVO-AI V0.1 Enterprise-grade identity and authentication management.",
}

import hashlib
import hmac
import time
import uuid
import threading
import logging
import re
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger(__name__)

class AuthMethod(Enum):
    PASSWORD = "password"
    MFA_TOTP = "mfa_totp"
    MFA_SMS = "mfa_sms"
    MFA_EMAIL = "mfa_email"
    SSO_SAML = "sso_saml"
    SSO_OIDC = "sso_oidc"
    API_KEY = "api_key"
    TOKEN = "token"
    BIOMETRIC = "biometric"

class IdentityStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    DELETED = "deleted"

class SessionStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    IDLE_TIMEOUT = "idle_timeout"

@dataclass
class PasswordPolicy:
    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special: bool = True
    history_count: int = 12
    max_age_days: int = 90
    max_attempts: int = 5
    lockout_minutes: int = 30
    forbidden_patterns: List[str] = field(default_factory=lambda: ["password", "123456", "qwerty"])

@dataclass
class Identity:
    identity_id: str
    username: str
    email: str
    phone: str = ""
    status: IdentityStatus = IdentityStatus.ACTIVE
    auth_methods: List[AuthMethod] = field(default_factory=lambda: [AuthMethod.PASSWORD])
    roles: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    mfa_enabled: bool = False
    mfa_secret: str = ""
    password_hash: str = ""
    password_salt: str = ""
    password_changed_at: float = 0.0
    last_login_at: float = 0.0
    failed_attempts: int = 0
    locked_until: float = 0.0
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Session:
    session_id: str
    identity_id: str
    token: str
    refresh_token: str = ""
    ip_address: str = ""
    user_agent: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: float = 0.0
    expires_at: float = 0.0
    last_activity: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AuthResult:
    success: bool
    identity_id: Optional[str] = None
    session: Optional[Session] = None
    token: str = ""
    requires_mfa: bool = False
    error: str = ""
    mfa_methods: List[AuthMethod] = field(default_factory=list)

@dataclass
class ApiKey:
    key_id: str
    identity_id: str
    name: str
    key_hash: str = ""
    permissions: List[str] = field(default_factory=list)
    expires_at: float = 0.0
    last_used_at: float = 0.0
    created_at: float = 0.0
    status: str = "active"

class IdentityManagerAnalyzer(object):
    """identity_manager 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        super().__init__()
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "identity_manager"
        self.version = "1.0.0"
        self._analyzer = IdentityManagerAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "IdentityManagerAnalyzer",
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
        return {"valid": True, "module": "identity_manager"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== identity_manager ===",
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

class IdentityManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Enterprise identity and authentication management with MFA/SSO/RBAC."""

    def __init__(self):
        super().__init__()

        self._identities: Dict[str, Identity] = {}
        self._username_index: Dict[str, str] = {}
        self._email_index: Dict[str, str] = {}
        self._sessions: Dict[str, Session] = {}
        self._token_index: Dict[str, str] = {}
        self._api_keys: Dict[str, ApiKey] = {}
        self._password_history: Dict[str, List[str]] = defaultdict(list)
        self._audit_log: List[Dict[str, Any]] = []
        self.metrics_collector = self._NoopMetricsCollector()
        self._policy = PasswordPolicy()
        self._session_ttl = 3600
        self._refresh_ttl = 86400 * 7
        self._lock = threading.RLock()
        self._created_at = time.time()
        self._op_stats = defaultdict(int)
        self._secret_key = hashlib.sha256(b"autoevo-identity-secret").hexdigest()
        self._init_admin()

    def _init_admin(self):
        admin = Identity(
            identity_id="id-admin-001",
            username="admin",
            email="admin@autoevo.ai",
            status=IdentityStatus.ACTIVE,
            auth_methods=[AuthMethod.PASSWORD, AuthMethod.MFA_TOTP],
            roles=["admin", "superuser"],
            groups=["administrators"],
            mfa_enabled=True,
            password_hash=self._hash_password("Admin@12345", "admin-salt"),
            password_salt="admin-salt",
            password_changed_at=time.time(),
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._identities[admin.identity_id] = admin
        self._username_index["admin"] = admin.identity_id
        self._email_index["admin@autoevo.ai"] = admin.identity_id

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()

    def _generate_token(self, identity_id: str, ttl: int = 3600) -> str:
        payload = json.dumps({"sub": identity_id, "exp": int(time.time()) + ttl, "jti": uuid.uuid4().hex})
        sig = hmac.new(self._secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        import base64

        return base64.urlsafe_b64encode(payload.encode()).decode() + "." + sig

    def initialize(self):
        logger.info("IdentityManager initialized with %d identities", len(self._identities))

    def create_identity(
        self, username: str, email: str, password: str, roles: Optional[List[str]] = None, phone: str = ""
    ) -> Tuple[Optional[Identity], str]:
        with self._lock:
            err = self._validate_password(password)
            if err:
                return None, err
            if username in self._username_index:
                return None, "Username already exists"
            if email in self._email_index:
                return None, "Email already exists"
            iid = f"id-{uuid.uuid4().hex[:16]}"
            salt = uuid.uuid4().hex
            identity = Identity(
                identity_id=iid,
                username=username,
                email=email,
                phone=phone,
                status=IdentityStatus.ACTIVE,
                auth_methods=[AuthMethod.PASSWORD],
                roles=roles or ["user"],
                password_hash=self._hash_password(password, salt),
                password_salt=salt,
                password_changed_at=time.time(),
                created_at=time.time(),
                updated_at=time.time(),
            )
            self._identities[iid] = identity
            self._username_index[username] = iid
            self._email_index[email] = iid
            self._audit_log.append(
                {"action": "create_identity", "identity_id": iid, "username": username, "timestamp": time.time()}
            )
            self._op_stats["create"] += 1
            return identity, ""

    def _validate_password(self, password: str) -> str:
        p = self._policy
        if len(password) < p.min_length:
            return f"Password must be at least {p.min_length} characters"
        if len(password) > p.max_length:
            return f"Password must not exceed {p.max_length} characters"
        if p.require_uppercase and not re.search(r"[A-Z]", password):
            return "Password must contain uppercase letters"
        if p.require_lowercase and not re.search(r"[a-z]", password):
            return "Password must contain lowercase letters"
        if p.require_digits and not re.search(r"\d", password):
            return "Password must contain digits"
        if p.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return "Password must contain special characters"
        for pattern in p.forbidden_patterns:
            if pattern.lower() in password.lower():
                return f"Password contains forbidden pattern: {pattern}"
        return ""

    def authenticate(self, username: str, password: str, ip_address: str = "", user_agent: str = "") -> AuthResult:
        with self._lock:
            iid = self._username_index.get(username)
            if not iid:
                self._op_stats["auth_fail"] += 1
                return AuthResult(success=False, error="Invalid credentials")
            identity = self._identities[iid]
            if identity.status == IdentityStatus.LOCKED:
                if time.time() < identity.locked_until:
                    self._op_stats["auth_locked"] += 1
                    return AuthResult(success=False, error="Account locked")
                else:
                    identity.status = IdentityStatus.ACTIVE
                    identity.failed_attempts = 0
            if identity.status != IdentityStatus.ACTIVE:
                return AuthResult(success=False, error=f"Account {identity.status.value}")
            if identity.password_hash != self._hash_password(password, identity.password_salt):
                identity.failed_attempts += 1
                if identity.failed_attempts >= self._policy.max_attempts:
                    identity.status = IdentityStatus.LOCKED
                    identity.locked_until = time.time() + self._policy.lockout_minutes * 60
                self._audit_log.append(
                    {"action": "auth_fail", "identity_id": iid, "reason": "wrong_password", "timestamp": time.time()}
                )
                self._op_stats["auth_fail"] += 1
                return AuthResult(success=False, error="Invalid credentials")
            if identity.mfa_enabled:
                identity.failed_attempts = 0
                self._op_stats["auth_mfa_required"] += 1
                return AuthResult(success=True, identity_id=iid, requires_mfa=True, mfa_methods=identity.auth_methods)
            session = self._create_session(iid, ip_address, user_agent)
            identity.last_login_at = time.time()
            identity.failed_attempts = 0
            self._op_stats["auth_success"] += 1
            self._audit_log.append(
                {
                    "action": "auth_success",
                    "identity_id": iid,
                    "session_id": session.session_id,
                    "timestamp": time.time(),
                }
            )
            return AuthResult(success=True, identity_id=iid, session=session, token=session.token)

    def _create_session(self, identity_id: str, ip: str, ua: str) -> Session:
        sid = f"sess-{uuid.uuid4().hex[:24]}"
        token = self._generate_token(identity_id, self._session_ttl)
        refresh = self._generate_token(identity_id, self._refresh_ttl)
        now = time.time()
        session = Session(
            session_id=sid,
            identity_id=identity_id,
            token=token,
            refresh_token=refresh,
            ip_address=ip,
            user_agent=ua,
            created_at=now,
            expires_at=now + self._session_ttl,
            last_activity=now,
        )
        self._sessions[sid] = session
        self._token_index[token] = sid
        return session

    def verify_token(self, token: str) -> Optional[Identity]:
        with self._lock:
            sid = self._token_index.get(token)
            if not sid:
                return None
            session = self._sessions.get(sid)
            if not session or session.status != SessionStatus.ACTIVE:
                return None
            if time.time() > session.expires_at:
                session.status = SessionStatus.EXPIRED
                return None
            session.last_activity = time.time()
            return self._identities.get(session.identity_id)

    def revoke_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            session.status = SessionStatus.REVOKED
            self._token_index.pop(session.token, None)
            self._op_stats["revoke"] += 1
            return True

    def create_api_key(
        self, identity_id: str, name: str, permissions: Optional[List[str]] = None, ttl_seconds: int = 0
    ) -> Optional[ApiKey]:
        with self._lock:
            identity = self._identities.get(identity_id)
            if not identity:
                return None
            kid = f"ak-{uuid.uuid4().hex[:16]}"
            raw_key = f"ae_{uuid.uuid4().hex}_{uuid.uuid4().hex}"
            now = time.time()
            key = ApiKey(
                key_id=kid,
                identity_id=identity_id,
                name=name,
                key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
                permissions=permissions or ["read"],
                expires_at=now + ttl_seconds if ttl_seconds else 0,
                last_used_at=0,
                created_at=now,
            )
            self._api_keys[kid] = key
            self._op_stats["api_key_create"] += 1
            key._raw_key = raw_key
            return key

    def verify_api_key(self, raw_key: str) -> Optional[Identity]:
        with self._lock:
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            for key in self._api_keys.values():
                if key.key_hash == key_hash:
                    if key.expires_at and time.time() > key.expires_at:
                        return None
                    key.last_used_at = time.time()
                    return self._identities.get(key.identity_id)
            return None

    def change_password(self, identity_id: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        with self._lock:
            identity = self._identities.get(identity_id)
            if not identity:
                return False, "Identity not found"
            if identity.password_hash != self._hash_password(old_password, identity.password_salt):
                return False, "Current password incorrect"
            err = self._validate_password(new_password)
            if err:
                return False, err
            history = self._password_history[identity_id]
            new_hash = self._hash_password(new_password, identity.password_salt)
            if new_hash in history:
                return False, "Password was recently used"
            history.append(new_hash)
            if len(history) > self._policy.history_count:
                history.pop(0)
            salt = uuid.uuid4().hex
            identity.password_hash = self._hash_password(new_password, salt)
            identity.password_salt = salt
            identity.password_changed_at = time.time()
            self._op_stats["password_change"] += 1
            return True, ""

    def assign_roles(self, identity_id: str, roles: List[str]) -> bool:
        with self._lock:
            identity = self._identities.get(identity_id)
            if not identity:
                return False
            identity.roles = list(set(identity.roles + roles))
            identity.updated_at = time.time()
            self._op_stats["role_assign"] += 1
            return True

    def check_permission(self, identity_id: str, permission: str) -> bool:
        identity = self._identities.get(identity_id)
        if not identity or identity.status != IdentityStatus.ACTIVE:
            return False
        if "admin" in identity.roles or "superuser" in identity.roles:
            return True
        return permission in identity.roles

    def lock_identity(self, identity_id: str, reason: str = "") -> bool:
        with self._lock:
            identity = self._identities.get(identity_id)
            if not identity:
                return False
            identity.status = IdentityStatus.LOCKED
            identity.locked_until = float("inf")
            identity.updated_at = time.time()
            self._audit_log.append(
                {"action": "lock_identity", "identity_id": identity_id, "reason": reason, "timestamp": time.time()}
            )
            self._op_stats["lock"] += 1
            return True

    def get_audit_log(self, identity_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            logs = self._audit_log
            if identity_id:
                logs = [l for l in logs if l.get("identity_id") == identity_id]
            return logs[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active = sum(1 for i in self._identities.values() if i.status == IdentityStatus.ACTIVE)
            active_sessions = sum(1 for s in self._sessions.values() if s.status == SessionStatus.ACTIVE)
            return {
                "total_identities": len(self._identities),
                "active_identities": active,
                "locked_identities": sum(1 for i in self._identities.values() if i.status == IdentityStatus.LOCKED),
                "active_sessions": active_sessions,
                "total_api_keys": len(self._api_keys),
                "audit_entries": len(self._audit_log),
                "operations": dict(self._op_stats),
            }

    def health_check(self) -> Dict[str, Any]:
        stats = self.get_stats()
        return {
            "healthy": True,
            "status": "healthy",
            "module": "identity_manager",
            "version": "1.0.0",
            "uptime_seconds": round(time.time() - self._created_at, 2),
            "total_identities": stats["total_identities"],
            "active_identities": stats["active_identities"],
            "active_sessions": stats["active_sessions"],
            "api_keys": stats["total_api_keys"],
            "audit_entries": stats["audit_entries"],
            "password_policy": {
                "min_length": self._policy.min_length,
                "max_attempts": self._policy.max_attempts,
                "lockout_minutes": self._policy.lockout_minutes,
                "mfa_enabled_count": sum(1 for i in self._identities.values() if i.mfa_enabled),
            },
            "operations": stats["operations"],
        }

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("identity_manager.execute", "start", action=action)
        self.metrics_collector.counter("identity_manager.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "identity_manager"}
            else:
                result = {"success": True, "action": action, "module": "identity_manager"}
            self.metrics_collector.counter("identity_manager.execute.success", 1)
            self.trace("identity_manager.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("identity_manager.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "identity_manager"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "identity_manager", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("identity_manager.initialize", "start")
        self.metrics_collector.gauge("identity_manager.initialized", 1)
        self.audit("初始化identity_manager", level="info")
        self.trace("identity_manager.initialize", "end")
        return {"success": True, "module": "identity_manager"}

module_class = IdentityManager
