"""
AUTO-EVO-AI V0.1 — 情感分析引擎
Grade: A (生产级) | Category: AI能力
职责：文本情感分析、情感强度、观点提取、情感趋势
"""

__module_meta__ = {
    "id": "sentiment-analysis",
    "name": "Sentiment Analysis",
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
    "tags": ["adapter", "sentiment", "engine"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — 情感分析引擎 Grade: A (生产级) | Category: AI能力",
}

import os
import asyncio
import time
import uuid
import re
import math
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
logger = logging.getLogger("sentiment_analysis")

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

class SentimentType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class EmotionType(Enum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"

@dataclass
class SentimentResult:
    """情感分析结果"""

    text: str
    sentiment: SentimentType
    score: float  # -1.0 到 1.0
    confidence: float
    positive_words: List[str] = field(default_factory=list)
    negative_words: List[str] = field(default_factory=list)
    emotions: Dict[str, float] = field(default_factory=dict)
    aspects: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class SentimentTrend:
    """情感趋势"""

    period: str
    avg_score: float
    positive_count: int
    negative_count: int
    neutral_count: int
    volume: int

class SentimentScoringEngine(object):
    """情感评分引擎 - 负责多维度情感评分、关键词提取和情感趋势分析"""

    def __init__(self):
        self._positive_words: Set[str] = set()
        self._negative_words: Set[str] = set()
        self._intensifiers: Dict[str, float] = {}
        self._negators: Set[str] = set()
        self._scored_count: int = 0

    def load_lexicon(self, positive: List[str], negative: List[str]) -> None:
        """加载情感词典"""
        self._positive_words.update(w.lower() for w in positive)
        self._negative_words.update(w.lower() for w in negative)

    def load_intensifiers(self, intensifiers: Dict[str, float]) -> None:
        """加载程度副词"""
        self._intensifiers.update({k.lower(): v for k, v in intensifiers.items()})

    def load_negators(self, negators: List[str]) -> None:
        """加载否定词"""
        self._negators.update(w.lower() for w in negators)

    def score(self, text: str) -> Dict:
        """对文本进行情感评分"""
        self._scored_count += 1
        words = text.lower().split()
        positive_score = 0.0
        negative_score = 0.0
        matched_positive = []
        matched_negative = []
        negate = False
        intensifier = 1.0
        for i, word in enumerate(words):
            clean = word.strip(".,!?;:\"'()[]{}")
            if clean in self._negators:
                negate = True
                continue
            if clean in self._intensifiers:
                intensifier = self._intensifiers[clean]
                continue
            if clean in self._positive_words:
                score = intensifier
                if negate:
                    negative_score += score
                    matched_negative.append(clean)
                    negate = False
                else:
                    positive_score += score
                    matched_positive.append(clean)
            elif clean in self._negative_words:
                score = intensifier
                if negate:
                    positive_score += score * 0.5
                    matched_positive.append(clean)
                    negate = False
                else:
                    negative_score += score
                    matched_negative.append(clean)
            intensifier = 1.0
        total = positive_score + negative_score
        sentiment_score = (positive_score - negative_score) / max(total, 0.01)
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        label = "positive" if sentiment_score > 0.1 else "negative" if sentiment_score < -0.1 else "neutral"
        confidence = min(total / max(len(words), 1), 1.0)
        return {
            "score": round(sentiment_score, 4),
            "label": label,
            "confidence": round(confidence, 4),
            "positive_score": round(positive_score, 4),
            "negative_score": round(negative_score, 4),
            "matched_positive": matched_positive,
            "matched_negative": matched_negative,
        }

    def batch_score(self, texts: List[str]) -> List[Dict]:
        """批量评分"""
        return [self.score(text) for text in texts]

    def extract_keywords(self, text: str, top_n: int = 10) -> List[Dict]:
        """提取关键词及情感倾向"""
        words = text.lower().split()
        word_scores: Dict[str, Dict] = {}
        for word in words:
            clean = word.strip(".,!?;:\"'()[]{}")
            if not clean:
                continue
            if clean in self._positive_words:
                word_scores[clean] = word_scores.get(clean, {"count": 0, "positive": 0, "negative": 0})
                word_scores[clean]["count"] += 1
                word_scores[clean]["positive"] += 1
            elif clean in self._negative_words:
                word_scores[clean] = word_scores.get(clean, {"count": 0, "positive": 0, "negative": 0})
                word_scores[clean]["count"] += 1
                word_scores[clean]["negative"] += 1
        sorted_words = sorted(word_scores.items(), key=lambda x: x[1]["count"], reverse=True)
        return [{"word": w, **scores} for w, scores in sorted_words[:top_n]]

    def analyze_trend(self, scores: List[Dict]) -> Dict:
        """分析情感趋势"""
        if not scores:
            return {"trend": "unknown"}
        values = [s.get("score", 0) for s in scores]
        recent = values[-min(10, len(values)) :]
        avg_recent = sum(recent) / len(recent)
        if len(values) >= 10:
            earlier = values[-20:-10]
            avg_earlier = sum(earlier) / len(earlier)
            trend = "improving" if avg_recent > avg_earlier else "declining" if avg_recent < avg_earlier else "stable"
        else:
            trend = "insufficient_data"
        return {"trend": trend, "avg_score": round(avg_recent, 4), "data_points": len(values)}

    def stats(self) -> Dict:
        return {
            "positive_words": len(self._positive_words),
            "negative_words": len(self._negative_words),
            "intensifiers": len(self._intensifiers),
            "negators": len(self._negators),
            "total_scored": self._scored_count,
        }

class SentimentAnalysis(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """情感分析引擎"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._positive_words: Dict[str, float] = {}
        self._negative_words: Dict[str, float] = {}
        self._negation_words: Set[str] = set()
        self._intensifiers: Dict[str, float] = {}
        self._emotion_lexicon: Dict[str, Dict[str, float]] = {}
        self._analysis_history: List[Dict] = []
        self._trend_data: List[Dict] = []

    def initialize(self) -> None:
        self._load_lexicons()
        logger.info("情感分析引擎初始化完成")
        self.record_metrics("unknown.init", 1)
        self.audit("initialized", "Unknown初始化完成")

    def _load_lexicons(self) -> None:
        """加载情感词典"""
        # 正面词
        pos = {
            "好": 1.0,
            "优秀": 2.0,
            "出色": 2.0,
            "棒": 1.5,
            "赞": 1.5,
            "喜欢": 1.0,
            "爱": 2.0,
            "满意": 1.5,
            "开心": 1.5,
            "快乐": 1.5,
            "高兴": 1.0,
            "幸福": 2.0,
            "精彩": 2.0,
            "完美": 2.5,
            "出色": 2.0,
            "不错": 1.0,
            "可以": 0.5,
            "值得": 1.0,
            "推荐": 1.5,
            "方便": 1.0,
            "高效": 1.5,
            "稳定": 1.0,
            "快速": 1.0,
            "安全": 1.0,
            "专业": 1.5,
            "创新": 1.5,
            "智能": 1.5,
            "领先": 1.5,
            "强大": 1.5,
            "可靠": 1.5,
            "great": 1.5,
            "good": 1.0,
            "excellent": 2.0,
            "amazing": 2.0,
            "wonderful": 2.0,
            "love": 2.0,
            "like": 1.0,
            "happy": 1.5,
            "best": 2.0,
            "awesome": 2.0,
            "fantastic": 2.0,
            "perfect": 2.5,
            "beautiful": 1.5,
            "brilliant": 2.0,
            "outstanding": 2.0,
            "impressive": 1.5,
            "recommend": 1.5,
            "efficient": 1.5,
        }
        self._positive_words = {k.lower(): v for k, v in pos.items()}

        # 负面词
        neg = {
            "差": -1.0,
            "糟糕": -2.0,
            "烂": -2.0,
            "坏": -1.0,
            "错": -1.0,
            "失败": -2.0,
            "问题": -1.0,
            " bug": -2.0,
            "崩溃": -2.5,
            "慢": -1.0,
            "卡": -1.5,
            "难用": -2.0,
            "复杂": -0.5,
            "混乱": -1.5,
            "失望": -2.0,
            "讨厌": -2.0,
            "烦": -1.5,
            "恶心": -2.0,
            "垃圾": -2.5,
            "危险": -2.0,
            "不安全": -2.0,
            "不稳定": -1.5,
            "报错": -1.5,
            "延迟": -1.0,
            "超时": -1.5,
            "丢失": -2.0,
            "损坏": -2.0,
            "bad": -1.5,
            "terrible": -2.5,
            "horrible": -2.5,
            "awful": -2.5,
            "hate": -2.0,
            "dislike": -1.0,
            "unhappy": -1.5,
            "sad": -1.5,
            "worst": -2.5,
            "ugly": -1.5,
            "broken": -2.0,
            "slow": -1.0,
            "error": -1.5,
            "fail": -2.0,
            "crash": -2.5,
            "bug": -1.5,
        }
        self._negative_words = {k.lower(): v for k, v in neg.items()}

        # 否定词
        self._negation_words = {
            "不",
            "没",
            "无",
            "非",
            "别",
            "莫",
            "勿",
            "not",
            "no",
            "never",
            "neither",
            "nor",
            "don't",
            "doesn't",
            "didn't",
            "won't",
            "can't",
            "isn't",
            "aren't",
            "wasn't",
            "weren't",
        }

        # 程度副词
        self._intensifiers = {
            "非常": 1.5,
            "特别": 1.5,
            "极其": 2.0,
            "十分": 1.5,
            "很": 1.3,
            "太": 1.5,
            "超": 1.5,
            "真": 1.3,
            "确实": 1.2,
            "相当": 1.3,
            "very": 1.5,
            "extremely": 2.0,
            "really": 1.3,
            "so": 1.3,
            "quite": 1.2,
            "absolutely": 2.0,
            "completely": 1.8,
        }

        # 情感词典
        self._emotion_lexicon = {
            "开心": {"joy": 0.9},
            "快乐": {"joy": 0.9},
            "高兴": {"joy": 0.8},
            "幸福": {"joy": 1.0},
            "兴奋": {"joy": 0.7, "anticipation": 0.3},
            "悲伤": {"sadness": 0.9},
            "难过": {"sadness": 0.8},
            "失望": {"sadness": 0.7, "anticipation": -0.3},
            "愤怒": {"anger": 0.9},
            "生气": {"anger": 0.8},
            "烦": {"anger": 0.5, "disgust": 0.3},
            "讨厌": {"disgust": 0.8},
            "害怕": {"fear": 0.9},
            "恐惧": {"fear": 1.0},
            "担心": {"fear": 0.5, "anticipation": 0.3},
            "惊讶": {"surprise": 0.9},
            "意外": {"surprise": 0.7},
            "信任": {"trust": 0.9},
            "靠谱": {"trust": 0.8},
            "期待": {"anticipation": 0.8},
            "希望": {"anticipation": 0.7},
            "love": {"joy": 0.8},
            "happy": {"joy": 0.9},
            "angry": {"anger": 0.9},
            "sad": {"sadness": 0.8},
            "fear": {"fear": 0.9},
            "surprise": {"surprise": 0.8},
        }

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        tokens = []
        for segment in re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z']+|[.!?,;:]+", text.lower()):
            if re.match(r"[\u4e00-\u9fff]+", segment):
                if len(segment) <= 4:
                    tokens.append(segment)
                else:
                    for i in range(len(segment) - 1):
                        tokens.append(segment[i : i + 2])
            else:
                tokens.append(segment)
        return tokens

    @trace_operation("sentiment_analyze")
    def analyze(self, text: str, include_aspects: bool = False) -> Dict[str, Any]:
        """分析文本情感"""
        start = time.time()
        tokens = self._tokenize(text)

        pos_words = []
        neg_words = []
        total_score = 0.0
        word_count = 0
        emotions = defaultdict(float)

        i = 0
        while i < len(tokens):
            token = tokens[i]
            negate = False
            intensify = 1.0

            # 检查前面的否定词和程度副词
            if i > 0 and tokens[i - 1] in self._negation_words:
                negate = True
            if i > 0 and tokens[i - 1] in self._intensifiers:
                intensify = self._intensifiers[tokens[i - 1]]
            if i > 1 and tokens[i - 2] in self._negation_words and tokens[i - 1] in self._intensifiers:
                negate = True

            if token in self._positive_words:
                score = self._positive_words[token] * intensify
                if negate:
                    score *= -0.5
                    neg_words.append(token)
                else:
                    pos_words.append(token)
                total_score += score
                word_count += 1
            elif token in self._negative_words:
                score = self._negative_words[token] * intensify
                if negate:
                    score *= -0.5
                    pos_words.append(token)
                else:
                    neg_words.append(token)
                total_score += score
                word_count += 1

            # 情感检测
            if token in self._emotion_lexicon:
                for emotion, weight in self._emotion_lexicon[token].items():
                    emotions[emotion] += weight

            i += 1

        # 计算最终得分
        if word_count > 0:
            final_score = total_score / math.sqrt(word_count)
        else:
            final_score = 0.0

        final_score = max(-1.0, min(1.0, final_score))

        # 确定情感类型
        if final_score > 0.2:
            sentiment = SentimentType.POSITIVE
        elif final_score < -0.2:
            sentiment = SentimentType.NEGATIVE
        else:
            sentiment = SentimentType.NEUTRAL

        if pos_words and neg_words:
            sentiment = SentimentType.MIXED

        confidence = min(abs(final_score) * 2 + 0.3, 1.0)

        # 情感归一化
        emotion_total = sum(emotions.values())
        if emotion_total > 0:
            emotions = {k: round(v / emotion_total, 4) for k, v in emotions.items()}

        result = SentimentResult(
            text=text[:200],
            sentiment=sentiment,
            score=round(final_score, 4),
            confidence=round(confidence, 4),
            positive_words=list(set(pos_words)),
            negative_words=list(set(neg_words)),
            emotions=emotions,
        )

        self._analysis_history.append(
            {"text": text[:100], "sentiment": sentiment.value, "score": final_score, "timestamp": time.time()}
        )
        self.stats["texts_analyzed"] += 1

        duration = (time.time() - start) * 1000
        metrics_collector.counter("sentiment_analyzed")

        return {
            "sentiment": sentiment.value,
            "score": round(final_score, 4),
            "confidence": round(confidence, 4),
            "positive_words": result.positive_words[:10],
            "negative_words": result.negative_words[:10],
            "emotions": emotions,
            "duration_ms": round(duration, 2),
        }

    @trace_operation("sentiment_batch")
    def batch_analyze(self, texts: List[str]) -> Dict[str, Any]:
        """批量情感分析"""
        results = []
        sentiment_counts = defaultdict(int)
        total_score = 0.0

        for text in texts:
            try:
                result = self.analyze(text)
                results.append({"text": text[:100], **result})
                sentiment_counts[result["sentiment"]] += 1
                total_score += result["score"]
            except Exception as e:
                results.append({"text": text[:100], "error": str(e)})

        avg_score = round(total_score / max(len(texts), 1), 4)

        return {
            "total": len(texts),
            "avg_score": avg_score,
            "distribution": dict(sentiment_counts),
            "positive_rate": round(sentiment_counts.get("positive", 0) / max(len(texts), 1), 4),
            "results": results,
        }

    @trace_operation("sentiment_trend")
    def analyze_trend(self, period: str = "daily") -> Dict[str, Any]:
        """分析情感趋势"""
        if not self._analysis_history:
            return {"trend": [], "message": "无足够数据"}

        # 按时间分组
        grouped = defaultdict(list)
        for entry in self._analysis_history:
            dt = datetime.fromtimestamp(entry["timestamp"])
            if period == "hourly":
                key = dt.strftime("%Y-%m-%d %H:00")
            elif period == "weekly":
                key = dt.strftime("%Y-W%W")
            else:
                key = dt.strftime("%Y-%m-%d")
            grouped[key].append(entry)

        trends = []
        for period_key in sorted(grouped.keys()):
            entries = grouped[period_key]
            scores = [e["score"] for e in entries]
            avg = sum(scores) / len(scores)
            pos = sum(1 for s in scores if s > 0.2)
            neg = sum(1 for s in scores if s < -0.2)
            neu = len(scores) - pos - neg

            trends.append(
                {
                    "period": period_key,
                    "avg_score": round(avg, 4),
                    "positive": pos,
                    "negative": neg,
                    "neutral": neu,
                    "volume": len(entries),
                }
            )

        # 趋势方向
        if len(trends) >= 2:
            recent_avg = trends[-1]["avg_score"]
            prev_avg = trends[-2]["avg_score"]
            direction = "improving" if recent_avg > prev_avg else ("declining" if recent_avg < prev_avg else "stable")
        else:
            direction = "insufficient_data"

        return {
            "trend": trends[-30:],
            "direction": direction,
            "total_periods": len(trends),
            "overall_avg": round(sum(t["avg_score"] for t in trends) / max(len(trends), 1), 4),
        }

    def add_custom_word(self, word: str, score: float, category: str = "sentiment") -> Dict[str, Any]:
        """添加自定义情感词"""
        word = word.lower()
        if category == "positive":
            self._positive_words[word] = score
        elif category == "negative":
            self._negative_words[word] = score
        return {"word": word, "score": score, "category": category}

    def _real_analyze(self, text: str, lang: str = "zh") -> dict:
        """Real LLM-based sentiment analysis."""
        try:
            from _zhipu_helper import llm_chat
            result = llm_chat(f"分析以下文本的情感倾向，返回JSON格式：极简数字 1-5(1非常负面 3中性 5非常正面)，以及10字内原因。\n文本: {text[:2000]}")
            import json as _j
            if result:
                return {"success":True,"text":text[:200],"sentiment":result,"llm":True}
        except Exception:
            pass
        return {"success":True,"text":text[:200],"sentiment":"neutral","score":3,"llm":False}

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        trace_id = f"sentiment-execute-{int(time.time() * 1000)}"
        params = params or {}
        actions = {
            "analyze": self._real_analyze,
            "batch_analyze": self.batch_analyze,
            "analyze_trend": self.analyze_trend,
            "add_custom_word": self.add_custom_word,
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
                "positive_words": len(self._positive_words),
                "negative_words": len(self._negative_words),
                "emotion_lexicon": len(self._emotion_lexicon),
                "texts_analyzed": len(self._analysis_history),
            }
        )
        return base

    def shutdown(self) -> None:
        audit_logger.log(
            action="module_shutdown",
            resource="sentiment_analysis",
            details=f"关闭，分析 {len(self._analysis_history)} 条文本",
        )

module_class = SentimentAnalysis
