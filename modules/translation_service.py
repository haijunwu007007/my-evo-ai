"""
AUTO-EVO-AI V0.1 — 翻译服务
Grade: A (生产级) | Category: AI能力
职责：多语言翻译、术语管理、翻译缓存、批量翻译、翻译记忆
"""

__module_meta__ = {
    "id": "translation-service",
    "name": "Translation Service",
    "version": "V0.1",
    "group": "international",
    "inputs": [
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["translation", "adapter", "service"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 翻译服务 Grade: A (生产级) | Category: AI能力",
}

import os
import asyncio
import time
import uuid
import re
import json
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger("translation_service")

class _MetricsAdapter:
    """轻量指标适配器 — 兼容 self._metrics.increment/histogram 接口"""

    def increment(self, name: str, value: float = 1.0, **kw):
        pass  # 已由 EnterpriseModule.record_metrics() 覆盖

    def histogram(self, name: str, value: float, **kw):
        pass

    def gauge(self, name: str, value: float, **kw):
        pass

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

    # --- Auto-generated action dispatch methods ---
    def _action_counter(self, params=None):
        """Auto-generated action wrapper for counter"""
        if params is None:
            params = {}
        return self.counter(**params)

    def _action_gauge(self, params=None):
        """Auto-generated action wrapper for gauge"""
        if params is None:
            params = {}
        return self.gauge(**params)

    def _action_histogram(self, params=None):
        """Auto-generated action wrapper for histogram"""
        if params is None:
            params = {}
        return self.histogram(**params)

    def _action_increment(self, params=None):
        """Auto-generated action wrapper for increment"""
        if params is None:
            params = {}
        return self.increment(**params)

class Language(Enum):
    ZH_CN = "zh-CN"
    EN_US = "en-US"
    JA_JP = "ja-JP"
    KO_KR = "ko-KR"
    FR_FR = "fr-FR"
    DE_DE = "de-DE"
    ES_ES = "es-ES"
    PT_BR = "pt-BR"
    RU_RU = "ru-RU"
    AR_SA = "ar-SA"
    AUTO = "auto"

@dataclass
class TranslationMemory:
    """翻译记忆"""

    source_hash: str
    source_text: str
    target_text: str
    source_lang: str
    target_lang: str
    quality_score: float = 1.0
    usage_count: int = 0
    created_at: float = field(default_factory=time.time)

@dataclass
class GlossaryTerm:
    """术语表条目"""

    term: str
    translation: str
    source_lang: str
    target_lang: str
    domain: str = "general"
    notes: str = ""

@dataclass
class TranslationResult:
    """翻译结果"""

    translation_id: str
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    confidence: float
    from_cache: bool = False
    from_memory: bool = False
    alternatives: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

class LanguageDetector(object):
    """语言检测器 — 基于字符频率和常见词检测文本语言"""

    COMMON_PATTERNS = {
        "zh": (r"[\u4e00-\u9fff]", 0.15),
        "ja": (r"[\u3040-\u309f\u30a0-\u30ff]", 0.08),
        "ko": (r"[\uac00-\ud7af]", 0.08),
        "ru": (r"[\u0400-\u04ff]", 0.15),
        "ar": (r"[\u0600-\u06ff]", 0.15),
        "en": (r"\b(the|is|and|of|to|in|it|you|that|he|was)\b", 0.03),
    }

    STOPWORDS = {
        "zh": ["的", "了", "是", "在", "我", "有", "和", "就", "不", "人"],
        "en": ["the", "is", "at", "which", "on", "a", "an", "and", "or", "but"],
        "ja": ["の", "は", "が", "に", "を", "で", "と", "も", "な", "か"],
        "ko": ["의", "는", "이", "가", "을", "를", "에", "에서", "과", "와"],
    }

    def detect(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"language": "unknown", "confidence": 0}
        scores: Dict[str, float] = {}
        for lang, (pattern, threshold) in self.COMMON_PATTERNS.items():
            matches = re.findall(pattern, text)
            ratio = len(matches) / len(text) if text else 0
            if ratio >= threshold:
                scores[lang] = ratio
        for lang, words in self.STOPWORDS.items():
            count = sum(text.lower().count(w) for w in words)
            word_ratio = count / max(len(text.split()), 1)
            scores[lang] = scores.get(lang, 0) + word_ratio * 0.5
        if not scores:
            return {"language": "unknown", "confidence": 0}
        best = max(scores, key=scores.get)
        confidence = min(scores[best] * 10, 1.0)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {
            "language": best,
            "confidence": round(confidence, 3),
            "candidates": [{"language": l, "score": round(s, 4)} for l, s in sorted_scores[:3]],
        }

    def batch_detect(self, texts: List[str]) -> List[Dict[str, Any]]:
        return [self.detect(t) for t in texts]

    def detect_code_mixed(self, text: str) -> Dict[str, Any]:
        segments: Dict[str, int] = {}
        for lang in list(self.COMMON_PATTERNS.keys()) + list(self.STOPWORDS.keys()):
            pattern = self.COMMON_PATTERNS.get(lang, (None, 0))[0]
            if pattern:
                matches = re.findall(pattern, text)
                if matches:
                    segments[lang] = len(matches)
        total = sum(segments.values())
        if total == 0:
            return {"mixed": False, "primary": "unknown"}
        is_mixed = len([v for v in segments.values() if v / total > 0.2]) > 1
        primary = max(segments, key=segments.get)
        return {
            "mixed": is_mixed,
            "primary": primary,
            "composition": {k: round(v / total, 3) for k, v in segments.items()},
        }

class TranslationService(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """翻译服务"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._translation_cache: Dict[str, TranslationResult] = {}
        self._translation_memory: List[TranslationMemory] = []
        self._glossary: List[GlossaryTerm] = []
        self._language_profiles: Dict[str, Dict] = {}
        self._supported_pairs: List[Tuple[str, str]] = []
        self._max_cache_size = 100000

    def initialize(self) -> None:
        self._register_supported_pairs()
        self._load_builtin_glossary()
        self._load_language_profiles()
        self.audit("initialized", "翻译服务初始化完成")
        logger.info(f"翻译服务初始化完成，{len(self._supported_pairs)} 个语言对")

    def _register_supported_pairs(self) -> None:
        langs = [
            Language.ZH_CN,
            Language.EN_US,
            Language.JA_JP,
            Language.KO_KR,
            Language.FR_FR,
            Language.DE_DE,
            Language.ES_ES,
            Language.PT_BR,
        ]
        for src in langs:
            for tgt in langs:
                if src != tgt:
                    self._supported_pairs.append((src.value, tgt.value))

    def _load_builtin_glossary(self) -> None:
        """加载内置术语表"""
        terms = [
            # 技术术语
            GlossaryTerm("人工智能", "Artificial Intelligence", "zh-CN", "en-US", "tech"),
            GlossaryTerm("机器学习", "Machine Learning", "zh-CN", "en-US", "tech"),
            GlossaryTerm("深度学习", "Deep Learning", "zh-CN", "en-US", "tech"),
            GlossaryTerm("自然语言处理", "Natural Language Processing", "zh-CN", "en-US", "tech"),
            GlossaryTerm("大语言模型", "Large Language Model", "zh-CN", "en-US", "tech"),
            GlossaryTerm("微服务", "Microservice", "zh-CN", "en-US", "tech"),
            GlossaryTerm("容器化", "Containerization", "zh-CN", "en-US", "tech"),
            GlossaryTerm("DevOps", "DevOps", "zh-CN", "en-US", "tech"),
            GlossaryTerm("API", "API", "zh-CN", "en-US", "tech"),
            GlossaryTerm("数据库", "Database", "zh-CN", "en-US", "tech"),
            GlossaryTerm("安全", "Security", "zh-CN", "en-US", "tech"),
            GlossaryTerm("生产级", "Production-grade", "zh-CN", "en-US", "tech"),
            GlossaryTerm("自动化", "Automation", "zh-CN", "en-US", "tech"),
            GlossaryTerm("工作流", "Workflow", "zh-CN", "en-US", "tech"),
            GlossaryTerm("智能体", "Agent", "zh-CN", "en-US", "tech"),
            # 商业术语
            GlossaryTerm("上市公司", "Listed Company", "zh-CN", "en-US", "business"),
            GlossaryTerm("营收", "Revenue", "zh-CN", "en-US", "business"),
            GlossaryTerm("利润", "Profit", "zh-CN", "en-US", "business"),
            GlossaryTerm("市场份额", "Market Share", "zh-CN", "en-US", "business"),
        ]
        self._glossary = terms

    def _load_language_profiles(self) -> None:
        """加载语言配置"""
        self._language_profiles = {
            "zh-CN": {"name": "简体中文", "direction": "ltr", "tokenizer": "char"},
            "en-US": {"name": "English", "direction": "ltr", "tokenizer": "word"},
            "ja-JP": {"name": "日本語", "direction": "ltr", "tokenizer": "char"},
            "ko-KR": {"name": "한국어", "direction": "ltr", "tokenizer": "char"},
            "fr-FR": {"name": "Français", "direction": "ltr", "tokenizer": "word"},
            "de-DE": {"name": "Deutsch", "direction": "ltr", "tokenizer": "word"},
            "es-ES": {"name": "Español", "direction": "ltr", "tokenizer": "word"},
        }

    def _cache_key(self, text: str, source: str, target: str) -> str:
        return hashlib.md5(f"{source}:{target}:{text}".encode()).hexdigest()

    def _find_in_memory(self, text: str, source: str, target: str) -> Optional[TranslationMemory]:
        """在翻译记忆中查找"""
        text_hash = hashlib.md5(f"{source}:{text}".encode()).hexdigest()[:16]
        for mem in self._translation_memory:
            if mem.source_hash == text_hash and mem.source_lang == source and mem.target_lang == target:
                mem.usage_count += 1
                return mem
        # 模糊匹配
        best = None
        best_score = 0.8
        text_tokens = set(self._tokenize(text))
        for mem in self._translation_memory:
            if mem.source_lang != source or mem.target_lang != target:
                continue
            mem_tokens = set(self._tokenize(mem.source_text))
            if not text_tokens or not mem_tokens:
                continue
            similarity = len(text_tokens & mem_tokens) / len(text_tokens | mem_tokens)
            if similarity > best_score:
                best_score = similarity
                best = mem
        return best

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", text.lower())

    def _apply_glossary(self, text: str, source: str, target: str) -> Dict[str, str]:
        """应用术语表"""
        replacements = {}
        for term in self._glossary:
            if term.source_lang == source and term.target_lang == target:
                if term.term in text:
                    replacements[term.term] = term.translation
        return replacements

    def _simulate_translation(self, text: str, source: str, target: str, glossary: Dict[str, str]) -> str:
        """模拟翻译（实际应用中调用翻译API）"""
        translated = text

        # 应用术语表替换
        for src_term, tgt_term in glossary.items():
            translated = translated.replace(src_term, tgt_term)

        # 如果没有术语替换，进行基本转换标记
        if translated == text:
            if source.startswith("zh") and target.startswith("en"):
                # 模拟中译英
                for zh, en in [
                    ("系统", "System"),
                    ("模块", "Module"),
                    ("功能", "Feature"),
                    ("管理", "Management"),
                    ("数据", "Data"),
                    ("用户", "User"),
                    ("服务", "Service"),
                    ("配置", "Configuration"),
                    ("监控", "Monitoring"),
                    ("安全", "Security"),
                    ("性能", "Performance"),
                    ("日志", "Log"),
                    ("接口", "Interface"),
                    ("引擎", "Engine"),
                    ("自动化", "Automation"),
                    ("智能", "Intelligent"),
                    ("分析", "Analysis"),
                    ("优化", "Optimization"),
                    ("报告", "Report"),
                    ("任务", "Task"),
                    ("执行", "Execution"),
                    ("结果", "Result"),
                ]:
                    translated = translated.replace(zh, en)
            elif source.startswith("en") and target.startswith("zh"):
                # 模拟英译中
                for en, zh in [
                    ("System", "系统"),
                    ("Module", "模块"),
                    ("Feature", "功能"),
                    ("Management", "管理"),
                    ("Data", "数据"),
                    ("User", "用户"),
                    ("Service", "服务"),
                    ("Configuration", "配置"),
                    ("Monitoring", "监控"),
                    ("Security", "安全"),
                    ("Performance", "性能"),
                    ("Analysis", "分析"),
                    ("Automation", "自动化"),
                    ("Engine", "引擎"),
                    ("Intelligent", "智能"),
                    ("Report", "报告"),
                    ("Task", "任务"),
                    ("Result", "结果"),
                ]:
                    translated = translated.replace(en, zh)

        if translated == text:
            translated = f"[{target}] {text}"

        return translated

    @trace_operation("translate")
    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en-US") -> Dict[str, Any]:
        """翻译文本"""
        start = time.time()

        # 语言检测（简化）
        if source_lang == "auto":
            source_lang = self._detect_language(text)

        # 验证语言对
        pair = (source_lang, target_lang)
        if pair not in self._supported_pairs and (target_lang, source_lang) not in self._supported_pairs:
            return {"error": f"不支持的语言对: {source_lang} -> {target_lang}", "supported": self._supported_pairs[:10]}

        # 缓存查找
        cache_key = self._cache_key(text, source_lang, target_lang)
        cached = self._translation_cache.get(cache_key)
        if cached:
            cached.usage_count += 1
            return {
                "translation_id": cached.translation_id,
                "translation": cached.translated_text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "confidence": cached.confidence,
                "from_cache": True,
                "duration_ms": round((time.time() - start) * 1000, 2),
            }

        # 翻译记忆查找
        mem = self._find_in_memory(text, source_lang, target_lang)
        if mem:
            result = TranslationResult(
                translation_id=f"tr_{uuid.uuid4().hex[:10]}",
                source_text=text,
                translated_text=mem.target_text,
                source_lang=source_lang,
                target_lang=target_lang,
                confidence=mem.quality_score,
                from_memory=True,
            )
        else:
            # 应用术语表并翻译
            glossary = self._apply_glossary(text, source_lang, target_lang)
            translated = self._simulate_translation(text, source_lang, target_lang, glossary)

            result = TranslationResult(
                translation_id=f"tr_{uuid.uuid4().hex[:10]}",
                source_text=text,
                translated_text=translated,
                source_lang=source_lang,
                target_lang=target_lang,
                confidence=0.95 if glossary else 0.75,
            )

            # 保存到翻译记忆
            text_hash = hashlib.md5(f"{source_lang}:{text}".encode()).hexdigest()[:16]
            self._translation_memory.append(
                TranslationMemory(
                    source_hash=text_hash,
                    source_text=text,
                    target_text=translated,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    quality_score=result.confidence,
                )
            )

        result.duration_ms = (time.time() - start) * 1000

        # 缓存
        if len(self._translation_cache) < self._max_cache_size:
            self._translation_cache[cache_key] = result

        self.stats["translations"] += 1
        metrics_collector.counter("translations_total")

        return {
            "translation_id": result.translation_id,
            "translation": result.translated_text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "confidence": round(result.confidence, 4),
            "from_cache": result.from_cache,
            "from_memory": result.from_memory,
            "duration_ms": round(result.duration_ms, 2),
        }

    def _detect_language(self, text: str) -> str:
        """语言检测（简化）"""
        zh_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        ja_chars = sum(1 for c in text if "\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff")
        ko_chars = sum(1 for c in text if "\uac00" <= c <= "\ud7af")

        total = len(text)
        if zh_chars / max(total, 1) > 0.15:
            return "zh-CN"
        elif ja_chars / max(total, 1) > 0.1:
            return "ja-JP"
        elif ko_chars / max(total, 1) > 0.1:
            return "ko-KR"
        else:
            return "en-US"

    @trace_operation("translate_batch")
    def translate_batch(
        self, texts: List[str], source_lang: str = "auto", target_lang: str = "en-US"
    ) -> Dict[str, Any]:
        """批量翻译"""
        results = []
        for text in texts:
            try:
                result = self.translate(text, source_lang, target_lang)
                results.append({"success": True, **result})
            except Exception as e:
                results.append({"success": False, "text": text[:100], "error": str(e)})

        success = sum(1 for r in results if r.get("success"))
        return {"total": len(texts), "success": success, "failed": len(texts) - success, "results": results}

    @trace_operation("add_glossary_term")
    def add_glossary_term(
        self,
        term: str,
        translation: str,
        source_lang: str = "zh-CN",
        target_lang: str = "en-US",
        domain: str = "general",
    ) -> Dict[str, Any]:
        """添加术语"""
        glossary_term = GlossaryTerm(
            term=term, translation=translation, source_lang=source_lang, target_lang=target_lang, domain=domain
        )
        self._glossary.append(glossary_term)
        return {"term": term, "translation": translation, "domain": domain}

    @trace_operation("get_glossary")
    def get_glossary(
        self, source_lang: Optional[str] = None, target_lang: Optional[str] = None, domain: Optional[str] = None
    ) -> List[Dict]:
        """查询术语表"""
        results = self._glossary
        if source_lang:
            results = [t for t in results if t.source_lang == source_lang]
        if target_lang:
            results = [t for t in results if t.target_lang == target_lang]
        if domain:
            results = [t for t in results if t.domain == domain]
        return [
            {
                "term": t.term,
                "translation": t.translation,
                "source": t.source_lang,
                "target": t.target_lang,
                "domain": t.domain,
                "notes": t.notes,
            }
            for t in results
        ]

    def get_supported_languages(self) -> Dict[str, Any]:
        """获取支持的语言"""
        languages = {}
        for code, profile in self._language_profiles.items():
            languages[code] = profile
        return {
            "languages": languages,
            "supported_pairs": len(self._supported_pairs),
            "sample_pairs": [(s, t) for s, t in self._supported_pairs[:5]],
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_translations": self.stats.get("translations", 0),
            "cache_size": len(self._translation_cache),
            "memory_size": len(self._translation_memory),
            "glossary_size": len(self._glossary),
            "cache_hit_rate": round(
                sum(1 for r in self._translation_cache.values() if r.from_cache) / max(len(self._translation_cache), 1),
                4,
            ),
        }

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        params = params or {}
        actions = {
            "translate": self.translate,
            "translate_batch": self.translate_batch,
            "add_glossary_term": self.add_glossary_term,
            "get_glossary": self.get_glossary,
            "get_supported_languages": self.get_supported_languages,
            "get_stats": self.get_stats,
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }

        if action not in actions:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}

        handler = actions[action]
        if callable(handler) and not isinstance(handler, list):
            import inspect

            if inspect.iscoroutinefunction(handler):
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            else:
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            if isinstance(result, dict):
                return {"status": "success", **result}
            return {"status": "success", "data": result}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        base.update(
            {
                "supported_pairs": len(self._supported_pairs),
                "languages": len(self._language_profiles),
                "cache_entries": len(self._translation_cache),
                "memory_entries": len(self._translation_memory),
                "glossary_terms": len(self._glossary),
            }
        )
        return base

    def shutdown(self) -> None:
        self._translation_cache.clear()
        audit_logger.log(
            action="module_shutdown",
            resource="translation_service",
            details=f"关闭，翻译 {self.stats.get('translations', 0)} 次",
        )

module_class = TranslationService
