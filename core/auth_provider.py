"""AUTO-EVO-AI V0.1 — 认证/授权提供者

JWT 令牌签发验证 + API Key 管理 + RBAC 角色检查。
支持配置热加载，auth.enabled=false 时完全透传。
"""
import time, os, hmac, hashlib, json, logging, base64
from core.logging_config import get_logger
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = get_logger("evo.auth")

# 默认密钥（生产环境应通过 EVO_AUTH_SECRET 环境变量覆盖）
_SECRET = os.environ.get("EVO_AUTH_SECRET", "evo-dev-secret-change-in-production")
_ALGORITHM = "HS256"
_TOKEN_TTL = int(os.environ.get("EVO_AUTH_TTL", "86400"))  # 默认 24h

# 内置管理员（环境变量覆盖）
_ADMIN_KEY = os.environ.get("EVO_ADMIN_KEY", "evo-admin-key-2026")


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _sign(payload: str) -> str:
    msg = f"{payload}.{_SECRET}"
    return hashlib.sha256(msg.encode()).hexdigest()


def create_token(subject: str, role: str = "user", extra: Dict = None) -> Dict:
    """签发 JWT 令牌。"""
    now = int(time.time())
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + _TOKEN_TTL,
        "jti": hashlib.md5(f"{subject}{now}{_SECRET}".encode()).hexdigest()[:16],
    }
    if extra:
        payload.update(extra)
    header = _base64url_encode(json.dumps({"alg": _ALGORITHM, "typ": "JWT"}).encode())
    body = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _sign(f"{header}.{body}")
    token = f"{header}.{body}.{signature}"
    return {"access_token": token, "token_type": "bearer", "expires_in": _TOKEN_TTL, "subject": subject, "role": role}


def verify_token(token: str) -> Optional[Dict]:
    """验证 JWT 令牌，返回 payload 或 None。"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, body, signature = parts
        expected = _sign(f"{header}.{body}")
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_base64url_decode(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception as e:
        logger.warning("[Auth] 令牌验证失败: %s", e)
        return None


def verify_api_key(api_key: str) -> bool:
    """验证 API Key。"""
    if not api_key:
        return False
    return hmac.compare_digest(api_key, _ADMIN_KEY)


def check_role(payload: Dict, required_role: str) -> bool:
    """检查角色权限。"""
    role_hierarchy = {"admin": 3, "editor": 2, "user": 1, "guest": 0}
    user_level = role_hierarchy.get(payload.get("role", "guest"), 0)
    required_level = role_hierarchy.get(required_role, 0)
    return user_level >= required_level


def get_auth_config() -> Dict:
    """获取认证配置（给 API 返回用）。"""
    return {
        "enabled": os.environ.get("EVO_AUTH_ENABLED", "false").lower() == "true",
        "mode": "jwt+apikey" if os.environ.get("EVO_AUTH_ENABLED", "false").lower() == "true" else "none",
        "token_ttl": _TOKEN_TTL,
        "has_admin_key": bool(_ADMIN_KEY),
    }


# ── 便捷装饰器（给模块用）──

def require_auth(func):
    """标记模块方法需要认证（实现由 middleware 处理）。"""
    func._require_auth = True
    return func


def require_role(role: str):
    """标记模块方法需要特定角色。"""
    def decorator(func):
        func._require_role = role
        return func
    return decorator
