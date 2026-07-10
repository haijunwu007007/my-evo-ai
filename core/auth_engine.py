"""
AUTO-EVO-AI V0.1 — JWT 认证引擎
上市公司生产级别：JWT令牌签发/验证/刷新、角色权限RBAC、登录审计、暴力破解防护
"""
import logging
logger = logging.getLogger("evo.auth_engine")

import hashlib, hmac, time, json, os, secrets, base64, threading
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum


# ═══════════════════════════════════════════════════════
# JWT 纯Python实现（无PyJWT依赖）
# ═══════════════════════════════════════════════════════

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += '=' * pad
    return base64.urlsafe_b64decode(s)

def _hmac_sign(header_b64: str, payload_b64: str, secret: str) -> str:
    msg = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).digest()
    return _b64url_encode(sig)


class JWTError(Exception):
    """JWT令牌错误"""
    pass

class JWTExpiredError(JWTError):
    """令牌已过期"""
    pass

class JWTInvalidError(JWTError):
    """令牌无效"""
    pass


class JWTEngine:
    """纯Python JWT引擎 — HS256"""
    
    def __init__(self, secret: str = None):
        self.secret = secret or secrets.token_hex(32)
    
    def create_token(self, payload: dict, expires_in: int = 3600) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        payload["exp"] = int(time.time()) + expires_in
        payload["iat"] = int(time.time())
        payload["jti"] = secrets.token_hex(16)
        h = _b64url_encode(json.dumps(header, separators=(',', ':')).encode())
        p = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode())
        sig = _hmac_sign(h, p, self.secret)
        return f"{h}.{p}.{sig}"
    
    def verify_token(self, token: str) -> dict:
        parts = token.split('.')
        if len(parts) != 3:
            raise JWTInvalidError("Invalid token format")
        h, p, sig = parts
        expected_sig = _hmac_sign(h, p, self.secret)
        if not hmac.compare_digest(sig, expected_sig):
            raise JWTInvalidError("Invalid signature")
        payload = json.loads(_b64url_decode(p))
        if payload.get('exp', 0) < time.time():
            raise JWTExpiredError("Token expired")
        return payload


# ═══════════════════════════════════════════════════════
# 用户与角色模型
# ═══════════════════════════════════════════════════════

class Role(Enum):
    SUPER_ADMIN = "super_admin"    # 超级管理员：全部权限
    ADMIN = "admin"                # 管理员：大部分权限，不可删除系统
    OPERATOR = "operator"          # 操作员：执行模块/查看状态
    VIEWER = "viewer"              # 只读：仅查看

# 角色权限矩阵
ROLE_PERMISSIONS: dict[str, list[str]] = {
    Role.SUPER_ADMIN.value: ["*"],
    Role.ADMIN.value: [
        "modules:*", "execute:*", "pipelines:*", "config:*",
        "scheduler:*", "events:*", "queue:*", "github:*",
        "system:*", "notifications:*", "coordinator:*",
        "planner:*", "ws:*", "docs:*", "persistence:*",
    ],
    Role.OPERATOR.value: [
        "modules:read", "modules:execute",
        "pipelines:read", "pipelines:execute",
        "config:read", "scheduler:read", "events:read",
        "queue:read", "github:read", "system:read",
        "ws:*", "coordinator:read", "planner:read",
    ],
    Role.VIEWER.value: [
        "modules:read", "pipelines:read", "config:read",
        "scheduler:read", "events:read", "queue:read",
        "github:read", "system:read", "coordinator:read",
        "planner:read",
    ],
}

@dataclass
class User:
    username: str
    password_hash: str
    role: str = Role.VIEWER.value
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    last_login: float | None = None
    login_count: int = 0
    failed_attempts: int = 0
    locked_until: float = 0.0


# ═══════════════════════════════════════════════════════
# 认证引擎
# ═══════════════════════════════════════════════════════

