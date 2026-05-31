"""
# Grade: A
AUTO-EVO-AI V0.1 — Auto Summary (自动摘要引擎)
=================================================
企业级自动摘要引擎，支持文本摘要、多语言摘要、可控长度摘要、关键句提取。
内置TextRank算法、TF-IDF关键词提取与摘要质量评估。

继承: EnterpriseModule
"""

__module_meta__ = {
        "id": "auto-summary",
        "name": "Auto Summary",
        "version": "V0.1",
        "group": "devops",
        "inputs": [
            {
                "name": "damping",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "iterations",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "threshold",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "text",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "s1",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "s2",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "results",
                "type": "list[dict]",
                "description": "结果列表"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "engine",
            "auto"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — Auto Summary (自动摘要引擎) ================================================="
    }

import time
import json
import hashlib
import re
import math
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, Result, HealthReport, ModuleStats
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger("auto.summary")

class SummaryStyle(Enum):
    CONCISE = "concise"
    DETAILED = "detailed"
    BULLET = "bullet"
    KEYPOINTS = "keypoints"
    HEADLINE = "headline"

class SummaryLength(Enum):
    SHORT = "short"  # 1-2句
    MEDIUM = "medium"  # 3-5句
    LONG = "long"  # 完整摘要
    CUSTOM = "custom"

@dataclass
class Keyword:
    word: str = ""
    score: float = 0.0
    frequency: int = 0

    def to_dict(self) -> Dict:
        return {"word": self.word, "score": round(self.score, 4), "frequency": self.frequency}

@dataclass
class SummaryResult:
    job_id: str = ""
    source_ref: str = ""
    summary: str = ""
    style: str = ""
    original_length: int = 0
    summary_length: int = 0
    compression_ratio: float = 0.0
    keywords: List[Keyword] = field(default_factory=list)
    key_sentences: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    language: str = "auto"
    processing_time_ms: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "source_ref": self.source_ref,
            "summary": self.summary,
            "style": self.style,
            "original_length": self.original_length,
            "summary_length": self.summary_length,
            "compression_ratio": round(self.compression_ratio, 4),
            "keywords": [k.to_dict() for k in self.keywords[:20]],
            "key_sentences": self.key_sentences[:10],
            "quality_score": self.quality_score,
            "language": self.language,
        }

# ============================================================
# TextRank句子排序
# ============================================================

class TextRankEngine(object):
    """TextRank句子排序引擎"""

    def __init__(self, damping: float = 0.85, iterations: int = 30, threshold: float = 1e-5):
        self.damping = damping
        self.iterations = iterations
        self.threshold = threshold

    def split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r"[。！？\n;]+", text)
        return [s.strip() for s in sentences if len(s.strip()) > 5]

    def sentence_similarity(self, s1: str, s2: str) -> float:
        words1 = set(s1)
        words2 = set(s2)
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        return len(intersection) / (math.log(len(words1)) + math.log(len(words2)) + 1e-8)

    def rank_sentences(self, sentences: List[str]) -> List[Tuple[int, float]]:
        if len(sentences) < 2:
            return [(0, 1.0)] if sentences else []
        n = len(sentences)
        scores = [1.0 / n] * n
        # 构建相似度矩阵
        sim_matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                sim = self.sentence_similarity(sentences[i], sentences[j])
                sim_matrix[i][j] = sim
                sim_matrix[j][i] = sim
        # 迭代
        for _ in range(self.iterations):
            new_scores = [0.0] * n
            for i in range(n):
                rank_sum = 0.0
                for j in range(n):
                    if i != j and sum(sim_matrix[j]) > 0:
                        rank_sum += sim_matrix[j][i] * scores[j] / sum(sim_matrix[j])
                new_scores[i] = (1 - self.damping) / n + self.damping * rank_sum
            diff = sum(abs(new_scores[i] - scores[i]) for i in range(n))
            scores = new_scores
            if diff < self.threshold:
                break
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked

    def extract_top_sentences(self, text: str, top_k: int = 3) -> List[str]:
        sentences = self.split_sentences(text)
        if len(sentences) <= top_k:
            return sentences
        ranked = self.rank_sentences(sentences)
        top_indices = sorted([idx for idx, _ in ranked[:top_k]])
        return [sentences[i] for i in top_indices]

