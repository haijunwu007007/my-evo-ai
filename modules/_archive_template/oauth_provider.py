# -*- coding: utf-8 -*-
# STATUS: TEMPLATE - generated skeleton, minimal real logic
"""
AUTO-EVO-AI V0.1 - OAuth2 授权服务器（A级生产实现）
====================================================
模块ID: oauth-provider
功能：OAuth2 授权码、客户端凭证、密码、刷新令牌四种模式。
"""
__module_meta__ = {
    "id": "oauth-provider", "name": "OAuth2 Provider", "version": "1.0.0",
    "group": "security",
    "inputs": [{"name": "action", "type": "string", "required": True, "description": "authorize/token/refresh/revoke"}],
    "outputs": [{"name": "result", "type": "dict", "description": "OAuth2 响应"}],
    "triggers": [], "depends_on": [],
    "tags": ["security", "oauth2", "auth", "core"],
    "grade": "A",
    "description": "OAuth2 授权服务器 - 4种授权模式",
}

import time
import json
import hashlib
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from modules._base.enterprise_module import (
    EnterpriseModule, ModuleStatus, HealthReport,
    CircuitBreakerMixin, RateLimiterMixin, Result,
)
from modules._base.metrics import metrics_collector

logger = logging.getLogger("evo.oauth-provider")

