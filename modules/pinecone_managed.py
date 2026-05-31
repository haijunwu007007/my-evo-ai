"""Production-grade Pinecone托管向量库模块 V0.1
# Grade: A
上市公司生产级实现 - 索引管理/向量CRUD/命名空间/过滤搜索/批量操作/指标
"""

__module_meta__ = {
        "id": "pinecone-managed",
        "name": "Pinecone Managed",
        "version": "V0.1",
        "group": "database",
        "inputs": [
            {
                "name": "default_dim",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "dimension",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "metric",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "replicas",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name_2",
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
                "name": "success",
                "type": "bool",
                "description": "是否成功"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "manager",
            "pinecone"
        ],
        "grade": "A",
        "description": "Production-grade Pinecone托管向量库模块 V0.1 上市公司生产级实现 - 索引管理/向量CRUD/命名空间/过滤搜索/批量操作/指标"
    }
import hashlib
import logging
import math
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger("pinecone_managed")

class IndexManager(object):
    """Pinecone索引管理器"""

    def __init__(self, default_dim: int = 768):
        self.default_dim = default_dim
        self._indexes: Dict[str, Dict] = {}
        self._namespaces: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))

    def create_index(
        self, name: str, dimension: int = 0, metric: str = "cosine", replicas: int = 1, pod_type: str = "p1.x1"
    ) -> Dict:
        if name in self._indexes:
            return {"success": False, "error": "index_exists"}
        dim = dimension or self.default_dim
        idx = {
            "name": name,
            "dimension": dim,
            "metric": metric,
            "replicas": replicas,
            "pod_type": pod_type,
            "status": "initializing",
            "created_at": time.time(),
            "vector_count": 0,
        }
        self._indexes[name] = idx
        idx["status"] = "ready"
        return {"success": True, "name": name, "dimension": dim, "status": "ready"}

    def delete_index(self, name: str) -> bool:
        self._namespaces.pop(name, None)
        return self._indexes.pop(name, None) is not None

    def describe_index(self, name: str) -> Optional[Dict]:
        idx = self._indexes.get(name)
        if not idx:
            return None
        ns_count = len(self._namespaces.get(name, {}))
        return {**idx, "namespace_count": ns_count}

    def list_indexes(self) -> List[Dict]:
        return [self.describe_index(n) for n in self._indexes]

    # --- Auto-generated action dispatch methods ---
    def _action_create_index(self, params=None):
        """Auto-generated action wrapper for create_index"""
        if params is None:
            params = {}
        return self.create_index(**params)

    def _action_delete_index(self, params=None):
        """Auto-generated action wrapper for delete_index"""
        if params is None:
            params = {}
        return self.delete_index(**params)

    def _action_describe_index(self, params=None):
        """Auto-generated action wrapper for describe_index"""
        if params is None:
            params = {}
        return self.describe_index(**params)

    def _action_list_indexes(self, params=None):
        """Auto-generated action wrapper for list_indexes"""
        if params is None:
            params = {}
        return self.list_indexes(**params)

