"""
AUTO-EVO-AI V0.1 — Internationalization Service (Runtime Translation Layer)
===========================================================================
上市公司级设计：零侵入运行时翻译，不改任何模块源码。
支持中文/英文，自动降级（缺翻译显示中文），热加载。

核心原理：
  1. 扫描输出文本中的中文，自动匹配翻译
  2. Accept-Language / Cookie → 自动切换语言
  3. 翻译缺失时优雅降级显示原文（中文）
  4. 翻译词典独立于业务代码，可热更新
"""

import os
import re
import json
import logging
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("evo.i18n")

# ── 翻译词典加载 ──

_TRANSLATIONS: Dict[str, Dict[str, str]] = {}
"""{locale: {text: translation}}"""

_DICTIONARY_DIR = Path(__file__).parent.parent / "i18n"


def _load_dictionaries():
    """加载所有翻译词典文件"""
    global _TRANSLATIONS
    _TRANSLATIONS = {}
    if not _DICTIONARY_DIR.exists():
        _DICTIONARY_DIR.mkdir(parents=True, exist_ok=True)
        _create_default_dictionaries()
    for fpath in sorted(_DICTIONARY_DIR.glob("*.json")):
        locale = fpath.stem
        try:
            with open(str(fpath), "r", encoding="utf-8") as f:
                data = json.load(f)
            _TRANSLATIONS[locale] = data
            logger.info("[I18N] Loaded %s: %d entries", locale, len(data))
        except Exception as e:
            logger.warning("[I18N] Failed to load %s: %s", fpath.name, e)
    if not _TRANSLATIONS:
        _create_default_dictionaries()


def _create_default_dictionaries():
    """首次运行时创建默认翻译词典模板"""
    # en-US 空词典
    en_path = _DICTIONARY_DIR / "en-US.json"
    if not en_path.exists():
        with open(str(en_path), "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    # zh-CN 模板
    zh_path = _DICTIONARY_DIR / "zh-CN.json"
    if not zh_path.exists():
        with open(str(zh_path), "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    logger.info("[I18N] Created default dictionary files in %s", _DICTIONARY_DIR)


# ── 核心翻译函数 ──


def get_available_locales() -> List[str]:
    """获取可用语言列表"""
    if not _TRANSLATIONS:
        _load_dictionaries()
    return list(_TRANSLATIONS.keys())


def translate(text: str, locale: str = "en-US") -> str:
    """翻译文本：locale缺失时返回原文"""
    if not text or locale == "zh-CN":
        return text
    if not _TRANSLATIONS:
        _load_dictionaries()
    data = _TRANSLATIONS.get(locale)
    if not data:
        return text
    return data.get(text, text)


def translate_object(obj, locale: str = "en-US") -> dict:
    """递归翻译dict/list中的所有可翻译文本字段"""
    if not _TRANSLATIONS:
        _load_dictionaries()
    if locale == "zh-CN":
        return obj
    if isinstance(obj, dict):
        return {k: translate_object(v, locale) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [translate_object(item, locale) for item in obj]
    elif isinstance(obj, str):
        return translate(obj, locale)
    return obj


def detect_locale(accept_language: str = "", cookie: str = "") -> str:
    """从请求头/ Cookie 检测语言"""
    if cookie in ("en-US", "zh-CN"):
        return cookie
    if accept_language:
        # 解析 Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
        for part in accept_language.split(","):
            lang = part.split(";")[0].strip().split("-")[0].lower()
            if lang == "zh":
                return "zh-CN"
            if lang == "en":
                return "en-US"
    return "zh-CN"  # 默认中文


# ── 词典管理 ──


def scan_and_register(texts: List[str], locale: str = "en-US"):
    """
    扫描并注册新文本到翻译词典
    用于自动积累需要翻译的文本
    """
    if not _TRANSLATIONS:
        _load_dictionaries()
    data = _TRANSLATIONS.get(locale)
    if data is None:
        _TRANSLATIONS[locale] = {}
        data = _TRANSLATIONS[locale]
    changed = False
    for text in texts:
        if text and text not in data:
            data[text] = ""
            changed = True
    if changed:
        _save_dictionary(locale)


def _save_dictionary(locale: str):
    """持久化翻译词典"""
    data = _TRANSLATIONS.get(locale, {})
    fpath = _DICTIONARY_DIR / f"{locale}.json"
    try:
        with open(str(fpath), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("[I18N] Save %s failed: %s", locale, e)


def update_translation(text: str, translation: str, locale: str = "en-US") -> bool:
    """更新单条翻译"""
    if not _TRANSLATIONS:
        _load_dictionaries()
    data = _TRANSLATIONS.get(locale)
    if data is None:
        _TRANSLATIONS[locale] = {}
        data = _TRANSLATIONS[locale]
    data[text] = translation
    _save_dictionary(locale)
    return True


def get_pending_translations(locale: str = "en-US") -> Dict[str, str]:
    """获取尚未翻译的条目"""
    if not _TRANSLATIONS:
        _load_dictionaries()
    data = _TRANSLATIONS.get(locale, {})
    return {k: v for k, v in data.items() if not v}


def get_stats() -> Dict:
    """翻译引擎统计"""
    if not _TRANSLATIONS:
        _load_dictionaries()
    stats = {"available_locales": list(_TRANSLATIONS.keys())}
    for locale, data in _TRANSLATIONS.items():
        total = len(data)
        translated = sum(1 for v in data.values() if v)
        stats[locale] = {"total": total, "translated": translated, "pending": total - translated}
    return stats


# ── 启动时自动加载 ──

_load_dictionaries()
