"""
AUTO-EVO-AI V0.1 — i18n 多语言引擎
提供 /api/v1/i18n?lang=zh-CN 端点，支持 Accept-Language
纯文件驱动：从 i18n/*.json 加载所有翻译，无内置硬编码
"""
import logging
logger = logging.getLogger("evo.routes_i18n")

from fastapi import APIRouter, Request
from typing import Optional
import json, os
from pathlib import Path

router = APIRouter()

BASE = Path(__file__).resolve().parent.parent.parent
I18N_DIR = BASE / "i18n"

# 从文件系统加载所有翻译
_TRANSLATIONS: dict[str, dict] = {}
for f in sorted(I18N_DIR.glob("*.json")):
    try:
        lang = f.stem
        data = json.loads(f.read_text(encoding="utf-8"))
        _TRANSLATIONS[lang] = data
    except Exception as _e:
        logger.warning(f"error: {_e}")


@router.get("/api/v1/i18n")
async def get_i18n(lang: str = "zh-CN", request: Request = None):
    """获取翻译 JSON"""
    # 支持 Accept-Language
    if request and request.headers.get("accept-language"):
        accept = request.headers["accept-language"].split(",")[0].split("-")[0]
        for code in _TRANSLATIONS:
            if code.startswith(accept):
                lang = code
                break
    
    data = _TRANSLATIONS.get(lang) or _TRANSLATIONS.get("zh-CN", {})
    return {"success": True, "lang": lang, "data": data, "available": list(_TRANSLATIONS.keys())}


@router.get("/api/v1/i18n/langs")
async def list_langs():
    return {"success": True, "languages": list(_TRANSLATIONS.keys()), "names": {k: v.get("lang_name", k) for k, v in _TRANSLATIONS.items()}}