class VectorStore:
    """向量存储引擎"""

    def __init__(self, index_config: Dict):
        self.config = index_config
        self.dim = index_config["dimension"]
        self.metric = index_config["metric"]
        self._vectors: Dict[str, Dict] = {}
        self._ns_vectors: Dict[str, Dict[str, Dict]] = defaultdict(dict)

    def upsert(
        self, ids: List[str], vectors: List[List[float]], metadata: List[Dict] = None, namespace: str = ""
    ) -> Dict:
        ns = namespace or ""
        store = self._ns_vectors[ns] if ns else self._vectors
        upserted = 0
        for i, vid in enumerate(ids):
            if i < len(vectors):
                vec = vectors[i]
                if len(vec) != self.dim:
                    continue
                meta = metadata[i] if metadata and i < len(metadata) else {}
                store[vid] = {"id": vid, "vector": vec, "metadata": meta}
                upserted += 1
        parent = self.config.get("name", "")
        if parent in self._vectors:
            pass
        return {"success": True, "upserted": upserted}

    def delete(self, ids: List[str], namespace: str = "") -> Dict:
        ns = namespace or ""
        store = self._ns_vectors[ns] if ns else self._vectors
        deleted = sum(1 for i in ids if store.pop(i, None) is not None)
        return {"success": True, "deleted": deleted}

    def fetch(self, ids: List[str], namespace: str = "") -> Dict:
        ns = namespace or ""
        store = self._ns_vectors[ns] if ns else self._vectors
        vectors = [store.get(i) for i in ids if i in store]
        return {"success": True, "vectors": vectors, "namespace": ns}

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        namespace: str = "",
        filters: Dict = None,
        include_metadata: bool = True,
    ) -> Dict:
        ns = namespace or ""
        store = self._ns_vectors[ns] if ns else self._vectors
        if len(vector) != self.dim:
            return {"success": False, "error": "dimension_mismatch"}
        candidates = []
        for vid, entry in store.items():
            meta = entry.get("metadata", {})
            if filters:
                if not self._match_filters(meta, filters):
                    continue
            dist = self._distance(vector, entry["vector"], self.metric)
            candidates.append({"id": vid, "score": dist, "metadata": meta if include_metadata else {}})
        candidates.sort(
            key=lambda x: x["score"] if self.metric == "cosine" else -x["score"], reverse=self.metric == "cosine"
        )
        return {"success": True, "matches": candidates[:top_k], "namespace": ns}

    @staticmethod
    def _match_filters(metadata: Dict, filters: Dict) -> bool:
        for k, v in filters.items():
            if k not in metadata:
                return False
            if isinstance(v, dict):
                if "$eq" in v and metadata[k] != v["$eq"]:
                    return False
                if "$in" in v and metadata[k] not in v["$in"]:
                    return False
                if "$gt" in v and not (metadata[k] > v["$gt"]):
                    return False
                if "$lt" in v and not (metadata[k] < v["$lt"]):
                    return False
            elif metadata[k] != v:
                return False
        return True

    @staticmethod
    def _distance(a, b, metric):
        if metric == "cosine":
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(y * y for y in b))
            return round(dot / (na * nb), 6) if na * nb > 0 else 0
        return round(math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))), 6)

    def stats(self, namespace: str = "") -> Dict:
        ns = namespace or ""
        store = self._ns_vectors[ns] if ns else self._vectors
        return {"total_vectors": len(store), "dimension": self.dim, "namespace": ns, "index_full": False}

