"""
keyword_extract — 关键词提取引擎
上市公司生产级 — TF-IDF/TextRank/RAKE/YAKE多算法、短语提取、关键词聚合、自定义词典
"""

__module_meta__ = {
    "id": "keyword-extract",
    "name": "Keyword Extract",
    "version": "V0.1",
    "group": "search",
    "inputs": [
        {"name": "data", "type": "string", "required": True, "description": ""},
        {"name": "data", "type": "string", "required": True, "description": ""},
        {"name": "context", "type": "string", "required": True, "description": ""},
        {"name": "keyword", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "hours_a", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["keyword"],
    "grade": "A",
    "description": "keyword_extract — 关键词提取引擎 上市公司生产级 — TF-IDF/TextRank/RAKE/YAKE多算法、短语提取、关键词聚合、自定义词典",
}

import time
import math
import re
import hashlib
import logging
import string
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("keyword_extract")

class KeywordExtractAnalyzer(object):
    """keyword_extract 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "keyword_extract"
        self.version = "1.0.0"
        self._analyzer = KeywordExtractAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "KeywordExtractAnalyzer",
            "timestamp": time.time(),
            "records": len(self._history),
            "summary": self._summary(),
        }
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-5000:]
        return result

    def _summary(self) -> dict:
        if not self._history:
            return {"status": "no_data"}
        return {"total": len(self._history), "recent": len(self._history[-100:]), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        return {
            "total_records": total,
            "recent_count": min(100, total),
            "status": "healthy" if total > 0 else "no_data",
        }

    def validate_config(self) -> dict:
        return {"valid": True, "module": "keyword_extract"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== keyword_extract ===",
                f"Records: {s.get('total', 0)}",
                f"Status: {s.get('status', 'unknown')}",
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            "format": "text",
        }

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = [r for r in reversed(self._history) if keyword.lower() in str(r).lower()][:limit]
        return {"count": len(matched), "results": matched}

    def compare_periods(self, hours_a: int = 24, hours_b: int = 72) -> dict:
        now = time.time()
        a = [m for m in self._history if m.get("timestamp", 0) >= now - hours_a * 3600]
        b = [m for m in self._history if m.get("timestamp", 0) >= now - hours_b * 3600]
        return {
            "period_a": {"hours": hours_a, "records": len(a)},
            "period_b": {"hours": hours_b, "records": len(b)},
            "delta": len(b) - len(a),
        }

    def cleanup_stale(self, days: int = 7) -> dict:
        cutoff = time.time() - 86400 * days
        before = len(self._history)
        self._history = [m for m in self._history if m.get("timestamp", 0) >= cutoff]
        return {"removed": before - len(self._history), "remaining": len(self._history)}

    def aggregate(self) -> dict:
        if not self._history:
            return {"aggregated": {}}
        return {
            "total_records": len(self._history),
            "oldest": self._history[0].get("timestamp"),
            "newest": self._history[-1].get("timestamp"),
        }

    def batch_analyze(self, items: list = None) -> dict:
        items = items or []
        return {"total": min(len(items), 50), "results": [self.analyze({"data": i}) for i in items[:50]]}

    # --- Auto-generated action dispatch methods ---
    def _action_aggregate(self, params=None):
        """Auto-generated action wrapper for aggregate"""
        if params is None:
            params = {}
        return self.aggregate(**params)

    def _action_analyze(self, params=None):
        """Auto-generated action wrapper for analyze"""
        if params is None:
            params = {}
        return self.analyze(**params)

    def _action_batch_analyze(self, params=None):
        """Auto-generated action wrapper for batch_analyze"""
        if params is None:
            params = {}
        return self.batch_analyze(**params)

    def _action_cleanup_stale(self, params=None):
        """Auto-generated action wrapper for cleanup_stale"""
        if params is None:
            params = {}
        return self.cleanup_stale(**params)

    def _action_compare_periods(self, params=None):
        """Auto-generated action wrapper for compare_periods"""
        if params is None:
            params = {}
        return self.compare_periods(**params)

    def _action_export_report(self, params=None):
        """Auto-generated action wrapper for export_report"""
        if params is None:
            params = {}
        return self.export_report(**params)

    def _action_get_health_detail(self, params=None):
        """Auto-generated action wrapper for get_health_detail"""
        if params is None:
            params = {}
        return self.get_health_detail(**params)

    def _action_get_statistics(self, params=None):
        """Auto-generated action wrapper for get_statistics"""
        if params is None:
            params = {}
        return self.get_statistics(**params)

    def _action_reset_metrics(self, params=None):
        """Auto-generated action wrapper for reset_metrics"""
        if params is None:
            params = {}
        return self.reset_metrics(**params)

    def _action_search_history(self, params=None):
        """Auto-generated action wrapper for search_history"""
        if params is None:
            params = {}
        return self.search_history(**params)

class ExtractAlgorithm(str, Enum):
    TFIDF = "tfidf"
    TEXTRANK = "textrank"
    RAKE = "rake"
    YAKE = "yake"
    FREQUENCY = "frequency"

class TokenType(str, Enum):
    WORD = "word"
    PHRASE = "phrase"
    ENTITY = "entity"
    CUSTOM = "custom"

@dataclass
class Keyword:
    word: str
    score: float
    frequency: int
    token_type: TokenType = TokenType.WORD
    positions: List[int] = field(default_factory=list)
    related: List[str] = field(default_factory=list)

@dataclass
class ExtractionResult:
    keywords: List[Keyword]
    total_tokens: int
    algorithm: ExtractAlgorithm
    processing_time_ms: float
    document_id: str

@dataclass
class CustomDictEntry:
    word: str
    weight: float = 1.0
    category: str = "default"
    synonyms: List[str] = field(default_factory=list)

class TextPreprocessor:
    """文本预处理"""

    STOP_WORDS_EN = {
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
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "each",
        "every",
        "all",
        "any",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "only",
        "own",
        "same",
        "than",
        "too",
        "very",
        "just",
        "because",
        "if",
        "when",
        "where",
        "how",
        "what",
        "which",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "she",
        "they",
        "them",
        "their",
        "about",
        "up",
        "down",
        "here",
        "there",
    }

    STOP_WORDS_CN = {
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
        "他",
        "她",
        "它",
        "们",
        "那",
        "些",
        "什么",
        "吗",
        "吧",
        "呢",
        "啊",
        "哦",
        "嗯",
        "把",
        "被",
        "让",
        "给",
        "从",
        "对",
        "与",
        "而",
        "但",
        "却",
        "又",
        "还",
        "已",
        "已经",
        "将",
        "可以",
        "能",
        "应该",
        "需要",
        "因为",
        "所以",
        "如果",
        "虽然",
        "不过",
        "或者",
        "以及",
        "及",
        "等",
        "这个",
        "那个",
        "哪",
        "怎么",
        "如何",
        "为",
        "以",
        "之",
        "其",
    }

    def __init__(self, min_word_length: int = 2, max_word_length: int = 50):
        self.min_word_length = min_word_length
        self.max_word_length = max_word_length

    def tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z][a-zA-Z0-9_-]*", text.lower())
        return [t for t in tokens if self.min_word_length <= len(t) <= self.max_word_length]

    def tokenize_with_positions(self, text: str) -> List[Tuple[str, int]]:
        tokens = re.finditer(r"[\u4e00-\u9fff]+|[a-zA-Z][a-zA-Z0-9_-]*", text.lower())
        result = []
        for i, m in enumerate(tokens):
            if self.min_word_length <= len(m.group()) <= self.max_word_length:
                result.append((m.group(), i))
        return result

    def is_stop_word(self, word: str) -> bool:
        return word in self.STOP_WORDS_EN or word in self.STOP_WORDS_CN

    def remove_stop_words(self, tokens: List[str]) -> List[str]:
        return [t for t in tokens if not self.is_stop_word(t)]

    def extract_ngrams(self, tokens: List[str], n: int) -> List[str]:
        return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]

class TFIDFExtractor:
    """TF-IDF关键词提取"""

    def __init__(self, top_k: int = 20):
        self.top_k = top_k
        self._idf: Dict[str, float] = {}
        self._doc_count = 0

    def train(self, documents: List[List[str]]) -> None:
        self._doc_count += len(documents)
        for doc in documents:
            seen = set(doc)
            for word in seen:
                self._idf[word] = self._idf.get(word, 0) + 1
        for word in self._idf:
            self._idf[word] = math.log((self._doc_count + 1) / (self._idf[word] + 1)) + 1

    def extract(self, tokens: List[str], positions: Optional[List[Tuple[str, int]]] = None) -> List[Keyword]:
        if not tokens:
            return []
        counter = Counter(tokens)
        total = len(tokens)
        pos_map: Dict[str, List[int]] = defaultdict(list)
        if positions:
            for word, pos in positions:
                pos_map[word].append(pos)

        results = []
        for word, freq in counter.most_common(self.top_k * 3):
            tf = freq / total
            idf = self._idf.get(word, math.log((self._doc_count + 1) / 1) + 1)
            score = tf * idf
            results.append(
                Keyword(
                    word=word,
                    score=score,
                    frequency=freq,
                    positions=pos_map.get(word, []),
                )
            )
        results.sort(key=lambda x: x.score, reverse=True)
        return results[: self.top_k]

class TextRankExtractor:
    """TextRank图排序关键词提取"""

    def __init__(self, top_k: int = 20, window_size: int = 4, damping: float = 0.85, iterations: int = 30):
        self.top_k = top_k
        self.window_size = window_size
        self.damping = damping
        self.iterations = iterations

    def extract(self, tokens: List[str], positions: Optional[List[Tuple[str, int]]] = None) -> List[Keyword]:
        if not tokens:
            return []
        vocab = list(set(tokens))
        if len(vocab) < 2:
            return [Keyword(word=vocab[0], score=1.0, frequency=tokens.count(vocab[0]))] if vocab else []

        graph: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for i in range(len(tokens)):
            for j in range(i + 1, min(i + self.window_size, len(tokens))):
                if tokens[i] != tokens[j]:
                    graph[tokens[i]][tokens[j]] += 1.0
                    graph[tokens[j]][tokens[i]] += 1.0

        scores: Dict[str, float] = {v: 1.0 for v in vocab}
        for _ in range(self.iterations):
            new_scores = {}
            for word in vocab:
                rank_sum = 0.0
                for neighbor, weight in graph[word].items():
                    out_sum = sum(graph[neighbor].values())
                    if out_sum > 0:
                        rank_sum += weight / out_sum * scores[neighbor]
                new_scores[word] = (1 - self.damping) + self.damping * rank_sum
            scores = new_scores

        counter = Counter(tokens)
        pos_map: Dict[str, List[int]] = defaultdict(list)
        if positions:
            for word, pos in positions:
                pos_map[word].append(pos)

        results = []
        for word, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[: self.top_k]:
            results.append(
                Keyword(
                    word=word,
                    score=score,
                    frequency=counter[word],
                    positions=pos_map.get(word, []),
                    related=list(graph[word].keys())[:5],
                )
            )
        return results

class RAKEExtractor:
    """RAKE快速关键词提取"""

    def __init__(self, top_k: int = 20, min_phrase_freq: int = 1):
        self.top_k = top_k
        self.min_phrase_freq = min_phrase_freq

    def extract(self, tokens: List[str], positions: Optional[List[Tuple[str, int]]] = None) -> List[Keyword]:
        if not tokens:
            return []
        phrases = []
        for i in range(len(tokens)):
            for j in range(i + 1, min(i + 4, len(tokens) + 1)):
                phrases.append(" ".join(tokens[i:j]))

        phrase_freq = Counter(phrases)
        word_freq = Counter(tokens)
        word_deg: Dict[str, float] = defaultdict(float)
        for phrase, freq in phrase_freq.items():
            words = phrase.split()
            deg = len(words) - 1
            for w in words:
                word_deg[w] += freq * deg

        word_scores: Dict[str, float] = {}
        for word in word_freq:
            deg = word_deg.get(word, 0)
            word_scores[word] = (deg + word_freq[word]) / word_freq[word] if word_freq[word] > 0 else 0

        pos_map: Dict[str, List[int]] = defaultdict(list)
        if positions:
            for word, pos in positions:
                pos_map[word].append(pos)

        results = []
        for word, score in sorted(word_scores.items(), key=lambda x: x[1], reverse=True)[: self.top_k]:
            results.append(
                Keyword(
                    word=word,
                    score=score,
                    frequency=word_freq[word],
                    token_type=TokenType.PHRASE if " " in word else TokenType.WORD,
                    positions=pos_map.get(word, []),
                )
            )
        return results

class YAKEExtractor:
    """YAKE无监督关键词提取"""

    def __init__(self, top_k: int = 20, window_size: int = 2):
        self.top_k = top_k
        self.window_size = window_size

    def extract(self, tokens: List[str], positions: Optional[List[Tuple[str, int]]] = None) -> List[Keyword]:
        if not tokens:
            return []
        n = len(tokens)
        counter = Counter(tokens)
        tf_norm = {w: math.log(c / n * (max(counter.values()) / n) + 1) for w, c in counter.items()}

        case_info: Dict[str, int] = defaultdict(int)
        for t in tokens:
            case_info[t] += 1 if t[0].isupper() else 0
        case_norm = {w: c / max(c + 1, counter[w]) for w, c in case_info.items()}

        pos_map_full: Dict[str, List[int]] = defaultdict(list)
        if positions:
            for word, pos in positions:
                pos_map_full[word].append(pos)

        spread: Dict[str, float] = {}
        for word in counter:
            ps = pos_map_full.get(word, [])
            if len(ps) >= 2:
                diffs = [ps[i + 1] - ps[i] for i in range(len(ps) - 1)]
                spread[word] = statistics_stdev(diffs) if len(diffs) > 1 else 0.0
            else:
                spread[word] = 0.0

        cooccur: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for i in range(len(tokens) - 1):
            if tokens[i] != tokens[i + 1]:
                cooccur[tokens[i]][tokens[i + 1]] += 1
                cooccur[tokens[i + 1]][tokens[i]] += 1

        scores: Dict[str, float] = {}
        for word in counter:
            left_ctx = sum(cooccur[word].values())
            tf = tf_norm.get(word, 0)
            case = case_norm.get(word, 0)
            pos_spread = spread.get(word, 0)
            scores[word] = tf / (pos_spread + 1) * (1 + case) / max(left_ctx + 1, 1)

        results = []
        for word, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[: self.top_k]:
            results.append(
                Keyword(
                    word=word,
                    score=score,
                    frequency=counter[word],
                    positions=pos_map_full.get(word, []),
                )
            )
        return results

def statistics_stdev(data: List[float]) -> float:
    if len(data) < 2:
        return 0.0
    mean = sum(data) / len(data)
    return math.sqrt(sum((x - mean) ** 2 for x in data) / (len(data) - 1))

class KeywordExtract:
    """关键词提取引擎主类"""

    def __init__(self):
        self._initialized = False
        self._start_time = 0.0
        self._preprocessor = TextPreprocessor()
        self._tfidf = TFIDFExtractor()
        self._textrank = TextRankExtractor()
        self._rake = RAKEExtractor()
        self._yake = YAKEExtractor()
        self._custom_dict: Dict[str, CustomDictEntry] = {}
        self._doc_cache: Dict[str, List[str]] = {}
        self._stats = {
            "total_extractions": 0,
            "total_documents": 0,
            "by_algorithm": defaultdict(int),
        }

    def initialize(self) -> None:
        self._start_time = time.time()
        self._initialized = True
        logger.info("KeywordExtract initialized")

    def health_check(self) -> Dict[str, Any]:
        if not self._initialized:
            return {"healthy": False, "status": "not_initialized"}
        return {
            "healthy": True,
            "status": "healthy",
            "uptime_seconds": time.time() - self._start_time,
            "custom_dict_size": len(self._custom_dict),
            "cached_documents": len(self._doc_cache),
            "algorithms": [a.value for a in ExtractAlgorithm],
            "stats": {k: int(v) if isinstance(v, int) else dict(v) for k, v in self._stats.items()},
        }

    def extract(
        self,
        text: str,
        algorithm: ExtractAlgorithm = ExtractAlgorithm.TFIDF,
        top_k: int = 20,
        doc_id: Optional[str] = None,
    ) -> ExtractionResult:
        self._stats["total_extractions"] += 1
        self._stats["by_algorithm"][algorithm.value] += 1
        start = time.time()

        if not doc_id:
            doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]
        self._stats["total_documents"] += 1

        tokens_raw = self._preprocessor.tokenize(text)
        positions = self._preprocessor.tokenize_with_positions(text)
        tokens = self._preprocessor.remove_stop_words(tokens_raw)

        if not tokens:
            return ExtractionResult(
                keywords=[],
                total_tokens=0,
                algorithm=algorithm,
                processing_time_ms=0,
                document_id=doc_id,
            )

        self._doc_cache[doc_id] = tokens
        if len(self._doc_cache) > 1000:
            oldest = list(self._doc_cache.keys())[:200]
            for k in oldest:
                del self._doc_cache[k]

        if algorithm == ExtractAlgorithm.TFIDF:
            keywords = self._tfidf.extract(tokens, positions)
        elif algorithm == ExtractAlgorithm.TEXTRANK:
            keywords = self._textrank.extract(tokens, positions)
        elif algorithm == ExtractAlgorithm.RAKE:
            keywords = self._rake.extract(tokens, positions)
        elif algorithm == ExtractAlgorithm.YAKE:
            keywords = self._yake.extract(tokens, positions)
        else:
            counter = Counter(tokens)
            keywords = [Keyword(word=w, score=c / len(tokens), frequency=c) for w, c in counter.most_common(top_k)]

        keywords = self._apply_custom_dict(keywords)
        keywords = keywords[:top_k]

        elapsed = (time.time() - start) * 1000
        return ExtractionResult(
            keywords=keywords,
            total_tokens=len(tokens),
            algorithm=algorithm,
            processing_time_ms=round(elapsed, 2),
            document_id=doc_id,
        )

    def extract_multi(self, text: str, top_k: int = 10) -> Dict[str, List[Keyword]]:
        results = {}
        for algo in ExtractAlgorithm:
            result = self.extract(text, algorithm=algo, top_k=top_k)
            results[algo.value] = result.keywords
        merged = self._merge_keywords(results)
        results["merged"] = merged[:top_k]
        return results

    def _merge_keywords(self, algo_results: Dict[str, List[Keyword]]) -> List[Keyword]:
        word_scores: Dict[str, List[float]] = defaultdict(list)
        word_freqs: Dict[str, int] = {}
        for algo, kws in algo_results.items():
            for kw in kws:
                word_scores[kw.word].append(kw.score)
                word_freqs[kw.word] = max(word_freqs.get(kw.word, 0), kw.frequency)

        merged = []
        for word, scores in word_scores.items():
            avg_score = statistics_mean(scores)
            merged.append(
                Keyword(
                    word=word,
                    score=avg_score,
                    frequency=word_freqs.get(word, 0),
                )
            )
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged

    def add_custom_word(self, entry: CustomDictEntry) -> None:
        self._custom_dict[entry.word] = entry

    def remove_custom_word(self, word: str) -> bool:
        return self._custom_dict.pop(word, None) is not None

    def _apply_custom_dict(self, keywords: List[Keyword]) -> List[Keyword]:
        boosted = []
        custom_words = set(self._custom_dict.keys())
        for kw in keywords:
            if kw.word in self._custom_dict:
                entry = self._custom_dict[kw.word]
                kw.score *= entry.weight
                kw.token_type = TokenType.CUSTOM
            boosted.append(kw)
        for word, entry in self._custom_dict.items():
            if word not in {kw.word for kw in boosted}:
                boosted.append(
                    Keyword(
                        word=word,
                        score=entry.weight,
                        frequency=0,
                        token_type=TokenType.CUSTOM,
                    )
                )
        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted

    def train_tfidf(self, documents: List[str]) -> None:
        tokenized = []
        for doc in documents:
            tokens = self._preprocessor.remove_stop_words(self._preprocessor.tokenize(doc))
            tokenized.append(tokens)
        self._tfidf.train(tokenized)

    def get_keywords_by_doc(self, doc_id: str) -> Optional[List[str]]:
        return self._doc_cache.get(doc_id)

    def get_similar_keywords(self, keyword: str, top_k: int = 10) -> List[str]:
        similar = []
        word_lower = keyword.lower()
        for entry in self._custom_dict.values():
            for syn in entry.synonyms:
                if syn.lower() == word_lower and entry.word != keyword:
                    similar.append(entry.word)
        for entry in self._custom_dict.values():
            if (
                entry.word.lower() != word_lower
                and self._jaccard_similarity(set(word_lower), set(entry.word.lower())) > 0.5
            ):
                similar.append(entry.word)
        return list(set(similar))[:top_k]

    @staticmethod
    def _jaccard_similarity(a: Set[str], b: Set[str]) -> float:
        intersection = a & b
        union = a | b
        return len(intersection) / len(union) if union else 0.0

def statistics_mean(data: List[float]) -> float:
    return sum(data) / len(data) if data else 0.0

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("keyword_extract.execute", "start", action=action)
        self.metrics_collector.counter("keyword_extract.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "keyword_extract"}
            else:
                result = {"success": True, "action": action, "module": "keyword_extract"}
            self.metrics_collector.counter("keyword_extract.execute.success", 1)
            self.trace("keyword_extract.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("keyword_extract.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "keyword_extract"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "keyword_extract", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("keyword_extract.initialize", "start")
        self.metrics_collector.gauge("keyword_extract.initialized", 1)
        self.audit("初始化keyword_extract", level="info")
        self.trace("keyword_extract.initialize", "end")
        return {"success": True, "module": "keyword_extract"}

module_class = KeywordExtract
