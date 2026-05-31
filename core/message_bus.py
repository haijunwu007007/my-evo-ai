"""AUTO-EVO-AI V0.1 — 进程内事件总线

轻量级发布/订阅系统，支持同步/异步分发、通配符主题、持久化事件。
为未来分布式消息队列提供兼容接口。
"""
import asyncio, time, json, logging, uuid, threading, sqlite3
from core.logging_config import get_logger
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

logger = get_logger("evo.message-bus")
DATA_DIR = Path(".evo_data/queue")
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Event:
    """总线事件。"""
    topic: str
    data: Any = None
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    source: str = ""


class MessageBus:
    """进程内事件总线（单例）。"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self._sync_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._async_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: List[Event] = []
        self._max_history = 1000
        self._wildcard_cache: Dict[str, Set[str]] = {}
        logger.info("[MessageBus] 初始化完成")

    # ── 注册 ──

    def subscribe(self, topic: str, handler: Callable):
        """订阅同步 handler。topic 支持尾部通配符 'module.*'。"""
        self._sync_handlers[topic].append(handler)
        self._wildcard_cache.clear()
        logger.debug("[MessageBus] 订阅 sync: %s", topic)

    def subscribe_async(self, topic: str, handler: Callable):
        """订阅异步 handler。"""
        self._async_handlers[topic].append(handler)
        self._wildcard_cache.clear()
        logger.debug("[MessageBus] 订阅 async: %s", topic)

    def unsubscribe(self, topic: str, handler: Callable):
        self._sync_handlers[topic] = [h for h in self._sync_handlers[topic] if h != handler]
        self._async_handlers[topic] = [h for h in self._async_handlers[topic] if h != handler]

    # ── 持久化队列 ──

    def _ensure_queue_table(self):
        """确保队列表存在。"""
        db_path = str(DATA_DIR / "events.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS queue (
                id TEXT PRIMARY KEY, topic TEXT, data TEXT, source TEXT,
                created_at REAL, status TEXT DEFAULT 'pending',
                consumer TEXT, consumed_at REAL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_topic ON queue(topic)")
            conn.commit()

    def enqueue(self, topic: str, data: Any = None, source: str = "",
                persistent: bool = True) -> str:
        """发布持久化事件到队列（跨进程可见）。返回 event_id。"""
        event_id = uuid.uuid4().hex[:12]
        if persistent:
            self._ensure_queue_table()
            db_path = str(DATA_DIR / "events.db")
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "INSERT INTO queue (id,topic,data,source,created_at,status) VALUES (?,?,?,?,?,?)",
                    (event_id, topic, json.dumps(data, ensure_ascii=False, default=str),
                     source, time.time(), "pending"))
                conn.commit()
        # 同时也在进程内发布
        event = Event(topic=topic, data=data, source=source, event_id=event_id)
        self._history.append(event)
        return event_id

    def dequeue(self, consumer: str = "default", batch: int = 1,
                topics: List[str] = None) -> List[Dict]:
        """消费队列中待处理的事件（跨进程安全）。"""
        self._ensure_queue_table()
        db_path = str(DATA_DIR / "events.db")
        with sqlite3.connect(db_path) as conn:
            if topics:
                placeholders = ",".join("?" * len(topics))
                rows = conn.execute(
                    f"SELECT * FROM queue WHERE status='pending' AND topic IN ({placeholders}) ORDER BY created_at LIMIT ?",
                    tuple(topics) + (batch,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM queue WHERE status='pending' ORDER BY created_at LIMIT ?",
                    (batch,)).fetchall()
            results = []
            for r in rows:
                conn.execute("UPDATE queue SET status='processing', consumer=?, consumed_at=? WHERE id=?",
                             (consumer, time.time(), r[0]))
                results.append({
                    "event_id": r[0], "topic": r[1],
                    "data": json.loads(r[2]) if r[2] else None,
                    "source": r[3], "created_at": r[4]
                })
            conn.commit()
        return results

    def ack(self, event_id: str):
        """确认消费完成。"""
        db_path = str(DATA_DIR / "events.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE queue SET status='completed' WHERE id=?", (event_id,))
            conn.commit()

    def queue_stats(self) -> Dict:
        """队列统计。"""
        self._ensure_queue_table()
        db_path = str(DATA_DIR / "events.db")
        with sqlite3.connect(db_path) as conn:
            pending = conn.execute("SELECT COUNT(*) FROM queue WHERE status='pending'").fetchone()[0]
            processing = conn.execute("SELECT COUNT(*) FROM queue WHERE status='processing'").fetchone()[0]
            completed = conn.execute("SELECT COUNT(*) FROM queue WHERE status='completed'").fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM queue").fetchone()[0]
            return {"pending": pending, "processing": processing,
                    "completed": completed, "total": total}

    # ── 发布 ──

    def publish(self, topic: str, data: Any = None, source: str = "",
                persistent: bool = True) -> int:
        """发布事件（同步分发 + 可选持久化）。返回触发的 handler 数量。"""
        if persistent and len(self._sync_handlers.get(topic, [])) == 0:
            # 没有同步 handler 时走持久化队列
            self.enqueue(topic, data, source, persistent=True)
        event = Event(topic=topic, data=data, source=source)
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        count = 0
        for matched_topic in self._match_topics(topic):
            for handler in self._sync_handlers.get(matched_topic, []):
                try:
                    handler(event)
                    count += 1
                except Exception as e:
                    logger.error("[MessageBus] sync handler 异常: %s", e, exc_info=True)
        return count

    async def publish_async(self, topic: str, data: Any = None, source: str = "") -> int:
        """发布事件（异步分发）。"""
        event = Event(topic=topic, data=data, source=source)
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        count = 0
        for matched_topic in self._match_topics(topic):
            for handler in self._async_handlers.get(matched_topic, []):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                    count += 1
                except Exception as e:
                    logger.error("[MessageBus] async handler 异常: %s", e, exc_info=True)
        return count

    # ── 查询 ──

    def get_history(self, topic: Optional[str] = None, limit: int = 50) -> List[Dict]:
        events = self._history
        if topic:
            matched = self._match_topics(topic)
            events = [e for e in events if e.topic in matched]
        return [
            {"event_id": e.event_id, "topic": e.topic, "data": e.data,
             "timestamp": e.timestamp, "source": e.source}
            for e in events[-limit:]
        ]

    def stats(self) -> Dict:
        s = {
            "sync_subscriptions": sum(len(v) for v in self._sync_handlers.values()),
            "async_subscriptions": sum(len(v) for v in self._async_handlers.values()),
            "history_count": len(self._history),
            "topics": list(set(list(self._sync_handlers.keys()) + list(self._async_handlers.keys()))),
        }
        try:
            s["queue"] = self.queue_stats()
        except Exception:
            s["queue"] = {"error": "unavailable"}
        return s

    # ── 内部 ──

    def _match_topics(self, topic: str) -> Set[str]:
        """支持 'module.*'、'system.#' 通配符匹配。同时包含历史事件主题。"""
        if topic in self._wildcard_cache:
            return self._wildcard_cache[topic]
        # 订阅主题 + 历史事件主题
        all_topics = set(self._sync_handlers.keys()) | set(self._async_handlers.keys())
        all_topics |= {e.topic for e in self._history}
        matched = {topic}  # 精确匹配始终包含
        for t in all_topics:
            if t == topic:
                matched.add(t)
            elif t.endswith(".*"):
                prefix = t[:-2]
                if topic.startswith(prefix):
                    matched.add(t)
            elif t.endswith(".#"):
                prefix = t[:-2]
                if topic == prefix or topic.startswith(prefix + "."):
                    matched.add(t)
        self._wildcard_cache[topic] = matched
        return matched
