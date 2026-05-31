"""AUTO-EVO-AI V0.1 - 全文搜索引擎（A级）
# Grade: A

基于 DataEngine SQLite 的倒排索引全文搜索，支持中文/英文分词、TF-IDF 评分。
"""
__module_meta__ = {"id":"fts-query","name":"FtsQuery","version":"V0.1","group":"system","grade":"A",
    "tags":["search","fts","fulltext","index"],"description":"基于 DataEngine SQLite 的全文搜索引擎"}
import time, uuid, logging, re, math, json
from pathlib import Path
from typing import Any, Dict, List, Set
from collections import defaultdict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
from core.data_layer import DataEngine
logger = logging.getLogger("evo.fts")

class FtsQuery(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    MODULE_ID = "fts-query"
    MODULE_NAME = "全文搜索"
    VERSION = "v2.0"
    MODULE_LEVEL = "A"

    def __init__(self, config=None):
        super().__init__(config)
        self._db = DataEngine.get("fts_query")
        self._ensure_schema()
        self._max_docs = int((config or {}).get("max_documents", 50_000))
        self._cache_terms: dict[str, dict[str, int]] = defaultdict(dict)
        self._cache_docs: dict[str, dict] = {}
        self._total_docs = 0
        self._load_cache()

    def _ensure_schema(self):
        self._db.create_table("documents", {
            "id": "TEXT PRIMARY KEY",
            "title": "TEXT DEFAULT ''",
            "text": "TEXT DEFAULT ''",
            "metadata": "TEXT DEFAULT '{}'",
            "tokens": "INTEGER DEFAULT 0",
            "unique_terms": "INTEGER DEFAULT 0",
            "indexed_at": "REAL"
        })
        self._db.create_table("terms", {
            "term": "TEXT",
            "doc_id": "TEXT",
            "frequency": "INTEGER DEFAULT 0",
            "PRIMARY KEY": "(term, doc_id)"
        })

    def _load_cache(self):
        docs = self._db.fetch_all("SELECT id,title,text,metadata,tokens,unique_terms,indexed_at FROM documents")
        self._cache_docs = {d["id"]: d for d in docs}
        self._total_docs = len(docs)
        terms = self._db.fetch_all("SELECT term,doc_id,frequency FROM terms")
        for t in terms:
            self._cache_terms[t["term"]][t["doc_id"]] = t["frequency"]
        logger.info("loaded %d docs, %d terms from SQLite", len(self._cache_docs), len(self._cache_terms))

    def _save_doc(self, doc_id: str, title: str, text: str, metadata: str,
                  tokens: int, unique_terms: int, indexed_at: float):
        self._db.upsert("documents", {
            "id": doc_id, "title": title, "text": text,
            "metadata": metadata, "tokens": tokens,
            "unique_terms": unique_terms, "indexed_at": indexed_at
        }, "id")

    def _save_terms_batch(self, term_data: list[dict]):
        if term_data:
            self._db.bulk_insert("terms", term_data)

    def _delete_doc_terms(self, doc_id: str):
        self._db.delete("terms", "doc_id=?", (doc_id,))

    def _tokenize(self, text: str) -> list[str]:
        """中文/英文分词 — 简单 unicode 分词"""
        text = text.lower()
        tokens = []
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f':
                tokens.append(ch)
        for word in re.findall(r'[a-z0-9_]+', text):
            tokens.append(word)
        return tokens

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value, healthy=True,
            module_id=self.MODULE_ID,
            checks={
                "documents": len(self._cache_docs),
                "terms": len(self._cache_terms),
                "engine": "SQLite"
            }
        )

    async def execute(self, action=None, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _tfidf_score(self, doc_id: str, tokens: list[str]) -> float:
        """TF-IDF 相关性评分"""
        score = 0.0
        doc = self._cache_docs.get(doc_id)
        if not doc:
            return 0.0
        doc_len = doc.get("tokens", 0)
        if doc_len == 0:
            return 0.0
        term_counts = defaultdict(int)
        for t in tokens:
            term_counts[t] += 1
        for term, tf in term_counts.items():
            tf_val = tf / doc_len
            df = len(self._cache_terms.get(term, {}))
            idf_val = math.log((self._total_docs + 1) / (df + 1)) + 1 if df > 0 else 0
            score += tf_val * idf_val
        return round(score, 4)

    def _dispatch(self, p: dict) -> dict:
        a = p.get("action", "status")

        if a == "status":
            return {
                "success": True,
                "documents": len(self._cache_docs),
                "terms": len(self._cache_terms),
                "total_docs_indexed": self._total_docs,
                "engine": "SQLite"
            }

        if a == "index":
            text = p.get("text", "")
            doc_id = p.get("doc_id", uuid.uuid4().hex[:12])
            title = p.get("title", "")
            metadata = p.get("metadata", {})
            if not text.strip():
                return {"error": "text is empty"}
            tokens = self._tokenize(text)
            if not tokens:
                return {"error": "no indexable tokens"}
            # 清理旧索引
            if doc_id in self._cache_docs:
                self._delete_doc_terms(doc_id)
            # 词频统计
            term_counts = defaultdict(int)
            for t in tokens:
                term_counts[t] += 1
            # 更新缓存
            for term, count in term_counts.items():
                self._cache_terms[term][doc_id] = count
            # 存储文档
            md_json = json.dumps(metadata, ensure_ascii=False)
            now = time.time()
            self._cache_docs[doc_id] = {
                "id": doc_id, "title": title, "text": text[:100_000],
                "metadata": md_json, "tokens": len(tokens),
                "unique_terms": len(term_counts), "indexed_at": now
            }
            self._save_doc(doc_id, title, text[:100_000], md_json,
                          len(tokens), len(term_counts), now)
            # 批量写索引
            terms_batch = [{"term": t, "doc_id": doc_id, "frequency": c}
                          for t, c in term_counts.items()]
            self._save_terms_batch(terms_batch)
            self._total_docs = max(self._total_docs, len(self._cache_docs))
            if len(self._cache_docs) > self._max_docs:
                oldest = min(self._cache_docs.keys(),
                            key=lambda k: self._cache_docs[k].get("indexed_at", 0))
                self._delete_doc(oldest)
            return {
                "success": True, "doc_id": doc_id,
                "terms": len(term_counts), "tokens": len(tokens)
            }

        if a == "search":
            query = p.get("query", "").lower()
            top_k = int(p.get("top_k", 10))
            min_score = float(p.get("min_score", 0.01))
            if not query.strip():
                return {"success": True, "results": [], "total": 0}
            query_tokens = self._tokenize(query)
            if not query_tokens:
                return {"success": True, "results": [], "total": 0}
            doc_scores: dict[str, set[str]] = defaultdict(set)
            for qt in query_tokens:
                for doc_id in self._cache_terms.get(qt, {}):
                    doc_scores[doc_id].add(qt)
            scored = []
            for doc_id, matched_terms in doc_scores.items():
                doc = self._cache_docs.get(doc_id)
                if not doc:
                    continue
                doc_tokens = [qt for qt in query_tokens if qt in matched_terms]
                score = self._tfidf_score(doc_id, doc_tokens)
                if score < min_score:
                    continue
                scored.append({
                    "doc_id": doc_id, "score": score,
                    "title": doc.get("title", ""),
                    "snippet": doc.get("text", "")[:200],
                    "metadata": json.loads(doc.get("metadata", "{}"))
                })
            scored.sort(key=lambda x: -x["score"])
            results = scored[:top_k]
            return {
                "success": True, "query": query,
                "results": results, "total": len(results),
                "total_matched": len(doc_scores)
            }

        if a == "delete":
            doc_id = p.get("doc_id", "")
            if doc_id not in self._cache_docs:
                return {"error": f"doc_id not found: {doc_id}"}
            self._delete_doc(doc_id)
            return {"success": True, "deleted": doc_id}

        if a == "get":
            doc_id = p.get("doc_id", "")
            doc = self._cache_docs.get(doc_id)
            if not doc:
                return {"error": f"doc_id not found: {doc_id}"}
            return {
                "success": True, "doc_id": doc_id,
                "title": doc.get("title", ""),
                "text": doc.get("text", "")[:10_000],
                "metadata": json.loads(doc.get("metadata", "{}")),
                "tokens": doc.get("tokens", 0),
                "unique_terms": doc.get("unique_terms", 0),
                "engine": "SQLite"
            }

        if a == "stats":
            term_docs = [(term, len(postings)) for term, postings in self._cache_terms.items()]
            term_docs.sort(key=lambda x: -x[1])
            top_terms = [{"term": t, "docs": d} for t, d in term_docs[:20]]
            avg_tokens = round(sum(d.get("tokens", 0) for d in self._cache_docs.values()) / max(len(self._cache_docs), 1), 1)
            return {
                "success": True, "documents": len(self._cache_docs),
                "unique_terms": len(self._cache_terms),
                "total_docs_indexed": self._total_docs,
                "avg_tokens_per_doc": avg_tokens,
                "top_terms": top_terms,
                "engine": "SQLite"
            }

        if a == "clear":
            self._db.execute("DELETE FROM terms")
            self._db.execute("DELETE FROM documents")
            self._cache_terms.clear()
            self._cache_docs.clear()
            self._total_docs = 0
            return {"success": True, "cleared": True}

        if a == "search_advanced":
            query = p.get("query", "").lower()
            top_k = int(p.get("top_k", 10))
            min_score = float(p.get("min_score", 0.01))
            filters = p.get("filters", {})
            if not query.strip():
                results = []
                for doc_id, doc in list(self._cache_docs.items())[:top_k]:
                    results.append({
                        "doc_id": doc_id, "score": 0,
                        "title": doc.get("title", ""),
                        "snippet": doc.get("text", "")[:200]
                    })
                return {"success": True, "results": results, "total": len(results), "query": query}
            query_tokens = self._tokenize(query)
            doc_scores: dict[str, set[str]] = defaultdict(set)
            for qt in query_tokens:
                for doc_id in self._cache_terms.get(qt, {}):
                    doc_scores[doc_id].add(qt)
            scored = []
            for doc_id, matched_terms in doc_scores.items():
                doc = self._cache_docs.get(doc_id)
                if not doc: continue
                # 过滤
                if filters:
                    md = json.loads(doc.get("metadata", "{}"))
                    skip = False
                    for fk, fv in filters.items():
                        if md.get(fk) != fv:
                            skip = True
                            break
                    if skip: continue
                doc_tokens = [qt for qt in query_tokens if qt in matched_terms]
                score = self._tfidf_score(doc_id, doc_tokens)
                if score < min_score: continue
                scored.append({
                    "doc_id": doc_id, "score": score,
                    "title": doc.get("title", ""),
                    "snippet": doc.get("text", "")[:200],
                    "metadata": json.loads(doc.get("metadata", "{}"))
                })
            scored.sort(key=lambda x: -x["score"])
            return {"success": True, "query": query,
                    "results": scored[:top_k], "total": len(scored)}

        return {"error": f"unknown action: {a}"}

    def _delete_doc(self, doc_id: str):
        self._cache_docs.pop(doc_id, None)
        self._delete_doc_terms(doc_id)
        # 从缓存中移除该 doc 的所有 term 记录
        for term, postings in list(self._cache_terms.items()):
            postings.pop(doc_id, None)
            if not postings:
                del self._cache_terms[term]

    async def shutdown(self) -> None:
        self._cache_terms.clear()
        self._cache_docs.clear()
        self.status = ModuleStatus.STOPPED

module_class = FtsQuery
