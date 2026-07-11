"""
AUTO-EVO-AI V0.1 — 知识库引擎
Grade: A (生产级) | Category: 工具链
职责：知识存储/检索/分类/标签/全文搜索/向量嵌入/版本管理
"""

__module_meta__ = {
        "id": "knowledge-base",
        "name": "Knowledge Base",
        "version": "V0.1",
        "group": "search",
        "inputs": [
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name_3",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value_3",
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
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "adapter",
            "knowledge"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 知识库引擎 Grade: A (生产级) | Category: 工具链"
    }

import asyncio
import time
import uuid
import re
import json
import os
import math
import logging
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, Counter

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
logger = logging.getLogger("knowledge_base")

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

class EntryType(Enum):
    ARTICLE = "article"
    NOTE = "note"
    FAQ = "faq"
    PROCEDURE = "procedure"
    DECISION = "decision"
    REFERENCE = "reference"
    GLOSSARY = "glossary"

class SearchType(Enum):
    FULLTEXT = "fulltext"
    SEMANTIC = "semantic"
    TAG = "tag"
    HYBRID = "hybrid"

@dataclass
class KnowledgeEntry:
    """知识条目"""

    entry_id: str
    title: str
    content: str
    entry_type: EntryType
    category: str = ""
    tags: list[str] = field(default_factory=list)
    author: str = "system"
    version: int = 1
    status: str = "published"
    related_entries: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    word_count: int = 0
    embedding: list[float] | None = None  # 模拟向量嵌入

    def __post_init__(self):
        if not self.word_count:
            self.word_count = len(self.content.split())

@dataclass
class SearchResult:
    """搜索结果"""

    entry_id: str
    title: str
    entry_type: str
    score: float
    snippet: str = ""
    highlights: list[str] = field(default_factory=list)
    matched_tags: list[str] = field(default_factory=list)

@dataclass
class CategoryNode:
    """分类节点"""

    category_id: str
    name: str
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    description: str = ""
    entry_count: int = 0

class KnowledgeIndexerAnalyzer:
    """知识索引器 — 构建倒排索引、计算TF-IDF、排序相关性"""

    def __init__(self):
        self._documents: dict[str, str] = {}
        self._inverted_index: dict[str, set[str]] = {}
        self._doc_lengths: dict[str, int] = {}
        self._avg_doc_length = 0.0
        self._total_docs = 0

    def add_document(self, doc_id: str, content: str) -> dict[str, Any]:
        """添加文档到索引，自动分词并构建倒排索引"""
        self._documents[doc_id] = content
        tokens = self._tokenize(content)
        self._doc_lengths[doc_id] = len(tokens)
        self._total_docs += 1
        total_length = sum(self._doc_lengths.values())
        self._avg_doc_length = total_length / self._total_docs
        for token in set(tokens):
            self._inverted_index.setdefault(token, set()).add(doc_id)
        return {
            "doc_id": doc_id,
            "tokens": len(tokens),
            "unique_terms": len(set(tokens)),
            "total_docs": self._total_docs,
        }

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """使用TF-IDF搜索相关文档"""
        if not self._documents:
            return []
        query_tokens = self._tokenize(query)
        scores: dict[str, float] = {}
        for doc_id in self._documents:
            score = 0.0
            for token in query_tokens:
                tf = self._term_frequency(doc_id, token)
                idf = self._inverse_document_frequency(token)
                score += tf * idf
            if score > 0:
                scores[doc_id] = score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            {"doc_id": doc_id, "score": round(score, 4), "preview": self._documents[doc_id][:100]}
            for doc_id, score in ranked
        ]

    def compute_similarity(self, doc_id_a: str, doc_id_b: str) -> dict[str, Any]:
        """计算两个文档之间的余弦相似度"""
        if doc_id_a not in self._documents or doc_id_b not in self._documents:
            return {"error": "document not found", "similarity": 0}
        terms_a = set(self._tokenize(self._documents[doc_id_a]))
        terms_b = set(self._tokenize(self._documents[doc_id_b]))
        intersection = terms_a & terms_b
        if not intersection:
            return {"doc_a": doc_id_a, "doc_b": doc_id_b, "similarity": 0.0, "shared_terms": 0}
        union = terms_a | terms_b
        jaccard = len(intersection) / len(union)
        return {
            "doc_a": doc_id_a,
            "doc_b": doc_id_b,
            "similarity": round(jaccard, 4),
            "shared_terms": len(intersection),
            "unique_to_a": len(terms_a - terms_b),
            "unique_to_b": len(terms_b - terms_a),
        }

    def get_stats(self) -> dict[str, Any]:
        """获取索引统计信息"""
        return {
            "total_documents": self._total_docs,
            "total_unique_terms": len(self._inverted_index),
            "avg_doc_length": round(self._avg_doc_length, 1),
            "index_size_bytes": sum(len(d) for d in self._documents.values()),
        }

    def _tokenize(self, text: str) -> list[str]:
        return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9\u4e00-\u9fff]+\b", text) if len(w) > 1]

    def _term_frequency(self, doc_id: str, term: str) -> float:
        doc_tokens = self._tokenize(self._documents[doc_id])
        if not doc_tokens:
            return 0
        return doc_tokens.count(term.lower()) / len(doc_tokens)

    def _inverse_document_frequency(self, term: str) -> float:
        docs_with_term = len(self._inverted_index.get(term.lower(), set()))
        if docs_with_term == 0:
            return 0
        import math

        return math.log(self._total_docs / docs_with_term) + 1

