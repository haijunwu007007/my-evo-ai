"""
AUTO-EVO-AI V0.1 — NLP引擎
Grade: A (生产级) | Category: AI能力
职责：文本处理、实体识别、关键词提取、文本分类、相似度计算
"""

__module_meta__ = {
    "id": "nlp-engine",
    "name": "Nlp Engine",
    "version": "V0.1",
    "group": "ai",
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
    "tags": ["adapter", "nlp", "engine"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — NLP引擎 Grade: A (生产级) | Category: AI能力",
}

import os
import asyncio
import time
import uuid
import re
import math
import logging
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter, defaultdict

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
logger = logging.getLogger("nlp_engine")

class _MetricsAdapter:
    """轻量指标适配器"""
    def __init__(self):self._data={}
    def increment(self,name:str,value:float=1.0,**kw):self._data[name]=self._data.get(name,0)+value
    def histogram(self,name:str,value:float,**kw):self._data[name]=value
    def gauge(self,name:str,value:float,**kw):self._data[name]=value
    def snapshot(self):return dict(self._data)

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

class TextPreprocessing(Enum):
    LOWERCASE = "lowercase"
    REMOVE_PUNCT = "remove_punctuation"
    REMOVE_STOPWORDS = "remove_stopwords"
    STEM = "stem"
    NORMALIZE = "normalize"

@dataclass
class Entity:
    """实体"""

    text: str
    entity_type: str
    start: int
    end: int
    confidence: float = 1.0

@dataclass
class TextClassification:
    """文本分类结果"""

    label: str
    confidence: float
    probabilities: Dict[str, float] = field(default_factory=dict)

@dataclass
class NLPResult:
    """NLP处理结果"""

    task_id: str
    task_type: str
    input_text: str = ""
    result: Any = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class TextSimilarityEngine(object):
    """文本相似度引擎 — Jaccard相似度、余弦相似度、编辑距离、语义邻近度"""

    def __init__(self):
        self._corpus_vectors: Dict[str, List[float]] = {}

    def jaccard_similarity(self, text_a: str, text_b: str) -> Dict[str, Any]:
        """计算Jaccard相似度（基于词集合重叠）"""
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())
        if not tokens_a and not tokens_b:
            return {"similarity": 1.0, "shared_terms": 0}
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return {
            "similarity": round(len(intersection) / len(union), 4),
            "shared_terms": len(intersection),
            "unique_to_a": len(tokens_a - tokens_b),
            "unique_to_b": len(tokens_b - tokens_a),
        }

    def cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> Dict[str, Any]:
        """计算余弦相似度（基于TF向量）"""
        if len(vec_a) != len(vec_b):
            return {"error": "vector dimensions must match", "similarity": 0}
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return {"similarity": 0.0, "norm_a": norm_a, "norm_b": norm_b}
        return {"similarity": round(dot / (norm_a * norm_b), 6), "dot_product": round(dot, 4)}

    def levenshtein_distance(self, text_a: str, text_b: str) -> Dict[str, Any]:
        """计算Levenshtein编辑距离"""
        m, n = len(text_a), len(text_b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if text_a[i - 1] == text_b[j - 1] else 1
                dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
        max_len = max(m, n)
        normalized = 1 - dp[m][n] / max_len if max_len > 0 else 1.0
        return {"distance": dp[m][n], "normalized_similarity": round(normalized, 4), "length_a": m, "length_b": n}

    def ngram_overlap(self, text_a: str, text_b: str, n: int = 2) -> Dict[str, Any]:
        """计算N-gram重叠度"""

        def get_ngrams(text, n):
            words = text.lower().split()
            return set(tuple(words[i : i + n]) for i in range(len(words) - n + 1))

        ngrams_a = get_ngrams(text_a, n)
        ngrams_b = get_ngrams(text_b, n)
        if not ngrams_a and not ngrams_b:
            return {"overlap": 1.0, "n": n}
        intersection = ngrams_a & ngrams_b
        union = ngrams_a | ngrams_b
        return {"overlap": round(len(intersection) / len(union), 4), "shared_ngrams": len(intersection), "n": n}

    def batch_compare(self, query: str, candidates: List[str], method: str = "jaccard") -> List[Dict[str, Any]]:
        """批量比较查询文本与候选文本的相似度"""
        results = []
        for i, candidate in enumerate(candidates):
            if method == "jaccard":
                sim = self.jaccard_similarity(query, candidate)["similarity"]
            elif method == "levenshtein":
                sim = self.levenshtein_distance(query, candidate)["normalized_similarity"]
            elif method == "ngram":
                sim = self.ngram_overlap(query, candidate)["overlap"]
            else:
                sim = 0.0
            results.append({"rank": i + 1, "text": candidate[:80], "similarity": sim})
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results

class NLPEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """NLP引擎"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._stop_words: Set[str] = self._init_stopwords()
        self._models: Dict[str, Dict] = {}
        self._vocab: Dict[str, int] = defaultdict(int)
        self._idf_cache: Dict[str, float] = {}
        self._processing_log: List[Dict] = []

    def _init_stopwords(self) -> Set[str]:
        return {
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一个",
            "上",
            "也",
            "很",
            "到",
            "说",
            "要",
            "去",
            "你",
            "会",
            "着",
            "没有",
            "看",
            "好",
            "自己",
            "这",
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "shall",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "and",
            "but",
            "or",
            "not",
            "so",
            "if",
            "it",
            "its",
        }

    def initialize(self) -> None:
        self._load_builtin_models()
        logger.info("NLP引擎初始化完成")
        self.record_metrics("unknown.init", 1)
        self.audit("initialized", "Unknown初始化完成")

    def _load_builtin_models(self) -> None:
        """加载内置模型"""
        self._models["zh_ner"] = {
            "name": "中文实体识别",
            "language": "zh",
            "entity_patterns": [
                (r"[\u4e00-\u9fff]{2,4}(?:公司|集团|科技|技术|网络|信息|电子|软件|数据)", "ORG"),
                (r"[（(]([\u4e00-\u9fff]{2,4})[)）]", "PERSON"),
                (r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]", "DATE"),
                (r"[\u4e00-\u9fff]{2,6}(?:省|市|区|县|镇|乡|路|街|道|号|栋|层|室)", "LOCATION"),
                (r"[\u4e00-\u9fff]+(?:大学|学院|研究院|研究所|中心)", "ORG"),
                (r"(?:人民币|美元|欧元|日元|港币|英镑)\s*\d+[\d,.]*亿?万?", "MONEY"),
                (r"\b\d{1,3}(?:,\d{3})+\b", "NUMBER"),
                (r"https?://\S+", "URL"),
                (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL"),
                (r"\b1[3-9]\d{9}\b", "PHONE"),
            ],
        }
        self._models["zh_classifier"] = {
            "name": "文本分类",
            "language": "zh",
            "categories": {
                "技术": ["代码", "编程", "算法", "数据库", "API", "服务器", "部署", "框架"],
                "商业": ["市场", "营收", "利润", "客户", "合作", "战略", "投资", "上市"],
                "运维": ["监控", "告警", "日志", "性能", "可用性", "故障", "备份", "恢复"],
                "安全": ["漏洞", "加密", "认证", "权限", "攻击", "防护", "审计", "合规"],
            },
        }

    def _tokenize(self, text: str, language: str = "auto") -> List[str]:
        """分词"""
        if language == "auto":
            zh_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
            language = "zh" if zh_chars > len(text) * 0.3 else "en"

        if language == "zh":
            tokens = []
            for segment in re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", text):
                if re.match(r"[\u4e00-\u9fff]+", segment):
                    # 简单的中文分词（bigram + 单字）
                    if len(segment) <= 4:
                        tokens.append(segment)
                    else:
                        for i in range(len(segment) - 1):
                            tokens.append(segment[i : i + 2])
                        tokens.append(segment)
                else:
                    tokens.append(segment.lower())
            return [t for t in tokens if t not in self._stop_words and len(t) > 1]
        else:
            return [
                w.lower() for w in re.findall(r"[a-zA-Z0-9]+", text) if w.lower() not in self._stop_words and len(w) > 1
            ]

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """计算TF"""
        counts = Counter(tokens)
        total = len(tokens)
        return {t: c / max(total, 1) for t, c in counts.items()}

    def _compute_tfidf(self, tokens: List[str]) -> Dict[str, float]:
        """计算TF-IDF"""
        tf = self._compute_tf(tokens)
        unique_terms = set(tokens)
        total_docs = max(len(self._vocab), 1)

        tfidf = {}
        for term in unique_terms:
            self._vocab[term] += 1
            doc_freq = self._vocab[term]
            idf = math.log((total_docs + 1) / (doc_freq + 1)) + 1
            tfidf[term] = tf[term] * idf
        return tfidf

    def _cosine_similarity(self, v1: Dict[str, float], v2: Dict[str, float]) -> float:
        """余弦相似度"""
        common = set(v1.keys()) & set(v2.keys())
        if not common:
            return 0.0
        dot = sum(v1[k] * v2[k] for k in common)
        n1 = math.sqrt(sum(v * v for v in v1.values()))
        n2 = math.sqrt(sum(v * v for v in v2.values()))
        return dot / max(n1 * n2, 1e-10)

    @trace_operation("nlp_tokenize")
    def tokenize(self, text: str, language: str = "auto") -> Dict[str, Any]:
        """分词"""
        start = time.time()
        tokens = self._tokenize(text, language)
        return {
            "tokens": tokens,
            "count": len(tokens),
            "language": language,
            "duration_ms": round((time.time() - start) * 1000, 2),
        }

    @trace_operation("nlp_extract_keywords")
    def extract_keywords(self, text: str, top_k: int = 10, method: str = "tfidf") -> Dict[str, Any]:
        """提取关键词"""
        start = time.time()
        tokens = self._tokenize(text)

        if method == "tfidf":
            scores = self._compute_tfidf(tokens)
        elif method == "tf":
            scores = self._compute_tf(tokens)
        else:
            scores = self._compute_tfidf(tokens)

        sorted_keywords = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        self.stats["keywords_extracted"] += 1
        return {
            "keywords": [{"word": w, "score": round(s, 4)} for w, s in sorted_keywords],
            "method": method,
            "duration_ms": round((time.time() - start) * 1000, 2),
        }

    @trace_operation("nlp_ner")
    def extract_entities(self, text: str, model: str = "zh_ner") -> Dict[str, Any]:
        """实体识别"""
        start = time.time()
        model_data = self._models.get(model)
        if not model_data:
            raise ValueError(f"模型 {model} 不存在")

        entities = []
        for pattern, entity_type in model_data.get("entity_patterns", []):
            for match in re.finditer(pattern, text):
                entities.append(
                    Entity(
                        text=match.group(),
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.92,
                    )
                )

        # 去重
        seen = set()
        unique = []
        for e in entities:
            key = (e.text, e.start, e.entity_type)
            if key not in seen:
                seen.add(key)
                unique.append(e)

        entity_types = Counter(e.entity_type for e in unique)
        self.stats["entities_extracted"] += len(unique)

        return {
            "entities": [
                {
                    "text": e.text,
                    "type": e.entity_type,
                    "start": e.start,
                    "end": e.end,
                    "confidence": round(e.confidence, 2),
                }
                for e in unique
            ],
            "by_type": dict(entity_types),
            "total": len(unique),
            "duration_ms": round((time.time() - start) * 1000, 2),
        }

    @trace_operation("nlp_classify")
    def classify_text(self, text: str, model: str = "zh_classifier") -> Dict[str, Any]:
        """文本分类"""
        start = time.time()
        model_data = self._models.get(model)
        if not model_data:
            raise ValueError(f"模型 {model} 不存在")

        categories = model_data.get("categories", {})
        text_lower = text.lower()
        scores = {}

        for category, keywords in categories.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            scores[category] = matches / max(len(keywords), 1)

        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_label = sorted_cats[0][0] if sorted_cats else "unknown"
        top_confidence = sorted_cats[0][1] if sorted_cats else 0

        self.stats["texts_classified"] += 1
        return {
            "label": top_label,
            "confidence": round(top_confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in sorted_cats},
            "duration_ms": round((time.time() - start) * 1000, 2),
        }

    @trace_operation("nlp_similarity")
    def compute_similarity(self, text1: str, text2: str) -> Dict[str, Any]:
        """计算文本相似度"""
        start = time.time()
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        tfidf1 = self._compute_tfidf(tokens1)
        tfidf2 = self._compute_tfidf(tokens2)
        similarity = self._cosine_similarity(tfidf1, tfidf2)

        # Jaccard相似度
        set1 = set(tokens1)
        set2 = set(tokens2)
        jaccard = len(set1 & set2) / max(len(set1 | set2), 1)

        return {
            "cosine_similarity": round(similarity, 4),
            "jaccard_similarity": round(jaccard, 4),
            "shared_terms": list(set1 & set2)[:20],
            "duration_ms": round((time.time() - start) * 1000, 2),
        }

    @trace_operation("nlp_summarize")
    def summarize(self, text: str, max_sentences: int = 3) -> Dict[str, Any]:
        """文本摘要（抽取式）"""
        start = time.time()
        sentences = re.split(r"[。！？\n]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= max_sentences:
            summary = "".join(sentences)
        else:
            # 基于TF-IDF的句子排序
            tokens = self._tokenize(text)
            tfidf = self._compute_tfidf(tokens)

            sentence_scores = []
            for i, sent in enumerate(sentences):
                sent_tokens = set(self._tokenize(sent))
                score = sum(tfidf.get(t, 0) for t in sent_tokens)
                # 位置权重：首句和尾句加分
                if i == 0:
                    score *= 1.2
                elif i == len(sentences) - 1:
                    score *= 1.1
                sentence_scores.append((i, score, sent))

            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            top_sentences = sorted(sentence_scores[:max_sentences], key=lambda x: x[0])
            summary = "。".join(s[2] for s in top_sentences) + "。"

        return {
            "summary": summary,
            "original_sentences": len(sentences),
            "summary_sentences": min(len(sentences), max_sentences),
            "compression_ratio": round(len(summary) / max(len(text), 1), 4),
            "duration_ms": round((time.time() - start) * 1000, 2),
        }

    @trace_operation("nlp_batch_process")
    def batch_process(self, texts: List[str], task: str = "keywords") -> List[Dict]:
        """批量处理"""
        results = []
        handlers = {
            "keywords": lambda t: self.extract_keywords(t),
            "entities": lambda t: self.extract_entities(t),
            "classify": lambda t: self.classify_text(t),
            "tokenize": lambda t: self.tokenize(t),
            "summarize": lambda t: self.summarize(t),
        }
        handler = handlers.get(task)
        if not handler:
            raise ValueError(f"不支持的任务: {task}")

        for text in texts:
            try:
                result = handler(text)
                results.append({"success": True, **result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        return results

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        metrics_collector.counter("nlp_engine_ops_total", labels={"action": action})
        params = params or {}
        actions = {
            "tokenize": self.tokenize,
            "extract_keywords": self.extract_keywords,
            "extract_entities": self.extract_entities,
            "classify_text": self.classify_text,
            "compute_similarity": self.compute_similarity,
            "summarize": self.summarize,
            "batch_process": self.batch_process,
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
                "models_loaded": len(self._models),
                "vocab_size": len(self._vocab),
                "processing_log": len(self._processing_log),
            }
        )
        return base

    def shutdown(self) -> None:
        audit_logger.log(action="module_shutdown", resource="nlp_engine", details=f"关闭，词汇量: {len(self._vocab)}")

    def batch_tokenize(self, texts: List[str]) -> List[Dict[str, Any]]:
        """批量分词：统计token数量、字符比、平均token长度"""
        results = []
        for text in texts:
            tokens = text.lower().split()
            token_len = len(tokens)
            char_len = len(text)
            avg_tok_len = sum(len(t) for t in tokens) / max(token_len, 1)
            results.append(
                {
                    "token_count": token_len,
                    "char_count": char_len,
                    "avg_token_length": round(avg_tok_len, 1),
                    "token_char_ratio": round(token_len / max(char_len, 1), 3),
                }
            )
        return results

module_class = NLPEngine
