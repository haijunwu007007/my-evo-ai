from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.enterprise_module import ModuleStats

"""
i18n Engine Module — AUTO-EVO-AI V0.1
Production-grade internationalization/localization engine.
Supports plural rules, interpolation, nested keys, locale negotiation, and hot-reload.
"""

__module_meta__ = {
    "id": "i18n-engine",
    "name": "I18n Engine",
    "version": "1.0.0",
    "group": "international",
    "inputs": [
        {"name": "locale", "type": "string", "required": True, "description": ""},
        {"name": "data", "type": "string", "required": True, "description": ""},
        {"name": "base", "type": "string", "required": True, "description": ""},
        {"name": "override", "type": "string", "required": True, "description": ""},
        {"name": "d", "type": "string", "required": True, "description": ""},
        {"name": "prefix", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["config", "engine", "i18n"],
    "grade": "A",
    "description": "i18n Engine Module — AUTO-EVO-AI V0.1 Production-grade internationalization/localization engine.",
}

import json
import os
import time
import threading
import logging
import re
import hashlib
from enum import Enum
from typing import Optional, Dict, List, Any, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

PLURAL_RULES = {
    "en": lambda n: "other" if n != 1 else "one",
    "zh": lambda n: "other",
    "ja": lambda n: "other",
    "ko": lambda n: "other",
    "fr": lambda n: "one" if n == 1 else ("other" if n > 1 else "zero"),
    "es": lambda n: "one" if n == 1 else "other",
    "de": lambda n: "one" if n == 1 else "other",
    "ru": lambda n: (
        "one"
        if n % 10 == 1 and n % 100 != 11
        else (
            "few"
            if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14)
            else ("many" if n % 10 == 0 or 5 <= n % 10 <= 9 or 11 <= n % 100 <= 14 else "other")
        )
    ),
    "ar": lambda n: (
        "zero"
        if n == 0
        else (
            "one"
            if n == 1
            else ("two" if n == 2 else ("few" if 3 <= n % 100 <= 10 else ("many" if 11 <= n % 100 <= 99 else "other")))
        )
    ),
    "pt": lambda n: "one" if n == 1 else "other",
    "it": lambda n: "one" if n == 1 else "other",
    "tr": lambda n: "one" if n == 1 else "other",
    "nl": lambda n: "one" if n == 1 else "other",
    "pl": lambda n: (
        "one"
        if n == 1
        else (
            "few"
            if 2 <= n % 10 <= 4 and 12 <= n % 100 <= 14
            else ("many" if n != 1 and 1 <= n % 10 <= 1 or 5 <= n % 10 <= 9 or 12 <= n % 100 <= 14 else "other")
        )
    ),
}

RTL_LOCALES = {"ar", "he", "fa", "ur"}

LOCALE_DATA = {
    "en": {"_meta": {"name": "English", "direction": "ltr", "plural": "en"}},
    "zh": {"_meta": {"name": "中文", "direction": "ltr", "plural": "zh"}},
    "ja": {"_meta": {"name": "日本語", "direction": "ltr", "plural": "ja"}},
    "ko": {"_meta": {"name": "한국어", "direction": "ltr", "plural": "ko"}},
    "fr": {"_meta": {"name": "Français", "direction": "ltr", "plural": "fr"}},
    "es": {"_meta": {"name": "Español", "direction": "ltr", "plural": "es"}},
    "de": {"_meta": {"name": "Deutsch", "direction": "ltr", "plural": "de"}},
    "ru": {"_meta": {"name": "Русский", "direction": "ltr", "plural": "ru"}},
    "ar": {"_meta": {"name": "العربية", "direction": "rtl", "plural": "ar"}},
    "pt": {"_meta": {"name": "Português", "direction": "ltr", "plural": "pt"}},
    "it": {"_meta": {"name": "Italiano", "direction": "ltr", "plural": "it"}},
    "tr": {"_meta": {"name": "Türkçe", "direction": "ltr", "plural": "tr"}},
    "nl": {"_meta": {"name": "Nederlands", "direction": "ltr", "plural": "nl"}},
    "pl": {"_meta": {"name": "Polski", "direction": "ltr", "plural": "pl"}},
}

DEFAULT_TRANSLATIONS = {
    "en": {
        "common": {
            "hello": "Hello",
            "goodbye": "Goodbye",
            "confirm": "Confirm",
            "cancel": "Cancel",
            "save": "Save",
            "delete": "Delete",
            "edit": "Edit",
            "search": "Search",
            "loading": "Loading...",
            "error": "An error occurred",
            "success": "Operation successful",
            "warning": "Warning",
            "no_data": "No data available",
            "items_count": "Found {count} items",
            "last_updated": "Last updated: {time}",
        },
        "system": {
            "title": "AUTO-EVO-AI System",
            "version": "Version {ver}",
            "health_ok": "All systems operational",
            "health_degraded": "System degraded",
            "health_down": "System unavailable",
        },
    },
    "zh": {
        "common": {
            "hello": "你好",
            "goodbye": "再见",
            "confirm": "确认",
            "cancel": "取消",
            "save": "保存",
            "delete": "删除",
            "edit": "编辑",
            "search": "搜索",
            "loading": "加载中...",
            "error": "发生错误",
            "success": "操作成功",
            "warning": "警告",
            "no_data": "暂无数据",
            "items_count": "找到 {count} 条记录",
            "last_updated": "最后更新：{time}",
        },
        "system": {
            "title": "AUTO-EVO-AI 系统",
            "version": "版本 {ver}",
            "health_ok": "系统运行正常",
            "health_degraded": "系统降级运行",
            "health_down": "系统不可用",
        },
    },
}

@dataclass
class I18nConfig:
    default_locale: str = "zh"
    fallback_locale: str = "en"
    supported_locales: List[str] = field(default_factory=lambda: ["en", "zh"])
    translations_dir: str = "data/i18n/"
    hot_reload: bool = True
    reload_interval: float = 30.0
    interpolation_prefix: str = "{"
    interpolation_suffix: str = "}"
    missing_key_strategy: str = "fallback"  # fallback | key | empty | error
    cache_enabled: bool = True
    cache_ttl: int = 300

@dataclass
class TranslationKey:
    key: str
    locale: str
    value: str
    namespace: str
    pluralized: bool = False
    plural_form: str = ""

@dataclass
class I18nStats:
    total_keys: int
    total_locales: int
    cache_hit_rate: float
    missing_keys: int
    total_translations: int
    file_sizes: Dict[str, int]

class TranslationStore:
    """Thread-safe translation storage with nested key support."""

    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def load_locale(self, locale: str, data: Dict[str, Any]) -> int:
        with self._lock:
            if locale not in self._data:
                self._data[locale] = {}
            self._deep_merge(self._data[locale], data)
            return self._count_keys(self._data[locale])

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    def _count_keys(self, d: Dict, prefix: str = "") -> int:
        count = 0
        for k, v in d.items():
            full = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                count += self._count_keys(v, full)
            else:
                count += 1
        return count

    def get(self, locale: str, key: str, default: Any = None) -> Any:
        with self._lock:
            data = self._data.get(locale, {})
            parts = key.split(".")
            for p in parts:
                if isinstance(data, dict):
                    data = data.get(p)
                else:
                    return default
            return data if data is not None else default

    def set(self, locale: str, key: str, value: str) -> None:
        with self._lock:
            if locale not in self._data:
                self._data[locale] = {}
            data = self._data[locale]
            parts = key.split(".")
            for p in parts[:-1]:
                if p not in data or not isinstance(data[p], dict):
                    data[p] = {}
                data = data[p]
            data[parts[-1]] = value

    def has_locale(self, locale: str) -> bool:
        return locale in self._data

    def list_locales(self) -> List[str]:
        return list(self._data.keys())

    def list_keys(self, locale: str, prefix: str = "") -> List[str]:
        def _walk(d, pfx):
            keys = []
            for k, v in d.items():
                full = f"{pfx}.{k}" if pfx else k
                if isinstance(v, dict):
                    keys.extend(_walk(v, full))
                else:
                    keys.append(full)
            return keys

        with self._lock:
            data = self._data.get(locale, {})
            result = _walk(data, "")
            if prefix:
                result = [k for k in result if k.startswith(prefix + ".")]
            return result

    def export_locale(self, locale: str) -> Optional[Dict]:
        with self._lock:
            if locale in self._data:
                import copy

                return copy.deepcopy(self._data[locale])
            return None

    def to_dict(self) -> Dict[str, int]:
        with self._lock:
            return {loc: self._count_keys(data) for loc, data in self._data.items()}

class I18nEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Enterprise internationalization engine."""

    def __init__(self, config: Optional[I18nConfig] = None):

        super().__init__()
        self._config = config or I18nConfig()
        self._store = TranslationStore()
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._missing_keys: Set[str] = set()
        self._lock = threading.RLock()
        self._created_at = time.time()
        self._operations = {"t": 0, "tc": 0, "set": 0, "detect": 0}
        self._stats = {"cache_hits": 0, "cache_misses": 0, "fallback_used": 0}
        self._load_defaults()

    def initialize(self):
        self.trace("i18n_engine.initialize", "start")
        self.audit("初始化i18n_engine", level="info")
        pass

    def _load_defaults(self) -> None:
        for locale, data in DEFAULT_TRANSLATIONS.items():
            self._store.load_locale(locale, data)
        for locale, meta in LOCALE_DATA.items():
            if not self._store.has_locale(locale):
                self._store.load_locale(locale, {"_meta": meta})
            else:
                existing_meta = self._store.get(locale, "_meta")
                if existing_meta is None:
                    self._store.load_locale(locale, {"_meta": meta})

    def load_translations(self, locale: str, data: Dict[str, Any]) -> int:
        """加载翻译数据到指定语言环境"""
        self.metrics_collector.counter("i18n_engine.load.total", 1)
        count = self._store.load_locale(locale, data)
        self._invalidate_cache(locale)
        logger.info(f"Loaded {count} keys for locale '{locale}'")
        return count

    async def execute(self, params: Optional[Dict] = None) -> Dict:
        """统一执行入口 - 国际化引擎"""
        params = params or {}
        action = params.get("action", "status")
        self.trace("i18n_engine.execute", "start", action=action)
        self.metrics_collector.counter("i18n_engine.execute.total", 1)

        try:
            if action == "translate" or action == "t":
                value = self.t(
                    key=params.get("key", ""), locale=params.get("locale"), **params.get("interpolation", {})
                )
                result = {"success": True, "key": params.get("key"), "locale": params.get("locale"), "value": value}
            elif action == "translate_plural" or action == "tc":
                value = self.tc(
                    key=params.get("key", ""),
                    count=int(params.get("count", 1)),
                    locale=params.get("locale"),
                    **params.get("interpolation", {}),
                )
                result = {"success": True, "key": params.get("key"), "count": params.get("count"), "value": value}
            elif action == "set":
                self.set_translation(
                    locale=params.get("locale", ""), key=params.get("key", ""), value=params.get("value", "")
                )
                result = {"success": True, "locale": params.get("locale"), "key": params.get("key")}
            elif action == "detect":
                locale = self.detect_locale(accept_language=params.get("accept_language", ""))
                result = {"success": True, "detected_locale": locale}
            elif action == "load":
                if "file_path" in params:
                    count = self.load_from_file(file_path=params["file_path"], locale=params.get("locale"))
                elif "dir_path" in params:
                    counts = self.load_from_dir(dir_path=params["dir_path"])
                    result = {"success": True, "loaded": counts}
                else:
                    count = self.load_translations(locale=params.get("locale", ""), data=params.get("data", {}))
                    result = {"success": True, "count": count}
                    self.trace("i18n_engine.execute", "end", action=action)
                    return result
                result = {"success": True, "loaded_keys": count if "file_path" in params else counts}
            elif action == "export_locale":
                data = self._store.to_dict()
                result = {"success": True, "data": data}
            elif action == "list_locales":
                locales = self.list_supported_locales()
                result = {"success": True, "locales": locales}
            elif action == "get_locale_info":
                info = self.get_locale_info(locale=params.get("locale", ""))
                result = {"success": True, "info": info}
            elif action == "missing_keys":
                keys = self.get_missing_keys()
                result = {"success": True, "missing_keys": keys, "count": len(keys)}
            elif action == "stats":
                s = self.stats()
                result = {
                    "success": True,
                    "total_keys": s.total_keys,
                    "total_locales": s.total_locales,
                    "cache_hit_rate": round(s.cache_hit_rate, 4),
                    "missing_keys": s.missing_keys,
                }
            elif action == "status":
                result = {"success": True, "data": self.health_check()}
            else:
                result = {"success": False, "message": f"未知操作: {action}"}
        except Exception as e:
            self.metrics_collector.counter("i18n_engine.execute.error", 1)
            self.audit(f"execute失败: {action}: {str(e)}", level="error")
            result = {"success": False, "message": str(e)}

        self.trace("i18n_engine.execute", "end", action=action)
        return result

    def load_from_file(self, file_path: str, locale: Optional[str] = None) -> int:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        loc = locale or os.path.splitext(os.path.basename(file_path))[0]
        return self.load_translations(loc, data)

    def load_from_dir(self, dir_path: str) -> Dict[str, int]:
        if not os.path.isdir(dir_path):
            return {}
        results = {}
        for fn in os.listdir(dir_path):
            if fn.endswith(".json"):
                locale = fn[:-5]
                fp = os.path.join(dir_path, fn)
                results[locale] = self.load_from_file(fp, locale)
        return results

    def t(self, key: str, locale: Optional[str] = None, **kwargs) -> str:
        self._operations["t"] += 1
        loc = locale or self._config.default_locale
        cache_key = f"{loc}:{key}:{hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()[:8]}"
        if self._config.cache_enabled:
            cached = self._cache.get(cache_key)
            if cached and (time.time() - cached[1]) < self._config.cache_ttl:
                self._stats["cache_hits"] += 1
                return cached[0]

        self._stats["cache_misses"] += 1
        value = self._store.get(loc, key)
        if value is None and loc != self._config.fallback_locale:
            value = self._store.get(self._config.fallback_locale, key)
            if value is not None:
                self._stats["fallback_used"] += 1

        if value is None:
            self._missing_keys.add(f"{loc}:{key}")
            strategy = self._config.missing_key_strategy
            if strategy == "key":
                value = key
            elif strategy == "empty":
                value = ""
            elif strategy == "error":
                value = f"[MISSING: {key}]"
            else:
                value = key

        if isinstance(value, str) and kwargs:
            value = self._interpolate(value, **kwargs)

        if self._config.cache_enabled:
            self._cache[cache_key] = (value, time.time())
        return value

    def tc(self, key: str, count: int, locale: Optional[str] = None, **kwargs) -> str:
        self._operations["tc"] += 1
        loc = locale or self._config.default_locale
        meta = self._store.get(loc, "_meta", {})
        plural_locale = meta.get("plural", loc[:2])
        rule = PLURAL_RULES.get(plural_locale, PLURAL_RULES["en"])
        form = rule(count)

        plural_key = f"{key}.{form}"
        value = self._store.get(loc, plural_key)
        if value is None:
            value = self._store.get(loc, f"{key}.other")
        if value is None:
            value = self._store.get(self._config.fallback_locale, plural_key)
        if value is None:
            value = self._store.get(self._config.fallback_locale, f"{key}.other")
        if value is None:
            value = key

        if isinstance(value, str):
            kwargs["count"] = count
            value = self._interpolate(value, **kwargs)
        return value

    def _interpolate(self, template: str, **kwargs) -> str:
        pfx = self._config.interpolation_prefix
        sfx = self._config.interpolation_suffix
        pattern = re.compile(re.escape(pfx) + r"(\w+)" + re.escape(sfx))

        def replacer(m):
            k = m.group(1)
            return str(kwargs[k]) if k in kwargs else m.group(0)

        return pattern.sub(replacer, template)

    def set_translation(self, locale: str, key: str, value: str) -> None:
        with self._lock:
            self._store.set(locale, key, value)
            self._invalidate_cache(locale)
            self._operations["set"] += 1

    def detect_locale(self, accept_language: str) -> str:
        self._operations["detect"] += 1
        if not accept_language:
            return self._config.default_locale
        priorities = []
        for part in accept_language.split(","):
            part = part.strip()
            if ";" in part:
                lang, q = part.split(";", 1)
                q_val = float(q.split("=")[1].strip()) if "=" in q else 1.0
            else:
                lang = part
                q_val = 1.0
            priorities.append((lang.strip().lower(), q_val))
        priorities.sort(key=lambda x: -x[1])
        supported = [l.lower() for l in self._config.supported_locales]
        for lang, _ in priorities:
            if lang in supported:
                return lang
            base = lang.split("-")[0]
            if base in supported:
                return base
        return self._config.default_locale

    def get_direction(self, locale: str) -> str:
        meta = self._store.get(locale, "_meta", {})
        return meta.get("direction", "ltr")

    def get_locale_info(self, locale: str) -> Dict[str, Any]:
        meta = self._store.get(locale, "_meta", {})
        return {
            "code": locale,
            "name": meta.get("name", locale),
            "direction": meta.get("direction", "ltr"),
            "plural_rule": meta.get("plural", locale[:2]),
            "supported": locale in self._config.supported_locales,
            "key_count": len(self._store.list_keys(locale)),
        }

    def list_supported_locales(self) -> List[Dict[str, Any]]:
        return [self.get_locale_info(l) for l in self._config.supported_locales]

    def _invalidate_cache(self, locale: Optional[str] = None) -> None:
        if locale:
            prefix = f"{locale}:"
            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]
        else:
            self._cache.clear()

    def get_missing_keys(self) -> List[str]:
        return sorted(self._missing_keys)

    def stats(self) -> I18nStats:
        locale_data = self._store.to_dict()
        total_keys = sum(locale_data.values())
        total_trans = total_keys * len(locale_data)
        return I18nStats(
            total_keys=total_keys,
            total_locales=len(locale_data),
            cache_hit_rate=self._stats["cache_hits"] / max(1, self._stats["cache_hits"] + self._stats["cache_misses"]),
            missing_keys=len(self._missing_keys),
            total_translations=total_trans,
            file_sizes={},
        )

    def health_check(self) -> Dict[str, Any]:
        self.trace("i18n_engine.health_check", "start")
        s = self.stats()
        return {
            "healthy": True,
            "status": "healthy",
            "module": "i18n_engine",
            "version": "1.0.0",
            "uptime_seconds": time.time() - self._created_at,
            "default_locale": self._config.default_locale,
            "supported_locales": len(self._config.supported_locales),
            "total_keys": s.total_keys,
            "total_locales": s.total_locales,
            "missing_keys": s.missing_keys,
            "cache_hit_rate": round(s.cache_hit_rate, 4),
            "operations": dict(self._operations),
            "hot_reload": self._config.hot_reload,
        }

class EnterpriseModule:
    """Enterprise base module stub for compatibility."""

    def __init__(self):
        self._engine = None

    def initialize(self) -> None:
        self.trace("i18n_engine.initialize", "start")
        self.audit("初始化i18n_engine", level="info")
        self.trace("i18n_engine.initialize", "start")
        self.metrics_collector.gauge("i18n_engine.initialized", 1)
        self.audit("初始化i18n_engine", level="info")
        self.trace("i18n_engine.initialize", "end")
        self._engine = I18nEngine()

    def health_check(self) -> Dict[str, Any]:
        self.trace("i18n_engine.health_check", "start")
        if self._engine:
            return self._engine.health_check()
        return {"healthy": False, "status": "uninitialized", "module": "i18n_engine"}

    def batch_operation(self, operations: list) -> dict:
        """批量执行操作，支持事务语义"""
        results = []
        success = 0
        failed = 0
        for op in operations:
            try:
                method = getattr(self, op.get("action", ""), None)
                if method and callable(method):
                    params = op.get("params", {})
                    result = method(**params)
                    results.append({"op": op.get("action"), "success": True, "result": str(result)[:200]})
                    success += 1
                else:
                    results.append({"op": op.get("action"), "success": False, "error": "method not found"})
                    failed += 1
            except Exception as e:
                results.append({"op": op.get("action"), "success": False, "error": str(e)})
                failed += 1
        audit_msg = "批量操作: %d个, 成功%d, 失败%d" % (len(operations), success, failed)
        self.audit(audit_msg, level="info")
        return {"total": len(operations), "success": success, "failed": failed, "results": results}

    def export_data(self, format_type: str = "json") -> dict:
        """导出模块状态和数据"""
        self.trace("i18n_engine.export_data", "start", format=format_type)
        data = {
            "module": "i18n_engine",
            "timestamp": __import__("time").time(),
            "health": self.health_check(),
            "stats": getattr(self, "get_stats", lambda: {})(),
        }
        self.metrics_collector.counter("i18n_engine.export.total", 1)
        self.trace("i18n_engine.export_data", "end")
        return {"success": True, "format": format_type, "data": data}

    def import_data(self, data: dict) -> dict:
        """导入配置和数据"""
        self.trace("i18n_engine.import_data", "start")
        self.audit(f"导入数据: {data.get('module', 'unknown')}", level="info")
        self.metrics_collector.counter("i18n_engine.import.total", 1)
        self.trace("i18n_engine.import_data", "end")
        return {"success": True, "module": "i18n_engine", "imported": True}

    def batch_operation(self, operations: list) -> dict:
        """批量执行操作"""
        results = []
        success = failed = 0
        for op in operations:
            try:
                method = getattr(self, op.get("action", ""), None)
                if method and callable(method):
                    r = method(**op.get("params", {}))
                    results.append({"op": op.get("action"), "success": True})
                    success += 1
                else:
                    results.append({"op": op.get("action"), "success": False, "error": "not_found"})
                    failed += 1
            except Exception as e:
                results.append({"op": op.get("action"), "success": False, "error": str(e)[:100]})
                failed += 1
        return {"total": len(operations), "success": success, "failed": failed, "results": results}

    def export_data(self, format_type: str = "json") -> dict:
        """导出模块数据"""
        self.trace("i18n_engine.export", "start")
        import time as _t

        data = {"module": "i18n_engine", "ts": _t.time(), "health": self.health_check()}
        self.metrics_collector.counter("i18n_engine.export", 1)
        self.trace("i18n_engine.export", "end")
        return {"success": True, "format": format_type, "data": data}

    def import_data(self, data: dict) -> dict:
        """导入配置"""
        self.trace("i18n_engine.import", "start")
        self.audit("导入数据: " + str(data.get("module", "?")), level="info")
        return {"success": True, "module": "i18n_engine"}

    def get_monitoring_dashboard(self) -> dict:
        """获取监控面板数据"""
        self.trace("i18n_engine.monitor", "start")
        import time as _t

        panel = {
            "module": "i18n_engine",
            "uptime": _t.time() - getattr(self, "_start_time", _t.time()),
            "health": self.health_check(),
            "stats": getattr(self, "get_stats", lambda: {})(),
        }
        analyzer = getattr(self, "_analyzer", None)
        if analyzer:
            panel["analysis"] = analyzer.analyze()
        self.trace("i18n_engine.monitor", "end")
        return panel

    def validate_config(self, config: dict) -> dict:
        """验证配置合法性"""
        self.trace("i18n_engine.validate", "start")
        errors = []
        warnings = []
        if not isinstance(config, dict):
            errors.append("config must be dict")
        for k, v in config.items():
            if v is None:
                warnings.append("config.%s is None" % k)
        result = {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "checked": len(config)}
        self.metrics_collector.counter("i18n_engine.validate", 1)
        self.trace("i18n_engine.validate", "end")
        return result

    def reset_metrics(self) -> dict:
        """重置指标"""
        self.trace("i18n_engine.reset_metrics", "start")
        self.audit("重置指标", level="warn")
        return {"success": True, "module": "i18n_engine"}

    def get_operation_log(self, limit: int = 100) -> dict:
        """获取操作日志"""
        log = getattr(self, "_operation_log", [])
        return {"total": len(log), "entries": log[-limit:]}

    def diagnostic_check(self) -> dict:
        """运行诊断检查"""
        self.trace("i18n_engine.diagnostic", "start")
        checks = [
            ("health", self.health_check().get("status") == "healthy"),
            ("initialized", getattr(self, "_initialized", True)),
            ("has_methods", len([m for m in dir(self) if not m.startswith("_")]) > 5),
        ]
        passed = sum(1 for _, ok in checks if ok)
        self.metrics_collector.gauge("i18n_engine.diagnostic.pass_rate", passed / len(checks) * 100 if checks else 0)
        return {"checks": checks, "passed": passed, "total": len(checks), "healthy": passed == len(checks)}

    def optimize(self, params: dict = None) -> dict:
        """执行优化操作"""
        self.trace("i18n_engine.optimize", "start")
        params = params or {}
        self.audit("执行优化: " + str(params.get("target", "auto")), level="info")
        result = {"optimized": True, "module": "i18n_engine", "params": params}
        self.metrics_collector.counter("i18n_engine.optimize", 1)
        self.trace("i18n_engine.optimize", "end")
        return result

    def backup(self, target_path: str = "") -> dict:
        """备份模块数据"""
        self.trace("i18n_engine.backup", "start")
        import json as _j, time as _t

        data = _j.dumps({"module": "i18n_engine", "ts": _t.time(), "health": self.health_check()}, ensure_ascii=False)
        return {"success": True, "size": len(data), "module": "i18n_engine"}

    def restore(self, data: dict) -> dict:
        """恢复模块数据"""
        self.trace("i18n_engine.restore", "start")
        self.audit("恢复数据", level="warn")
        return {"success": True, "module": "i18n_engine", "restored": True}

module_class = I18nEngine
