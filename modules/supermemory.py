"""Production-grade 超级记忆引擎模块 V0.1
# Grade: A
上市公司生产级实现 - 多模态记忆存储/语义检索/自动标签/关联图谱/遗忘策略/记忆审计
"""

__module_meta__ = {
        "id": "supermemory",
        "name": "Supermemory",
        "version": "V0.1",
        "group": "memory",
        "inputs": [
            {
                "name": "memory_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "embedding",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "query_vector",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "top_k",
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
                "name": "query_vector_2",
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
            "engine",
            "supermemory"
        ],
        "grade": "A",
        "description": "Production-grade 超级记忆引擎模块 V0.1 上市公司生产级实现 - 多模态记忆存储/语义检索/自动标签/关联图谱/遗忘策略/记忆审计"
    }
import hashlib
from core.logging_config import get_logger
import math
import re
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector

try:
    from modules._base.enterprise_module import CircuitBreakerMixin, RateLimiterMixin

    MIXIN_AVAILABLE = True
except ImportError:
    MIXIN_AVAILABLE = False

class MemoryRetrievalEngine(object):
    """记忆检索引擎 - 相似度搜索、上下文关联、时间衰减加权"""

    def __init__(self):
        self._index: Dict[str, List[float]] = {}
        self._retrievals: int = 0
        self._cache: Dict[str, List[Dict]] = {}

    def index_memory(self, memory_id: str, embedding: List[float]) -> None:
        """索引记忆向量"""
        self._index[memory_id] = embedding

    def search(self, query_vector: List[float], top_k: int = 10, threshold: float = 0.7) -> List[Dict]:
        """相似度搜索"""
        self._retrievals += 1
        results = []
        for mid, emb in self._index.items():
            sim = self._cosine_sim(query_vector, emb)
            if sim >= threshold:
                results.append({"id": mid, "score": sim})
        results.sort(key=lambda x: -x["score"])
        return results[:top_k]

    def search_with_decay(self, query_vector: List[float], memories: Dict, top_k: int = 10) -> List[Dict]:
        """带时间衰减的检索"""
        now = time.time()
        results = []
        for mid, emb in self._index.items():
            sim = self._cosine_sim(query_vector, emb)
            meta = memories.get(mid, {})
            last_access = meta.get("last_access", now)
            decay = max(0.1, 1.0 - (now - last_access) / 86400 * 0.1)
            results.append({"id": mid, "score": sim * decay})
        results.sort(key=lambda x: -x["score"])
        return results[:top_k]

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x**2 for x in a) ** 0.5
        nb = sum(x**2 for x in b) ** 0.5
        return dot / max(na * nb, 1e-10)

    def get_stats(self) -> Dict:
        return {"indexed": len(self._index), "retrievals": self._retrievals}

    # --- Auto-generated action dispatch methods ---
    def _action_get_stats(self, params=None):
        """Auto-generated action wrapper for get_stats"""
        if params is None:
            params = {}
        return self.get_stats(**params)

    def _action_index_memory(self, params=None):
        """Auto-generated action wrapper for index_memory"""
        if params is None:
            params = {}
        return self.index_memory(**params)

    def _action_search(self, params=None):
        """Auto-generated action wrapper for search"""
        if params is None:
            params = {}
        return self.search(**params)

    def _action_search_with_decay(self, params=None):
        """Auto-generated action wrapper for search_with_decay"""
        if params is None:
            params = {}
        return self.search_with_decay(**params)

logger = get_logger("supermemory")

# 记忆类型枚举
MEMORY_TYPES = ("episodic", "semantic", "procedural", "working", "flash")
RECALL_STRATEGIES = ("exact", "fuzzy", "semantic", "associative", "temporal")

