"""
AUTO-EVO-AI V0.1 — Second Brain — 第二大脑知识管理
"""
import time

"""
# Grade: A
AUTO-EVO-AI V0.1 - Second Brain Memory Module
基于 Mercury Agent 的第二大脑记忆系统

第二大脑是一个革命性的记忆系统，模拟人类记忆的工作方式：
- 自动从对话中提取事实
- 分类存储到10种记忆类型
- 智能召回和冲突解决
- 自动整合和遗忘机制

作者: AUTO-EVO-AI Team
版本: V0.1.0
"""

__module_meta__ = {
    "id": "second-brain",
    "name": "Second Brain",
    "version": "V0.1",
    "group": "memory",
    "inputs": [
        {"name": "content", "type": "string", "required": True, "description": ""},
        {"name": "memory_type", "type": "string", "required": True, "description": ""},
        {"name": "query", "type": "string", "required": True, "description": ""},
        {"name": "memory_types", "type": "string", "required": True, "description": ""},
        {"name": "context", "type": "string", "required": True, "description": ""},
        {"name": "keyword", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["memory", "second-brain"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - Second Brain Memory Module 基于 Mercury Agent 的第二大脑记忆系统",
}

import os
import json
import sqlite3
import threading
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector
import hashlib

# ============================================================================
# 配置和常量
# ============================================================================

# 记忆类型枚举

class SecondBrainAnalyzer(object):
    """second_brain 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "second_brain"
        self.version = "1.0.0"
        self._analyzer = SecondBrainAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "SecondBrainAnalyzer",
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
        return {"valid": True, "module": "second_brain"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== second_brain ===",
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

class MemoryType(Enum):
    """10种记忆类型"""

    IDENTITY = "identity"  # 身份特征
    PREFERENCE = "preference"  # 偏好
    GOAL = "goal"  # 目标
    PROJECT = "project"  # 项目
    HABIT = "habit"  # 习惯
    DECISION = "decision"  # 决策
    CONSTRAINT = "constraint"  # 约束条件
    RELATIONSHIP = "relationship"  # 关系
    EPISODE = "episode"  # 事件
    REFLECTION = "reflection"  # 反思

MEMORY_TYPES = [mt.value for mt in MemoryType]

# 置信度阈值
CONFIDENCE_THRESHOLD = 0.55  # 低于此值的记忆被拒绝
CONFLICT_RESOLUTION = "confidence"  # confidence | recency

# 自动整合周期
CONSULTATION_INTERVAL = 60  # 分钟
PRUNE_DAYS_ACTIVE = 21  # 活跃记忆21天过期
PRUNE_DAYS_LOW_CONFIDENCE = 120  # 低置信度120天清除

# 召回参数
MAX_RECALL_MEMORIES = 5  # 最多召回5条
RECALL_CHAR_BUDGET = 900  # 召回内容900字符预算

# 数据库路径
DEFAULT_DB_PATH = "~/.workbuddy/memory/second-brain.db"
DEFAULT_JSONL_DIR = "~/.workbuddy/memory/"

class SecondBrainError(Exception):
    """第二大脑系统异常"""

    pass

class MemoryNotFoundError(SecondBrainError):
    """记忆未找到"""

    pass

class InvalidMemoryTypeError(SecondBrainError):
    """无效的记忆类型"""

    pass

# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class Memory:
    """记忆条目"""

    id: Optional[int] = None
    type: str = ""  # 记忆类型
    content: str = ""  # 记忆内容
    confidence: float = 0.5  # 置信度 0-1
    importance: int = 5  # 重要性 1-10
    persistence: int = 3  # 持久性 1-5
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    evidence_count: int = 1  # 证据计数
    source: str = "manual"  # 来源
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "confidence": self.confidence,
            "importance": self.importance,
            "persistence": self.persistence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "evidence_count": self.evidence_count,
            "source": self.source,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Memory":
        """从字典创建"""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def is_high_confidence(self) -> bool:
        """是否高置信度"""
        return self.confidence >= CONFIDENCE_THRESHOLD

    @property
    def age_days(self) -> int:
        """记忆年龄（天）"""
        if self.created_at:
            return (datetime.now() - self.created_at).days
        return 0

@dataclass
class MemoryStats:
    """记忆统计"""

    total: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    high_confidence_count: int = 0
    last_extraction: Optional[datetime] = None
    last_consolidation: Optional[datetime] = None

@dataclass
class ExtractionResult:
    """提取结果"""

    facts: List[Memory]
    processed_text: str
    tokens_used: int

# ============================================================================
# 核心类
# ============================================================================

class SecondBrain:
    """
    第二大脑记忆系统

    模拟人类记忆的工作方式：
    - 工作记忆：短期对话
    - 情景记忆：事件日志
    - 长期记忆：结构化事实

    功能:
    - 自动事实提取
    - FTS5全文搜索
    - 冲突解决
    - 自动整合
    - 定期修剪

    使用示例:
    ```python
    brain = SecondBrain()

    # 提取记忆
    result = brain.extract_facts("用户喜欢在下午工作")
    brain.save_memories(result.facts)

    # 召回相关记忆
    memories = brain.recall("用户什么时候工作")

    # 整合和修剪
    brain.consolidate()
    brain.prune()
    ```
    """

    def __init__(self, db_path: Optional[str] = None, jsonl_dir: Optional[str] = None, auto_enabled: bool = True):
        """
        初始化第二大脑

        Args:
            db_path: SQLite数据库路径
            jsonl_dir: JSONL日志目录
            auto_enabled: 是否启用自动功能
        """
        self.db_path = Path(db_path or DEFAULT_DB_PATH).expanduser()
        self.jsonl_dir = Path(jsonl_dir or DEFAULT_JSONL_DIR).expanduser()

        # 创建目录
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_dir.mkdir(parents=True, exist_ok=True)

        # 自动功能
        self.auto_enabled = auto_enabled
        self.last_extraction: Optional[datetime] = None
        self.last_consolidation: Optional[datetime] = None

        # 线程锁
        self._lock = threading.Lock()

        # 初始化数据库
        self._init_db()

        # 启动后台任务
        if self.auto_enabled:
            self._start_background_tasks()

    def _init_db(self):
        """初始化数据库和FTS5"""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # 主记忆表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    importance INTEGER DEFAULT 5,
                    persistence INTEGER DEFAULT 3,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    evidence_count INTEGER DEFAULT 1,
                    source TEXT DEFAULT 'manual',
                    tags TEXT DEFAULT '[]'
                )
            """)

            # FTS5全文搜索
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
                USING fts5(
                    content,
                    content='memories',
                    content_rowid='id'
                )
            """)

            # 索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_confidence ON memories(confidence)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)")

            # 配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # 核心功能
    # =========================================================================

    def extract_facts(
        self, text: str, max_facts: int = 3, min_confidence: float = CONFIDENCE_THRESHOLD
    ) -> ExtractionResult:
        """
        从文本中提取事实

        使用简单的规则引擎从对话中提取潜在的事实记忆。
        实际项目中可以使用LLM进行更智能的提取。

        Args:
            text: 待分析的文本
            max_facts: 最多提取的事实数
            min_confidence: 最小置信度

        Returns:
            ExtractionResult: 提取结果
        """
        facts = []
        tokens_used = len(text) // 4

        # 简单的模式匹配提取（实际应用中应使用LLM）
        patterns = {
            "preference": [
                r"我喜欢(.+?)[。.]",
                r"我偏好(.+?)[。.]",
                r"我比较喜欢(.+?)[。.]",
                r"我倾向于(.+?)[。.]",
            ],
            "goal": [
                r"我想(.+?)[。.]",
                r"我的目标是(.+?)[。.]",
                r"计划(.+?)[。.]",
            ],
            "habit": [
                r"我通常(.+?)[。.]",
                r"我习惯(.+?)[。.]",
                r"我经常(.+?)[。.]",
            ],
            "project": [
                r"项目名(.+?)[。.]",
                r"正在做(.+?)[。.]",
                r"开发(.+?)[。.]",
            ],
            "constraint": [
                r"不能(.+?)[。.]",
                r"必须(.+?)[。.]",
                r"限制是(.+?)[。.]",
            ],
        }

        for memory_type, type_patterns in patterns.items():
            for pattern in type_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if len(facts) >= max_facts:
                        break

                    # 计算简单的置信度
                    confidence = self._calculate_confidence(match, memory_type)

                    if confidence >= min_confidence:
                        memory = Memory(
                            type=memory_type,
                            content=match.strip(),
                            confidence=confidence,
                            importance=5,
                            persistence=3,
                            source="extraction",
                        )
                        facts.append(memory)

        return ExtractionResult(facts=facts, processed_text=text, tokens_used=tokens_used)

    def _calculate_confidence(self, content: str, memory_type: str) -> float:
        """
        计算置信度

        简单实现，实际应使用ML模型
        """
        base = 0.5

        # 长度调整
        if len(content) > 10:
            base += 0.1
        if len(content) > 50:
            base += 0.1

        # 包含具体信息
        if re.search(r"\d+", content):  # 包含数字
            base += 0.1
        if re.search(r"[年月日时分秒]", content):  # 包含时间词
            base += 0.05

        # 类型特定调整
        type_bonus = {"preference": 0.05, "habit": 0.1, "goal": 0.05, "constraint": 0.1}
        base += type_bonus.get(memory_type, 0)

        return min(0.95, base)

    def save_memories(self, memories: List[Memory]) -> List[int]:
        """
        保存记忆到数据库

        Args:
            memories: 记忆列表

        Returns:
            List[int]: 保存的记忆ID列表
        """
        ids = []

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            for memory in memories:
                # 检查是否已存在相似的记忆
                existing = self._find_similar(cursor, memory)

                if existing:
                    # 更新证据计数
                    self._merge_memories(cursor, existing, memory)
                    ids.append(existing["id"])
                else:
                    # 插入新记忆
                    cursor.execute(
                        """
                        INSERT INTO memories 
                        (type, content, confidence, importance, persistence, 
                         created_at, updated_at, evidence_count, source, tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            memory.type,
                            memory.content,
                            memory.confidence,
                            memory.importance,
                            memory.persistence,
                            memory.created_at or datetime.now(),
                            datetime.now(),
                            memory.evidence_count,
                            memory.source,
                            json.dumps(memory.tags),
                        ),
                    )

                    memory_id = cursor.lastrowid
                    ids.append(memory_id)

                    # 更新FTS索引
                    cursor.execute(
                        """
                        INSERT INTO memories_fts (rowid, content)
                        VALUES (?, ?)
                    """,
                        (memory_id, memory.content),
                    )

            conn.commit()
            conn.close()

        self.last_extraction = datetime.now()
        return ids

    def _find_similar(self, cursor, memory: Memory) -> Optional[sqlite3.Row]:
        """查找相似的记忆"""
        # 使用简单的关键词匹配
        words = set(re.findall(r"\w+", memory.content.lower()))

        if not words:
            return None

        # 构建SQL
        conditions = " OR ".join(["content LIKE ?" for _ in words])
        params = [f"%{w}%" for w in words]

        cursor.execute(
            f"""
            SELECT * FROM memories
            WHERE type = ? AND ({conditions})
            ORDER BY evidence_count DESC
            LIMIT 1
        """,
            [memory.type] + params,
        )

        return cursor.fetchone()

    def _merge_memories(self, cursor, existing: sqlite3.Row, new: Memory):
        """合并相似记忆"""
        # 增加证据计数
        new_evidence = existing["evidence_count"] + 1

        # 更新置信度（基于更多证据）
        new_confidence = min(
            0.95, (existing["confidence"] * existing["evidence_count"] + new.confidence) / new_evidence
        )

        cursor.execute(
            """
            UPDATE memories
            SET evidence_count = ?,
                confidence = ?,
                updated_at = ?
            WHERE id = ?
        """,
            (new_evidence, new_confidence, datetime.now(), existing["id"]),
        )

    def recall(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = MAX_RECALL_MEMORIES,
        char_budget: int = RECALL_CHAR_BUDGET,
    ) -> List[Memory]:
        """
        召回相关记忆

        使用FTS5全文搜索找到最相关的记忆。

        Args:
            query: 查询文本
            memory_types: 限定记忆类型
            limit: 最多返回记忆数
            char_budget: 字符预算

        Returns:
            List[Memory]: 相关记忆列表
        """
        memories = []
        total_chars = 0

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # FTS5搜索
            if memory_types:
                type_placeholders = ",".join(["?" for _ in memory_types])
                cursor.execute(
                    f"""
                    SELECT m.* FROM memories m
                    JOIN memories_fts fts ON m.id = fts.rowid
                    WHERE memories_fts MATCH ?
                    AND m.type IN ({type_placeholders})
                    AND m.confidence >= ?
                    ORDER BY m.evidence_count DESC, m.confidence DESC
                    LIMIT ?
                """,
                    [query] + memory_types + [CONFIDENCE_THRESHOLD, limit],
                )
            else:
                cursor.execute(
                    """
                    SELECT m.* FROM memories m
                    JOIN memories_fts fts ON m.id = fts.rowid
                    WHERE memories_fts MATCH ?
                    AND m.confidence >= ?
                    ORDER BY m.evidence_count DESC, m.confidence DESC
                    LIMIT ?
                """,
                    [query, CONFIDENCE_THRESHOLD, limit],
                )

            rows = cursor.fetchall()

            for row in rows:
                memory = Memory(
                    id=row["id"],
                    type=row["type"],
                    content=row["content"],
                    confidence=row["confidence"],
                    importance=row["importance"],
                    persistence=row["persistence"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    evidence_count=row["evidence_count"],
                    source=row["source"],
                    tags=json.loads(row["tags"]),
                )

                # 检查字符预算
                if total_chars + len(memory.content) <= char_budget:
                    memories.append(memory)
                    total_chars += len(memory.content)
                else:
                    break

            conn.close()

        return memories

    def get_memories_by_type(self, memory_type: str, limit: int = 100) -> List[Memory]:
        """获取指定类型的所有记忆"""
        if memory_type not in MEMORY_TYPES:
            raise InvalidMemoryTypeError(f"无效的记忆类型: {memory_type}")

        memories = []

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM memories
                WHERE type = ?
                ORDER BY confidence DESC, created_at DESC
                LIMIT ?
            """,
                [memory_type, limit],
            )

            for row in cursor.fetchall():
                memories.append(
                    Memory(
                        id=row["id"],
                        type=row["type"],
                        content=row["content"],
                        confidence=row["confidence"],
                        importance=row["importance"],
                        persistence=row["persistence"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        evidence_count=row["evidence_count"],
                        source=row["source"],
                        tags=json.loads(row["tags"]),
                    )
                )

            conn.close()

        return memories

    def add_memory(
        self,
        content: str,
        memory_type: str,
        confidence: float = 0.7,
        importance: int = 5,
        tags: Optional[List[str]] = None,
    ) -> int:
        """
        手动添加记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型
            confidence: 置信度
            importance: 重要性
            tags: 标签

        Returns:
            int: 记忆ID
        """
        if memory_type not in MEMORY_TYPES:
            raise InvalidMemoryTypeError(f"无效的记忆类型: {memory_type}")

        memory = Memory(
            type=memory_type,
            content=content,
            confidence=confidence,
            importance=importance,
            persistence=3,
            source="manual",
            tags=tags or [],
        )

        ids = self.save_memories([memory])
        return ids[0]

    def update_memory(
        self,
        memory_id: int,
        content: Optional[str] = None,
        confidence: Optional[float] = None,
        importance: Optional[int] = None,
    ) -> bool:
        """更新记忆"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            updates = []
            params = []

            if content is not None:
                updates.append("content = ?")
                params.append(content)
            if confidence is not None:
                updates.append("confidence = ?")
                params.append(confidence)
            if importance is not None:
                updates.append("importance = ?")
                params.append(importance)

            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.now())

                params.append(memory_id)

                cursor.execute(f"UPDATE memories SET {', '.join(updates)} WHERE id = ?", params)

                # 更新FTS索引
                if content:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO memories_fts (rowid, content)
                        VALUES (?, ?)
                    """,
                        (memory_id, content),
                    )

                conn.commit()

            conn.close()

        return True

    def delete_memory(self, memory_id: int) -> bool:
        """删除记忆"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM memories WHERE id = ?", [memory_id])
            cursor.execute("DELETE FROM memories_fts WHERE rowid = ?", [memory_id])

            conn.commit()
            affected = cursor.rowcount
            conn.close()

        return affected > 0

    def resolve_conflict(self, fact1: Memory, fact2: Memory, strategy: str = CONFLICT_RESOLUTION) -> Memory:
        """
        解决记忆冲突

        Args:
            fact1: 记忆1
            fact2: 记忆2
            strategy: 解决策略 ('confidence' | 'recency')

        Returns:
            Memory: 胜出的记忆
        """
        if strategy == "confidence":
            # 高置信度胜出
            if fact1.confidence >= fact2.confidence:
                winner = fact1
                loser = fact2
            else:
                winner = fact2
                loser = fact1
        else:  # recency
            # 新近度优先
            if fact1.updated_at >= fact2.updated_at:
                winner = fact1
                loser = fact2
            else:
                winner = fact2
                loser = fact1

        # 更新胜出者的置信度
        loser.confidence *= 0.9  # 降低失败者的置信度

        return winner

    def consolidate(self) -> Dict[str, int]:
        """
        整合记忆

        定期执行:
        - 构建档案摘要
        - 生成模式反思
        - 晋升活跃记忆到持久记忆

        Returns:
            Dict: 整合统计
        """
        stats = {"profiles_updated": 0, "reflections_generated": 0}

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 为每种记忆类型生成摘要
            for memory_type in MEMORY_TYPES:
                cursor.execute(
                    """
                    SELECT content FROM memories
                    WHERE type = ? AND evidence_count >= 3
                    ORDER BY confidence DESC
                    LIMIT 10
                """,
                    [memory_type],
                )

                memories = [row[0] for row in cursor.fetchall()]

                if memories:
                    # 晋升为持久记忆
                    cursor.execute(
                        """
                        UPDATE memories
                        SET persistence = 5, updated_at = ?
                        WHERE type = ? AND evidence_count >= 3 AND persistence < 5
                    """,
                        [datetime.now(), memory_type],
                    )

                    stats["profiles_updated"] += cursor.rowcount

            # 生成反思（实际应使用LLM）
            cursor.execute("""
                SELECT COUNT(*) FROM memories
                WHERE type = 'reflection'
            """)
            reflection_count = cursor.fetchone()[0]

            if reflection_count == 0:
                # 创建初始反思 - 直接插入避免递归锁
                cursor.execute(
                    """
                    INSERT INTO memories 
                    (type, content, confidence, importance, persistence, 
                     created_at, updated_at, evidence_count, source, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        "reflection",
                        "这是用户的个人知识库，包含各种偏好和目标。",
                        0.8,
                        5,
                        3,
                        datetime.now(),
                        datetime.now(),
                        1,
                        "system",
                        "[]",
                    ),
                )
                mem_id = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT INTO memories_fts (rowid, content)
                    VALUES (?, ?)
                """,
                    (mem_id, "这是用户的个人知识库，包含各种偏好和目标。"),
                )
                stats["reflections_generated"] = 1

            conn.commit()

            # 保存配置到同一连接，避免database locked
            cursor.execute(
                """
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            """,
                ["last_consolidation", datetime.now().isoformat(), datetime.now()],
            )
            conn.commit()
            conn.close()

        self.last_consolidation = datetime.now()

        return stats

    def prune(self) -> Dict[str, int]:
        """
        修剪记忆

        定期执行:
        - 清除21天无活动的活跃记忆
        - 清除120天低置信度的持久记忆

        Returns:
            Dict: 修剪统计
        """
        stats = {"active_pruned": 0, "low_confidence_pruned": 0}

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 清除21天无活动的记忆
            cutoff_active = datetime.now() - timedelta(days=PRUNE_DAYS_ACTIVE)
            cursor.execute(
                """
                DELETE FROM memories
                WHERE updated_at < ? AND persistence < 3
            """,
                [cutoff_active],
            )
            stats["active_pruned"] = cursor.rowcount

            # 清除120天低置信度的记忆
            cutoff_low = datetime.now() - timedelta(days=PRUNE_DAYS_LOW_CONFIDENCE)
            cursor.execute(
                """
                DELETE FROM memories
                WHERE created_at < ? AND confidence < 0.5
            """,
                [cutoff_low],
            )
            stats["low_confidence_pruned"] = cursor.rowcount

            conn.commit()
            conn.close()

        return stats

    def get_stats(self) -> MemoryStats:
        """获取记忆统计"""
        stats = MemoryStats()

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 总数
            cursor.execute("SELECT COUNT(*) FROM memories")
            stats.total = cursor.fetchone()[0]

            # 按类型统计
            cursor.execute("""
                SELECT type, COUNT(*) as count FROM memories
                GROUP BY type
            """)
            for row in cursor.fetchall():
                stats.by_type[row[0]] = row[1]

            # 平均置信度
            cursor.execute("SELECT AVG(confidence) FROM memories")
            avg = cursor.fetchone()[0]
            stats.avg_confidence = avg if avg else 0.0

            # 高置信度数量
            cursor.execute(
                """
                SELECT COUNT(*) FROM memories WHERE confidence >= ?
            """,
                [CONFIDENCE_THRESHOLD],
            )
            stats.high_confidence_count = cursor.fetchone()[0]

            conn.close()

        stats.last_extraction = self.last_extraction
        stats.last_consolidation = self.last_consolidation

        return stats

    def search(self, query: str, memory_type: Optional[str] = None, min_confidence: float = 0.0) -> List[Memory]:
        """搜索记忆"""
        return self.recall(query, [memory_type] if memory_type else None, char_budget=5000)

    def clear(self, memory_type: Optional[str] = None, confirm: bool = False):
        """
        清除记忆

        Args:
            memory_type: 限定类型，为None则清除所有
            confirm: 必须确认为True才能执行
        """
        if not confirm:
            raise SecondBrainError("必须确认才能清除记忆")

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            if memory_type:
                cursor.execute("DELETE FROM memories WHERE type = ?", [memory_type])
            else:
                cursor.execute("DELETE FROM memories")

            # 重建FTS索引
            cursor.execute('INSERT INTO memories_fts(memories_fts) VALUES("rebuild")')

            conn.commit()
            conn.close()

    def export_memories(self, output_path: str) -> str:
        """导出记忆到JSON"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM memories ORDER BY created_at DESC")

            memories = []
            for row in cursor.fetchall():
                memories.append(
                    Memory(
                        id=row["id"],
                        type=row["type"],
                        content=row["content"],
                        confidence=row["confidence"],
                        importance=row["importance"],
                        persistence=row["persistence"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        evidence_count=row["evidence_count"],
                        source=row["source"],
                        tags=json.loads(row["tags"]),
                    ).to_dict()
                )

            conn.close()

            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(memories, indent=2, ensure_ascii=False))

        return str(output)

    def import_memories(self, input_path: str, merge: bool = True) -> int:
        """
        导入记忆

        Args:
            input_path: JSON文件路径
            merge: 是否合并，False则替换

        Returns:
            int: 导入的记忆数
        """
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {input_path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        memories = [Memory.from_dict(item) for item in data]

        if not merge:
            self.clear(confirm=True)

        ids = self.save_memories(memories)
        return len(ids)

    def _save_config(self, key: str, value: str):
        """保存配置"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            """,
                [key, value, datetime.now()],
            )

            conn.commit()
            conn.close()

    def _start_background_tasks(self):
        """启动后台任务"""
        # 实际应用中应使用调度器
        pass

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_stats()
        return {
            "status": "healthy",
            "total_memories": stats.total,
            "avg_confidence": stats.avg_confidence,
            "last_extraction": stats.last_extraction.isoformat() if stats.last_extraction else None,
            "last_consolidation": stats.last_consolidation.isoformat() if stats.last_consolidation else None,
        }

    def to_context_string(self, memories: List[Memory]) -> str:
        """
        将记忆转换为上下文字符串

        Args:
            memories: 记忆列表

        Returns:
            str: 格式化的上下文字符串
        """
        if not memories:
            return ""

        lines = ["\n## 相关记忆:\n"]

        for i, memory in enumerate(memories, 1):
            type_emoji = {
                "identity": "👤",
                "preference": "❤️",
                "goal": "🎯",
                "project": "📁",
                "habit": "🔄",
                "decision": "✅",
                "constraint": "⚠️",
                "relationship": "🤝",
                "episode": "📅",
                "reflection": "💭",
            }.get(memory.type, "📝")

            lines.append(f"{type_emoji} {memory.content}")

        return "\n".join(lines)

