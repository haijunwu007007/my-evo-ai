# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 — SSO 单点登录（生产级）
==========================================
模块ID: sso-auth
功能：JWT签发/验证 + 密码哈希(PBKDF2) + SQLite持久会话 + 票据交换
"""
__module_meta__ = {
    "id": "sso-auth", "name": "SSO Auth", "version": "V0.1",
    "group": "security",
    "inputs": [{"name": "action", "type": "string", "required": True}],
    "outputs": [{"name": "result", "type": "dict"}],
    "triggers": [], "depends_on": ["persistence"],
    "tags": ["security", "sso", "auth", "core", "production"],
    "grade": "A",
    "description": "SSO 单点登录 - JWT + PBKDF2 + SQLite持久化 + 票据交换",
}

import time, uuid, hmac, json, os, hashlib, logging, base64, sqlite3
from typing import Any, Dict, List, Optional

from modules._base.enterprise_module import (
    EnterpriseModule, ModuleStatus, HealthReport,
    CircuitBreakerMixin, RateLimiterMixin, Result,
)
from modules._base.metrics import metrics_collector

logger = logging.getLogger("evo.sso-auth")

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sso.db")

_INIT_DB_SQL = """
CREATE TABLE IF NOT EXISTS sso_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    attributes TEXT DEFAULT '{}',
    apps TEXT DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS sso_apps (
    app_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    secret TEXT NOT NULL,
    callback_urls TEXT DEFAULT '[]',
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sso_users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    roles TEXT DEFAULT '["user"]',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sso_sessions_user ON sso_sessions(user_id);
"""


class SsoAuth(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """SSO 单点登录模块 — JWT + PBKDF2 + SQLite持久化"""

    MODULE_ID = "sso-auth"
    MODULE_NAME = "SSO 单点登录"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    # JWT 常量
    _JWT_ALGORITHM = "HS256"
    _JWT_SECRET = os.environ.get("SSO_JWT_SECRET", "evo-sso-secret-change-me-2026")
    _JWT_ISSUER = "auto-evo-ai"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._sessions: Dict[str, Dict] = {}
        self._tickets: Dict[str, Dict] = {}
        self._apps: Dict[str, Dict] = {}
        self._session_ttl = int(self.config.get("session_ttl", 28800))
        self._ticket_ttl = int(self.config.get("ticket_ttl", 300))
        self._setup_rate_limit(rate=500, burst=1000)

    def initialize(self) -> None:
        self._init_db()
        self._restore_sessions()
        self.status = ModuleStatus.RUNNING
        logger.info("SSO初始化完成, 恢复会话: %d", len(self._sessions))

    def _init_db(self):
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(_DB_PATH, timeout=5)
        conn.executescript(_INIT_DB_SQL)
        conn.commit()
        conn.close()

    def _restore_sessions(self):
        try:
            conn = sqlite3.connect(_DB_PATH, timeout=5)
            conn.row_factory = sqlite3.Row
            now = time.time()
            cur = conn.execute("SELECT * FROM sso_sessions WHERE expires_at > ?", (now,))
            for row in cur.fetchall():
                self._sessions[row["token"]] = {
                    "user_id": row["user_id"],
                    "created_at": row["created_at"],
                    "expires_at": row["expires_at"],
                    "attributes": json.loads(row["attributes"] or "{}"),
                    "apps": json.loads(row["apps"] or "[]"),
                }
            conn.close()
        except Exception as e:
            logger.warning("恢复会话失败: %s", e)

    def _save_session(self, token, session):
        try:
            conn = sqlite3.connect(_DB_PATH, timeout=5)
            conn.execute(
                "INSERT OR REPLACE INTO sso_sessions(token,user_id,created_at,expires_at,attributes,apps) VALUES(?,?,?,?,?,?)",
                (token, session["user_id"], session["created_at"], session["expires_at"],
                 json.dumps(session["attributes"]), json.dumps(session["apps"]))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug("save session error: %s", e)

    def _delete_session(self, token):
        try:
            conn = sqlite3.connect(_DB_PATH, timeout=5)
            conn.execute("DELETE FROM sso_sessions WHERE token=?", (token,))
            conn.commit()
            conn.close()
        except: pass

    # ── JWT ──

    def _base64url(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    def _gen_jwt(self, payload: dict, ttl: int = 3600) -> str:
        header = self._base64url(json.dumps({"alg": self._JWT_ALGORITHM, "typ": "JWT"}).encode())
        now = int(time.time())
        claims = {"iss": self._JWT_ISSUER, "iat": now, "exp": now + ttl}
        claims.update(payload)
        payload_b64 = self._base64url(json.dumps(claims, separators=(",", ":")).encode())
        sig = hmac.new(self._JWT_SECRET.encode(), f"{header}.{payload_b64}".encode(), hashlib.sha256).hexdigest()
        return f"{header}.{payload_b64}.{sig}"

    def _verify_jwt(self, token: str) -> dict:
        parts = token.split(".")
        if len(parts) != 3:
            return {"valid": False, "error": "malformed"}
        expected_sig = hmac.new(self._JWT_SECRET.encode(), f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, parts[2]):
            return {"valid": False, "error": "invalid signature"}
        try:
            decoded = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        except Exception as e:
            return {"valid": False, "error": f"decode error: {e}"}
        now = time.time()
        if decoded.get("exp", 0) < now:
            return {"valid": False, "error": "expired"}
        decoded["valid"] = True
        return decoded

    # ── 密码哈希 ──

    def _hash_password(self, password: str, salt: bytes = None) -> str:
        if salt is None:
            salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return base64.b64encode(salt + dk).decode()

    def _verify_password(self, password: str, stored: str) -> bool:
        try:
            raw = base64.b64decode(stored.encode())
            salt, dk = raw[:16], raw[16:]
            expected = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
            return hmac.compare_digest(dk, expected)
        except Exception:
            return False

    # ── Health ──

    def health_check(self) -> HealthReport:
        now = time.time()
        active = sum(1 for s in self._sessions.values() if s["expires_at"] > now)
        return HealthReport(
            status=self.status.value, healthy=self.status == ModuleStatus.RUNNING,
            module_id=self.MODULE_ID, version=self.VERSION,
            checks={"active_sessions": active, "registered_apps": len(self._apps)},
        )

    async def execute(self, action: str, params: Optional[Dict] = None) -> Any:
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _dispatch(self, params: Dict) -> Dict:
        action = params.get("action", "status")
        dispatch = {
            "login": self._login,
            "validate": self._validate_session,
            "logout": self._logout,
            "create_ticket": self._create_ticket,
            "exchange_ticket": self._exchange_ticket,
            "register_app": self._register_app,
            "list_sessions": self._list_sessions,
            "register_user": self._register_user,
            "authenticate": self._authenticate,
            "generate_jwt": self._generate_jwt,
            "verify_jwt": self._verify_jwt_action,
            "get_user": self._get_user,
        }
        handler = dispatch.get(action)
        if handler:
            return handler(params)
        return {"success": False, "error": f"unknown action: {action}"}

    def _login(self, params: Dict) -> Dict:
        user_id = params.get("user_id", "")
        username = params.get("username", "")
        password = params.get("password", "")
        if user_id and password:
            auth = self._authenticate({"username": username or user_id, "password": password})
            if not auth.get("success"):
                return auth
            user_id = auth["user_id"]
        if not user_id:
            user_id = f"user_{hashlib.md5(username.encode()).hexdigest()[:8]}"
        attributes = params.get("attributes", {"username": username or user_id, "roles": ["user"]})
        now = time.time()
        session_token = f"sso_{uuid.uuid4().hex}"
        self._sessions[session_token] = {
            "user_id": user_id, "created_at": now,
            "expires_at": now + self._session_ttl,
            "attributes": attributes, "apps": [],
        }
        self._save_session(session_token, self._sessions[session_token])
        metrics_collector.counter("sso_login", labels={"user_id": user_id[:8]})
        jwt = self._gen_jwt({"sub": user_id, "roles": attributes.get("roles", ["user"])}, self._session_ttl)
        return {"success": True, "session_token": session_token, "user_id": user_id,
                "jwt": jwt, "expires_in": self._session_ttl}

    def _validate_session(self, params: Dict) -> Dict:
        token = params.get("token", params.get("session_token", ""))
        if not token:
            return {"success": False, "valid": False, "error": "no token"}
        session = self._sessions.get(token)
        if not session:
            return {"success": False, "valid": False, "error": "session not found"}
        if time.time() > session["expires_at"]:
            self._sessions.pop(token, None)
            self._delete_session(token)
            return {"success": False, "valid": False, "error": "session expired"}
        session["expires_at"] = time.time() + self._session_ttl
        self._save_session(token, session)
        return {"success": True, "valid": True, "user_id": session["user_id"],
                "attributes": session["attributes"]}

    def _logout(self, params: Dict) -> Dict:
        token = params.get("token", params.get("session_token", ""))
        if token:
            self._sessions.pop(token, None)
            self._delete_session(token)
        user_id = params.get("user_id", "")
        if user_id:
            to_delete = [k for k, v in self._sessions.items() if v["user_id"] == user_id]
            for k in to_delete:
                self._sessions.pop(k, None)
                self._delete_session(k)
        metrics_collector.counter("sso_logout")
        return {"success": True, "logged_out": True}

    def _create_ticket(self, params: Dict) -> Dict:
        session_token = params.get("session_token", "")
        service = params.get("service", "")
        if not session_token or not service:
            return {"success": False, "error": "session_token and service required"}
        session = self._sessions.get(session_token)
        if not session or time.time() > session["expires_at"]:
            return {"success": False, "error": "invalid session"}
        ticket = f"st-{uuid.uuid4().hex[:16]}"
        self._tickets[ticket] = {"user_id": session["user_id"], "service": service,
                                 "expires_at": time.time() + self._ticket_ttl, "used": False}
        if service not in session["apps"]:
            session["apps"].append(service)
            self._save_session(session_token, session)
        return {"success": True, "ticket": ticket, "service": service}

    def _exchange_ticket(self, params: Dict) -> Dict:
        ticket = params.get("ticket", "")
        service = params.get("service", "")
        if not ticket:
            return {"success": False, "error": "ticket required"}
        ticket_data = self._tickets.get(ticket)
        if not ticket_data or ticket_data.get("used"):
            return {"success": False, "error": "invalid or used ticket"}
        if service and ticket_data["service"] != service:
            return {"success": False, "error": "service mismatch"}
        if time.time() > ticket_data["expires_at"]:
            self._tickets.pop(ticket, None)
            return {"success": False, "error": "ticket expired"}
        ticket_data["used"] = True
        app_session_token = f"app_{uuid.uuid4().hex}"
        now = time.time()
        self._sessions[app_session_token] = {
            "user_id": ticket_data["user_id"], "created_at": now,
            "expires_at": now + self._session_ttl,
            "attributes": {}, "apps": [service],
        }
        self._save_session(app_session_token, self._sessions[app_session_token])
        jwt = self._gen_jwt({"sub": ticket_data["user_id"]}, self._session_ttl)
        return {"success": True, "app_session_token": app_session_token, "jwt": jwt,
                "user_id": ticket_data["user_id"]}

    def _register_app(self, params: Dict) -> Dict:
        app_id = params.get("app_id", f"app_{uuid.uuid4().hex[:8]}")
        secret = params.get("secret", uuid.uuid4().hex)
        self._apps[app_id] = {"name": params.get("name", app_id), "secret": secret,
                              "callback_urls": params.get("callback_urls", []),
                              "created_at": time.time()}
        # persist
        try:
            conn = sqlite3.connect(_DB_PATH, timeout=5)
            conn.execute("INSERT OR REPLACE INTO sso_apps(app_id,name,secret,callback_urls,created_at) VALUES(?,?,?,?,?)",
                         (app_id, self._apps[app_id]["name"], secret,
                          json.dumps(params.get("callback_urls", [])), time.time()))
            conn.commit()
            conn.close()
        except: pass
        return {"success": True, "app_id": app_id, "app_secret": secret}

    def _list_sessions(self, params: Dict) -> Dict:
        limit = int(params.get("limit", 100))
        now = time.time()
        active = {k: v for k, v in self._sessions.items() if v["expires_at"] > now}
        sessions = [{"user_id": s["user_id"], "apps": s["apps"],
                      "expires_at": datetime.fromtimestamp(s["expires_at"]).isoformat()
                      if hasattr(datetime, 'fromtimestamp') else s["expires_at"]}
                     for s in list(active.values())[:limit]]
        return {"success": True, "sessions": sessions, "total_active": len(active)}

    def _register_user(self, params: Dict) -> Dict:
        username = params.get("username", "")
        password = params.get("password", "")
        if not username or not password:
            return {"success": False, "error": "username and password required"}
        user_id = params.get("user_id", f"u_{uuid.uuid4().hex[:8]}")
        password_hash = self._hash_password(password)
        roles = json.dumps(params.get("roles", ["user"]))
        try:
            conn = sqlite3.connect(_DB_PATH, timeout=5)
            conn.execute("INSERT INTO sso_users(user_id,username,password_hash,roles,created_at) VALUES(?,?,?,?,?)",
                         (user_id, username, password_hash, roles, time.time()))
            conn.commit()
            conn.close()
            metrics_collector.counter("sso_user_registered")
            return {"success": True, "user_id": user_id, "username": username}
        except sqlite3.IntegrityError:
            return {"success": False, "error": "username already exists"}

    def _authenticate(self, params: Dict) -> Dict:
        username = params.get("username", "")
        password = params.get("password", "")
        if not username or not password:
            return {"success": False, "error": "username and password required"}
        try:
            conn = sqlite3.connect(_DB_PATH, timeout=5)
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM sso_users WHERE username=?", (username,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return {"success": False, "error": "user not found"}
            if not self._verify_password(password, row["password_hash"]):
                return {"success": False, "error": "invalid password"}
            roles = json.loads(row["roles"] or '["user"]')
            return {"success": True, "user_id": row["user_id"], "username": row["username"],
                    "roles": roles}
        except Exception as e:
            return {"success": False, "error": f"auth error: {e}"}

    def _generate_jwt(self, params: Dict) -> Dict:
        payload = params.get("payload", {})
        ttl = int(params.get("ttl", 3600))
        token = self._gen_jwt(payload, ttl)
        return {"success": True, "jwt": token, "ttl": ttl}

    def _verify_jwt_action(self, params: Dict) -> Dict:
        token = params.get("token", "")
        if not token:
            return {"success": False, "error": "token required"}
        result = self._verify_jwt(token)
        return {"success": result.get("valid", False), **result}

    def _get_user(self, params: Dict) -> Dict:
        user_id = params.get("user_id", "")
        if not user_id:
            return {"success": False, "error": "user_id required"}
        # return user info from sso_users table
        try:
            conn = sqlite3.connect(_DB_PATH, timeout=5)
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT user_id, username, roles FROM sso_users WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            conn.close()
            if row:
                return {"success": True, "user_id": row["user_id"], "username": row["username"],
                        "roles": json.loads(row["roles"] or '["user"]')}
            return {"success": False, "error": "user not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def shutdown(self) -> None:
        self._sessions.clear()
        self._tickets.clear()
        self.status = ModuleStatus.STOPPED


# 需要 datetime 用于格式化
from datetime import datetime

module_class = SsoAuth
