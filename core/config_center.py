from __future__ import annotations
"""
AUTO-EVO-AI V0.1 — 统一配置中心 (Config Center)
=================================================
上市公司级安全配置管理:
- AES-256-GCM 加密存储敏感配置 (API Key / Token / Secret)
- 环境变量自动注入 + .env 文件加载
- 热加载: 修改后无需重启即时生效
- 配置分组: LLM / 通知 / CI-CD / 数据库 / 自定义
- 审计日志: 谁在什么时候改了什么
- 配置导出/导入: 方便环境迁移
"""


import os
import json
import time
import hmac
import hashlib
import base64
import secrets
from core.logging_config import get_logger
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from copy import deepcopy

logger = get_logger("evo.config")


# ═══════════════════════════════════════════════════════════
# 配置分组枚举
# ═══════════════════════════════════════════════════════════

class ConfigGroup(str, Enum):
    LLM = "llm"           # OpenAI / DeepSeek / Anthropic / Gemini / 智谱 / Ollama
    NOTIFY = "notify"     # 邮件 / 企微 / 钉钉 / 飞书 / Bark / Server酱 / PushPlus / Webhook
    CICD = "cicd"         # GitHub / GitLab / Jenkins
    DATABASE = "database" # PostgreSQL / MySQL / Redis / MongoDB / SQLite
    CUSTOM = "custom"     # 用户自定义配置


# ═══════════════════════════════════════════════════════════
# 配置项数据结构
# ═══════════════════════════════════════════════════════════

@dataclass
class ConfigItem:
    """单个配置项"""
    key: str                          # 配置键, 如 "openai_api_key"
    value: str = ""                   # 配置值 (明文, 存储时加密)
    group: str = "custom"             # 分组
    label: str = ""                   # 中文标签, 如 "OpenAI API Key"
    description: str = ""             # 说明
    is_secret: bool = True            # 是否敏感 (敏感值在API返回时脱敏)
    env_var: str = ""                 # 对应环境变量名, 如 "OPENAI_API_KEY"
    is_required: bool = False         # 是否必填
    default_value: str = ""           # 默认值
    validation_pattern: str = ""      # 校验正则
    created_at: str = ""              # 创建时间
    updated_at: str = ""              # 更新时间
    updated_by: str = "system"        # 更新人

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class ConfigAuditLog:
    """配置变更审计日志"""
    timestamp: str
    action: str          # create / update / delete / export / import
    key: str
    old_value_masked: str   # 脱敏旧值
    new_value_masked: str   # 脱敏新值
    operator: str        # 操作人
    group: str


# ═══════════════════════════════════════════════════════════
# AES-256-GCM 加密引擎
# ═══════════════════════════════════════════════════════════

