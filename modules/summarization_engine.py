"""
AUTO-EVO-AI V0.1 — 摘要生成引擎
Grade: A (生产级) | Category: AI能力
职责：文本摘要、多文档摘要、关键信息提取、摘要质量评估
"""

__module_meta__ = {
    "id": "summarization-engine",
    "name": "Summarization Engine",
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
    "tags": ["summarization", "engine", "adapter"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — 摘要生成引擎 Grade: A (生产级) | Category: AI能力",
}

import os
import asyncio
import time
import uuid
import re
import math
import logging
from _zhipu_helper import llm_chat  # LLM fallback
from typing import Any, Dict, List, Optional, Tuple
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
logger = logging.getLogger("summarization_engine")

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

class SummaryType(Enum):
    EXTRACTIVE = "extractive"  # 抽取式
    ABSTRACTIVE = "abstractive"  # 生成式
    HEADLINE = "headline"  # 标题式
    BULLET = "bullet"  # 要点式
    KEY_POINTS = "key_points"  # 关键点

class SummaryLength(Enum):
    SHORT = "short"  # ~50 words
    MEDIUM = "medium"  # ~150 words
    LONG = "long"  # ~300 words
    CUSTOM = "custom"

@dataclass
class SummaryResult:
    """摘要结果"""

    summary_id: str
    summary: str
    summary_type: SummaryType
    original_length: int
    summary_length: int
    compression_ratio: float
    score: float = 0.0
    key_sentences: List[str] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

class KeywordExtractor:
    """关键词提取引擎 — 基于TF-IDF + TextRank算法提取文本关键词"""

    def __init__(self):
        self._window_size = 4  # TextRank共现窗口大小

    def extract_tfidf_keywords(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """基于TF-IDF提取关键词"""
        tokens = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", text.lower())
        if not tokens:
            return []
        total = len(tokens)
        tf_counts: Dict[str, int] = {}
        for t in tokens:
            tf_counts[t] = tf_counts.get(t, 0) + 1
        # 模拟IDF: 文本越长，词的权重越高（单文档近似）
        keywords = []
        for word, count in tf_counts.items():
            tf = count / total
            idf = math.log(total / max(count, 1) + 1)
            score = tf * idf
            keywords.append({"word": word, "score": round(score, 4), "frequency": count})
        keywords.sort(key=lambda x: x["score"], reverse=True)
        return keywords[:top_k]

    def extract_textrank_keywords(
        self, text: str, top_k: int = 10, damping: float = 0.85, iterations: int = 30
    ) -> List[Dict[str, Any]]:
        """基于TextRank图算法提取关键词"""
        tokens = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", text.lower())
        if not tokens:
            return []
        # 构建共现图
        graph: Dict[str, Dict[str, float]] = {}
        for i, word in enumerate(tokens):
            if word not in graph:
                graph[word] = {}
            for j in range(max(0, i - self._window_size), min(len(tokens), i + self._window_size + 1)):
                if i != j:
                    neighbor = tokens[j]
                    if neighbor != word:
                        graph[word][neighbor] = graph[word].get(neighbor, 0) + 1
        # 初始化分数
        scores: Dict[str, float] = {w: 1.0 for w in graph}
        # 迭代
        for _ in range(iterations):
            new_scores: Dict[str, float] = {}
            for word in graph:
                rank_sum = 0.0
                for neighbor, weight in graph[word].items():
                    neighbor_total = sum(graph[neighbor].values())
                    if neighbor_total > 0:
                        rank_sum += (weight / neighbor_total) * scores[neighbor]
                new_scores[word] = (1 - damping) + damping * rank_sum
            scores = new_scores
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [{"word": w, "score": round(s, 4)} for w, s in ranked]

class SummaryComparator:
    """摘要对比分析器 — 比较不同摘要质量、相似度、信息保留率"""

    def compare_summaries(self, summary_a: str, summary_b: str, original: str = "") -> Dict[str, Any]:
        """对比两个摘要的质量差异"""
        tokens_a = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", summary_a.lower()))
        tokens_b = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", summary_b.lower()))
        if not tokens_a or not tokens_b:
            return {"similarity": 0, "unique_to_a": 0, "unique_to_b": 0}
        # Jaccard相似度
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / max(len(union), 1)
        result = {
            "jaccard_similarity": round(jaccard, 4),
            "shared_terms": len(intersection),
            "unique_to_a": len(tokens_a - tokens_b),
            "unique_to_b": len(tokens_b - tokens_a),
            "length_a": len(summary_a),
            "length_b": len(summary_b),
        }
        if original:
            orig_tokens = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", original.lower()))
            result["coverage_a"] = round(len(tokens_a & orig_tokens) / max(len(orig_tokens), 1), 4)
            result["coverage_b"] = round(len(tokens_b & orig_tokens) / max(len(orig_tokens), 1), 4)
            result["recommended"] = "a" if result["coverage_a"] > result["coverage_b"] else "b"
        return result

    def detect_information_loss(self, original: str, summary: str) -> Dict[str, Any]:
        """检测摘要中丢失的重要信息"""
        orig_tokens = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", original.lower()))
        summ_tokens = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", summary.lower()))
        lost = orig_tokens - summ_tokens
        # 按词频排序（高频词丢失更严重）
        freq: Dict[str, int] = {}
        for t in re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", original.lower()):
            freq[t] = freq.get(t, 0) + 1
        lost_sorted = sorted(lost, key=lambda x: freq.get(x, 0), reverse=True)
        retention_rate = len(summ_tokens & orig_tokens) / max(len(orig_tokens), 1)
        return {
            "retention_rate": round(retention_rate, 4),
            "lost_terms_count": len(lost),
            "lost_terms_top": lost_sorted[:10],
            "severity": "low" if retention_rate > 0.8 else "medium" if retention_rate > 0.5 else "high",
        }

class SummarizationEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """摘要生成引擎"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._stop_words: set = {
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
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "to",
            "of",
            "in",
            "and",
            "or",
            "but",
            "for",
            "on",
            "with",
            "as",
            "at",
            "by",
            "from",
        }
        self._summary_history: List[Dict] = []
        self._keyword_extractor = KeywordExtractor()
        self._summary_comparator = SummaryComparator()

    def initialize(self) -> None:
        logger.info("摘要生成引擎初始化完成")
        self.record_metrics("unknown.init", 1)
        self.audit("initialized", "Unknown初始化完成")

    def _split_sentences(self, text: str) -> List[str]:
        """分句"""
        sentences = re.split(r"[。！？\n.!?]+", text)
        return [s.strip() for s in sentences if len(s.strip()) > 5]

    def _split_paragraphs(self, text: str) -> List[str]:
        """分段"""
        paragraphs = re.split(r"\n{2,}|\r\n{2,}", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", text.lower())
        return [t for t in tokens if t not in self._stop_words and len(t) > 1]

    def _compute_sentence_score(self, sentence: str, all_tokens: List[str], position: int, total: int) -> float:
        """计算句子重要性分数"""
        tokens = set(self._tokenize(sentence))
        if not tokens:
            return 0.0

        # TF: 词在当前句中的频率
        tf = sum(1 for t in tokens for _ in range(sentence.lower().count(t)))
        tf = tf / max(len(tokens), 1)

        # IDF: 词在文档中的独特性
        doc_freq = sum(1 for t in tokens if t in all_tokens)
        idf = math.log(len(all_tokens) / max(doc_freq, 1) + 1)

        # 位置权重
        position_weight = 1.0
        if position == 0:
            position_weight = 1.3
        elif position == 1:
            position_weight = 1.1
        elif position == total - 1:
            position_weight = 1.05

        # 长度权重：适中的句子得分更高
        length = len(sentence)
        length_weight = min(length / 50, 1.0) * min(100 / max(length, 1), 1.0)

        return tf * idf * position_weight * length_weight

    @trace_operation("summarize")
    def summarize(
        self,
        text: str,
        summary_type: SummaryType = SummaryType.EXTRACTIVE,
        max_length: SummaryLength = SummaryLength.MEDIUM,
        custom_max_sentences: int = 0,
    ) -> Dict[str, Any]:
        """生成摘要"""
        start = time.time()

        if summary_type == SummaryType.EXTRACTIVE:
            result = self._extractive_summarize(text, max_length, custom_max_sentences)
        elif summary_type == SummaryType.ABSTRACTIVE:
            result = self._abstractive_summarize(text, max_length)
        elif summary_type == SummaryType.HEADLINE:
            result = self._headline_summarize(text)
        elif summary_type == SummaryType.BULLET:
            result = self._bullet_summarize(text, max_length)
        elif summary_type == SummaryType.KEY_POINTS:
            result = self._key_points_summarize(text)
        else:
            result = self._extractive_summarize(text, max_length, custom_max_sentences)

        result.duration_ms = (time.time() - start) * 1000
        result.summary_id = f"sum_{uuid.uuid4().hex[:10]}"

        # 质量评分
        result.score = self._evaluate_quality(text, result.summary)

        self._summary_history.append(
            {
                "summary_id": result.summary_id,
                "type": summary_type.value,
                "original_length": result.original_length,
                "summary_length": result.summary_length,
                "score": result.score,
                "timestamp": time.time(),
            }
        )

        self.stats["summaries_generated"] += 1
        metrics_collector.counter("summaries_generated")

        return {
            "summary_id": result.summary_id,
            "summary": result.summary,
            "type": summary_type.value,
            "original_length": result.original_length,
            "summary_length": result.summary_length,
            "compression_ratio": round(result.compression_ratio, 4),
            "quality_score": round(result.score, 4),
            "key_sentences": result.key_sentences[:5],
            "key_phrases": result.key_phrases[:10],
            "duration_ms": round(result.duration_ms, 2),
        }

    def _get_max_sentences(self, max_length: SummaryLength, custom: int) -> int:
        if custom > 0:
            return custom
        return {"short": 2, "medium": 5, "long": 10, "custom": 5}.get(max_length.value, 5)

    def _extractive_summarize(self, text: str, max_length: SummaryLength, custom_max: int) -> SummaryResult:
        """抽取式摘要"""
        sentences = self._split_sentences(text)
        if not sentences:
            return SummaryResult("", "", SummaryType.EXTRACTIVE, 0, 0, 0)

        all_tokens = self._tokenize(text)
        max_sent = self._get_max_sentences(max_length, custom_max)
        max_sent = min(max_sent, len(sentences))

        scored = []
        for i, sent in enumerate(sentences):
            score = self._compute_sentence_score(sent, all_tokens, i, len(sentences))
            scored.append((i, score, sent))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = sorted(scored[:max_sent], key=lambda x: x[0])

        summary = "。".join(s[2] for s in top) + "。"
        key_phrases = list(set(self._tokenize(summary)))[:10]

        return SummaryResult(
            summary=summary,
            summary_type=SummaryType.EXTRACTIVE,
            original_length=len(text),
            summary_length=len(summary),
            compression_ratio=len(summary) / max(len(text), 1),
            key_sentences=[s[2] for s in top],
            key_phrases=key_phrases,
        )

    def _abstractive_summarize(self, text: str, max_length: SummaryLength) -> SummaryResult:
        """生成式摘要（模拟）"""
        sentences = self._split_sentences(text)
        if not sentences:
            return SummaryResult("", "", SummaryType.ABSTRACTIVE, 0, 0, 0)

        # 基于抽取式+重组的模拟生成
        extracted = self._extractive_summarize(text, max_length, 0)

        # 简单的重组和压缩
        summary = extracted.summary
        # 去除冗余
        unique_sents = []
        seen_phrases = set()
        for sent in re.split(r"[。！？]+", summary):
            key = tuple(sorted(set(self._tokenize(sent))))
            if key not in seen_phrases:
                seen_phrases.add(key)
                unique_sents.append(sent)

        summary = "。".join(s for s in unique_sents if s.strip()) + "。"

        return SummaryResult(
            summary=summary,
            summary_type=SummaryType.ABSTRACTIVE,
            original_length=len(text),
            summary_length=len(summary),
            compression_ratio=len(summary) / max(len(text), 1),
            key_sentences=unique_sents[:5],
            key_phrases=list(set(self._tokenize(summary)))[:10],
        )

    def _headline_summarize(self, text: str) -> SummaryResult:
        """标题式摘要"""
        sentences = self._split_sentences(text)
        all_tokens = self._tokenize(text)

        if not sentences:
            return SummaryResult("", "", SummaryType.HEADLINE, 0, 0, 0)

        # 选择得分最高的句子作为标题
        scored = [
            (i, self._compute_sentence_score(s, all_tokens, i, len(sentences)), s) for i, s in enumerate(sentences)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        headline = scored[0][2][:60]
        if len(scored[0][2]) > 60:
            headline = headline[:57] + "..."

        return SummaryResult(
            summary=headline,
            summary_type=SummaryType.HEADLINE,
            original_length=len(text),
            summary_length=len(headline),
            compression_ratio=len(headline) / max(len(text), 1),
            key_sentences=[scored[0][2]],
            key_phrases=self._tokenize(headline)[:5],
        )

    def _bullet_summarize(self, text: str, max_length: SummaryLength) -> SummaryResult:
        """要点式摘要"""
        extracted = self._extractive_summarize(text, max_length, 0)
        sentences = extracted.key_sentences[:5]

        bullets = []
        for sent in sentences:
            # 提取要点
            if len(sent) > 80:
                # 截取关键部分
                bullet = sent[:77] + "..."
            else:
                bullet = sent
            bullets.append(f"- {bullet}")

        summary = "\n".join(bullets)

        return SummaryResult(
            summary=summary,
            summary_type=SummaryType.BULLET,
            original_length=len(text),
            summary_length=len(summary),
            compression_ratio=len(summary) / max(len(text), 1),
            key_sentences=sentences,
            key_phrases=extracted.key_phrases,
        )

    def _key_points_summarize(self, text: str) -> SummaryResult:
        """关键点提取"""
        sentences = self._split_sentences(text)
        all_tokens = self._tokenize(text)

        scored = []
        for i, sent in enumerate(sentences):
            score = self._compute_sentence_score(sent, all_tokens, i, len(sentences))
            scored.append((score, sent))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_points = scored[:5]

        points = []
        for i, (score, sent) in enumerate(top_points):
            # 提取关键短语
            phrases = self._tokenize(sent)
            point = {"point": i + 1, "summary": sent, "importance": round(score, 4), "key_terms": phrases[:5]}
            points.append(point)

        summary = "\n".join(f"{p['point']}. {p['summary']}" for p in points)

        return SummaryResult(
            summary=summary,
            summary_type=SummaryType.KEY_POINTS,
            original_length=len(text),
            summary_length=len(summary),
            compression_ratio=len(summary) / max(len(text), 1),
            key_sentences=[p["summary"] for p in points],
            key_phrases=list(set(t for p in points for t in p["key_terms"]))[:10],
        )

    def _evaluate_quality(self, original: str, summary: str) -> float:
        """评估摘要质量"""
        if not summary or not original:
            return 0.0

        orig_tokens = set(self._tokenize(original))
        summ_tokens = set(self._tokenize(summary))

        # 覆盖率
        coverage = len(summ_tokens & orig_tokens) / max(len(orig_tokens), 1)

        # 简洁性
        compression = len(summary) / max(len(original), 1)
        conciseness = 1.0 - abs(compression - 0.3)  # 理想压缩率30%

        # 信息密度
        density = len(summ_tokens) / max(len(summary.split()), 1)

        # 综合评分
        score = coverage * 0.4 + conciseness * 0.3 + min(density / 5, 1.0) * 0.3
        return min(max(score, 0), 1.0)

    @trace_operation("summarize_multi")
    def summarize_multi_document(self, documents: List[str], max_sentences: int = 10) -> Dict[str, Any]:
        """多文档摘要"""
        if not documents:
            return {"summary": "", "documents": 0}

        # 每个文档生成摘要
        doc_summaries = []
        for doc in documents:
            result = self._extractive_summarize(doc, SummaryLength.SHORT, 2)
            doc_summaries.append(result)

        # 合并摘要
        all_sentences = []
        for ds in doc_summaries:
            all_sentences.extend(ds.key_sentences)

        # 去重
        seen = set()
        unique = []
        for sent in all_sentences:
            key = tuple(sorted(set(self._tokenize(sent))))
            if key not in seen:
                seen.add(key)
                unique.append(sent)

        final = unique[:max_sentences]
        summary = "。".join(final) + "。" if final else ""

        return {
            "summary": summary,
            "documents": len(documents),
            "sentences_selected": len(final),
            "compression_ratio": round(len(summary) / max(sum(len(d) for d in documents), 1), 4),
        }

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        params = params or {}
        actions = {
            "summarize": self.summarize,
            "summarize_multi_document": self.summarize_multi_document,
            "extract_keywords": lambda p: self._keyword_extractor.extract_tfidf_keywords(
                p.get("text", ""), p.get("top_k", 10)
            ),
            "extract_keywords_textrank": lambda p: self._keyword_extractor.extract_textrank_keywords(
                p.get("text", ""), p.get("top_k", 10)
            ),
            "compare_summaries": lambda p: self._summary_comparator.compare_summaries(
                p.get("summary_a", ""), p.get("summary_b", ""), p.get("original", "")
            ),
            "detect_info_loss": lambda p: self._summary_comparator.detect_information_loss(
                p.get("original", ""), p.get("summary", "")
            ),
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
        base.update({"summaries_generated": len(self._summary_history), "stop_words": len(self._stop_words)})
        return base

    def shutdown(self) -> None:
        audit_logger.log(
            action="module_shutdown",
            resource="summarization_engine",
            details=f"关闭，生成 {len(self._summary_history)} 个摘要",
        )

module_class = SummarizationEngine