class OAuthProvider(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """OAuth2 授权服务器"""

    MODULE_ID = "oauth-provider"
    MODULE_NAME = "OAuth2 授权服务器"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # 已注册的客户端 {client_id: {name, secret, redirect_uris, grants}}
        self._clients: Dict[str, Dict] = {}
        # 授权码 {code: {client_id, redirect_uri, scopes, expires_at, user_id}}
        self._auth_codes: Dict[str, Dict] = {}
        # 已颁发的令牌 {token: {client_id, user_id, scopes, expires_at, type}}
        self._tokens: Dict[str, Dict] = {}
        # 刷新令牌映射 {refresh_token: access_token}
        self._refresh_tokens: Dict[str, str] = {}
        self._access_ttl = int(self.config.get("access_ttl", 3600))
        self._refresh_ttl = int(self.config.get("refresh_ttl", 2592000))
        self._code_ttl = int(self.config.get("code_ttl", 300))  # 5分钟
        self._setup_rate_limit(rate=500, burst=1000)

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value, healthy=self.status == ModuleStatus.RUNNING,
            module_id=self.MODULE_ID, version=self.VERSION,
            checks={"clients": len(self._clients), "tokens": len(self._tokens)},
        )

    async def execute(self, action: str, params: Optional[Dict] = None) -> Any:
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _dispatch(self, params: Dict) -> Dict:
        action = params.get("action", "status")
        if action == "register_client": return self._register_client(params)
        elif action == "authorize": return self._authorize(params)
        elif action == "token": return self._issue_token(params)
        elif action == "refresh": return self._refresh_token(params)
        elif action == "validate": return self._validate_token(params)
        elif action == "revoke": return self._revoke_token(params)
        elif action == "list_clients": return {"clients": list(self._clients.keys()), "count": len(self._clients)}
        elif action == "introspect": return self._introspect(params)
        return {"success": False, "error": f"unknown action: {action}"}

    def _register_client(self, params: Dict) -> Dict:
        client_id = params.get("client_id", f"client_{uuid.uuid4().hex[:8]}")
        if client_id in self._clients:
            return {"success": False, "error": "client_id already exists"}
        client_secret = params.get("client_secret", uuid.uuid4().hex)
        self._clients[client_id] = {
            "name": params.get("name", client_id),
            "secret": client_secret,
            "redirect_uris": params.get("redirect_uris", []),
            "grants": params.get("grants", ["authorization_code", "client_credentials", "refresh_token"]),
            "scopes": params.get("scopes", ["read", "write"]),
            "created_at": time.time(),
        }
        metrics_collector.counter("oauth_client_registered")
        return {"success": True, "client_id": client_id, "client_secret": client_secret}

    def _authenticate_client(self, client_id: str, client_secret: str) -> Optional[Dict]:
        client = self._clients.get(client_id)
        if not client or client["secret"] != client_secret:
            return None
        return client

    def _authorize(self, params: Dict) -> Dict:
        """授权码模式：生成授权码"""
        client_id = params.get("client_id", "")
        redirect_uri = params.get("redirect_uri", "")
        user_id = params.get("user_id", "default_user")
        scopes = params.get("scopes", ["read"])

        client = self._clients.get(client_id)
        if not client:
            return {"success": False, "error": "invalid client"}
        if redirect_uri and redirect_uri not in client.get("redirect_uris", []):
            return {"success": False, "error": "redirect_uri mismatch"}
        if "authorization_code" not in client.get("grants", []):
            return {"success": False, "error": "grant type not allowed"}

        code = uuid.uuid4().hex[:16]
        self._auth_codes[code] = {
            "client_id": client_id, "redirect_uri": redirect_uri,
            "user_id": user_id, "scopes": scopes,
            "expires_at": time.time() + self._code_ttl,
            "used": False,
        }
        return {"success": True, "code": code, "redirect_uri": redirect_uri}

    def _issue_token(self, params: Dict) -> Dict:
        """通过授权码或客户端凭证颁发令牌"""
        grant_type = params.get("grant_type", "authorization_code")
        client_id = params.get("client_id", "")
        client_secret = params.get("client_secret", "")
        client = self._authenticate_client(client_id, client_secret)
        if not client:
            return {"success": False, "error": "invalid client credentials"}

        if grant_type == "authorization_code":
            code = params.get("code", "")
            code_data = self._auth_codes.get(code)
            if not code_data or code_data.get("used") or time.time() > code_data.get("expires_at", 0):
                return {"success": False, "error": "invalid or expired code"}
            if code_data["client_id"] != client_id:
                return {"success": False, "error": "code client mismatch"}
            code_data["used"] = True
            user_id = code_data.get("user_id", "anonymous")
            scopes = code_data.get("scopes", ["read"])

        elif grant_type == "client_credentials":
            user_id = params.get("user_id", client_id)
            scopes = params.get("scopes", client.get("scopes", ["read"]))

        elif grant_type == "password":
            username = params.get("username", "")
            password = params.get("password", "")
            if not username or not password:
                return {"success": False, "error": "username and password required"}
            if "password" not in client.get("grants", []):
                return {"success": False, "error": "password grant not allowed"}
            user_id = username
            scopes = params.get("scopes", ["read"])

        else:
            return {"success": False, "error": f"unsupported grant_type: {grant_type}"}

        now = time.time()
        access_token = f"at_{uuid.uuid4().hex}"
        refresh_token = f"rt_{uuid.uuid4().hex}"
        self._tokens[access_token] = {
            "client_id": client_id, "user_id": user_id,
            "scopes": scopes, "expires_at": now + self._access_ttl,
            "type": "access", "issued_at": now,
        }
        self._refresh_tokens[refresh_token] = access_token

        metrics_collector.counter("oauth_token_issued", labels={"grant_type": grant_type})
        return {
            "success": True, "access_token": access_token,
            "token_type": "Bearer", "expires_in": self._access_ttl,
            "refresh_token": refresh_token, "scope": " ".join(scopes),
        }

    def _refresh_token(self, params: Dict) -> Dict:
        ref_token = params.get("refresh_token", "")
        client_id = params.get("client_id", "")
        client_secret = params.get("client_secret", "")
        if not self._authenticate_client(client_id, client_secret):
            return {"success": False, "error": "invalid client"}
        old_access = self._refresh_tokens.pop(ref_token, None)
        if not old_access:
            return {"success": False, "error": "invalid refresh_token"}
        token_data = self._tokens.pop(old_access, None)
        if not token_data:
            return {"success": False, "error": "original token not found"}
        now = time.time()
        new_access = f"at_{uuid.uuid4().hex}"
        new_refresh = f"rt_{uuid.uuid4().hex}"
        self._tokens[new_access] = {**token_data, "expires_at": now + self._access_ttl, "issued_at": now}
        self._refresh_tokens[new_refresh] = new_access
        return {
            "success": True, "access_token": new_access,
            "token_type": "Bearer", "expires_in": self._access_ttl,
            "refresh_token": new_refresh,
        }

    def _validate_token(self, params: Dict) -> Dict:
        token = params.get("token", "")
        required_scope = params.get("scope", "")
        token_data = self._tokens.get(token)
        if not token_data:
            return {"success": False, "valid": False, "error": "token not found"}
        if time.time() > token_data["expires_at"]:
            self._tokens.pop(token, None)
            return {"success": False, "valid": False, "error": "token expired"}
        if required_scope and required_scope not in token_data.get("scopes", []):
            return {"success": False, "valid": False, "error": "insufficient scope"}
        return {"success": True, "valid": True, **token_data}

    def _revoke_token(self, params: Dict) -> Dict:
        token = params.get("token", "")
        self._tokens.pop(token, None)
        return {"success": True, "revoked": True}

    def _introspect(self, params: Dict) -> Dict:
        token = params.get("token", "")
        result = self._validate_token({"token": token})
        if result.get("valid"):
            return {"success": True, "active": True, **result}
        return {"success": True, "active": False}

    async def shutdown(self) -> None:
        self._tokens.clear()
        self._auth_codes.clear()
        self._refresh_tokens.clear()
        self.status = ModuleStatus.STOPPED

module_class = OAuthProvider