class _CryptoEngine:
    """AES-256-GCM 加密/解密"""

    BLOCK_SIZE = 16  # AES block size

    @staticmethod
    def _derive_key(master_key: str, salt: bytes) -> bytes:
        """PBKDF2 派生256位密钥"""
        import hashlib
        return hashlib.pbkdf2_hmac(
            'sha256', master_key.encode('utf-8'), salt, 100000, dklen=32
        )

    @classmethod
    def encrypt(cls, plaintext: str, master_key: str) -> str:
        """加密 → base64(salt.nonce.ciphertext.tag)"""
        if not plaintext:
            return ""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            # fallback: 简单XOR混淆 (生产环境应安装cryptography)
            logger.warning("[Config] cryptography未安装, 使用XOR回退加密")
            return cls._xor_encrypt(plaintext, master_key)

        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)
        key = cls._derive_key(master_key, salt)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        # salt(16) + nonce(12) + tag(last 16 of ct) + ciphertext
        raw = salt + nonce + ct
        return base64.b64encode(raw).decode('ascii')

    @classmethod
    def decrypt(cls, ciphertext: str, master_key: str) -> str:
        """解密 base64 → plaintext"""
        if not ciphertext:
            return ""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            return cls._xor_decrypt(ciphertext, master_key)

        try:
            raw = base64.b64decode(ciphertext)
            salt = raw[:16]
            nonce = raw[16:28]
            ct = raw[28:]
            key = cls._derive_key(master_key, salt)
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, ct, None).decode('utf-8')
        except Exception:
            logger.error("[Config] 解密失败, 可能密钥不匹配")
            return ""

    @classmethod
    def _xor_encrypt(cls, plaintext: str, key: str) -> str:
        """XOR回退加密"""
        data = plaintext.encode('utf-8')
        key_bytes = hashlib.sha256(key.encode()).digest()
        result = bytearray(len(data))
        for i, b in enumerate(data):
            result[i] = b ^ key_bytes[i % len(key_bytes)]
        return base64.b64encode(bytes(result)).decode('ascii')

    @classmethod
    def _xor_decrypt(cls, ciphertext: str, key: str) -> str:
        """XOR回退解密"""
        data = base64.b64decode(ciphertext)
        key_bytes = hashlib.sha256(key.encode()).digest()
        result = bytearray(len(data))
        for i, b in enumerate(data):
            result[i] = b ^ key_bytes[i % len(key_bytes)]
        return bytes(result).decode('utf-8')

    @staticmethod
    def mask_value(value: str, show_len: int = 4) -> str:
        """脱敏: sk-abc123xyz → sk-****xyz"""
        if not value or len(value) <= show_len * 2:
            return "****"
        return value[:show_len] + "****" + value[-show_len:]


# ═══════════════════════════════════════════════════════════
# 预置配置模板
# ═══════════════════════════════════════════════════════════