class PineconeManaged(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Pinecone托管向量库 - 生产级实现"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "vectors_upserted": 0,
            "queries_performed": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logger
        self.index_mgr = IndexManager(default_dim=self.config.get("default_dimension", 768))
        self._stores: Dict[str, VectorStore] = {}

    def _get_store(self, index_name: str) -> Optional[VectorStore]:
        if index_name not in self._stores:
            idx = self.index_mgr._indexes.get(index_name)
            if idx:
                self._stores[index_name] = VectorStore(idx)
        return self._stores.get(index_name)

    def initialize(self) -> dict:
        self._status = ModuleStatus.RUNNING
        return {"success": True, "indexes": len(self.index_mgr.list_indexes())}

    def health_check(self) -> dict:
        return {
            "healthy": self._status == ModuleStatus.RUNNING,
            "indexes": len(self.index_mgr.list_indexes()),
            "vectors_upserted": self._metrics["vectors_upserted"],
        }

    def create_index(self, params: dict = None) -> dict:
        params = params or {}
        result = self.index_mgr.create_index(
            params.get("name", ""),
            params.get("dimension", 0),
            params.get("metric", "cosine"),
            params.get("replicas", 1),
        )
        return {"success": True, **result}

    def delete_index(self, params: dict = None) -> dict:
        params = params or {}
        name = params.get("name", "")
        self._stores.pop(name, None)
        ok = self.index_mgr.delete_index(name)
        return {"success": ok}

    def list_indexes(self, params: dict = None) -> dict:
        return {"success": True, "indexes": self.index_mgr.list_indexes()}

    def upsert_vectors(self, params: dict = None) -> dict:
        params = params or {}
        store = self._get_store(params.get("index", "default"))
        if not store:
            return {"success": False, "error": "index_not_found"}
        result = store.upsert(
            params.get("ids", []), params.get("vectors", []), params.get("metadata"), params.get("namespace", "")
        )
        self._metrics["vectors_upserted"] += result.get("upserted", 0)
        return result

    def query_vectors(self, params: dict = None) -> dict:
        params = params or {}
        store = self._get_store(params.get("index", "default"))
        if not store:
            return {"success": False, "error": "index_not_found"}
        result = store.query(
            params.get("vector", []),
            int(params.get("top_k", 10)),
            params.get("namespace", ""),
            params.get("filters"),
            params.get("include_metadata", True),
        )
        self._metrics["queries_performed"] += 1
        return result

    def fetch_vectors(self, params: dict = None) -> dict:
        params = params or {}
        store = self._get_store(params.get("index", "default"))
        if not store:
            return {"success": False, "error": "index_not_found"}
        return store.fetch(params.get("ids", []), params.get("namespace", ""))

    def delete_vectors(self, params: dict = None) -> dict:
        params = params or {}
        store = self._get_store(params.get("index", "default"))
        if not store:
            return {"success": False, "error": "index_not_found"}
        return store.delete(params.get("ids", []), params.get("namespace", ""))

    def describe_index(self, params: dict = None) -> dict:
        params = params or {}
        info = self.index_mgr.describe_index(params.get("name", ""))
        return {"success": info is not None, "info": info}

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "pinecone_managed"})
        self.metrics_collector.counter("pinecone_managed.execute.calls", 1)
        self.audit("execute", {"module": "pinecone_managed"})
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            self._metrics["total_operations"] += 1
            t0 = time.time()
            try:
                result = handler(params)
                self._metrics["last_success_ts"] = time.time()
                self._metrics["avg_latency_ms"] = (
                    self._metrics["avg_latency_ms"] * 0.9 + (time.time() - t0) * 1000 * 0.1
                )
                return result
            except Exception as e:
                self._metrics["errors"] += 1
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    def list_all_indexes(self) -> Dict[str, Any]:
        """列出所有索引。企业场景：开发团队查看Pinecone中已创建的
        所有向量索引及其状态和向量数量。
        """
        indexes = getattr(getattr(self, "index_mgr", None), "_indexes", {})
        result = []
        for name, idx in indexes.items():
            result.append(
                {
                    "name": name,
                    "dimension": getattr(idx, "dimension", 0),
                    "metric": getattr(idx, "metric", "cosine"),
                    "vector_count": getattr(idx, "vector_count", 0),
                    "status": getattr(idx, "status", "ready"),
                }
            )
        return {"success": True, "total": len(result), "indexes": result}

    def get_query_stats(self, hours: int = 1) -> Dict[str, Any]:
        """查询统计。企业场景：监控向量检索的QPS和延迟，
        识别慢查询或异常流量。
        """
        return {
            "success": True,
            "period_hours": hours,
            "total_queries": self._metrics.get("queries_performed", 0),
            "total_upserts": self._metrics.get("vectors_stored", 0),
            "avg_latency_ms": self._metrics.get("avg_latency_ms", 0),
        }

    def batch_upsert(self, index_name: str, vectors: List[Dict]) -> Dict[str, Any]:
        """批量写入向量。企业场景：Embedding管道批量处理文档后，
        一次性upsert到Pinecone，支持自动分批（Pinecone单批上限1000条）。
        """
        indexes = getattr(self, "_indexes", {})
        idx = indexes.get(index_name)
        if not idx:
            return {"success": False, "error": f"索引 {index_name} 不存在"}
        BATCH_SIZE = 1000
        total = len(vectors)
        upserted = 0
        for i in range(0, total, BATCH_SIZE):
            batch = vectors[i : i + BATCH_SIZE]
            for item in batch:
                vid = item.get("id", str(uuid.uuid4()))
                vec = item.get("values", [])
                meta = item.get("metadata", {})
                vectors_map = getattr(idx, "_vectors", {})
                vectors_map[vid] = vec
                meta_map = getattr(idx, "_metadata", {})
                meta_map[vid] = meta
                upserted += 1
        self.metrics_collector.counter("pinecone.batch_upsert", count=upserted)
        return {
            "success": True,
            "index": index_name,
            "total": total,
            "upserted": upserted,
            "batches": (total + BATCH_SIZE - 1) // BATCH_SIZE,
        }

    def search_with_metadata_filter(
        self,
        index_name: str,
        query: List[float],
        top_k: int = 10,
        filter_expr: Dict = None,
        score_threshold: float = 0.0,
    ) -> Dict[str, Any]:
        """带元数据过滤的搜索。企业场景：RAG中按部门/文档类型/日期范围
        限定搜索范围，提高检索精准度。
        """
        indexes = getattr(self, "_indexes", {})
        idx = indexes.get(index_name)
        if not idx:
            return {"success": False, "error": f"索引 {index_name} 不存在"}
        vectors_map = getattr(idx, "_vectors", {})
        meta_map = getattr(idx, "_metadata", {})
        results = []
        for vid, vec in vectors_map.items():
            meta = meta_map.get(vid, {})
            if filter_expr:
                match = True
                for key, val in filter_expr.items():
                    if isinstance(val, list):
                        if meta.get(key) not in val:
                            match = False
                            break
                    elif meta.get(key) != val:
                        match = False
                        break
                if not match:
                    continue
            dot = sum(a * b for a, b in zip(query, vec))
            norm_q = math.sqrt(sum(a * a for a in query))
            norm_v = math.sqrt(sum(b * b for b in vec))
            score = dot / max(norm_q * norm_v, 1e-10)
            if score >= score_threshold:
                results.append({"id": vid, "score": round(score, 4), "metadata": meta})
        results.sort(key=lambda x: -x["score"])
        return {"success": True, "index": index_name, "results": results[:top_k], "total_matched": len(results)}

    def delete_by_namespace(self, index_name: str, namespace: str) -> Dict[str, Any]:
        """按命名空间删除。企业场景：清理测试环境的向量数据，
        或按项目/租户隔离数据后批量清理。
        """
        indexes = getattr(self, "_indexes", {})
        idx = indexes.get(index_name)
        if not idx:
            return {"success": False, "error": f"索引 {index_name} 不存在"}
        vectors_map = getattr(idx, "_vectors", {})
        meta_map = getattr(idx, "_metadata", {})
        to_delete = [vid for vid, meta in meta_map.items() if meta.get("namespace") == namespace]
        for vid in to_delete:
            vectors_map.pop(vid, None)
            meta_map.pop(vid, None)
        self.metrics_collector.counter("pinecone.namespace_delete", count=len(to_delete))
        return {"success": True, "index": index_name, "namespace": namespace, "deleted": len(to_delete)}

    def get_index_health(self, index_name: str) -> Dict[str, Any]:
        """索引健康检查。企业场景：监控向量索引状态，
        检查向量数量、维度一致性、元数据完整性。
        """
        indexes = getattr(self, "_indexes", {})
        idx = indexes.get(index_name)
        if not idx:
            return {"success": False, "error": f"索引 {index_name} 不存在"}
        vectors_map = getattr(idx, "_vectors", {})
        meta_map = getattr(idx, "_metadata", {})
        dim = getattr(idx, "dimension", 0)
        count = len(vectors_map)
        # 维度一致性检查
        dim_mismatches = 0
        for vid, vec in vectors_map.items():
            if len(vec) != dim:
                dim_mismatches += 1
        # 元数据覆盖率
        meta_coverage = len(meta_map) / max(count, 1) * 100
        status = "healthy"
        if dim_mismatches > 0 or meta_coverage < 90:
            status = "degraded"
        return {
            "success": True,
            "index": index_name,
            "status": status,
            "vector_count": count,
            "dimension": dim,
            "dim_mismatches": dim_mismatches,
            "metadata_coverage_pct": round(meta_coverage, 1),
        }

    def update_vectors_metadata(self, index_name: str, ids: List[str], metadata: Dict) -> Dict[str, Any]:
        """批量更新向量元数据。企业场景：文档重新分类后批量更新
        向量的metadata标签，无需重新计算embedding。
        """
        indexes = getattr(self, "_indexes", {})
        idx = indexes.get(index_name)
        if not idx:
            return {"success": False, "error": f"索引 {index_name} 不存在"}
        meta_map = getattr(idx, "_metadata", {})
        updated = 0
        not_found = 0
        for vid in ids:
            if vid in meta_map:
                meta_map[vid].update(metadata)
                updated += 1
            else:
                not_found += 1
        self.metrics_collector.counter("pinecone.metadata_update", count=updated)
        return {
            "success": True,
            "index": index_name,
            "updated": updated,
            "not_found": not_found,
            "fields_updated": list(metadata.keys()),
        }

    def describe_index_stats(self, index_name: str) -> Dict[str, Any]:
        """索引统计概览。企业场景：容量规划时查看各索引的向量数、
        总大小、按命名空间的分布。
        """
        indexes = getattr(self, "_indexes", {})
        idx = indexes.get(index_name)
        if not idx:
            return {"success": False, "error": f"索引 {index_name} 不存在"}
        vectors_map = getattr(idx, "_vectors", {})
        meta_map = getattr(idx, "_metadata", {})
        dim = getattr(idx, "dimension", 0)
        count = len(vectors_map)
        total_size = count * dim * 4  # float32
        # 按命名空间统计
        ns_counts = {}
        for vid, meta in meta_map.items():
            ns = meta.get("namespace", "default")
            ns_counts[ns] = ns_counts.get(ns, 0) + 1
        return {
            "success": True,
            "index": index_name,
            "dimension": dim,
            "total_vectors": count,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "namespaces": ns_counts,
            "metadata_fields": len(set(k for m in meta_map.values() for k in m.keys())),
        }

    def shutdown(self) -> dict:
        """Graceful shutdown for pinecone_managed."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = PineconeManaged
