# 原 system_coordinator_v3.py L217-716 — 模块能力图谱
"""模块能力图谱 — 自动扫描所有模块并构建能力索引"""
import logging, time, re, os, sys, math, asyncio
from typing import Dict, Any, Optional, List, Set
from collections.abc import Callable
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector
logger = logging.getLogger("evo.coordinator.v3")

class ModuleCapabilityGraph(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    模块能力图谱 v3.0
    自动扫描 modules/ 目录下所有 .py 文件
    提取类、方法、文档字符串，构建可查询的能力图谱
    """

    def __init__(self, modules_dir: str = None):
        super().__init__()
        self.modules_dir = Path(modules_dir) if modules_dir else Path(__file__).parent
        self.graph: dict[str, dict] = {}  # module_id -> {classes, methods, capabilities, tags}
        self.capability_index: dict[str, list[str]] = defaultdict(list)  # capability -> [module_ids]
        self.method_index: dict[str, list[str]] = defaultdict(list)  # method_name -> [module_ids]
        self.tag_index: dict[str, list[str]] = defaultdict(list)  # tag -> [module_ids]
        self._tfidf_built = False
        self._tfidf_docs: dict[str, str] = {}
        self._idf: dict[str, float] = {}
        self._doc_freq: dict[str, int] = defaultdict(int)
        # ChromaDB 向量语义索引
        self._chroma_client = None
        self._chroma_col = None
        self._chroma_built = False
        self._scan_all_modules()

    def _scan_all_modules(self):
        """扫描所有模块文件"""
        if not self.modules_dir.exists():
            return

        for py_file in self.modules_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                self._scan_module_file(py_file)
            except Exception as e:
                logger.debug(f"[CapabilityGraph] 扫描失败 {py_file.name}: {e}")

        logger.info(
            f"[CapabilityGraph] 扫描完成: {len(self.graph)} 模块, "
            f"{len(self.capability_index)} 能力, {len(self.method_index)} 方法"
        )

    def _scan_module_file(self, py_file: Path):
        """扫描单个模块文件"""
        module_id = py_file.stem
        content = py_file.read_text(encoding="utf-8")

        # 提取类定义
        classes = re.findall(r"^class\s+(\w+)", content, re.MULTILINE)
        # 提取方法定义
        methods = re.findall(r"^\s+def\s+(\w+)\(", content, re.MULTILINE)
        # 提取文档字符串中的关键词
        doc_keywords = re.findall(r'["\']{3}(.+?)["\']{3}', content, re.DOTALL)
        doc_text = " ".join(doc_keywords).lower()

        # 推断能力标签
        tags = self._infer_tags(module_id, content.lower(), methods, doc_text)

        # 推断核心能力
        capabilities = []
        for method in methods:
            cap = self._method_to_capability(method)
            if cap:
                capabilities.append(cap)

        self.graph[module_id] = {
            "file": str(py_file),
            "classes": classes,
            "methods": methods,
            "capabilities": list(set(capabilities)),
            "tags": tags,
            "doc_summary": doc_text[:200] if doc_text else "",
        }

        # 构建索引
        for cap in capabilities:
            self.capability_index[cap].append(module_id)
        for method in methods:
            self.method_index[method].append(module_id)
        for tag in tags:
            self.tag_index[tag].append(module_id)

    def _infer_tags(self, module_id: str, content: str, methods: list[str], doc: str) -> list[str]:
        """推断模块标签"""
        tags = set()

        # 基于模块名
        name_patterns = {
            "ai": ["ai", "gpt", "llm", "model", "chat", "gateway"],
            "data": ["data", "db", "sql", "cache", "pipeline", "etl"],
            "finance": ["stock", "fund", "crypto", "forex", "futures", "macro", "fin"],
            "video": ["video", "pixel", "frame", "movie"],
            "web": ["web", "browser", "scrape", "crawl", "http"],
            "file": ["file", "fs", "export", "import", "backup"],
            "notify": ["notify", "feishu", "email", "push", "webhook"],
            "security": ["security", "scan", "vuln", "audit"],
            "schedule": ["cron", "schedule", "task", "job"],
            "monitor": ["monitor", "perf", "health", "metric"],
            "ml": ["ml", "train", "model", "huggingface", "pytorch"],
            "code": ["code", "template", "generate", "refactor"],
            "memory": ["memory", "brain", "remember", "recall"],
            "integration": ["integration", "mcp", "api", "connector"],
            "i18n": ["i18n", "translate", "lang"],
        }

        for tag, patterns in name_patterns.items():
            if any(p in module_id.lower() or p in doc for p in patterns):
                tags.add(tag)

        # 基于方法名
        method_tags = {
            "get_": "read",
            "set_": "write",
            "send_": "notify",
            "scan_": "scan",
            "train": "ml",
            "chat": "ai",
            "translate": "i18n",
            "export_": "export",
            "import_": "import",
            "backup": "backup",
            "restore": "backup",
        }
        for method in methods:
            for prefix, tag in method_tags.items():
                if method.startswith(prefix):
                    tags.add(tag)

        return list(tags)

    def _method_to_capability(self, method: str) -> str | None:
        """将方法名映射到能力"""
        cap_map = {
            "get_": "read",
            "set_": "write",
            "create_": "create",
            "update_": "update",
            "delete_": "delete",
            "send_": "send",
            "receive_": "receive",
            "scan_": "scan",
            "analyze_": "analyze",
            "generate_": "generate",
            "chat": "chat",
            "translate": "translate",
            "search": "search",
            "query": "query",
            "execute": "execute",
            "run": "execute",
            "backup": "backup",
            "restore": "backup",
            "deploy": "deploy",
            "health": "health",
            "encrypt": "encrypt",
            "decrypt": "encrypt",
            "monitor": "monitor",
            "alert": "alert",
            "train": "train",
            "predict": "predict",
            "evaluate": "analyze",
            "schedule": "schedule",
            "notify": "send",
            "push": "send",
            "cache": "cache",
            "index": "search",
            "optimize": "optimize",
        }
        for prefix, cap in cap_map.items():
            if method.startswith(prefix) or prefix in method:
                return cap
        return None

    # ═══════════════════════════════════════════════════════
    # TF-IDF 语义匹配引擎
    # ═══════════════════════════════════════════════════════

    def _tokenize(self, text: str) -> list[str]:
        """分词：支持中英文混合"""
        text = text.lower()
        # 英文单词
        en_tokens = re.findall(r"[a-z][a-z0-9_]+", text)
        # 中文单字+双字
        cn_chars = re.findall(r"[\u4e00-\u9fff]", text)
        cn_bigrams = [text[i : i + 2] for i in range(len(cn_chars)) if i < len(cn_chars) - 1]
        # 下划线分割的模块名各部分
        underscore_tokens = []
        for t in en_tokens:
            if "_" in t:
                underscore_tokens.extend(t.split("_"))
        return en_tokens + underscore_tokens + cn_chars + cn_bigrams

    def _build_module_document(self, module_id: str, info: dict) -> str:
        """为每个模块构建搜索文档"""
        parts = [module_id.replace("_", " ")]
        if info.get("description"):
            parts.append(info["description"])
        if info.get("tags"):
            parts.append(" ".join(info["tags"]))
        if info.get("methods"):
            parts.append(" ".join(info["methods"][:20]))
        if info.get("category"):
            parts.append(info["category"])
        return " ".join(parts)

    def _build_tfidf_index(self):
        """构建 TF-IDF 索引（模块文档）"""
        self._tfidf_docs = {}  # module_id -> document string
        self._idf = defaultdict(float)  # term -> IDF value
        self._doc_freq = defaultdict(int)  # term -> document frequency
        N = len(self.graph)

        if N == 0:
            return

        # 构建每个模块的文档
        for module_id, info in self.graph.items():
            doc = self._build_module_document(module_id, info)
            self._tfidf_docs[module_id] = doc

        # 计算文档频率
        for module_id, doc in self._tfidf_docs.items():
            seen_terms = set()
            for token in self._tokenize(doc):
                if token not in seen_terms:
                    self._doc_freq[token] += 1
                    seen_terms.add(token)

        # 计算 IDF = log(N / df)
        for term, df in self._doc_freq.items():
            self._idf[term] = math.log(1 + N / (1 + df)) + 1

        self._tfidf_built = True
        logger.debug(f"[CapabilityGraph] TF-IDF index built: {N} docs, {len(self._idf)} terms")

    def _tfidf_vector(self, text: str) -> dict[str, float]:
        """计算文本的 TF-IDF 向量"""
        tokens = self._tokenize(text)
        if not tokens:
            return {}

        # TF
        tf = Counter(tokens)
        total = len(tokens)
        tf_normalized = {t: count / total for t, count in tf.items()}

        # TF-IDF
        vector = {}
        for term, tf_val in tf_normalized.items():
            idf = self._idf.get(term, 1.0)
            vector[term] = tf_val * idf

        return vector

    def _cosine_similarity(self, vec1: dict[str, float], vec2: dict[str, float]) -> float:
        """余弦相似度"""
        if not vec1 or not vec2:
            return 0.0

        # 点积
        dot = sum(vec1.get(t, 0) * vec2.get(t, 0) for t in set(vec1) & set(vec2))
        # 范数
        norm1 = math.sqrt(sum(v**2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v**2 for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def find_modules_semantic(self, task: str, top_k: int = 10) -> list[tuple]:
        """TF-IDF 语义匹配 — 返回 [(module_id, score)]"""
        if not self._tfidf_built:
            self._build_tfidf_index()

        if not self._tfidf_docs:
            return []

        query_vec = self._tfidf_vector(task)
        if not query_vec:
            return []

        scores = []
        for module_id, doc in self._tfidf_docs.items():
            doc_vec = self._tfidf_vector(doc)
            sim = self._cosine_similarity(query_vec, doc_vec)
            if sim > 0.01:  # 过滤极低分
                scores.append((module_id, sim))

        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]

    def _build_chroma_index(self):
        """构建 ChromaDB 向量语义索引（all-MiniLM-L6-v2 嵌入）"""
        try:
            import chromadb
            import os

            # 持久化路径（避免每次重启重建）
            persist_dir = os.path.join(os.path.dirname(__file__), "..", ".chroma_data")
            os.makedirs(persist_dir, exist_ok=True)

            self._chroma_client = chromadb.PersistentClient(path=persist_dir)
            self._chroma_col = self._chroma_client.get_or_create_collection(
                name="module_semantic_index", metadata={"hnsw:space": "cosine"}
            )

            # 如果已有索引且数量匹配，直接复用
            if self._chroma_col.count() >= len(self.graph):
                self._chroma_built = True
                return

            # 增量更新：只添加缺少的
            existing_ids = set()
            if self._chroma_col.count() > 0:
                existing_ids = set(self._chroma_col.get()["ids"])

            ids = []
            documents = []
            for module_id, info in self.graph.items():
                if module_id not in existing_ids:
                    doc = self._build_module_document(module_id, info)
                    ids.append(module_id)
                    documents.append(doc)

            if not ids:
                self._chroma_built = True
                return

            # 分批写入（每批100，减少单次阻塞时间）
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i : i + batch_size]
                batch_docs = documents[i : i + batch_size]
                self._chroma_col.add(ids=batch_ids, documents=batch_docs)

            self._chroma_built = True
        except Exception:
            self._chroma_built = False  # ChromaDB不可用时优雅降级

    def find_modules_vector(self, task: str, top_k: int = 10) -> list[tuple]:
        """ChromaDB 向量语义搜索 — 返回 [(module_id, score)]"""
        if not self._chroma_built:
            self._build_chroma_index()

        if not self._chroma_built or not self._chroma_col:
            return []

        try:
            results = self._chroma_col.query(query_texts=[task], n_results=min(top_k * 2, self._chroma_col.count()))
            if not results or not results["ids"] or not results["ids"][0]:
                return []

            # 过度通用模块列表（文档包含大量通用词但不应该成为默认路由）
            _overly_generic = {"ai_gateway", "system_coordinator_v3", "unified_registry"}

            task_words = set(task.lower().replace("_", " ").split())
            scores = []
            for i, mid in enumerate(results["ids"][0]):
                dist = results["distances"][0][i] if results["distances"] else 0
                similarity = max(0, 1.0 - dist)

                # 对过度通用模块降权：除非任务词明确出现在模块名中
                if mid in _overly_generic:
                    name_words = set(mid.replace("_", " ").split())
                    if not task_words & name_words:
                        similarity *= 0.2  # 大幅降权

                scores.append((mid, similarity))
            scores.sort(key=lambda x: -x[1])
            return scores[:top_k]
        except Exception:
            return []

        """将方法名映射到能力"""
        capability_map = {
            "get_": "read",
            "set_": "write",
            "create_": "create",
            "update_": "update",
            "delete_": "delete",
            "send_": "send",
            "receive_": "receive",
            "scan_": "scan",
            "analyze_": "analyze",
            "generate_": "generate",
            "train": "train",
            "predict": "predict",
            "chat": "chat",
            "translate": "translate",
            "search": "search",
            "query": "query",
            "execute": "execute",
            "run": "execute",
            "backup": "backup",
            "restore": "restore",
            "export_": "export",
            "import_": "import",
            "health_check": "health",
            "get_stats": "stats",
        }
        for prefix, cap in capability_map.items():
            if method.startswith(prefix) or method == prefix.rstrip("_"):
                return cap
        return None

    def find_modules_by_capability(self, capability: str) -> list[str]:
        """按能力查找模块"""
        return self.capability_index.get(capability, [])

    def find_modules_by_task(self, task: str) -> list[tuple]:
        """
        按任务描述查找最匹配的模块 — Chroma向量 + TF-IDF + 关键词多级匹配
        返回: [(module_id, score), ...]
        """
        task_lower = task.lower()
        scores: dict[str, float] = defaultdict(float)

        # ═══ Layer 0: ChromaDB 向量语义匹配（权重最高） ═══
        vector_results = self.find_modules_vector(task, top_k=30)
        for module_id, sim_score in vector_results:
            scores[module_id] += sim_score * 6.0

        # ═══ Layer 0.5: 语义增强 — 对向量Top1额外加分，确保向量意图不被关键词淹没 ═══
        if vector_results:
            top_module, top_score = vector_results[0]
            if top_score > 0.3:  # 只在向量置信度较高时加分
                scores[top_module] += 3.0

        # ═══ Layer 1: TF-IDF 语义匹配（加权最高） ═══
        semantic_results = self.find_modules_semantic(task, top_k=30)
        for module_id, sim_score in semantic_results:
            # 语义相似度归一化到 0-5 分制
            scores[module_id] += sim_score * 5.0

        # ═══ Layer 2: 标签匹配 ═══
        for tag, modules in self.tag_index.items():
            if tag in task_lower:
                for m in modules:
                    scores[m] += 3.0

        # ═══ Layer 3: 能力关键词匹配 ═══
        capability_keywords = {
            "read": ["获取", "读取", "查询", "查看", "get", "read", "query", "fetch"],
            "write": ["写入", "保存", "存储", "set", "write", "save", "store"],
            "create": ["创建", "生成", "新建", "create", "generate", "new", "build"],
            "delete": ["删除", "移除", "delete", "remove", "clear"],
            "send": ["发送", "推送", "通知", "send", "push", "notify"],
            "scan": ["扫描", "检测", "scan", "detect", "check", "探测", "排查"],
            "analyze": ["分析", "统计", "analyze", "analysis", "stats", "评估", "趋势"],
            "chat": ["聊天", "对话", "chat", "talk", "ask", "AI"],
            "translate": ["翻译", "translate", "translation"],
            "search": ["搜索", "查找", "search", "find", "lookup", "发现", "探索"],
            "train": ["训练", "学习", "train", "learn", "fit"],
            "predict": ["预测", "forecast", "predict"],
            "backup": ["备份", "backup", "archive"],
            "health": ["健康", "状态", "health", "status"],
            "github": ["github", "开源", "开源项目", "trending", "代码仓库", "open source", "repository"],
            "trend": ["trending", "趋势", "热门", "流行", "潜力", "trend"],
            "encrypt": ["加密", "解密", "密码", "encrypt", "decrypt", "security", "ssl", "tls"],
            "cache": ["缓存", "cache", "redis", "memcached", "高速"],
            "queue": ["队列", "消息", "queue", "message", "kafka", "rabbitmq"],
            "monitor": ["监控", "告警", "monitor", "alert", "observe", "metric", "指标"],
            "deploy": ["部署", "发布", "deploy", "release", "rollout", "容器"],
            "test": ["测试", "test", "spec", "verify", "validate", "单元"],
        }

        for cap, keywords in capability_keywords.items():
            if any(kw in task_lower for kw in keywords):
                for m in self.capability_index.get(cap, []):
                    scores[m] += 2.5

        # ═══ Layer 4: 模块名直接匹配 ═══
        for module_id, info in self.graph.items():
            name_parts = module_id.replace("_", " ").replace("-", " ").lower().split()
            for part in name_parts:
                if part in task_lower and len(part) > 2:
                    scores[module_id] += 2.0

        # ═══ Layer 5: 方法名匹配 ═══
        for method, modules in self.method_index.items():
            if method in task_lower.replace(" ", "_") or method in task_lower:
                for m in modules:
                    scores[m] += 1.5

        # 排序返回
        sorted_modules = sorted(scores.items(), key=lambda x: -x[1])
        return sorted_modules

    def get_module_info(self, module_id: str) -> dict | None:
        """获取模块信息"""
        return self.graph.get(module_id)

    def list_all_capabilities(self) -> list[str]:
        """列出所有能力"""
        return list(self.capability_index.keys())

# ============================================================================
# 自主决策循环 — 让系统能自主运行
# ============================================================================