BUILTIN_TEMPLATES: list[ConfigItem] = [
    # ─── LLM Providers ───
    ConfigItem(key="openai_api_key", group="llm", label="OpenAI API Key",
               description="OpenAI GPT系列接口密钥", env_var="OPENAI_API_KEY",
               validation_pattern=r"^sk-[a-zA-Z0-9]{20,}$"),
    ConfigItem(key="openai_base_url", group="llm", label="OpenAI Base URL",
               description="OpenAI接口地址(可改为代理)", env_var="OPENAI_BASE_URL",
               is_secret=False, default_value="https://api.openai.com/v1"),
    ConfigItem(key="openai_default_model", group="llm", label="OpenAI 默认模型",
               description="默认使用的GPT模型", env_var="OPENAI_DEFAULT_MODEL",
               is_secret=False, default_value="gpt-4o"),
    ConfigItem(key="deepseek_api_key", group="llm", label="DeepSeek API Key",
               description="DeepSeek接口密钥", env_var="DEEPSEEK_API_KEY"),
    ConfigItem(key="deepseek_base_url", group="llm", label="DeepSeek Base URL",
               description="DeepSeek接口地址", env_var="DEEPSEEK_BASE_URL",
               is_secret=False, default_value="https://api.deepseek.com/v1"),
    ConfigItem(key="anthropic_api_key", group="llm", label="Anthropic API Key",
               description="Claude系列接口密钥", env_var="ANTHROPIC_API_KEY"),
    ConfigItem(key="gemini_api_key", group="llm", label="Google Gemini API Key",
               description="Gemini接口密钥", env_var="GEMINI_API_KEY"),
    ConfigItem(key="zhipu_api_key", group="llm", label="智谱 API Key",
               description="智谱GLM系列接口密钥", env_var="ZHIPU_API_KEY"),
    ConfigItem(key="ollama_base_url", group="llm", label="Ollama Base URL",
               description="本地Ollama服务地址", env_var="OLLAMA_BASE_URL",
               is_secret=False, default_value="http://localhost:11434"),
    ConfigItem(key="llm_max_tokens", group="llm", label="最大Token数",
               description="LLM单次请求最大token", env_var="LLM_MAX_TOKENS",
               is_secret=False, default_value="4096"),
    ConfigItem(key="llm_timeout", group="llm", label="请求超时(秒)",
               description="LLM请求超时时间", env_var="LLM_TIMEOUT",
               is_secret=False, default_value="60"),
    ConfigItem(key="llm_temperature", group="llm", label="Temperature",
               description="LLM生成温度(0-2)", env_var="LLM_TEMPERATURE",
               is_secret=False, default_value="0.7"),

    # ─── 通知渠道 ───
    ConfigItem(key="notify_email_smtp_host", group="notify", label="SMTP服务器",
               description="邮件发送SMTP地址", env_var="SMTP_HOST", is_secret=False),
    ConfigItem(key="notify_email_smtp_port", group="notify", label="SMTP端口",
               description="SMTP端口", env_var="SMTP_PORT", is_secret=False, default_value="465"),
    ConfigItem(key="notify_email_user", group="notify", label="邮箱用户名",
               description="发件邮箱地址", env_var="SMTP_USER", is_secret=False),
    ConfigItem(key="notify_email_password", group="notify", label="邮箱密码",
               description="发件邮箱密码/授权码", env_var="SMTP_PASSWORD"),
    ConfigItem(key="notify_wechat_webhook", group="notify", label="企业微信Webhook",
               description="企业微信机器人Webhook URL", env_var="WECHAT_WEBHOOK_URL"),
    ConfigItem(key="notify_dingtalk_webhook", group="notify", label="钉钉Webhook",
               description="钉钉机器人Webhook URL + Secret", env_var="DINGTALK_WEBHOOK_URL"),
    ConfigItem(key="notify_dingtalk_secret", group="notify", label="钉钉签名密钥",
               description="钉钉机器人签名Secret", env_var="DINGTALK_SECRET"),
    ConfigItem(key="notify_feishu_webhook", group="notify", label="飞书Webhook",
               description="飞书机器人Webhook URL", env_var="FEISHU_WEBHOOK_URL"),
    ConfigItem(key="notify_serverchan_key", group="notify", label="Server酱Key",
               description="Server酱SendKey", env_var="SERVERCHAN_KEY"),
    ConfigItem(key="notify_pushplus_token", group="notify", label="PushPlus Token",
               description="PushPlus推送Token", env_var="PUSHPLUS_TOKEN"),
    ConfigItem(key="notify_bark_device_key", group="notify", label="Bark设备Key",
               description="iOS Bark推送设备Key", env_var="BARK_DEVICE_KEY"),
    ConfigItem(key="notify_bark_server", group="notify", label="Bark服务器",
               description="Bark自建服务器地址", env_var="BARK_SERVER",
               is_secret=False, default_value="https://api.day.app"),

    # ─── CI/CD ───
    ConfigItem(key="github_token", group="cicd", label="GitHub Personal Token",
               description="GitHub API访问令牌(repo/workflow权限)", env_var="GITHUB_TOKEN"),
    ConfigItem(key="github_username", group="cicd", label="GitHub用户名",
               description="GitHub用户名", env_var="GITHUB_USERNAME", is_secret=False),
    ConfigItem(key="github_default_repo", group="cicd", label="默认仓库",
               description="默认操作的仓库 owner/repo", env_var="GITHUB_DEFAULT_REPO", is_secret=False),
    ConfigItem(key="gitlab_token", group="cicd", label="GitLab Token",
               description="GitLab API访问令牌", env_var="GITLAB_TOKEN"),
    ConfigItem(key="docker_hub_user", group="cicd", label="Docker Hub用户名",
               description="Docker Hub登录用户名", env_var="DOCKER_HUB_USER", is_secret=False),
    ConfigItem(key="docker_hub_token", group="cicd", label="Docker Hub Token",
               description="Docker Hub访问令牌", env_var="DOCKER_HUB_TOKEN"),

    # ─── 数据库 ───
    ConfigItem(key="redis_url", group="database", label="Redis URL",
               description="Redis连接地址", env_var="REDIS_URL", is_secret=False,
               default_value="redis://localhost:6379/0"),
    ConfigItem(key="postgres_url", group="database", label="PostgreSQL URL",
               description="PostgreSQL连接字符串", env_var="DATABASE_URL"),
    ConfigItem(key="mongo_url", group="database", label="MongoDB URL",
               description="MongoDB连接字符串", env_var="MONGO_URL"),
]


# ═══════════════════════════════════════════════════════════
# 配置中心核心
# ═══════════════════════════════════════════════════════════