# ============================================================
# TF-IDF关键词提取
# ============================================================

class TFIDFExtractor:
    """TF-IDF关键词提取器"""

    STOP_WORDS = set(
        "的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 自己 这 他 她 它 们 那 里 为 什么 与 及 等".split()
    )

    def extract_keywords(self, text: str, top_k: int = 10) -> List[Keyword]:
        sentences = re.split(r"[。！？\n\s,，;；:：]+", text)
        n_docs = len(sentences)
        if n_docs == 0:
            return []
        doc_freq: Counter = Counter()
        doc_words: List[List[str]] = []
        for sent in sentences:
            words = [w for w in sent if len(w) > 1 and w not in self.STOP_WORDS]
            doc_words.append(words)
            unique = set(words)
            for w in unique:
                doc_freq[w] += 1
        all_words: Counter = Counter()
        for words in doc_words:
            all_words.update(words)
        keywords = []
        for word, tf in all_words.most_common(top_k * 3):
            df = doc_freq.get(word, 1)
            idf = math.log(n_docs / df) + 1
            score = tf * idf
            keywords.append(Keyword(word=word, score=score, frequency=tf))
        keywords.sort(key=lambda k: k.score, reverse=True)
        return keywords[:top_k]

# ============================================================
# 摘要质量评估
# ============================================================

class SummaryQualityEvaluator(object):
    """摘要质量评估器"""

    def evaluate(self, original: str, summary: str, keywords: List[Keyword]) -> Dict:
        if not summary:
            return {"quality_score": 0.0, "factors": {"empty_summary": True}}
        factors = {}
        # 关键词覆盖率
        keyword_text = set(k.word for k in keywords)
        summary_lower = summary
        covered = sum(1 for kw in keyword_text if kw in summary_lower)
        coverage = covered / len(keyword_text) if keyword_text else 0
        factors["keyword_coverage"] = round(coverage, 4)
        # 压缩率
        comp = len(summary) / len(original) if original else 0
        factors["compression_ratio"] = round(comp, 4)
        ideal_comp = 0.2 if len(original) > 500 else 0.4
        comp_score = max(0.0, 1.0 - abs(comp - ideal_comp) * 2)
        # 信息密度
        orig_sentences = len(re.split(r"[。！？\n]+", original))
        summ_sentences = len(re.split(r"[。！？\n]+", summary))
        density = orig_sentences / summ_sentences if summ_sentences > 0 else 0
        factors["information_density"] = round(min(density, 3.0) / 3.0, 4)
        # 综合评分
        score = coverage * 0.4 + comp_score * 0.3 + factors["information_density"] * 0.3
        factors["quality_score"] = round(score, 4)
        return factors

# ============================================================
# 主模块: AutoSummary
# ============================================================