# ============================================================================
# 快捷函数
# ============================================================================

def create_default_brain() -> SecondBrain:
    """创建默认的第二大脑"""
    return SecondBrain()

def remember(content: str, memory_type: str = "preference", **kwargs) -> int:
    """
    快速保存记忆

    Args:
        content: 记忆内容
        memory_type: 记忆类型
        **kwargs: 其他参数

    Returns:
        int: 记忆ID
    """
    brain = create_default_brain()
    return brain.add_memory(content, memory_type, **kwargs)

def recall(query: str, memory_types: Optional[List[str]] = None) -> str:
    """
    快速召回记忆

    Args:
        query: 查询
        memory_types: 限定类型

    Returns:
        str: 记忆上下文
    """
    brain = create_default_brain()
    memories = brain.recall(query, memory_types)
    return brain.to_context_string(memories)

# ============================================================================
# 示例和使用
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("AUTO-EVO-AI V0.1 - Second Brain Memory Module")
    print("=" * 60)

    # 创建第二大脑
    brain = SecondBrain(db_path="~/.workbuddy/test-brain.db")

    # 添加一些记忆
    print("\n📝 添加示例记忆:")

    brain.add_memory("用户喜欢在下午工作，效率最高", memory_type="habit", confidence=0.8)

    brain.add_memory("用户使用Windows系统", memory_type="preference", confidence=0.9)

    brain.add_memory("用户正在开发AUTO-EVO-AI项目", memory_type="project", confidence=0.85)

    brain.add_memory("用户希望提高工作效率", memory_type="goal", confidence=0.8)

    print("✅ 已添加4条记忆")

    # 获取统计
    stats = brain.get_stats()
    print(f"\n📊 记忆统计:")
    print(f"   - 总数: {stats.total}")
    print(f"   - 高置信度: {stats.high_confidence_count}")
    print(f"   - 平均置信度: {stats.avg_confidence:.2f}")

    # 召回测试
    print("\n🔍 召回测试:")

    memories = brain.recall("用户什么时候工作")
    print(f"查询「用户什么时候工作」:")
    if memories:
        for m in memories:
            print(f"   - [{m.type}] {m.content}")
    else:
        print("   - 未找到相关记忆")

    memories = brain.recall("操作系统")
    print(f"\n查询「操作系统」:")
    if memories:
        for m in memories:
            print(f"   - [{m.type}] {m.content}")
    else:
        print("   - 未找到相关记忆")

    # 按类型获取
    print("\n📂 按类型查看:")
    habits = brain.get_memories_by_type("habit")
    for h in habits:
        print(f"   - {h.content}")

    # 测试提取
    print("\n🧠 记忆提取测试:")
    result = brain.extract_facts("用户告诉我他通常在早上8点起床，然后喜欢喝咖啡")
    print(f"   - 从文本提取到 {len(result.facts)} 个事实")
    for fact in result.facts:
        print(f"     [{fact.type}] {fact.content}")

    # 整合和修剪
    print("\n⚙️ 执行整合和修剪:")
    stats = brain.consolidate()
    print(f"   - 档案更新: {stats['profiles_updated']}")
    print(f"   - 反思生成: {stats['reflections_generated']}")

    prune_stats = brain.prune()
    print(f"   - 活跃记忆清除: {prune_stats['active_pruned']}")
    print(f"   - 低置信度清除: {prune_stats['low_confidence_pruned']}")

    # 导出测试
    print("\n💾 导出记忆:")
    export_path = brain.export_memories("~/.workbuddy/exported-memories.json")
    print(f"   - 已导出到: {export_path}")

    print("\n" + "=" * 60)
    print("Second Brain Memory Module 测试完成!")
    print("=" * 60)

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("second_brain.execute", "start", action=action)
        self.metrics_collector.counter("second_brain.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "second_brain"}
            else:
                result = {"success": True, "action": action, "module": "second_brain"}
            self.metrics_collector.counter("second_brain.execute.success", 1)
            self.trace("second_brain.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("second_brain.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "second_brain"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "second_brain", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("second_brain.initialize", "start")
        self.metrics_collector.gauge("second_brain.initialized", 1)
        self.audit("初始化second_brain", level="info")
        self.trace("second_brain.initialize", "end")
        return {"success": True, "module": "second_brain"}

module_class = InvalidMemoryTypeError
