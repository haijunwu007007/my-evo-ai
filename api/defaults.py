"""
AUTO-EVO-AI V0.1 — 默认配置与密钥管理
======================================
集中管理所有默认配置项。各模块通过 import defaults 读取，
而非硬编码。
"""
import logging
logger = logging.getLogger("evo.defaults")

import os
import hashlib
import secrets

# ── 管理员密码 ──
# 优先读取环境变量 EVO_ADMIN_PASSWORD；若未设置则生成随机密码并打印
_ADMIN_PASSWORD_ENV = "EVO_ADMIN_PASSWORD"
_DEFAULT_PASSWORD_ENV_VAR = os.environ.get(_ADMIN_PASSWORD_ENV, "")

if _DEFAULT_PASSWORD_ENV_VAR:
    ADMIN_PASSWORD = _DEFAULT_PASSWORD_ENV_VAR
else:
    # 生成随机 16 位密码
    ADMIN_PASSWORD = secrets.token_hex(8)  # e.g. "a1b2c3d4e5f6g7h8"
    logger.info(f"[AUTO-EVO-AI] ⚠️ 未设置 {_ADMIN_PASSWORD_ENV}，使用随机密码: {ADMIN_PASSWORD}")
    logger.info(f"[AUTO-EVO-AI]   → 请在 .env 中添加 {_ADMIN_PASSWORD_ENV}=你的密码 以固定")

ADMIN_PASSWORD_HASH = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

# ── SSL 证书路径 ──
SSL_CERT_DIR = os.environ.get("EVO_SSL_DIR", "/etc/nginx/ssl")
SSL_CERT_PATH = os.path.join(SSL_CERT_DIR, "evo.crt")
SSL_KEY_PATH = os.path.join(SSL_CERT_DIR, "evo.key")