class MemoryVector:
    """记忆向量 - 简化版TF-IDF向量表示"""

    def __init__(self, text: str, dim: int = 128):
        self.dim = dim
        self.vector = self._text_to_vector(text)

    def _tokenize(self, text: str) -> List[str]:
        """中文+英文混合分词"""
        tokens = []
        # 提取英文单词
        en_words = re.findall(r"[a-zA-Z]+", text.lower())
        tokens.extend(en_words)
        # 提取中文单字和双字组合
        cn_chars = re.findall(r"[\u4e00-\u9fff]+", text)
        for segment in cn_chars:
            tokens.append(segment)
            if len(segment) >= 2:
                for i in range(len(segment) - 1):
                    tokens.append(segment[i : i + 2])
            if len(segment) >= 3:
                for i in range(len(segment) - 2):
                    tokens.append(segment[i : i + 3])
        return tokens

    def _text_to_vector(self, text: str) -> List[float]:
        """将文本转换为归一化向量"""
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dim
        # 使用token hash映射到固定维度
        vec = [0.0] * self.dim
        for token in tokens:
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            idx = h % self.dim
            val = 1.0 / (1 + (h // self.dim) % 10)
            vec[idx] += val
        # L2归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

class MemoryStore:
    """分层记忆存储引擎"""

    def __init__(self, max_working: int = 1000, max_long_term: int = 100000):
        self.max_working = max_working
        self.max_long_term = max_long_term
        self._working: Dict[str, Dict] = {}  # 工作记忆（短期）
        self._long_term: Dict[str, Dict] = {}  # 长期记忆
        self._flash: deque = deque(maxlen=500)  # 闪存记忆（最快淘汰）
        self._vectors: Dict[str, List[float]] = {}  # 记忆ID到向量的映射
        self._tags_index: Dict[str, List[str]] = defaultdict(list)  # 标签到记忆ID的反向索引
        self._access_count: Dict[str, int] = defaultdict(int)  # 访问频率统计
        self._access_time: Dict[str, float] = {}  # 最近访问时间
        self._stats = {
            "total_memories": 0,
            "working_count": 0,
            "long_term_count": 0,
            "flash_count": 0,
            "evicted": 0,
            "promoted": 0,
        }

    def store(
        self,
        content: str,
        memory_type: str = "semantic",
        tags: List[str] = None,
        priority: float = 1.0,
        metadata: Dict = None,
    ) -> Dict:
        """存储一条记忆"""
        memory_id = str(uuid.uuid4())[:12]
        ts = time.time()
        tags = tags or []
        if memory_type not in MEMORY_TYPES:
            memory_type = "semantic"

        vector = MemoryVector(content).vector
        memory = {
            "id": memory_id,
            "content": content,
            "type": memory_type,
            "tags": list(set(tags)),
            "priority": max(0.0, min(10.0, priority)),
            "created_at": ts,
            "updated_at": ts,
            "access_count": 0,
            "metadata": metadata or {},
            "vector_dim": len(vector),
        }

        # 根据类型存入不同层
        if memory_type == "working":
            self._working[memory_id] = memory
            if len(self._working) > self.max_working:
                self._evict_working()
        elif memory_type == "flash":
            memory["expires_at"] = ts + 300  # 闪存5分钟过期
            self._flash.append(memory)
        else:
            self._long_term[memory_id] = memory
            if len(self._long_term) > self.max_long_term:
                self._evict_long_term()

        # 建立索引
        self._vectors[memory_id] = vector
        for tag in tags:
            self._tags_index[tag].append(memory_id)
        self._access_count[memory_id] = 0
        self._access_time[memory_id] = ts
        self._stats["total_memories"] += 1

        return {"id": memory_id, "type": memory_type, "tags": len(tags)}

    def retrieve(
        self, query: str, strategy: str = "semantic", limit: int = 10, threshold: float = 0.3, filters: Dict = None
    ) -> List[Dict]:
        """检索记忆，支持多种策略"""
        filters = filters or {}
        results = []

        if strategy == "exact":
            # 精确匹配：内容完全包含
            all_memories = {**self._working, **self._long_term}
            for mid, mem in all_memories.items():
                if query.lower() in mem["content"].lower():
                    if self._match_filters(mem, filters):
                        results.append(mem)
                if len(results) >= limit:
                    break

        elif strategy in ("semantic", "fuzzy", "associative"):
            # 语义/模糊/关联检索：基于向量相似度
            query_vec = MemoryVector(query).vector
            all_ids = list({**self._working, **self._long_term}.keys())
            scored = []
            for mid in all_ids:
                mem = {**self._working, **self._long_term}.get(mid)
                if not mem or not self._match_filters(mem, filters):
                    continue
                mem_vec = self._vectors.get(mid, [])
                sim = MemoryVector.cosine_similarity(query_vec, mem_vec)
                # 加权：访问频率 + 优先级 + 时效性
                recency = 1.0 / (1 + (time.time() - mem["created_at"]) / 86400)
                access_bonus = min(self._access_count.get(mid, 0) * 0.01, 0.2)
                priority_bonus = mem.get("priority", 1.0) * 0.05
                score = sim * 0.7 + recency * 0.1 + access_bonus + priority_bonus
                scored.append((score, mem))

            # 关联检索额外查找标签相关
            if strategy == "associative":
                query_tags = self._auto_extract_tags(query)
                related_ids = set()
                for tag in query_tags:
                    related_ids.update(self._tags_index.get(tag, []))
                for rid in related_ids:
                    if rid in self._working:
                        mem = self._working[rid]
                    elif rid in self._long_term:
                        mem = self._long_term[rid]
                    else:
                        continue
                    if not self._match_filters(mem, filters):
                        continue
                    mem_vec = self._vectors.get(rid, [])
                    sim = MemoryVector.cosine_similarity(query_vec, mem_vec)
                    score = sim * 0.6 + 0.3  # 关联记忆加分
                    scored.append((score, mem))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = [m for s, m in scored if s >= threshold][:limit]

        elif strategy == "temporal":
            # 时间线检索：按时间排序
            all_memories = {**self._working, **self._long_term}
            start_ts = filters.get("start_time", 0)
            end_ts = filters.get("end_time", float("inf"))
            temporal = []
            for mid, mem in all_memories.items():
                if start_ts <= mem["created_at"] <= end_ts:
                    if self._match_filters(mem, filters):
                        temporal.append(mem)
            temporal.sort(key=lambda m: m["created_at"], reverse=True)
            results = temporal[:limit]

        # 更新访问统计
        for mem in results:
            mid = mem["id"]
            self._access_count[mid] += 1
            self._access_time[mid] = time.time()
            mem["access_count"] += 1

        return results

    def _match_filters(self, memory: Dict, filters: Dict) -> bool:
        """检查记忆是否匹配过滤条件"""
        if filters.get("type") and memory.get("type") != filters["type"]:
            return False
        if filters.get("tags"):
            mem_tags = set(memory.get("tags", []))
            filter_tags = set(filters["tags"])
            if not mem_tags.intersection(filter_tags):
                return False
        if filters.get("min_priority"):
            if memory.get("priority", 0) < filters["min_priority"]:
                return False
        return True

    def _auto_extract_tags(self, text: str) -> List[str]:
        """自动从文本提取标签"""
        tags = []
        # 提取高频中文双字词
        cn_segments = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
        tags.extend(cn_segments[:5])
        # 提取英文关键词
        en_words = re.findall(r"[a-zA-Z]{3,}", text.lower())
        tags.extend(en_words[:5])
        return list(set(tags))

    def _evict_working(self) -> int:
        """工作记忆淘汰：LRU策略"""
        evicted = 0
        while len(self._working) > self.max_working:
            oldest_id = min(self._working, key=lambda k: self._access_time.get(k, 0))
            # 高优先级的不淘汰，提升到长期记忆
            mem = self._working[oldest_id]
            if mem.get("priority", 1.0) >= 5.0:
                self._long_term[oldest_id] = mem
                self._stats["promoted"] += 1
            else:
                self._cleanup_memory(oldest_id)
            del self._working[oldest_id]
            evicted += 1
        self._stats["evicted"] += evicted
        return evicted

    def _evict_long_term(self) -> int:
        """长期记忆淘汰：LFU + 时效综合策略"""
        evicted = 0
        while len(self._long_term) > self.max_long_term:
            # 综合评分：访问频率低 + 时间久远的优先淘汰
            min_id = min(
                self._long_term,
                key=lambda k: self._access_count.get(k, 0) * 10 + (time.time() - self._access_time.get(k, 0)) / 86400,
            )
            self._cleanup_memory(min_id)
            del self._long_term[min_id]
            evicted += 1
        self._stats["evicted"] += evicted
        return evicted

    def _cleanup_memory(self, memory_id: str):
        """清理记忆相关索引"""
        self._vectors.pop(memory_id, None)
        self._access_count.pop(memory_id, None)
        self._access_time.pop(memory_id, None)
        # 从标签索引中移除
        for tag in list(self._tags_index.keys()):
            if memory_id in self._tags_index[tag]:
                self._tags_index[tag].remove(memory_id)
                if not self._tags_index[tag]:
                    del self._tags_index[tag]

    def get_stats(self) -> Dict:
        """获取存储统计"""
        self._stats["working_count"] = len(self._working)
        self._stats["long_term_count"] = len(self._long_term)
        self._stats["flash_count"] = len(self._flash)
        self._stats["total_memories"] = len(self._working) + len(self._long_term) + len(self._flash)
        return dict(self._stats)

class MemoryRelation:
    """记忆关联图谱"""

    def __init__(self):
        self._edges: Dict[str, List[Dict]] = defaultdict(list)  # 节点 -> 边列表
        self._edge_count = 0

    def add_relation(
        self, source_id: str, target_id: str, relation_type: str = "related", weight: float = 1.0, metadata: Dict = None
    ) -> Dict:
        """添加两条记忆之间的关联关系"""
        edge_id = str(uuid.uuid4())[:8]
        edge = {
            "id": edge_id,
            "source": source_id,
            "target": target_id,
            "type": relation_type,
            "weight": max(0.0, min(10.0, weight)),
            "created_at": time.time(),
            "metadata": metadata or {},
        }
        self._edges[source_id].append(edge)
        self._edge_count += 1
        return {"edge_id": edge_id, "type": relation_type}

    def find_related(self, memory_id: str, max_depth: int = 2, min_weight: float = 0.5) -> List[Dict]:
        """查找关联记忆（广度优先遍历）"""
        visited = {memory_id}
        queue = [(memory_id, 0)]
        results = []

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for edge in self._edges.get(current, []):
                target = edge["target"]
                if edge["weight"] < min_weight:
                    continue
                if target not in visited:
                    visited.add(target)
                    results.append(
                        {"id": target, "relation": edge["type"], "weight": edge["weight"], "depth": depth + 1}
                    )
                    queue.append((target, depth + 1))

        results.sort(key=lambda r: r["weight"], reverse=True)
        return results

    def get_stats(self) -> Dict:
        return {"total_edges": self._edge_count, "node_count": len(self._edges)}

class ForgettingCurve:
    """遗忘曲线管理 - 基于艾宾浩斯遗忘模型"""

    def __init__(self):
        self._review_records: Dict[str, List[float]] = defaultdict(list)
        self._intervals = [1, 6, 24, 72, 168, 720]  # 复习间隔（小时）

    def record_access(self, memory_id: str):
        """记录记忆被访问"""
        self._review_records[memory_id].append(time.time())

    def get_retention_score(self, memory_id: str) -> float:
        """计算记忆保持率（0-1）"""
        records = self._review_records.get(memory_id, [])
        if not records:
            return 0.0
        last_access = max(records)
        hours_since = (time.time() - last_access) / 3600
        review_count = len(records)
        # 艾宾浩斯模型：R = e^(-t/S)，S随复习次数增长
        stability = self._intervals[min(review_count - 1, len(self._intervals) - 1)]
        retention = math.exp(-hours_since / stability)
        return max(0.0, min(1.0, retention))

    def should_review(self, memory_id: str) -> bool:
        """判断是否需要复习"""
        records = self._review_records.get(memory_id, [])
        if not records:
            return True
        review_count = len(records)
        last_access = max(records)
        hours_since = (time.time() - last_access) / 3600
        next_interval = self._intervals[min(review_count, len(self._intervals) - 1)]
        return hours_since >= next_interval

    def get_weak_memories(self, memory_ids: List[str], threshold: float = 0.3) -> List[str]:
        """获取需要加强的记忆列表"""
        weak = []
        for mid in memory_ids:
            score = self.get_retention_score(mid)
            if score < threshold:
                weak.append(mid)
        weak.sort(key=lambda m: self.get_retention_score(m))
        return weak

class AutoTagger:
    """自动标签引擎"""

    def __init__(self):
        self._tag_rules: List[Dict] = []
        self._category_keywords: Dict[str, List[str]] = defaultdict(list)
        self._tag_stats: Dict[str, int] = defaultdict(int)

    def add_category(self, category: str, keywords: List[str]):
        """添加分类关键词"""
        self._category_keywords[category] = keywords

    def tag_content(self, content: str, existing_tags: List[str] = None) -> List[str]:
        """自动为内容生成标签"""
        tags = set(existing_tags or [])
        content_lower = content.lower()

        # 基于分类关键词匹配
        for category, keywords in self._category_keywords.items():
            for kw in keywords:
                if kw.lower() in content_lower:
                    tags.add(category)
                    break

        # 基于内容特征自动提取
        # 检测语言
        cn_count = len(re.findall(r"[\u4e00-\u9fff]", content))
        en_count = len(re.findall(r"[a-zA-Z]", content))
        if cn_count > en_count:
            tags.add("chinese")
        elif en_count > cn_count:
            tags.add("english")
        tags.add("bilingual") if cn_count > 0 and en_count > 0 else None

        # 检测内容类型
        if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", content):
            tags.add("has_date")
        if re.search(r"https?://", content):
            tags.add("has_url")
        if re.search(r"[$¥€£]", content):
            tags.add("has_currency")
        if re.search(r"[.!？!]{3,}", content):
            tags.add("emotional")
        if len(content) > 500:
            tags.add("long_text")
        elif len(content) < 50:
            tags.add("short_text")

        # 检测领域
        domain_keywords = {
            "tech": ["python", "java", "算法", "模型", "AI", "系统", "api", "数据库"],
            "finance": ["股票", "基金", "收益", "投资", "利率", "GDP", "CPI"],
            "medical": ["诊断", "治疗", "症状", "药物", "临床", "患者"],
        }
        for domain, kws in domain_keywords.items():
            for kw in kws:
                if kw.lower() in content_lower:
                    tags.add(domain)
                    break

        # 更新统计
        for tag in tags:
            self._tag_stats[tag] += 1

        return list(tags)

_SM_BASES = (EnterpriseModule,) if not MIXIN_AVAILABLE else (EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin)

class SuperMemory(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """超级记忆引擎 - 生产级实现
    支持多模态记忆存储、语义检索、自动标签、关联图谱、遗忘曲线管理
    """

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.config = config or {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "memories_stored": 0,
            "memories_retrieved": 0,
            "tags_generated": 0,
            "relations_created": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: deque = deque(maxlen=5000)
        self._status = ModuleStatus.INITIALIZING
        self._logger = logger

        # 核心组件
        self._store = MemoryStore(
            max_working=self.config.get("max_working", 1000), max_long_term=self.config.get("max_long_term", 100000)
        )
        self._relations = MemoryRelation()
        self._forgetting = ForgettingCurve()
        self._tagger = AutoTagger()

        # 初始化默认分类
        default_categories = self.config.get("categories", {})
        for cat, kws in default_categories.items():
            self._tagger.add_category(cat, kws)

    def initialize(self) -> dict:
        """初始化超级记忆引擎"""
        try:
            categories = self.config.get("categories", {})
            for cat, kws in categories.items():
                self._tagger.add_category(cat, kws)
            self._status = ModuleStatus.RUNNING
            self._logger.info("超级记忆引擎初始化完成")
            return {"success": True, "categories": len(categories)}
        except Exception as e:
            self._status = ModuleStatus.ERROR
            self._logger.error(f"初始化失败: {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        """健康检查"""
        store_stats = self._store.get_stats()
        return {
            "healthy": self._status == ModuleStatus.RUNNING,
            "memories": store_stats["total_memories"],
            "working": store_stats["working_count"],
            "long_term": store_stats["long_term_count"],
            "relations": self._relations.get_stats()["total_edges"],
            "operations": self._metrics["total_operations"],
        }

    def ingest(self, params: dict = None) -> dict:
        """摄入记忆 - 支持自动标签和分类"""
        params = params or {}
        content = params.get("content", "")
        if not content.strip():
            return {"success": False, "error": "content_required"}

        memory_type = params.get("type", "semantic")
        priority = float(params.get("priority", 1.0))

        # 自动标签
        existing_tags = params.get("tags", [])
        auto_tags = self._tagger.tag_content(content, existing_tags)
        all_tags = list(set(existing_tags + auto_tags))
        self._metrics["tags_generated"] += len(auto_tags)

        # 存储
        result = self._store.store(
            content=content,
            memory_type=memory_type,
            tags=all_tags,
            priority=priority,
            metadata=params.get("metadata", {}),
        )
        self._metrics["memories_stored"] += 1
        self._audit_log.append(
            {
                "action": "ingest",
                "memory_id": result["id"],
                "type": memory_type,
                "tags": all_tags,
                "timestamp": time.time(),
            }
        )

        return {
            "success": True,
            "memory_id": result["id"],
            "type": memory_type,
            "auto_tags": auto_tags,
            "total_tags": len(all_tags),
        }

    def query(self, params: dict = None) -> dict:
        """检索记忆 - 支持多种检索策略"""
        params = params or {}
        query_text = params.get("query", "")
        if not query_text.strip():
            return {"success": False, "error": "query_required"}

        strategy = params.get("strategy", "semantic")
        limit = int(params.get("limit", 10))
        threshold = float(params.get("threshold", 0.3))
        filters = params.get("filters", {})

        results = self._store.retrieve(
            query=query_text, strategy=strategy, limit=limit, threshold=threshold, filters=filters
        )

        # 记录遗忘曲线
        for mem in results:
            self._forgetting.record_access(mem["id"])

        self._metrics["memories_retrieved"] += len(results)
        self._audit_log.append(
            {
                "action": "query",
                "query": query_text[:100],
                "strategy": strategy,
                "results": len(results),
                "timestamp": time.time(),
            }
        )

        return {
            "success": True,
            "results": len(results),
            "memories": [
                {
                    "id": m["id"],
                    "content": m["content"][:200],
                    "type": m["type"],
                    "tags": m.get("tags", []),
                    "access_count": m.get("access_count", 0),
                }
                for m in results
            ],
        }

    def auto_tag(self, params: dict = None) -> dict:
        """自动标签 - 为已有记忆补充标签"""
        params = params or {}
        memory_id = params.get("memory_id", "")
        new_tags_input = params.get("tags", [])

        if not memory_id:
            return {"success": False, "error": "memory_id_required"}

        # 查找记忆
        memory = self._store._working.get(memory_id) or self._store._long_term.get(memory_id)
        if not memory:
            return {"success": False, "error": "memory_not_found"}

        # 自动生成标签
        auto_tags = self._tagger.tag_content(memory["content"], memory.get("tags", []))
        # 合并手动指定的标签
        all_new_tags = list(set(auto_tags + new_tags_input))

        # 更新记忆标签
        old_tags = set(memory.get("tags", []))
        updated_tags = list(old_tags | set(all_new_tags))
        memory["tags"] = updated_tags
        memory["updated_at"] = time.time()

        # 更新标签索引
        for tag in all_new_tags:
            if memory_id not in self._store._tags_index[tag]:
                self._store._tags_index[tag].append(memory_id)

        self._metrics["tags_generated"] += len(all_new_tags)
        self._audit_log.append(
            {"action": "auto_tag", "memory_id": memory_id, "new_tags": all_new_tags, "timestamp": time.time()}
        )

        return {"success": True, "memory_id": memory_id, "added_tags": all_new_tags, "total_tags": len(updated_tags)}

    def relate(self, params: dict = None) -> dict:
        """建立记忆关联"""
        params = params or {}
        source_id = params.get("source_id", "")
        target_id = params.get("target_id", "")
        relation_type = params.get("type", "related")
        weight = float(params.get("weight", 1.0))

        if not source_id or not target_id:
            return {"success": False, "error": "source_id_and_target_id_required"}
        if source_id == target_id:
            return {"success": False, "error": "cannot_relate_to_self"}

        result = self._relations.add_relation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            metadata=params.get("metadata", {}),
        )
        self._metrics["relations_created"] += 1
        self._audit_log.append(
            {
                "action": "relate",
                "source": source_id,
                "target": target_id,
                "type": relation_type,
                "timestamp": time.time(),
            }
        )

        return {"success": True, **result}

    def forget(self, params: dict = None) -> dict:
        """遗忘管理 - 查看遗忘曲线和需要复习的记忆"""
        params = params or {}
        action_type = params.get("action", "review_list")

        if action_type == "review_list":
            # 获取需要复习的弱记忆
            all_ids = list(self._store._working.keys()) + list(self._store._long_term.keys())
            weak_ids = self._forgetting.get_weak_memories(all_ids, threshold=0.3)
            weak_memories = []
            for mid in weak_ids[:20]:
                mem = self._store._working.get(mid) or self._store._long_term.get(mid)
                if mem:
                    score = self._forgetting.get_retention_score(mid)
                    weak_memories.append(
                        {"id": mid, "content": mem["content"][:100], "retention": round(score, 3), "type": mem["type"]}
                    )
            return {"success": True, "weak_memories": weak_memories, "count": len(weak_memories)}

        elif action_type == "delete":
            # 删除指定记忆
            memory_id = params.get("memory_id", "")
            if not memory_id:
                return {"success": False, "error": "memory_id_required"}
            removed = False
            if memory_id in self._store._working:
                del self._store._working[memory_id]
                removed = True
            elif memory_id in self._store._long_term:
                del self._store._long_term[memory_id]
                removed = True
            if removed:
                self._store._cleanup_memory(memory_id)
                self._forgetting._review_records.pop(memory_id, None)
            return {"success": True, "deleted": removed}

        elif action_type == "consolidate":
            # 整合工作记忆到长期记忆
            promoted = 0
            for mid, mem in list(self._store._working.items()):
                score = self._forgetting.get_retention_score(mid)
                if score > 0.7 or mem.get("access_count", 0) > 5:
                    self._store._long_term[mid] = mem
                    del self._store._working[mid]
                    promoted += 1
            self._store._stats["promoted"] += promoted
            return {"success": True, "promoted": promoted}

        return {"success": False, "error": f"unknown_action: {action_type}"}

    def get_stats(self, params: dict = None) -> dict:
        """获取记忆系统统计"""
        params = params or {}
        store_stats = self._store.get_stats()
        relation_stats = self._relations.get_stats()
        return {
            "success": True,
            "store": store_stats,
            "relations": relation_stats,
            "operations": self._metrics["total_operations"],
            "errors": self._metrics["errors"],
        }

    async def execute(self, action: str, params: dict = None) -> dict:
        _ = self.trace("execute")
        metrics_collector.counter("supermemory_ops_total", labels={"action": action})
        """统一执行入口"""
        self.audit("execute", f"action={action}")
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
                self._logger.error(f"执行 {action} 失败: {e}")
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    def shutdown(self) -> dict:
        """Graceful shutdown for supermemory."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = SuperMemory
