"""
AUTO-EVO-AI V0.1 — 配置加载器（上市公司级）
=============================================
优先级链: 环境变量 > environment yaml > defaults.yaml > 硬编码默认值

用法:
    from core.config_loader import load_config
    cfg = load_config()
    cfg["server"]["port"]  # → 8765 (或 EVO_PORT 覆盖)
"""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Any, Dict


def _find_config_dir() -> Path:
    """从文件位置推断 config/ 目录"""
    return Path(__file__).resolve().parent.parent / "config"


def _load_yaml(path: Path) -> Dict[str, Any]:
    """加载单个 YAML 文件，文件不存在时返回空字典"""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """深度合并字典（override 覆盖 base）"""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _env_overrides() -> Dict[str, Any]:
    """将 EVO_ 前缀的环境变量转为嵌套字典

    例: EVO_SERVER_PORT=9000 → {"server": {"port": 9000}}
        EVO_SECURITY_RATE_LIMIT_MAX_REQUESTS=5000 → {"security": {"rate_limit": {"max_requests": 5000}}}
    """
    result: Dict[str, Any] = {}
    prefix = "EVO_"
    for key, val in os.environ.items():
        if not key.startswith(prefix):
            continue
        # 去掉 EVO_ 前缀，小写并分割
        parts = key[len(prefix):].lower().split("_")
        # 尝试数值转换
        try:
            val_parsed = int(val)
        except ValueError:
            try:
                val_parsed = float(val)
            except ValueError:
                if val.lower() in ("true", "false"):
                    val_parsed = val.lower() == "true"
                elif val.lower() in ("", "none", "null"):
                    val_parsed = None
                else:
                    val_parsed = val

        # 构建嵌套结构
        target = result
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = val_parsed
    return result


def load_config(env: str | None = None) -> Dict[str, Any]:
    """加载完整配置链

    Args:
        env: 环境名称 (development/production/staging)，默认从 EVO_ENV 读取

    Returns:
        合并后的配置字典
    """
    config_dir = _find_config_dir()

    # 1. 加载默认配置
    config = _load_yaml(config_dir / "defaults.yaml")

    # 2. 加载环境特定配置
    if env is None:
        env = os.environ.get("EVO_ENV", "")
    if env:
        env_config = _load_yaml(config_dir / "environments" / f"{env}.yaml")
        config = _deep_merge(config, env_config)

    # 3. 环境变量覆盖（最高优先级）
    config = _deep_merge(config, _env_overrides())

    return config


def get_config_value(config: Dict[str, Any], key: str, default: Any = None) -> Any:
    """点分键取值，例如 get_config_value(cfg, 'server.port', 8765)"""
    parts = key.split(".")
    target = config
    for part in parts:
        if isinstance(target, dict):
            target = target.get(part)
        else:
            return default
    return target if target is not None else default