class KnowledgeBase(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """知识库引擎"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._entries: dict[str, KnowledgeEntry] = {}
        self._categories: dict[str, CategoryNode] = {}
        self._inverted_index: dict[str, set[str]] = defaultdict(set)
        self._tag_index: dict[str, set[str]] = defaultdict(set)
        self._category_index: dict[str, set[str]] = defaultdict(set)
        self._search_history: list[dict] = []
        self._max_entries = 100000
        self._stop_words = {
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
            "we",
            "you",
            "he",
            "she",
            "they",
            "me",
            "us",
            "him",
            "her",
            "them",
            "my",
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
        }

    def initialize(self) -> None:
        self._register_root_categories()
        logger.info("知识库引擎初始化完成")
        self.record_metrics("unknown.init", 1)
        self.audit("initialized", "Unknown初始化完成")

    def _register_root_categories(self) -> None:
        root_categories = [
            ("architecture", "系统架构", "系统设计、技术选型、架构决策"),
            ("development", "开发指南", "编码规范、开发流程、工具使用"),
            ("operations", "运维手册", "部署、监控、故障排查"),
            ("business", "业务知识", "产品需求、业务规则、领域知识"),
            ("security", "安全策略", "安全规范、合规要求、应急响应"),
        ]
        for cat_id, name, desc in root_categories:
            self._categories[cat_id] = CategoryNode(category_id=cat_id, name=name, description=desc)

    def _tokenize(self, text: str) -> list[str]:
        """分词"""
        # 英文分词
        tokens = re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", text.lower())
        return [t for t in tokens if t not in self._stop_words and len(t) > 1]

    def _build_index(self, entry: KnowledgeEntry) -> None:
        """构建倒排索引"""
        # 内容索引
        tokens = self._tokenize(f"{entry.title} {entry.content}")
        for token in set(tokens):
            self._inverted_index[token].add(entry.entry_id)

        # 标签索引
        for tag in entry.tags:
            self._tag_index[tag.lower()].add(entry.entry_id)

        # 分类索引
        if entry.category:
            self._category_index[entry.category].add(entry.entry_id)

        # 模拟向量嵌入
        entry.embedding = self._simple_embed(tokens)

    def _simple_embed(self, tokens: list[str]) -> list[float]:
        """简单的词频向量嵌入（模拟，实际应用中用 SentenceTransformers）"""
        dim = 64
        vec = [0.0] * dim
        for i, token in enumerate(tokens):
            idx = hash(token) % dim
            vec[idx] += 1.0 / (1 + i * 0.1)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        """余弦相似度"""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(b * b for b in v2))
        return dot / max(n1 * n2, 1e-10)

    @trace_operation("kb_add_entry")
    def add_entry(
        self,
        title: str,
        content: str,
        entry_type: EntryType = EntryType.ARTICLE,
        category: str = "",
        tags: list[str] | None = None,
        author: str = "system",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """添加知识条目"""
        if len(self._entries) >= self._max_entries:
            raise RuntimeError(f"知识库已满 ({self._max_entries})")

        entry_id = f"kb_{uuid.uuid4().hex[:10]}"
        entry = KnowledgeEntry(
            entry_id=entry_id,
            title=title,
            content=content,
            entry_type=entry_type,
            category=category,
            tags=tags or [],
            author=author,
            metadata=metadata or {},
        )
        self._entries[entry_id] = entry
        self._build_index(entry)

        if category and category in self._categories:
            self._categories[category].entry_count += 1

        self.stats["entries_added"] += 1
        metrics_collector.gauge("kb_total_entries", len(self._entries))

        return {
            "entry_id": entry_id,
            "title": title,
            "type": entry_type.value,
            "word_count": entry.word_count,
            "tags": entry.tags,
        }

    @trace_operation("kb_search")
    def search(
        self,
        query: str,
        search_type: SearchType = SearchType.HYBRID,
        category: str | None = None,
        entry_type: EntryType | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """搜索知识库"""
        start = time.time()
        query_tokens = self._tokenize(query)
        query_embedding = self._simple_embed(query_tokens)

        candidate_ids: set[str] = set()

        # 全文搜索候选
        if search_type in (SearchType.FULLTEXT, SearchType.HYBRID):
            for token in query_tokens:
                candidate_ids.update(self._inverted_index.get(token, set()))

        # 标签搜索候选
        if tags:
            for tag in tags:
                candidate_ids.update(self._tag_index.get(tag.lower(), set()))
        elif search_type == SearchType.TAG:
            for token in query_tokens:
                candidate_ids.update(self._tag_index.get(token, set()))

        # 分类过滤
        if category:
            cat_ids = self._category_index.get(category, set())
            candidate_ids = candidate_ids.intersection(cat_ids)

        # 类型过滤
        if entry_type:
            candidate_ids = {
                eid for eid in candidate_ids if eid in self._entries and self._entries[eid].entry_type == entry_type
            }

        # 评分
        scored = []
        for eid in candidate_ids:
            if eid not in self._entries:
                continue
            entry = self._entries[eid]
            score = 0.0

            if search_type in (SearchType.FULLTEXT, SearchType.HYBRID):
                # TF-IDF 简化评分
                title_match = sum(1 for t in query_tokens if t in entry.title.lower())
                content_match = sum(1 for t in query_tokens if t in entry.content.lower())
                tf_score = (title_match * 3 + content_match) / max(len(query_tokens), 1)
                # IDF 简化
                idf_score = sum(
                    math.log(max(len(self._entries), 1) / max(len(self._inverted_index.get(t, set())), 1) + 1)
                    for t in query_tokens
                ) / max(len(query_tokens), 1)
                score = tf_score * idf_score * 0.6

            if search_type in (SearchType.SEMANTIC, SearchType.HYBRID) and entry.embedding:
                sem_score = self._cosine_similarity(query_embedding, entry.embedding)
                score = score + sem_score * 0.4 if search_type == SearchType.HYBRID else sem_score

            if tags:
                tag_match = len(set(t.lower() for t in tags) & set(t.lower() for t in entry.tags))
                score += tag_match * 2.0

            if score > 0:
                # 生成摘要
                snippet = self._generate_snippet(entry.content, query_tokens)
                highlights = [
                    f"...{line.strip()}..."
                    for line in entry.content.split("
")
                    if any(t in line.lower() for t in query_tokens)
                ][:3]
                matched_tags = [t for t in entry.tags if any(t.lower() in qt for qt in query_tokens)]
                scored.append(
                    SearchResult(
                        entry_id=eid,
                        title=entry.title,
                        entry_type=entry.entry_type.value,
                        score=round(score, 4),
                        snippet=snippet,
                        highlights=highlights,
                        matched_tags=matched_tags,
                    )
                )

        scored.sort(key=lambda x: x.score, reverse=True)
        results = scored[:limit]

        duration = (time.time() - start) * 1000
        self._search_history.append(
            {
                "query": query,
                "results": len(results),
                "duration_ms": duration,
                "type": search_type.value,
                "timestamp": time.time(),
            }
        )

        self.stats["searches_total"] += 1

        return {
            "query": query,
            "total_found": len(scored),
            "returned": len(results),
            "search_type": search_type.value,
            "duration_ms": round(duration, 2),
            "results": [
                {
                    "entry_id": r.entry_id,
                    "title": r.title,
                    "type": r.entry_type,
                    "score": r.score,
                    "snippet": r.snippet,
                    "highlights": r.highlights[:2],
                    "matched_tags": r.matched_tags,
                }
                for r in results
            ],
        }

    def _generate_snippet(self, content: str, query_tokens: list[str], max_length: int = 200) -> str:
        """生成搜索摘要"""
        lines = content.split("
")
        for line in lines:
            if any(t in line.lower() for t in query_tokens):
                if len(line) <= max_length:
                    return line.strip()
                idx = line.lower().find(query_tokens[0])
                start = max(0, idx - 50)
                end = min(len(line), idx + max_length)
                return f"...{line[start:end].strip()}..."
        return content[:max_length] + "..."

    @trace_operation("kb_get_entry")
    def get_entry(self, entry_id: str) -> dict[str, Any]:
        if entry_id not in self._entries:
            raise ValueError(f"条目 {entry_id} 不存在")
        e = self._entries[entry_id]
        return {
            "entry_id": e.entry_id,
            "title": e.title,
            "content": e.content,
            "type": e.entry_type.value,
            "category": e.category,
            "tags": e.tags,
            "author": e.author,
            "version": e.version,
            "status": e.status,
            "word_count": e.word_count,
            "metadata": e.metadata,
            "related": e.related_entries,
            "created_at": datetime.fromtimestamp(e.created_at).isoformat(),
            "updated_at": datetime.fromtimestamp(e.updated_at).isoformat(),
        }

    @trace_operation("kb_update_entry")
    def update_entry(
        self,
        entry_id: str,
        title: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        if entry_id not in self._entries:
            raise ValueError(f"条目 {entry_id} 不存在")
        entry = self._entries[entry_id]
        entry.version += 1

        # 重建索引前清除旧索引
        for token in set(self._tokenize(f"{entry.title} {entry.content}")):
            self._inverted_index[token].discard(entry_id)
        for tag in entry.tags:
            self._tag_index[tag.lower()].discard(entry_id)

        if title is not None:
            entry.title = title
        if content is not None:
            entry.content = content
            entry.word_count = len(content.split())
        if tags is not None:
            entry.tags = tags

        entry.updated_at = time.time()
        self._build_index(entry)

        self.stats["entries_updated"] += 1
        return {"entry_id": entry_id, "version": entry.version}

    @trace_operation("kb_delete_entry")
    def delete_entry(self, entry_id: str) -> bool:
        if entry_id not in self._entries:
            raise ValueError(f"条目 {entry_id} 不存在")
        entry = self._entries[entry_id]

        # 清除索引
        for token in set(self._tokenize(f"{entry.title} {entry.content}")):
            self._inverted_index[token].discard(entry_id)
        for tag in entry.tags:
            self._tag_index[tag.lower()].discard(entry_id)
        if entry.category:
            self._category_index[entry.category].discard(entry_id)

        del self._entries[entry_id]
        self.stats["entries_deleted"] += 1
        return True

    @trace_operation("kb_related")
    def find_related(self, entry_id: str, limit: int = 5) -> list[dict]:
        """查找相关条目"""
        if entry_id not in self._entries:
            raise ValueError(f"条目 {entry_id} 不存在")
        entry = self._entries[entry_id]

        # 向量相似度找相关
        if not entry.embedding:
            return []

        scored = []
        for eid, other in self._entries.items():
            if eid == entry_id or not other.embedding:
                continue
            sim = self._cosine_similarity(entry.embedding, other.embedding)
            if sim > 0.3:
                scored.append({"entry_id": eid, "title": other.title, "similarity": round(sim, 4)})

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:limit]

    @trace_operation("kb_batch_import")
    def batch_import(self, entries: list[dict[str, str]]) -> dict[str, Any]:
        """批量导入"""
        imported = 0
        failed = 0
        for e in entries:
            try:
                self.add_entry(
                    title=e["title"],
                    content=e["content"],
                    entry_type=EntryType(e.get("type", "article")),
                    category=e.get("category", ""),
                    tags=e.get("tags", "").split(",") if e.get("tags") else [],
                )
                imported += 1
            except Exception as ex:
                failed += 1
        return {"imported": imported, "failed": failed, "total": len(entries)}

    def get_statistics(self) -> dict[str, Any]:
        """获取知识库统计"""
        type_counts = defaultdict(int)
        cat_counts = defaultdict(int)
        tag_counts = Counter()
        for entry in self._entries.values():
            type_counts[entry.entry_type.value] += 1
            if entry.category:
                cat_counts[entry.category] += 1
            for tag in entry.tags:
                tag_counts[tag] += 1

        return {
            "total_entries": len(self._entries),
            "by_type": dict(type_counts),
            "by_category": dict(cat_counts),
            "top_tags": tag_counts.most_common(20),
            "total_words": sum(e.word_count for e in self._entries.values()),
            "indexed_terms": len(self._inverted_index),
            "index_size": sum(len(ids) for ids in self._inverted_index.values()),
            "searches_total": self.stats.get("searches_total", 0),
            "categories": len(self._categories),
        }

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        params = params or {}
        actions = {
            "add_entry": self.add_entry,
            "search": self.search,
            "get_entry": self.get_entry,
            "update_entry": self.update_entry,
            "delete_entry": self.delete_entry,
            "find_related": self.find_related,
            "batch_import": self.batch_import,
            "get_statistics": self.get_statistics,
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

    def health_check(self) -> dict[str, Any]:
        base = super().health_check()
        base.update(
            {
                "entries": len(self._entries),
                "categories": len(self._categories),
                "indexed_terms": len(self._inverted_index),
                "total_words": sum(e.word_count for e in self._entries.values()),
                "searches": self.stats.get("searches_total", 0),
            }
        )
        return base

    def shutdown(self) -> None:
        self._inverted_index.clear()
        self._tag_index.clear()
        audit_logger.log(
            action="module_shutdown", resource="knowledge_base", details=f"关闭，{len(self._entries)} 个条目"
        )

module_class = KnowledgeBase
