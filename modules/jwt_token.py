"""
# Grade: A
AUTO-EVO-AI V0.1 - JWT 令牌管理（A级生产实现）
=================================================
模块ID: jwt-token
功能：JWT 令牌生成、验证、刷新、吊销，支持 HS256 算法。
"""
__module_meta__ = {
    "id": "jwt-token", "name": "JWT Token", "version": "V0.1",
    "group": "security",
    "inputs": [{"name": "action", "type": "string", "required": True, "description": "create/verify/refresh/revoke"}],
    "outputs": [{"name": "result", "type": "dict", "description": "操作结果"}],
    "triggers": [], "depends_on": [],
    "tags": ["security", "auth", "jwt", "core"],
    "grade": "A",
    "description": "JWT 令牌管理 - 生成/验证/刷新/吊销",
}

import time
import json
import hashlib
import hmac
import base64
from core.logging_config import get_logger
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from modules._base.enterprise_module import (
    EnterpriseModule, ModuleStatus, HealthReport,
    CircuitBreakerMixin, RateLimiterMixin, Result,
)
from modules._base.metrics import metrics_collector

logger = get_logger("evo.jwt-token")

class JwtToken(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """JWT 令牌管理模块"""

    MODULE_ID = "jwt-token"
    MODULE_NAME = "JWT 令牌管理"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    # 默认密钥（优先从环境变量读取）
    DEFAULT_SECRET = os.environ.get("EVO_JWT_SECRET", "evo-ai-jwt-secret-key-change-in-production")

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._secret = self.config.get("secret", self.DEFAULT_SECRET)
        self._access_ttl = int(self.config.get("access_ttl", 3600))  # 1小时
        self._refresh_ttl = int(self.config.get("refresh_ttl", 2592000))  # 30天
        # 吊销令牌黑名单（token_id -> 吊销时间戳）
        self._revoked: dict[str, float] = {}
        self._setup_rate_limit(rate=500, burst=1000)

    def initialize(self) -> None:
        self.info(f"JWT令牌管理初始化完成 (access_ttl={self._access_ttl}s, refresh_ttl={self._refresh_ttl}s)")
        self.status = ModuleStatus.RUNNING

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value,
            healthy=self.status == ModuleStatus.RUNNING,
            module_id=self.MODULE_ID,
            version=self.VERSION,
            checks={"revoked_count": len(self._revoked)},
            details={"secret_configured": self._secret != self.DEFAULT_SECRET},
        )

    async def execute(self, action: str, params: dict | None = None) -> Any:
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _dispatch(self, params: dict[str, Any]) -> dict[str, Any]:
        action = params.get("action", "status")
        if action == "create":
            return self._create_token(params)
        elif action == "verify":
            return self._verify_token(params)
        elif action == "refresh":
            return self._refresh_token(params)
        elif action == "revoke":
            return self._revoke_token(params)
        elif action == "decode":
            return self._decode_token(params)
        elif action == "list_revoked":
            return {"revoked_count": len(self._revoked), "revoked_ids": list(self._revoked.keys())[-100:]}
        return {"success": False, "error": f"Unknown action: {action}"}

    def _base64url_encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    def _base64url_decode(self, s: str) -> bytes:
        padding = 4 - len(s) % 4
        if padding != 4:
            s += "=" * padding
        return base64.urlsafe_b64decode(s)

    def _sign(self, payload: str) -> str:
        """HMAC-SHA256 签名"""
        sig = hmac.new(
            self._secret.encode(), payload.encode(), hashlib.sha256
        ).digest()
        return self._base64url_encode(sig)

    def _create_token(self, params: dict[str, Any]) -> dict[str, Any]:
        """创建 JWT 令牌"""
        claims = params.get("claims", {})
        if not isinstance(claims, dict):
            return {"success": False, "error": "claims must be a dict"}

        now = int(time.time())
        token_id = str(uuid.uuid4())
        sub = claims.get("sub", params.get("subject", "anonymous"))
        roles = claims.get("roles", params.get("roles", []))

        # 构建 Payload
        payload = {
            "jti": token_id,
            "sub": sub,
            "iat": now,
            "exp": now + self._access_ttl,
            "type": "access",
            "roles": roles if isinstance(roles, list) else [roles],
        }
        payload.update({k: v for k, v in claims.items() if k not in payload})

        # 编码
        header = self._base64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        body = self._base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        signature = self._sign(f"{header}.{body}")
        token = f"{header}.{body}.{signature}"

        # 同时生成 refresh_token
        refresh_payload = {
            "jti": str(uuid.uuid4()),
            "sub": sub,
            "iat": now,
            "exp": now + self._refresh_ttl,
            "type": "refresh",
        }
        refresh_body = self._base64url_encode(json.dumps(refresh_payload, separators=(",", ":")).encode())
        refresh_sig = self._sign(f"{header}.{refresh_body}")
        refresh_token = f"{header}.{refresh_body}.{refresh_sig}"

        metrics_collector.counter("jwt_token_created", labels={"sub": sub[:20] if sub else "anonymous"})

        return {
            "success": True,
            "access_token": token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self._access_ttl,
            "token_id": token_id,
            "subject": sub,
        }

    def _verify_token(self, params: dict[str, Any]) -> dict[str, Any]:
        """验证 JWT 令牌"""
        token = params.get("token", "")
        if not token:
            return {"success": False, "error": "token is required", "valid": False}

        parts = token.split(".")
        if len(parts) != 3:
            return {"success": False, "error": "invalid token format", "valid": False}

        header_b64, body_b64, sig_b64 = parts

        # 验证签名
        expected_sig = self._sign(f"{header_b64}.{body_b64}")
        if sig_b64 != expected_sig:
            return {"success": False, "error": "signature mismatch", "valid": False}

        # 解码 Payload
        try:
            body = json.loads(self._base64url_decode(body_b64))
        except Exception as e:
            return {"success": False, "error": f"invalid payload: {e}", "valid": False}

        # 检查过期
        now = time.time()
        exp = body.get("exp", 0)
        if now > exp:
            return {"success": False, "error": "token expired", "valid": False}

        # 检查吊销
        jti = body.get("jti", "")
        if jti in self._revoked:
            return {"success": False, "error": "token revoked", "valid": False}

        return {
            "success": True,
            "valid": True,
            "subject": body.get("sub", ""),
            "roles": body.get("roles", []),
            "token_type": body.get("type", "access"),
            "expires_at": exp,
            "issued_at": body.get("iat", 0),
            "token_id": jti,
            "claims": body,
        }

    def _refresh_token(self, params: dict[str, Any]) -> dict[str, Any]:
        """用 refresh_token 刷新 access_token"""
        refresh_token = params.get("refresh_token", "")
        if not refresh_token:
            return {"success": False, "error": "refresh_token is required"}

        # 先验证 refresh_token
        verify_result = self._verify_token({"token": refresh_token})
        if not verify_result.get("valid"):
            return {"success": False, "error": verify_result.get("error", "invalid refresh token")}

        claims = verify_result.get("claims", {})
        if claims.get("type") != "refresh":
            return {"success": False, "error": "not a refresh token"}

        # 吊销旧的 refresh_token
        old_jti = claims.get("jti", "")
        self._revoked[old_jti] = time.time()

        # 创建新令牌
        return self._create_token({
            "claims": {
                "sub": claims.get("sub", ""),
                "roles": claims.get("roles", []),
            }
        })

    def _revoke_token(self, params: dict[str, Any]) -> dict[str, Any]:
        """吊销令牌"""
        token_id = params.get("token_id", "")
        token = params.get("token", "")

        if token_id:
            self._revoked[token_id] = time.time()
            return {"success": True, "revoked": token_id}

        if token:
            # 从 token 中提取 jti
            parts = token.split(".")
            if len(parts) == 3:
                try:
                    body = json.loads(self._base64url_decode(parts[1]))
                    jti = body.get("jti", "")
                    if jti:
                        self._revoked[jti] = time.time()
                        return {"success": True, "revoked": jti}
                except Exception:
                    pass

        return {"success": False, "error": "token_id or token is required"}

    def _decode_token(self, params: dict[str, Any]) -> dict[str, Any]:
        """解码令牌（不验证签名，仅查看内容）"""
        token = params.get("token", "")
        if not token:
            return {"success": False, "error": "token is required"}
        parts = token.split(".")
        if len(parts) != 3:
            return {"success": False, "error": "invalid token format"}
        try:
            header = json.loads(self._base64url_decode(parts[0]))
            body = json.loads(self._base64url_decode(parts[1]))
            return {"success": True, "header": header, "payload": body}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def shutdown(self) -> None:
        self._revoked.clear()
        self.status = ModuleStatus.STOPPED

module_class = JwtToken
