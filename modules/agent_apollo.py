"""
AUTO-EVO-AI V0.1 — Apollo AI智能体
Grade: A (生产级) | Category: AI智能体
职责：知识管理、文档索引、语义搜索、知识图谱、智能问答
"""

__module_meta__ = {
    "id": "agent-apollo",
    "name": "Agent Apollo",
    "version": "V0.1",
    "group": "agent",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "title", "type": "string", "required": True, "description": ""},
        {"name": "content", "type": "string", "required": True, "description": ""},
        {"name": "doc_type", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
    ],
    "triggers": [{"type": "event", "config": {"on": "agent_apollo.task.request"}}],
    "depends_on": [],
    "tags": ["engine", "manager", "multi-agent", "agent"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — Apollo AI智能体 Grade: A (生产级) | Category: AI智能体",
}

import os
import asyncio
import time
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import (
        EnterpriseModulenterpriseModule,
        module_class,
        CircuitBreakerMixin,
        RateLimiterMixin,
    )
    from modules._base.tracing import trace_operation
    from modules._base.metrics import prometheus_timer, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("agent_apollo")

class DocType(Enum):
    DOC = "doc"
    WIKI = "wiki"
    API = "api"
    FAQ = "faq"
    RUNBOOK = "runbook"

@dataclass
class KnowledgeDoc:
    """知识文档"""

    doc_id: str
    title: str
    content: str
    doc_type: DocType = DocType.DOC
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    score: float = 0.0

@dataclass
class QARecord:
    """问答记录"""

    question: str
    answer: str
    doc_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    asked_at: float = field(default_factory=time.time)

class AgentApolloManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Apollo智能体 - 知识管理"""

    MODULE_ID = "agent_apollo"
    MODULE_NAME = "Apollo智能体"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._docs: Dict[str, KnowledgeDoc] = {}
        self._qa_history: List[QARecord] = []
        self._doc_counter: int = 0
        self._index: Dict[str, List[str]] = {}  # word -> [doc_ids]

    def initialize(self) -> None:
        try:
            self._docs.clear()
            self._index.clear()
            self._qa_history.clear()
            # 默认知识库
            defaults = [
                (
                    "系统架构",
                    "BGOS采用微服务架构，核心模块包括网关、认证、数据服务、AI引擎等，使用K8s编排部署。",
                    ["架构", "BGOS", "微服务"],
                ),
                (
                    "API认证",
                    "所有API请求需通过OAuth2.0认证，Token有效期2小时，支持刷新机制。",
                    ["认证", "API", "OAuth"],
                ),
                (
                    "故障处理",
                    "系统内置自愈机制，检测到故障后自动触发诊断和修复流程，平均恢复时间<30秒。",
                    ["故障", "自愈", "运维"],
                ),
            ]
            for title, content, tags in defaults:
                self._add_doc(title, content, DocType.WIKI, tags)
            if self._audit:
                self._audit.log("apollo_initialized", {"docs": len(self._docs)})
            self.stats.success_count += 1
            logger.info("Apollo智能体初始化完成")
        except Exception as e:
            logger.error(f"Apollo初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("agent_apollo_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        start = time.time()
        ok = False
        err = None

        try:
            if action == "add_doc":
                title = params.get("title", "")
                content = params.get("content", "")
                doc_type = params.get("doc_type", "doc")
                tags = params.get("tags", [])
                if not title or not content:
                    return {"success": False, "error": "Missing: title, content"}
                doc = self._add_doc(title, content, DocType(doc_type), tags)
                ok = True
                return {"success": True, "result": {"doc_id": doc.doc_id, "title": doc.title}}

            elif action == "search":
                query = params.get("query", "")
                limit = params.get("limit", 10)
                if not query:
                    return {"success": False, "error": "Missing: query"}
                results = self._search(query, limit)
                ok = True
                return {"success": True, "result": results}

            elif action == "ask":
                question = params.get("question", "")
                if not question:
                    return {"success": False, "error": "Missing: question"}
                answer = self._answer(question)
                ok = True
                return {"success": True, "result": answer}

            elif action == "list_docs":
                doc_type = params.get("doc_type", "")
                docs = self._docs.values()
                if doc_type:
                    docs = [d for d in docs if d.doc_type.value == doc_type]
                return {
                    "success": True,
                    "result": [
                        {
                            "doc_id": d.doc_id,
                            "title": d.title,
                            "type": d.doc_type.value,
                            "tags": d.tags,
                            "version": d.version,
                        }
                        for d in sorted(docs, key=lambda x: x.updated_at, reverse=True)[:50]
                    ],
                }

            elif action == "get_doc":
                doc_id = params.get("doc_id")
                if not doc_id:
                    return {"success": False, "error": "Missing: doc_id"}
                doc = self._docs.get(doc_id)
                if not doc:
                    return {"success": False, "error": "Doc not found"}
                return {
                    "success": True,
                    "result": {
                        "doc_id": doc.doc_id,
                        "title": doc.title,
                        "content": doc.content,
                        "type": doc.doc_type.value,
                        "tags": doc.tags,
                    },
                }

            elif action == "delete_doc":
                doc_id = params.get("doc_id")
                if not doc_id:
                    return {"success": False, "error": "Missing: doc_id"}
                doc = self._docs.pop(doc_id, None)
                if doc:
                    self._rebuild_index()
                    ok = True
                    return {"success": True, "result": {"deleted": doc_id}}
                return {"success": False, "error": "Doc not found"}

            elif action == "get_stats":
                type_counts = {}
                for d in self._docs.values():
                    t = d.doc_type.value
                    type_counts[t] = type_counts.get(t, 0) + 1
                return {
                    "success": True,
                    "result": {
                        "total_docs": len(self._docs),
                        "by_type": type_counts,
                        "qa_history": len(self._qa_history),
                        "index_terms": len(self._index),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "docs": len(self._docs),
            "index_terms": len(self._index),
            "qa_history": len(self._qa_history),
        }

    def shutdown(self) -> None:
        self._docs.clear()
        self._index.clear()
        self._qa_history.clear()

    def _add_doc(self, title: str, content: str, doc_type: DocType, tags: List[str]) -> KnowledgeDoc:
        self._doc_counter += 1
        doc_id = f"doc_{self._doc_counter}"
        doc = KnowledgeDoc(doc_id=doc_id, title=title, content=content, doc_type=doc_type, tags=tags)
        self._docs[doc_id] = doc
        self._index_doc(doc)
        if self._audit:
            self._audit.log("doc_added", {"doc_id": doc_id, "title": title, "type": doc_type.value})
        self.stats.success_count += 1
        return doc

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        text = text.lower()
        words = re.findall(r"[\w\u4e00-\u9fff]{2,}", text)
        return words

    def _index_doc(self, doc: KnowledgeDoc):
        for word in self._tokenize(doc.title + " " + " ".join(doc.tags) + " " + doc.content):
            if word not in self._index:
                self._index[word] = []
            if doc.doc_id not in self._index[word]:
                self._index[word].append(doc.doc_id)

    def _rebuild_index(self):
        self._index.clear()
        for doc in self._docs.values():
            self._index_doc(doc)

    def _search(self, query: str, limit: int = 10) -> List[Dict]:
        """语义搜索"""
        query_terms = self._tokenize(query)
        doc_scores: Dict[str, float] = {}
        for term in query_terms:
            for doc_id in self._index.get(term, []):
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1
        results = []
        for doc_id, score in sorted(doc_scores.items(), key=lambda x: -x[1])[:limit]:
            doc = self._docs.get(doc_id)
            if doc:
                results.append(
                    {
                        "doc_id": doc_id,
                        "title": doc.title,
                        "type": doc.doc_type.value,
                        "relevance_score": score,
                        "tags": doc.tags,
                        "snippet": doc.content[:100] + ("..." if len(doc.content) > 100 else ""),
                    }
                )
        return results

    def _answer(self, question: str) -> Dict:
        """智能问答"""
        results = self._search(question, 3)
        if not results:
            return {
                "question": question,
                "answer": "未找到相关知识，建议补充相关文档。",
                "confidence": 0.0,
                "sources": [],
            }
        # 构建答案
        parts = []
        source_ids = []
        for r in results:
            doc = self._docs.get(r["doc_id"])
            if doc:
                parts.append(doc.content[:200])
                source_ids.append(doc.doc_id)
        answer = "根据知识库检索结果：\n" + "\n---\n".join(parts[:3])
        confidence = min(0.95, 0.5 + len(results) * 0.15)
        self._qa_history.append(QARecord(question=question, answer=answer, doc_ids=source_ids, confidence=confidence))
        if len(self._qa_history) > 500:
            self._qa_history = self._qa_history[-300:]
        return {
            "question": question,
            "answer": answer,
            "confidence": round(confidence, 3),
            "sources": [{"doc_id": sid, "title": self._docs[sid].title} for sid in source_ids if sid in self._docs],
        }

module_class = AgentApolloManager

class KnowledgeIndexEngine(object):
    """知识索引引擎 - 倒排索引、TF-IDF评分、语义相似度"""

    def __init__(self):
        self._inverted_index: Dict[str, Dict[str, int]] = {}
        self._doc_vectors: Dict[str, Dict[str, float]] = {}
        self._idf_cache: Dict[str, float] = {}
        self._doc_count: int = 0
        self._avg_doc_len: float = 0.0

    def add_document(self, doc_id: str, title: str, content: str, tags: List[str] = None) -> None:
        """索引文档"""
        self._doc_count += 1
        text = (title + " " + content).lower()
        words = self._tokenize(text)
        self._avg_doc_len = (self._avg_doc_len * (self._doc_count - 1) + len(words)) / self._doc_count
        tf: Dict[str, int] = {}
        for w in words:
            tf[w] = tf.get(w, 0) + 1
        vector: Dict[str, float] = {}
        for w, count in tf.items():
            if w not in self._inverted_index:
                self._inverted_index[w] = {}
            self._inverted_index[w][doc_id] = count
            vector[w] = count / max(len(words), 1)
        if tags:
            for tag in tags:
                t = tag.lower()
                if t not in self._inverted_index:
                    self._inverted_index[t] = {}
                self._inverted_index[t][doc_id] = 10
                vector[t] = 1.0
        self._doc_vectors[doc_id] = vector
        self._update_idf()

    def remove_document(self, doc_id: str) -> None:
        """移除文档索引"""
        if doc_id not in self._doc_vectors:
            return
        del self._doc_vectors[doc_id]
        for w in list(self._inverted_index.keys()):
            if doc_id in self._inverted_index[w]:
                del self._inverted_index[w][doc_id]
                if not self._inverted_index[w]:
                    del self._inverted_index[w]
        self._doc_count = max(0, self._doc_count - 1)
        self._update_idf()

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索文档"""
        query_words = self._tokenize(query.lower())
        scores: Dict[str, float] = {}
        for w in query_words:
            postings = self._inverted_index.get(w, {})
            idf = self._idf_cache.get(w, 1.0)
            for doc_id, tf in postings.items():
                if doc_id not in scores:
                    scores[doc_id] = 0.0
                scores[doc_id] += tf * idf
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return [{"doc_id": did, "score": round(s, 4)} for did, s in ranked[:top_k]]

    def suggest(self, prefix: str, limit: int = 10) -> List[str]:
        """自动补全建议"""
        prefix = prefix.lower()
        suggestions = [w for w in self._inverted_index if w.startswith(prefix)]
        return sorted(suggestions, key=lambda w: -len(self._inverted_index[w]))[:limit]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "documents": self._doc_count,
            "vocab_size": len(self._inverted_index),
            "avg_doc_len": round(self._avg_doc_len, 1),
        }

    def _tokenize(self, text: str) -> List[str]:
        import re

        return re.findall(r"\w+", text)

    def _update_idf(self) -> None:
        for w, postings in self._inverted_index.items():
            self._idf_cache[w] = round(1.0 + 1.0 / (1.0 + len(postings)), 4)

    def get_similar(self, doc_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """找出与给定文档最相似的文档"""
        if doc_id not in self._doc_vectors:
            return []
        target = self._doc_vectors[doc_id]
        similarities: List[Tuple[str, float]] = []
        for other_id, other_vec in self._doc_vectors.items():
            if other_id == doc_id:
                continue
            score = self._cosine_sim(target, other_vec)
            if score > 0:
                similarities.append((other_id, score))
        similarities.sort(key=lambda x: -x[1])
        return [{"doc_id": did, "similarity": round(s, 4)} for did, s in similarities[:top_k]]

    def batch_search(self, queries: List[str], top_k: int = 3) -> List[List[Dict]]:
        """批量搜索"""
        return [self.search(q, top_k) for q in queries]

    def get_document_terms(self, doc_id: str) -> Dict[str, Any]:
        """获取文档的词项统计"""
        if doc_id not in self._doc_vectors:
            return {"doc_id": doc_id, "terms": 0}
        vec = self._doc_vectors[doc_id]
        top_terms = sorted(vec.items(), key=lambda x: -x[1])[:20]
        return {
            "doc_id": doc_id,
            "unique_terms": len(vec),
            "top_terms": [{"term": t, "weight": round(w, 4)} for t, w in top_terms],
        }

    def rebuild_index(self, documents: List[Dict]) -> int:
        """从文档列表重建整个索引"""
        self._inverted_index.clear()
        self._doc_vectors.clear()
        self._idf_cache.clear()
        self._doc_count = 0
        for doc in documents:
            self.add_document(doc["id"], doc.get("title", ""), doc.get("content", ""), doc.get("tags", []))
        return self._doc_count

    def get_trending_terms(self, top_n: int = 20) -> List[Dict]:
        """获取高频词汇"""
        term_freqs = [(w, sum(postings.values())) for w, postings in self._inverted_index.items()]
        term_freqs.sort(key=lambda x: -x[1])
        return [{"term": w, "frequency": f, "doc_count": len(self._inverted_index[w])} for w, f in term_freqs[:top_n]]

    def export_index(self) -> Dict[str, Any]:
        """导出索引数据"""
        return {
            "doc_count": self._doc_count,
            "vocab_size": len(self._inverted_index),
            "doc_ids": list(self._doc_vectors.keys()),
            "idf_entries": len(self._idf_cache),
        }

    @staticmethod
    def _cosine_sim(v1: Dict[str, float], v2: Dict[str, float]) -> float:
        """余弦相似度"""
        common = set(v1.keys()) & set(v2.keys())
        if not common:
            return 0.0
        dot = sum(v1[k] * v2[k] for k in common)
        n1 = sum(v**2 for v in v1.values()) ** 0.5
        n2 = sum(v**2 for v in v2.values()) ** 0.5
        return dot / max(n1 * n2, 1e-8)

class KnowledgeSyncManager(object):
    """知识同步管理器 - 多源同步、增量更新、冲突解决"""

    def __init__(self):
        self._sources: Dict[str, Dict] = {}
        self._sync_history: List[Dict] = []
        self._conflicts: List[Dict] = []
        self._last_sync: Dict[str, float] = {}

    def register_source(self, source_id: str, source_type: str, endpoint: str) -> None:
        """注册知识源"""
        self._sources[source_id] = {
            "type": source_type,
            "endpoint": endpoint,
            "status": "active",
            "registered_at": time.time(),
        }

    def sync_source(self, source_id: str, documents: List[Dict]) -> Dict[str, Any]:
        """同步知识源"""
        if source_id not in self._sources:
            return {"error": "source not found", "source_id": source_id}
        synced = 0
        skipped = 0
        for doc in documents:
            doc_id = doc.get("id", f"{source_id}-{synced}")
            if doc_id in self._last_sync:
                skipped += 1
                continue
            synced += 1
            self._last_sync[doc_id] = time.time()
        record = {
            "source_id": source_id,
            "synced": synced,
            "skipped": skipped,
            "timestamp": time.time(),
        }
        self._sync_history.append(record)
        return record

    def get_sync_status(self, source_id: str = None) -> Dict[str, Any]:
        """获取同步状态"""
        if source_id:
            records = [r for r in self._sync_history if r["source_id"] == source_id]
            return {"source_id": source_id, "sync_count": len(records), "last_sync": records[-1] if records else None}
        return {
            "sources": len(self._sources),
            "total_syncs": len(self._sync_history),
            "total_docs": len(self._last_sync),
            "conflicts": len(self._conflicts),
        }

    def resolve_conflict(self, conflict_id: str, resolution: str) -> bool:
        """解决冲突"""
        for c in self._conflicts:
            if c.get("id") == conflict_id:
                c["resolution"] = resolution
                c["resolved_at"] = time.time()
                return True
        return False

    def get_sync_history(self, limit: int = 50) -> List[Dict]:
        return self._sync_history[-limit:]

    def list_sources(self) -> List[Dict]:
        """列出所有知识源"""
        return [{"source_id": sid, "type": s["type"], "status": s["status"]} for sid, s in self._sources.items()]

    def remove_source(self, source_id: str) -> bool:
        """移除知识源"""
        if source_id in self._sources:
            del self._sources[source_id]
            self._sync_history = [r for r in self._sync_history if r["source_id"] != source_id]
            return True
        return False

    def get_source_metrics(self, source_id: str) -> Dict[str, Any]:
        """获取知识源指标"""
        records = [r for r in self._sync_history if r["source_id"] == source_id]
        total_synced = sum(r["synced"] for r in records)
        total_skipped = sum(r["skipped"] for r in records)
        return {
            "source_id": source_id,
            "total_synced": total_synced,
            "total_skipped": total_skipped,
            "sync_runs": len(records),
        }

    def analyze_knowledge_coverage(self) -> Dict[str, Any]:
        """分析知识库覆盖率：分类分布、知识缺口、冗余检测"""
        indices = self._indices if hasattr(self, "_indices") else {}
        if not indices:
            return {"total_indices": 0, "coverage": {}}
        total_docs = 0
        category_counts: Dict[str, int] = {}
        for idx_name, idx_data in indices.items():
            count = idx_data.get("doc_count", 0) if isinstance(idx_data, dict) else 0
            total_docs += count
            category = idx_data.get("category", "uncategorized") if isinstance(idx_data, dict) else "uncategorized"
            category_counts[category] = category_counts.get(category, 0) + count
        sorted_cats = sorted(category_counts.items(), key=lambda x: -x[1])
        if total_docs > 0:
            dominant_ratio = sorted_cats[0][1] / total_docs if sorted_cats else 0
        else:
            dominant_ratio = 0
        return {
            "total_documents": total_docs,
            "total_indices": len(indices),
            "category_distribution": [
                {"category": c, "count": n, "ratio": round(n / max(total_docs, 1), 3)} for c, n in sorted_cats
            ],
            "dominant_category_ratio": round(dominant_ratio, 3),
            "balance_score": round(1 - dominant_ratio, 3),
        }