class AuthEngine:
    """JWT认证引擎 — 上市公司生产级别"""
    
    def __init__(self, secret: str = None, persistence_dir: str = ".evo_data/auth"):
        self.jwt = JWTEngine(secret)
        self.persistence_dir = persistence_dir
        self.users: dict[str, User] = {}
        self.refresh_tokens: dict[str, dict] = {}  # jti -> {username, exp}
        self.blacklist: set = set()  # 被注销的jti
        self.login_history: list[dict] = []
        self.max_login_history = 1000
        self._lock = threading.Lock()
        
        # 暴力破解防护
        self.max_failed_attempts = 5
        self.lockout_duration = 300  # 5分钟锁定
        self._failed_ip: dict[str, dict] = {}  # IP -> {count, locked_until}
        self.max_ip_attempts = 10
        
        # 令牌配置
        self.access_token_ttl = 3600      # 1小时
        self.refresh_token_ttl = 86400 * 7  # 7天
        
        os.makedirs(persistence_dir, exist_ok=True)
        self._load_users()
    
    # ── 密码哈希 ──
    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"pbkdf2:{salt}:{h.hex()}"
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        try:
            parts = password_hash.split(':')
            if len(parts) != 3 or parts[0] != 'pbkdf2':
                return False
            salt, expected = parts[1], parts[2]
            h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hmac.compare_digest(h.hex(), expected)
        except Exception:
            return False
    
    # ── 用户管理 ──
    def _load_users(self):
        users_file = os.path.join(self.persistence_dir, "users.json")
        if os.path.exists(users_file):
            try:
                with open(users_file) as f:
                    data = json.load(f)
                for u in data:
                    self.users[u['username']] = User(**u)
            except Exception as _e:
                logger.warning(f"error: {_e}")
        # 创建默认管理员（仅在无用户时）
        if not self.users:
            self.create_user("admin", "admin123", Role.SUPER_ADMIN.value, force=True)
    
    def _save_users(self):
        users_file = os.path.join(self.persistence_dir, "users.json")
        data = []
        for u in self.users.values():
            data.append({
                "username": u.username, "password_hash": u.password_hash,
                "role": u.role, "enabled": u.enabled, "created_at": u.created_at,
                "last_login": u.last_login, "login_count": u.login_count,
                "failed_attempts": u.failed_attempts, "locked_until": u.locked_until,
            })
        with open(users_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def create_user(self, username: str, password: str, role: str = Role.VIEWER.value, force: bool = False) -> dict:
        with self._lock:
            if not force and username in self.users:
                return {"success": False, "error": "User already exists"}
            if len(username) < 3 or len(username) > 32:
                return {"success": False, "error": "Username must be 3-32 characters"}
            if len(password) < 6:
                return {"success": False, "error": "Password must be at least 6 characters"}
            user = User(
                username=username,
                password_hash=self.hash_password(password),
                role=role,
            )
            self.users[username] = user
            self._save_users()
            return {"success": True, "user": {"username": username, "role": role}}
    
    def delete_user(self, username: str, operator: str = "system") -> dict:
        with self._lock:
            if username not in self.users:
                return {"success": False, "error": "User not found"}
            if username == "admin":
                return {"success": False, "error": "Cannot delete default admin"}
            del self.users[username]
            self._save_users()
            self._log_auth(operator, "delete_user", f"Deleted user: {username}")
            return {"success": True}
    
    def update_user(self, username: str, role: str = None, enabled: bool = None, password: str = None) -> dict:
        with self._lock:
            if username not in self.users:
                return {"success": False, "error": "User not found"}
            user = self.users[username]
            if role and role in [r.value for r in Role]:
                user.role = role
            if enabled is not None:
                user.enabled = enabled
            if password and len(password) >= 6:
                user.password_hash = self.hash_password(password)
            self._save_users()
            return {"success": True, "user": {"username": username, "role": user.role, "enabled": user.enabled}}
    
    def list_users(self) -> list:
        result = []
        for u in self.users.values():
            result.append({
                "username": u.username,
                "role": u.role,
                "enabled": u.enabled,
                "created_at": u.created_at,
                "last_login": u.last_login,
                "login_count": u.login_count,
                "failed_attempts": u.failed_attempts,
                "locked": u.locked_until > time.time(),
            })
        return result
    
    # ── 登录/登出 ──
    def login(self, username: str, password: str, ip: str = "unknown") -> dict:
        now = time.time()
        
        # IP级别暴力破解防护
        ip_info = self._failed_ip.get(ip, {"count": 0, "locked_until": 0})
        if ip_info["locked_until"] > now:
            remaining = int(ip_info["locked_until"] - now)
            return {"success": False, "error": f"IP locked, try again in {remaining}s", "locked": True}
        
        with self._lock:
            if username not in self.users:
                self._record_failed_ip(ip)
                return {"success": False, "error": "Invalid credentials"}
            
            user = self.users[username]
            
            if not user.enabled:
                return {"success": False, "error": "Account disabled"}
            
            if user.locked_until > now:
                remaining = int(user.locked_until - now)
                return {"success": False, "error": f"Account locked, try again in {remaining}s", "locked": True}
            
            if not self.verify_password(password, user.password_hash):
                user.failed_attempts += 1
                if user.failed_attempts >= self.max_failed_attempts:
                    user.locked_until = now + self.lockout_duration
                    user.failed_attempts = 0
                    self._save_users()
                    self._log_auth(username, "account_locked", f"Locked for {self.lockout_duration}s")
                    return {"success": False, "error": "Account locked due to too many failed attempts", "locked": True}
                self._save_users()
                self._record_failed_ip(ip)
                return {"success": False, "error": "Invalid credentials"}
            
            # 登录成功
            user.failed_attempts = 0
            user.login_count += 1
            user.last_login = now
            self._save_users()
            
            # 签发令牌
            access_token = self.jwt.create_token(
                {"sub": username, "role": user.role, "type": "access"},
                self.access_token_ttl,
            )
            refresh_payload = self.jwt.create_token(
                {"sub": username, "role": user.role, "type": "refresh"},
                self.refresh_token_ttl,
            )
            refresh_token = refresh_payload
            refresh_jti = self.jwt.verify_token(refresh_token)["jti"]
            self.refresh_tokens[refresh_jti] = {"username": username, "exp": now + self.refresh_token_ttl}
            
            # 清除IP失败记录
            self._failed_ip.pop(ip, None)
            
            self._log_auth(username, "login", f"Success from {ip}")
            
            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": self.access_token_ttl,
                "user": {"username": username, "role": user.role},
            }
    
    def refresh_access_token(self, refresh_token: str) -> dict:
        try:
            payload = self.jwt.verify_token(refresh_token)
            if payload.get("type") != "refresh":
                return {"success": False, "error": "Invalid token type"}
            jti = payload.get("jti")
            if jti in self.blacklist or jti not in self.refresh_tokens:
                return {"success": False, "error": "Token revoked"}
            with self._lock:
                self.refresh_tokens.pop(jti, None)
            
            new_access = self.jwt.create_token(
                {"sub": payload["sub"], "role": payload["role"], "type": "access"},
                self.access_token_ttl,
            )
            return {
                "success": True,
                "access_token": new_access,
                "token_type": "Bearer",
                "expires_in": self.access_token_ttl,
            }
        except JWTExpiredError:
            return {"success": False, "error": "Refresh token expired, please login again"}
        except JWTError:
            return {"success": False, "error": "Invalid refresh token"}
    
    def logout(self, jti: str = None):
        if jti:
            self.blacklist.add(jti)
    
    # ── 权限检查 ──
    def check_permission(self, role: str, resource: str, action: str) -> bool:
        permissions = ROLE_PERMISSIONS.get(role, [])
        if "*" in permissions:
            return True
        required = f"{resource}:{action}"
        for perm in permissions:
            if perm == "*":
                return True
            if perm == required:
                return True
            # 支持通配符: modules:* 匹配 modules:read
            if perm.endswith(":*"):
                res = perm.split(":")[0]
                if resource == res:
                    return True
        return False
    
    def verify_access_token(self, token: str) -> dict:
        """验证access token并返回用户信息"""
        try:
            payload = self.jwt.verify_token(token)
            if payload.get("type") != "access":
                raise JWTInvalidError("Not an access token")
            jti = payload.get("jti")
            if jti in self.blacklist:
                raise JWTInvalidError("Token revoked")
            return {
                "valid": True,
                "username": payload["sub"],
                "role": payload["role"],
            }
        except JWTExpiredError:
            return {"valid": False, "error": "Token expired"}
        except JWTError:
            return {"valid": False, "error": "Invalid token"}
    
    # ── 内部方法 ──
    def _record_failed_ip(self, ip: str):
        now = time.time()
        info = self._failed_ip.get(ip, {"count": 0, "locked_until": 0})
        info["count"] += 1
        if info["count"] >= self.max_ip_attempts:
            info["locked_until"] = now + self.lockout_duration * 2
            info["count"] = 0
        self._failed_ip[ip] = info
    
    def _log_auth(self, username: str, action: str, detail: str):
        entry = {
            "username": username, "action": action, "detail": detail,
            "timestamp": time.time(), "ip": "system",
        }
        self.login_history.append(entry)
        if len(self.login_history) > self.max_login_history:
            self.login_history = self.login_history[-self.max_login_history:]
    
    def get_login_history(self, limit: int = 50) -> list:
        return list(reversed(self.login_history[-limit:]))
    
    def change_password(self, username: str, old_password: str, new_password: str) -> dict:
        with self._lock:
            if username not in self.users:
                return {"success": False, "error": "User not found"}
            user = self.users[username]
            if not self.verify_password(old_password, user.password_hash):
                return {"success": False, "error": "Old password incorrect"}
            if len(new_password) < 6:
                return {"success": False, "error": "New password must be at least 6 characters"}
            user.password_hash = self.hash_password(new_password)
            self._save_users()
            self._log_auth(username, "change_password", "Password changed")
            return {"success": True}
    
    def get_stats(self) -> dict:
        return {
            "total_users": len(self.users),
            "active_users": sum(1 for u in self.users.values() if u.enabled),
            "login_history_count": len(self.login_history),
            "active_tokens": len(self.refresh_tokens),
            "blacklisted_tokens": len(self.blacklist),
            "default_credentials": "admin/admin123" if self.users.get("admin") and self.verify_password("admin123", self.users["admin"].password_hash) else "changed",
        }


# ═══════════════════════════════════════════════════════
# FastAPI 依赖注入
# ═══════════════════════════════════════════════════════

# 全局实例
_auth_engine: AuthEngine | None = None
_auth_enabled = False

def init_auth(secret: str = None, enabled: bool = False) -> AuthEngine:
    global _auth_engine, _auth_enabled
    _auth_engine = AuthEngine(secret=secret)
    _auth_enabled = enabled
    return _auth_engine

def get_auth() -> AuthEngine:
    return _auth_engine

def is_auth_enabled() -> bool:
    return _auth_enabled

def set_auth_enabled(enabled: bool):
    global _auth_enabled
    _auth_enabled = enabled