class ConfigCenter:
    """
    统一配置中心 — 上市公司级安全管理
    """

    def __init__(self, data_dir: str = ".evo_data/config"):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # 存储文件
        self._store_path = self._data_dir / "config_store.enc"
        self._meta_path = self._data_dir / "config_meta.json"
        self._audit_path = self._data_dir / "config_audit.jsonl"

        # 主密钥: 优先环境变量, 否则自动生成并持久化
        self._master_key = self._load_or_create_master_key()

        # 内存配置缓存 {group.key: ConfigItem}
        self._configs: dict[str, ConfigItem] = {}
        # 变更回调
        self._change_callbacks: dict[str, list[callable]] = {}
        # 审计日志缓存
        self._audit_cache: list[ConfigAuditLog] = []

        # 初始化: 加载已有 + 注入预置模板 + 扫描环境变量
        self._load_from_disk()
        self._init_builtin_templates()
        self._inject_env_vars()

        logger.info("[ConfigCenter] 初始化完成 | 配置项: %d | 审计: %d条",
                     len(self._configs), len(self._audit_cache))

    # ─── 密钥管理 ───

    def _load_or_create_master_key(self) -> str:
        key_path = self._data_dir / ".master_key"
        env_key = os.environ.get("EVO_CONFIG_MASTER_KEY", "")
        if env_key and len(env_key) >= 16:
            return env_key
        if key_path.exists():
            return key_path.read_text(encoding='utf-8').strip()
        new_key = secrets.token_urlsafe(32)
        key_path.write_text(new_key, encoding='utf-8')
        # 设置文件权限 (仅当前用户可读)
        try:
            os.chmod(str(key_path), 0o600)
        except OSError as _e:
            logger.warning(f"error: {_e}")
        logger.info("[ConfigCenter] 自动生成主密钥 (建议设置EVO_CONFIG_MASTER_KEY环境变量)")
        return new_key

    # ─── 持久化 ───

    def _load_from_disk(self):
        """从磁盘加载加密配置"""
        if not self._store_path.exists() or not self._meta_path.exists():
            return
        try:
            meta = json.loads(self._meta_path.read_text(encoding='utf-8'))
            encrypted = self._store_path.read_text(encoding='utf-8')
            values = json.loads(_CryptoEngine.decrypt(encrypted, self._master_key))
            for key, data in meta.items():
                item = ConfigItem(**data)
                item.value = values.get(key, item.default_value or "")
                self._configs[f"{item.group}.{item.key}"] = item
        except Exception as e:
            logger.error("[ConfigCenter] 加载配置失败: %s", e)

        # 加载审计日志
        if self._audit_path.exists():
            try:
                for line in self._audit_path.read_text(encoding='utf-8').strip().split('\n'):
                    if line.strip():
                        self._audit_cache.append(ConfigAuditLog(**json.loads(line)))
            except Exception as _e:
                logger.warning(f"error: {_e}")

    def save_to_file(self):
        """加密持久化到磁盘（公开接口）"""
        self._save_to_disk()

    def _save_to_disk(self):
        """加密持久化到磁盘"""
        try:
            meta = {}
            values = {}
            for ck, item in self._configs.items():
                meta[ck] = asdict(item)
                values[ck] = item.value

            encrypted = _CryptoEngine.encrypt(json.dumps(values), self._master_key)
            self._store_path.write_text(encrypted, encoding='utf-8')
            self._meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            logger.error("[ConfigCenter] 保存配置失败: %s", e)

    def _append_audit(self, log: ConfigAuditLog):
        self._audit_cache.append(log)
        try:
            with open(self._audit_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(log), ensure_ascii=False) + '\n')
        except Exception as _e:
            logger.warning(f"error: {_e}")

    # ─── 初始化 ───

    def _init_builtin_templates(self):
        """注入预置配置模板 (不覆盖已有值)"""
        for tmpl in BUILTIN_TEMPLATES:
            ck = f"{tmpl.group}.{tmpl.key}"
            if ck not in self._configs:
                self._configs[ck] = deepcopy(tmpl)

    def _inject_env_vars(self):
        """从环境变量注入配置值 (环境变量优先级最高)"""
        for ck, item in self._configs.items():
            if item.env_var and os.environ.get(item.env_var, ""):
                env_val = os.environ[item.env_var]
                if env_val != item.value:
                    old_masked = _CryptoEngine.mask_value(item.value) if item.is_secret else item.value[:20]
                    item.value = env_val
                    item.updated_at = datetime.now().isoformat()
                    item.updated_by = "env_inject"
                    self._append_audit(ConfigAuditLog(
                        timestamp=datetime.now().isoformat(), action="env_inject",
                        key=ck, old_value_masked=old_masked,
                        new_value_masked="[env]", operator="system", group=item.group
                    ))

    # ═══════════════════════════════════════════════════════
    # 公共 API — CRUD
    # ═══════════════════════════════════════════════════════

    def get(self, key: str, group: str = "custom", default: str = "") -> str:
        """获取配置值"""
        ck = f"{group}.{key}"
        item = self._configs.get(ck)
        if item:
            return item.value or item.default_value or default
        return default

    def get_all(self, group: str | None = None, mask_secrets: bool = True) -> list[dict]:
        """获取配置列表 (支持分组过滤)"""
        result = []
        for ck, item in self._configs.items():
            if group and item.group != group:
                continue
            d = asdict(item)
            if mask_secrets and item.is_secret:
                d['value'] = _CryptoEngine.mask_value(d['value'])
            result.append(d)
        return sorted(result, key=lambda x: (x['group'], x['key']))

    def set(self, key: str, value: str, group: str = "custom",
            operator: str = "api", label: str = "", description: str = "",
            is_secret: bool = True, env_var: str = "") -> dict:
        """设置配置值"""
        ck = f"{group}.{key}"
        now = datetime.now().isoformat()
        old_masked = ""
        item = self._configs.get(ck)

        if item:
            old_masked = _CryptoEngine.mask_value(item.value) if item.is_secret else item.value[:20]
            item.value = value
            item.updated_at = now
            item.updated_by = operator
            if label:
                item.label = label
            if description:
                item.description = description
        else:
            old_masked = "(new)"
            item = ConfigItem(
                key=key, value=value, group=group, label=label or key,
                description=description, is_secret=is_secret, env_var=env_var,
                created_at=now, updated_at=now, updated_by=operator
            )
            self._configs[ck] = item

        self._save_to_disk()
        new_masked = _CryptoEngine.mask_value(value) if item.is_secret else value[:20]
        self._append_audit(ConfigAuditLog(
            timestamp=now, action="update" if old_masked != "(new)" else "create",
            key=ck, old_value_masked=old_masked, new_value_masked=new_masked,
            operator=operator, group=group
        ))

        # 触发变更回调
        self._fire_change_callbacks(ck, value, old_masked)

        return {"status": "ok", "key": ck, "action": "updated" if old_masked != "(new)" else "created"}

    def delete(self, key: str, group: str = "custom", operator: str = "api") -> dict:
        """删除配置项"""
        ck = f"{group}.{key}"
        item = self._configs.pop(ck, None)
        if not item:
            return {"status": "not_found", "key": ck}

        self._save_to_disk()
        self._append_audit(ConfigAuditLog(
            timestamp=datetime.now().isoformat(), action="delete",
            key=ck, old_value_masked=_CryptoEngine.mask_value(item.value) if item.is_secret else item.value[:20],
            new_value_masked="", operator=operator, group=group
        ))
        return {"status": "ok", "key": ck, "action": "deleted"}

    def get_groups(self) -> list[dict]:
        """获取配置分组统计"""
        groups: dict[str, dict] = {}
        for ck, item in self._configs.items():
            g = item.group
            if g not in groups:
                groups[g] = {"name": g, "count": 0, "has_secret": False, "configured": 0}
            groups[g]["count"] += 1
            if item.is_secret:
                groups[g]["has_secret"] = True
            if item.value:
                groups[g]["configured"] += 1
        return list(groups.values())

    def validate(self, key: str, group: str = "custom") -> dict:
        """校验配置项"""
        ck = f"{group}.{key}"
        item = self._configs.get(ck)
        if not item:
            return {"valid": False, "error": "配置项不存在"}
        errors = []
        if item.is_required and not item.value:
            errors.append("此配置为必填项")
        if item.validation_pattern and item.value:
            import re
            if not re.match(item.validation_pattern, item.value):
                errors.append(f"格式校验失败 (期望: {item.validation_pattern})")
        return {"valid": len(errors) == 0, "errors": errors}

    def validate_all(self) -> dict:
        """校验所有必填配置"""
        missing = []
        invalid = []
        for ck, item in self._configs.items():
            if item.is_required and not item.value:
                missing.append({"key": ck, "label": item.label, "group": item.group})
            if item.validation_pattern and item.value:
                import re
                if not re.match(item.validation_pattern, item.value):
                    invalid.append({"key": ck, "label": item.label, "group": item.group})
        return {
            "total": len(self._configs),
            "configured": sum(1 for i in self._configs.values() if i.value),
            "missing_required": missing,
            "invalid_pattern": invalid
        }

    # ─── 变更监听 ───

    def on_change(self, key: str, callback: callable):
        """注册配置变更回调"""
        ck = key if '.' in key else f"custom.{key}"
        self._change_callbacks.setdefault(ck, []).append(callback)

    def _fire_change_callbacks(self, ck: str, new_value: str, old_value: str):
        for cb in self._change_callbacks.get(ck, []):
            try:
                cb(ck, new_value, old_value)
            except Exception as e:
                logger.error("[ConfigCenter] 变更回调异常: %s → %s", ck, e)

    # ─── 审计日志 ───

    def get_audit_logs(self, limit: int = 50, group: str | None = None) -> list[dict]:
        """获取审计日志"""
        logs = self._audit_cache
        if group:
            logs = [l for l in logs if l.group == group]
        return [asdict(l) for l in logs[-limit:]]

    # ─── 导出/导入 ───

    def export_config(self, group: str | None = None, include_secrets: bool = False) -> str:
        """导出配置为JSON"""
        items = self.get_all(group=group, mask_secrets=not include_secrets)
        return json.dumps({
            "exported_at": datetime.now().isoformat(),
            "version": "V0.1",
            "items": items
        }, ensure_ascii=False, indent=2)

    def import_config(self, json_str: str, operator: str = "api", overwrite: bool = False) -> dict:
        """导入配置"""
        try:
            data = json.loads(json_str)
            items = data.get("items", [])
            imported = 0; skipped = 0; errors = 0
            for item_data in items:
                key = item_data.get("key", "")
                group = item_data.get("group", "custom")
                value = item_data.get("value", "")
                ck = f"{group}.{key}"
                if not overwrite and ck in self._configs and self._configs[ck].value:
                    skipped += 1
                    continue
                try:
                    self.set(key=key, value=value, group=group, operator=operator,
                             label=item_data.get("label", ""), description=item_data.get("description", ""),
                             is_secret=item_data.get("is_secret", True), env_var=item_data.get("env_var", ""))
                    imported += 1
                except Exception:
                    errors += 1
            return {"status": "ok", "imported": imported, "skipped": skipped, "errors": errors}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ─── 统计 ───

    def stats(self) -> dict:
        """配置统计"""
        total = len(self._configs)
        configured = sum(1 for i in self._configs.values() if i.value)
        groups = {}
        for ck, item in self._configs.items():
            groups[item.group] = groups.get(item.group, 0) + 1
        return {
            "total_items": total,
            "configured": configured,
            "unconfigured": total - configured,
            "coverage_pct": round(configured / total * 100, 1) if total else 0,
            "groups": groups,
            "audit_entries": len(self._audit_cache)
        }


# ═══════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════

_config_center: ConfigCenter | None = None

def get_config_center() -> ConfigCenter:
    global _config_center
    if _config_center is None:
        _config_center = ConfigCenter()
    return _config_center

def reset_config_center():
    global _config_center
    _config_center = None