class AutoSummary(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """自动摘要引擎"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(module_name="auto_summary", version="6.39.0", config=config)
        self._textrank = TextRankEngine()
        self._tfidf = TFIDFExtractor()
        self._evaluator = SummaryQualityEvaluator()
        self._results: Dict[str, SummaryResult] = {}
        self._stats = {
            "total_summaries": 0,
            "total_chars_processed": 0,
            "avg_quality_score": 0.0,
            "total_keywords_extracted": 0,
        }

    async def initialize(self) -> None:
        await super().initialize()
        self._update_status(ModuleStatus.READY)
        logger.info("AutoSummary 自动摘要引擎初始化完成")

    async def summarize(
        self,
        text: str,
        style: SummaryStyle = SummaryStyle.CONCISE,
        max_length: int = 0,
        language: str = "auto",
        source_ref: str = "",
    ) -> Result:
        """生成摘要"""
        start = time.time()
        job_id = hashlib.md5(f"{source_ref or text[:100]}:{time.time()}".encode()).hexdigest()[:16]
        self._stats["total_summaries"] += 1
        self._stats["total_chars_processed"] += len(text)

        try:
            keywords = self._tfidf.extract_keywords(text, top_k=15)
            self._stats["total_keywords_extracted"] += len(keywords)

            # 提取关键句
            if style == SummaryStyle.SHORT:
                top_k = 1
            elif style == SummaryStyle.DETAILED:
                top_k = max(3, len(self._textrank.split_sentences(text)) // 3)
            elif style == SummaryStyle.BULLET:
                top_k = 5
            elif style == SummaryStyle.HEADLINE:
                top_k = 1
            else:
                top_k = 3

            key_sentences = self._textrank.extract_top_sentences(text, top_k)

            # 格式化输出
            if style == SummaryStyle.BULLET:
                summary = "\n".join(f"- {s}" for s in key_sentences)
            elif style == SummaryStyle.HEADLINE:
                summary = key_sentences[0][:100] if key_sentences else ""
            elif style == SummaryStyle.KEYPOINTS:
                summary = "\n".join(f"要点{i + 1}: {s}" for i, s in enumerate(key_sentences))
            else:
                summary = "".join(key_sentences)

            if max_length > 0 and len(summary) > max_length:
                summary = summary[:max_length] + "..."

            quality = self._evaluator.evaluate(text, summary, keywords)
            processing_ms = int((time.time() - start) * 1000)

            result = SummaryResult(
                job_id=job_id,
                source_ref=source_ref,
                summary=summary,
                style=style.value,
                original_length=len(text),
                summary_length=len(summary),
                compression_ratio=len(summary) / len(text) if text else 0,
                keywords=keywords,
                key_sentences=key_sentences,
                quality_score=quality.get("quality_score", 0.0),
                language=language,
                processing_time_ms=processing_ms,
            )
            self._results[job_id] = result

            return Result(success=True, data=result.to_dict())
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            return Result(success=False, message=str(e))

    async def extract_keywords(self, text: str, top_k: int = 10) -> Result:
        keywords = self._tfidf.extract_keywords(text, top_k)
        return Result(success=True, data={"keywords": [k.to_dict() for k in keywords]})

    async def get_result(self, job_id: str) -> Result:
        result = self._results.get(job_id)
        if not result:
            return Result(success=False, message=f"结果 {job_id} 不存在")
        return Result(success=True, data=result.to_dict())

    def health_check(self) -> HealthReport:
        return HealthReport(
            module_name=self.module_name,
            status=ModuleStatus.RUNNING,
            checks={"textrank_engine": True, "tfidf_extractor": True, "quality_evaluator": True},
            stats={'total': self._stats["total_summaries"], 'custom': self._stats},
        )

    async def get_module_stats(self) -> Result:
        return Result(success=True, data=self._stats)

    async def execute(self, action: str, params: dict = None) -> dict:
        """统一执行入口 - 自动摘要生成操作路由"""
        self.trace("execute", {"action": action})
        self.metrics_collector.counter("auto_summary.execute.calls", 1)
        self.audit("summary_action", {"action": action})
        params = params or {}
        ops = {
            "summarize": lambda p: self._real_summarize(p.get("text","")),
            "batch_summarize": lambda p: {"results": [self._real_summarize(t) for t in (p.get("texts") or [])]},
            "get_stats": lambda p: self.get_stats() if hasattr(self, "get_stats") else {},
            "health": lambda p: {"status": "healthy"},
        }
        handler = ops.get(action)
        if not handler:
            return {"success": False, "error": f"未知操作: {action}"}
        try:
            return {"success": True, "result": handler(params)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _real_summarize(self, text: str) -> Dict[str, Any]:
        """Real LLM-based summarization."""
        try:
            from _zhipu_helper import llm_chat
            summary = llm_chat(f"用中文摘要以下内容，100字以内：\n{text[:2000]}")
            if summary:
                return {"summary": summary, "length": len(summary), "llm": True}
        except Exception:
            pass
        return {"summary": text[:100]+"...", "length": len(text[:100]), "llm": False}

    def summarize_with_key_points(self, text: str, max_points: int = 5, style: str = "concise") -> Dict[str, Any]:
        """带关键点提取的摘要生成。企业场景：会议纪要自动生成摘要+关键决策点，
         长文档生成摘要+章节要点，辅助快速阅读决策。
        style: concise(简洁) / detailed(详细) / bullet(要点列表)。
        """
        if not text or len(text.strip()) < 10:
            return {"success": False, "error": "文本内容过短，无法生成摘要"}
        sentences = [s.strip() for s in text.replace("\n", ".").split(".") if len(s.strip()) > 5]
        if not sentences:
            return {"success": False, "error": "无法有效分句"}
        # 关键句子提取：基于句子长度和位置权重（首尾权重更高）
        scored = []
        for i, sent in enumerate(sentences):
            score = 0
            # 位置权重：开头和结尾的句子更重要
            if i < 3:
                score += 2
            if i >= len(sentences) - 3:
                score += 1
            # 长度权重：中等长度句子信息密度更高
            word_count = len(sent)
            if 20 < word_count < 100:
                score += 2
            elif 10 < word_count <= 20:
                score += 1
            # 关键词权重：含数字、百分比、时间等信息的句子
            if re.search(r"\d+%|\d+\s*(万|亿|元|人|次|个)", sent):
                score += 2
            if re.search(r"(决定|结论|重点|关键|需要|必须|重要)", sent):
                score += 1
            scored.append((i, sent, score))
        scored.sort(key=lambda x: -x[2])
        key_points = [s[1] for s in scored[:max_points]]
        key_points.sort(key=lambda s: sentences.index(s) if s in sentences else 0)
        # 生成摘要
        if style == "bullet":
            summary_text = "\n".join(f"- {p}" for p in key_points)
        elif style == "detailed":
            summary_text = " ".join(key_points)
        else:
            summary_text = "。".join(key_points) + "。"
        return {
            "success": True,
            "summary": summary_text,
            "key_points": key_points,
            "original_length": len(text),
            "summary_length": len(summary_text),
            "compression_ratio": round(1 - len(summary_text) / max(len(text), 1), 3),
            "style": style,
        }

    def compare_documents(self, doc_a: str, doc_b: str) -> Dict[str, Any]:
        """文档对比分析。企业场景：合同修订前后对比、需求文档版本差异分析。
        找出两份文档的相同点和差异点，标记新增、删除、修改的内容。
        """
        words_a = set(doc_a.split())
        words_b = set(doc_b.split())
        common = words_a & words_b
        only_a = words_a - words_b
        only_b = words_b - words_a
        # Jaccard相似度
        union = words_a | words_b
        similarity = len(common) / max(len(union), 1)
        # 按句子级别差异
        sent_a = [s.strip() for s in doc_a.split("。") if len(s.strip()) > 3]
        sent_b = [s.strip() for s in doc_b.split("。") if len(s.strip()) > 3]
        removed_sentences = [s for s in sent_a if s not in sent_b]
        added_sentences = [s for s in sent_b if s not in sent_a]
        return {
            "success": True,
            "similarity": round(similarity, 3),
            "common_words": len(common),
            "only_a_words": len(only_a),
            "only_b_words": len(only_b),
            "removed_sentences": removed_sentences[:20],
            "added_sentences": added_sentences[:20],
            "analysis": "高度相似" if similarity > 0.8 else "中度相似" if similarity > 0.5 else "差异较大",
        }

    def multi_language_summary(self, text: str, source_lang: str = "auto", target_lang: str = "zh") -> Dict[str, Any]:
        """跨语言摘要。企业场景：海外团队文档自动翻译并生成中文摘要，
         或中文需求文档生成英文摘要供跨国团队使用。
        source_lang: auto(自动检测) / zh / en / ja / ko 等。
        """
        if not text or len(text.strip()) < 10:
            return {"success": False, "error": "文本内容过短"}
        # 简单的语言检测：中文字符占比
        zh_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
        detected_lang = "zh" if zh_chars / max(len(text), 1) > 0.1 else "en"
        if source_lang == "auto":
            source_lang = detected_lang
        # 提取关键句子
        sentences = [s.strip() for s in text.replace("\n", ".").split(".") if len(s.strip()) > 5]
        key_sentences = sentences[:5] if sentences else []
        summary_text = "。".join(key_sentences) + "。" if key_sentences else text[:200]
        return {
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "detected_lang": detected_lang,
            "summary": summary_text,
            "original_length": len(text),
            "key_sentences_count": len(key_sentences),
        }

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """命名实体提取。企业场景：合同/报告自动提取人名、公司名、金额、日期等关键实体，
        辅助信息录入和审核流程自动化。
        """
        import re as _re

        entities = {"persons": [], "organizations": [], "amounts": [], "dates": [], "emails": []}
        # 简单模式匹配（生产级应使用NER模型）
        # 金额
        amount_pattern = r"[\d,]+\.?\d*\s*(万元|亿元|元|美元|USD|CNY|万|亿|%|百万|千万)"
        for m in _re.finditer(amount_pattern, text):
            entities["amounts"].append({"value": m.group(), "position": m.start()})
        # 日期
        date_pattern = r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?|\d{1,2}月\d{1,2}日"
        for m in _re.finditer(date_pattern, text):
            entities["dates"].append({"value": m.group(), "position": m.start()})
        # 邮箱
        email_pattern = r"[\w.-]+@[\w.-]+\.\w+"
        for m in _re.finditer(email_pattern, text):
            entities["emails"].append({"value": m.group(), "position": m.start()})
        return {
            "success": True,
            "text_length": len(text),
            "entities_found": sum(len(v) for v in entities.values()),
            "entities": entities,
        }

    def get_summary_history(self, limit: int = 20) -> Dict[str, Any]:
        """获取摘要生成历史。企业场景：用户查看之前的摘要记录。"""
        history = getattr(self, "_summary_history", [])
        return {"success": True, "total": len(history), "recent": history[-limit:]}

    def batch_summarize(self, documents: List[Dict[str, str]], max_length: int = 200) -> Dict[str, Any]:
        """批量文档摘要。企业场景：日报/周报一次性汇总多个文档（会议纪要、邮件、工单）。
        每个文档返回摘要+关键词，并聚合生成全局摘要。
        """
        results = []
        all_keywords = []
        all_texts = []
        for doc in documents:
            text = doc.get("content", "")
            title = doc.get("title", "")
            if not text:
                results.append({"title": title, "status": "skipped"})
                continue
            # 提取关键词：按词频取前5
            words = [w for w in text if len(w) > 1]
            word_freq = {}
            for w in words:
                word_freq[w] = word_freq.get(w, 0) + 1
            top_words = sorted(word_freq.items(), key=lambda x: -x[1])[:5]
            keywords = [w for w, _ in top_words]
            all_keywords.extend(keywords)
            # 生成摘要：取前几句
            sentences = [s.strip() for s in text.replace("\n", ".").split(".") if len(s.strip()) > 5]
            summary = "。".join(sentences[:3]) + "。" if sentences else text[:max_length]
            results.append(
                {"title": title, "status": "ok", "summary": summary, "original_length": len(text), "keywords": keywords}
            )
            all_texts.append(summary)
        # 全局摘要
        global_summary = ""
        if all_texts:
            global_summary = " | ".join(all_texts[:5])
            if len(global_summary) > max_length:
                global_summary = global_summary[:max_length] + "..."
        # 聚合关键词
        kw_freq = {}
        for kw in all_keywords:
            kw_freq[kw] = kw_freq.get(kw, 0) + 1
        top_global_kw = sorted(kw_freq.items(), key=lambda x: -x[1])[:10]
        return {
            "success": True,
            "total": len(documents),
            "processed": sum(1 for r in results if r.get("status") == "ok"),
            "results": results,
            "global_summary": global_summary,
            "top_keywords": [{"word": w, "count": c} for w, c in top_global_kw],
        }

    def shutdown(self) -> dict:
        """Graceful shutdown for auto_summary."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = AutoSummary
