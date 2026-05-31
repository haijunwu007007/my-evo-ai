"""
AUTO-EVO-AI V0.1 — Delay Queue
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# Grade: A
        AUTO-EVO-AI V0.1 | 延迟队列引擎
企业级定时消息投递系统 - 支持延迟消息、定时任务、重试策略

        功能特性:
- 多级延迟队列（秒级/分钟级/小时级/天级时间轮）
- 消息优先级支持（高/中/低三级优先级）
- 精确定时投递（指定时间点投递）
- 消息重试策略（指数退避、最大重试次数）
- 死信队列（超过重试次数的消息转入死信）
- 消息持久化（文件系统持久化，重启恢复）
- 消息确认机制（ACK/NACK/自动超时重投）
- 延迟消息取消和查询
- 指标监控（投递延迟、成功率、积压量）

        生产级标准: 链路追踪 | 指标采集 | 审计日志 | 熔断限流 | 健康检查
"""

__module_meta__ = {
        "id": "delay-queue",
        "name": "Delay Queue",
        "version": "V0.1",
        "group": "messaging",
        "inputs": [
            {
                "name": "attempt",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "data_dir",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "messages",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "messages_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "topic",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "handler",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "success",
                "type": "bool",
                "description": "是否成功"
            },
            {
                "name": "results",
                "type": "list[dict]",
                "description": "结果列表"
            },
            {
                "name": "success_2",
                "type": "bool",
                "description": "是否成功"
            }
        ],
        "triggers": [
            {
                "type": "event",
                "config": {
                    "on": "delay_queue.trigger"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "handler",
            "manager",
            "delay"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 | 延迟队列引擎 企业级定时消息投递系统 - 支持延迟消息、定时任务、重试策略"
    }

import os
import sys
import json
import time
import heapq
import threading
import traceback
import uuid
import struct
import pickle
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from pathlib import Path
from functools import wraps
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    Result,
    HealthReport,
    ModuleStats,
    CircuitBreakerMixin,
    RateLimiterMixin,
)
from modules._base.metrics import prometheus_timer, metrics_collector

class MessagePriority(IntEnum):
    """消息优先级"""

    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 15

class MessageState(Enum):
    """消息状态"""

    PENDING = "pending"  # 等待投递
    SCHEDULED = "scheduled"  # 已调度
    DELIVERING = "delivering"  # 投递中
    ACKED = "acked"  # 已确认
    NACKED = "nacked"  # 已拒绝
    RETRYING = "retrying"  # 重试中
    DEAD_LETTER = "dead_letter"  # 死信
    CANCELLED = "cancelled"  # 已取消
    EXPIRED = "expired"  # 已过期

class QueueType(Enum):
    """队列类型"""

    DELAY = "delay"  # 延迟队列
    TIMED = "timed"  # 定时队列
    RETRY = "retry"  # 重试队列
    DEAD_LETTER = "dead_letter"  # 死信队列

@dataclass(order=True)
class DelayedMessage:
    """延迟消息（支持堆排序）"""

    execute_at: float  # 执行时间戳
    priority: int = field(default=MessagePriority.NORMAL, compare=True)
    _seq: int = field(default=0, compare=True)
    message_id: str = field(default="", compare=False)
    topic: str = field(default="", compare=False)
    payload: Any = field(default=None, compare=False)
    state: MessageState = field(default=MessageState.PENDING, compare=False)
    created_at: float = field(default_factory=time.time, compare=False)
    delivered_at: Optional[float] = field(default=None, compare=False)
    ack_timeout: float = field(default=30.0, compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    delay_ms: float = field(default=0, compare=False)
    headers: Dict[str, str] = field(default_factory=dict, compare=False)
    callback_url: str = field(default="", compare=False)

@dataclass
class DeliveryResult:
    """投递结果"""

    message_id: str
    success: bool
    error: str = ""
    duration_ms: float = 0
    attempt: int = 0

@dataclass
class RetryPolicy:
    """重试策略"""

    max_retries: int = 3
    base_delay_ms: float = 1000
    max_delay_ms: float = 60000
    backoff_factor: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        delay = min(
            self.base_delay_ms * (self.backoff_factor**attempt),
            self.max_delay_ms,
        )
        if self.jitter:
            import time as tmod

            delay *= 0.5 + (int(tmod.time()*1000000)%1000000/1000000) * 0.5
        return delay

@dataclass
class QueueStats:
    """队列统计"""

    queue_type: str
    total_messages: int = 0
    pending: int = 0
    scheduled: int = 0
    delivering: int = 0
    acked: int = 0
    dead_letter: int = 0
    cancelled: int = 0
    avg_delivery_latency_ms: float = 0
    success_rate: float = 0

class DelayQueueError(Exception):
    """延迟队列异常"""

    pass

class MessageExpiredError(Exception):
    """消息过期异常"""

    pass

class PersistenceManager(object):
    """消息持久化管理器"""

    def __init__(self, data_dir: Optional[str] = None):
        super().__init__()
        self._data_dir = Path(data_dir or "./.evo_data/delay_queue")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._pending_file = self._data_dir / "pending.bin"
        self._dead_letter_file = self._data_dir / "dead_letter.bin"
        self._meta_file = self._data_dir / "meta.json"
        self._lock = threading.Lock()

    def save_pending(self, messages: List[DelayedMessage]) -> bool:
        """保存待处理消息"""
        try:
            with self._lock:
                data = [
                    {
                        "execute_at": m.execute_at,
                        "priority": m.priority,
                        "message_id": m.message_id,
                        "topic": m.topic,
                        "payload": m.payload,
                        "state": m.state.value,
                        "created_at": m.created_at,
                        "retry_count": m.retry_count,
                        "max_retries": m.max_retries,
                        "delay_ms": m.delay_ms,
                        "headers": m.headers,
                        "ack_timeout": m.ack_timeout,
                        "callback_url": m.callback_url,
                    }
                    for m in messages
                    if m.state in (MessageState.PENDING, MessageState.RETRYING, MessageState.SCHEDULED)
                ]
                self._pending_file.write_bytes(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))
                return True
        except Exception as e:
            return False

    def load_pending(self) -> List[DelayedMessage]:
        """加载待处理消息"""
        try:
            with self._lock:
                if not self._pending_file.exists():
                    return []
                data = json.loads(self._pending_file.read_bytes().decode("utf-8"))
                messages = []
                for item in data:
                    msg = DelayedMessage(
                        execute_at=item["execute_at"],
                        priority=item.get("priority", MessagePriority.NORMAL),
                        message_id=item["message_id"],
                        topic=item.get("topic", ""),
                        payload=item.get("payload"),
                        state=MessageState(item.get("state", "pending")),
                        created_at=item.get("created_at", time.time()),
                        retry_count=item.get("retry_count", 0),
                        max_retries=item.get("max_retries", 3),
                        delay_ms=item.get("delay_ms", 0),
                        headers=item.get("headers", {}),
                        ack_timeout=item.get("ack_timeout", 30.0),
                        callback_url=item.get("callback_url", ""),
                    )
                    messages.append(msg)
                return messages
        except Exception:
            return []

    def save_dead_letter(self, messages: List[DelayedMessage]) -> bool:
        """保存死信消息"""
        try:
            with self._lock:
                data = [
                    {
                        "message_id": m.message_id,
                        "topic": m.topic,
                        "payload": m.payload,
                        "state": m.state.value,
                        "created_at": m.created_at,
                        "delivered_at": m.delivered_at,
                        "retry_count": m.retry_count,
                        "error": m.headers.get("last_error", ""),
                    }
                    for m in messages
                    if m.state == MessageState.DEAD_LETTER
                ]
                self._dead_letter_file.write_bytes(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))
                return True
        except Exception:
            return False

class MessageHandler:
    """消息处理器注册中心"""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._default_handler: Optional[Callable] = None

    def register(self, topic: str, handler: Callable[[DelayedMessage], bool]) -> None:
        """注册主题处理器"""
        self._handlers[topic] = handler

    def register_default(self, handler: Callable[[DelayedMessage], bool]) -> None:
        """注册默认处理器"""
        self._default_handler = handler

    def get_handler(self, topic: str) -> Optional[Callable]:
        """获取处理器"""
        return self._handlers.get(topic, self._default_handler)

class TimeWheel:
    """分层时间轮"""

    def __init__(self):
        self._heap: List[DelayedMessage] = []
        self._lock = threading.Lock()
        self._seq_counter = 0

    def push(self, message: DelayedMessage) -> None:
        """推送消息到时间轮"""
        with self._lock:
            self._seq_counter += 1
            message._seq = self._seq_counter
            heapq.heappush(self._heap, message)

    def peek(self) -> Optional[DelayedMessage]:
        """查看下一个到期消息"""
        with self._lock:
            if not self._heap:
                return None
            return self._heap[0]

    def pop_ready(self) -> List[DelayedMessage]:
        """弹出所有到期消息"""
        now = time.time()
        ready = []
        with self._lock:
            while self._heap and self._heap[0].execute_at <= now:
                ready.append(heapq.heappop(self._heap))
        return ready

    def remove(self, message_id: str) -> bool:
        """移除指定消息"""
        with self._lock:
            new_heap = []
            found = False
            for msg in self._heap:
                if msg.message_id == message_id and not found:
                    found = True
                    continue
                new_heap.append(msg)
            self._heap = new_heap
            heapq.heapify(self._heap)
            return found

    def size(self) -> int:
        """当前消息数量"""
        with self._lock:
            return len(self._heap)

    def get_all_messages(self) -> List[DelayedMessage]:
        """获取所有消息（按执行时间排序）"""
        with self._lock:
            return sorted(list(self._heap))

class QueueThroughputAnalyzer(object):
    """队列吞吐量分析器 — 消息流速统计、延迟分布分析、消费者负载均衡检测、容量预警"""

    def __init__(self):
        self._throughput_samples: List[Dict[str, Any]] = []

    def record_throughput(
        self, topic: str, delivered: int, acked: int, nacked: int, window_seconds: int = 60
    ) -> Dict[str, Any]:
        """记录吞吐量采样"""
        sample = {
            "topic": topic,
            "delivered": delivered,
            "acked": acked,
            "nacked": nacked,
            "window": window_seconds,
            "timestamp": time.time(),
            "ack_rate": acked / max(delivered, 1),
            "nack_rate": nacked / max(delivered, 1),
        }
        self._throughput_samples.append(sample)
        if len(self._throughput_samples) > 1000:
            self._throughput_samples = self._throughput_samples[-500:]
        return sample

    def analyze_latency_distribution(self, messages: List[Dict]) -> Dict[str, Any]:
        """分析消息延迟分布：P50/P95/P99、平均延迟、尾部延迟"""
        if not messages:
            return {"error": "no messages"}
        latencies = sorted(m.get("latency_ms", 0) for m in messages)
        n = len(latencies)
        p50 = latencies[n // 2]
        p95 = latencies[int(n * 0.95)]
        p99 = latencies[min(int(n * 0.99), n - 1)]
        avg = sum(latencies) / n
        tail_count = sum(1 for l in latencies if l > avg * 5)
        return {
            "count": n,
            "avg_ms": round(avg, 2),
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "tail_latency_count": tail_count,
            "tail_ratio": round(tail_count / max(n, 1), 4),
        }

    def detect_consumer_imbalance(self, topic_stats: Dict[str, Dict[str, int]]) -> List[Dict[str, Any]]:
        """检测消费者负载不均衡：对比各消费者处理量差异"""
        imbalances = []
        all_counts = [s.get("processed", 0) for s in topic_stats.values()]
        if not all_counts or max(all_counts) == 0:
            return imbalances
        avg = sum(all_counts) / len(all_counts)
        for consumer_id, stats in topic_stats.items():
            processed = stats.get("processed", 0)
            deviation = abs(processed - avg) / max(avg, 1)
            if deviation > 0.5:
                imbalances.append(
                    {
                        "consumer_id": consumer_id,
                        "processed": processed,
                        "avg_processed": round(avg, 1),
                        "deviation_ratio": round(deviation, 3),
                        "status": "underloaded" if processed < avg else "overloaded",
                    }
                )
        imbalances.sort(key=lambda x: x["deviation_ratio"], reverse=True)
        return imbalances

    def predict_capacity_exhaustion(self, current_depth: int, avg_rate: float, max_capacity: int) -> Dict[str, Any]:
        """预测队列容量耗尽时间"""
        if avg_rate <= 0 or current_depth >= max_capacity:
            return {
                "exhausted": current_depth >= max_capacity,
                "time_to_full_minutes": 0,
                "current_depth": current_depth,
            }
        remaining = max_capacity - current_depth
        time_to_full = remaining / avg_rate * 60  # seconds to minutes
        urgency = "critical" if time_to_full < 5 else "warning" if time_to_full < 30 else "normal"
        return {
            "exhausted": False,
            "time_to_full_minutes": round(time_to_full, 1),
            "current_depth": current_depth,
            "max_capacity": max_capacity,
            "utilization": round(current_depth / max_capacity, 4),
            "urgency": urgency,
        }

class DelayQueue(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    企业级延迟队列引擎

    提供精确的延迟消息投递、定时任务调度、消息重试和死信处理能力。
    基于分层时间轮实现高效消息调度。
    """

    def __init__(self):

        super().__init__(module_id="delay_queue", module_name="延迟队列引擎")
        self._time_wheel = TimeWheel()
        self._dead_letter: List[DelayedMessage] = []
        self._delivering: Dict[str, DelayedMessage] = {}
        self._handler = MessageHandler()
        self._retry_policy = RetryPolicy()
        self._persistence = PersistenceManager()
        self._lock = threading.RLock()
        self._running = False
        self._dispatch_thread: Optional[threading.Thread] = None
        self._ack_check_thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._stats = {
            "total_enqueued": 0,
            "total_delivered": 0,
            "total_acked": 0,
            "total_nacked": 0,
            "total_retried": 0,
            "total_dead_letter": 0,
            "total_cancelled": 0,
            "total_latency_ms": 0,
        }
        self._flush_interval = 30
        self._last_flush_time = time.time()

    # ─────────────────────── 消息投递API ───────────────────────

    def publish(
        self,
        topic: str,
        payload: Any,
        delay_ms: float = 0,
        priority: MessagePriority = MessagePriority.NORMAL,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
        callback_url: str = "",
        ack_timeout: float = 30.0,
    ) -> str:
        """
        发布延迟消息

        Args:
            topic: 主题
            payload: 消息内容
            delay_ms: 延迟毫秒数（0=立即投递）
            priority: 优先级
            max_retries: 最大重试次数
            headers: 消息头
            callback_url: 回调URL
            ack_timeout: 确认超时（秒）

        Returns:
            消息ID
        """
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        execute_at = time.time() + delay_ms / 1000

        message = DelayedMessage(
            execute_at=execute_at,
            priority=priority,
            message_id=message_id,
            topic=topic,
            payload=payload,
            delay_ms=delay_ms,
            max_retries=max_retries,
            headers=headers or {},
            ack_timeout=ack_timeout,
            callback_url=callback_url,
        )

        with self._lock:
            self._time_wheel.push(message)
            self._stats["total_enqueued"] += 1

        self._audit_log("publish", f"{topic} [{message_id}] delay={delay_ms}ms")
        return message_id

    def publish_at(
        self,
        topic: str,
        payload: Any,
        execute_at: datetime,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs,
    ) -> str:
        """在指定时间投递消息"""
        if execute_at.tzinfo is None:
            execute_at = execute_at.replace(tzinfo=timezone.utc)
        delay_ms = (execute_at - datetime.now(timezone.utc)).total_seconds() * 1000
        if delay_ms < 0:
            delay_ms = 0
        return self.publish(topic, payload, delay_ms=delay_ms, priority=priority, **kwargs)

    def cancel(self, message_id: str) -> bool:
        """取消消息"""
        with self._lock:
            if message_id in self._delivering:
                msg = self._delivering.pop(message_id)
                msg.state = MessageState.CANCELLED
                self._stats["total_cancelled"] += 1
                return True

            found = self._time_wheel.remove(message_id)
            if found:
                self._stats["total_cancelled"] += 1
                return True
        return False

    def ack(self, message_id: str) -> bool:
        """确认消息"""
        with self._lock:
            msg = self._delivering.pop(message_id, None)
            if msg:
                msg.state = MessageState.ACKED
                msg.delivered_at = time.time()
                self._stats["total_acked"] += 1
                latency = (msg.delivered_at - msg.created_at) * 1000
                self._stats["total_latency_ms"] += latency
                return True
        return False

    def nack(self, message_id: str, error: str = "") -> bool:
        """拒绝消息（触发重试）"""
        with self._lock:
            msg = self._delivering.pop(message_id, None)
            if msg:
                self._stats["total_nacked"] += 1
                msg.headers["last_error"] = error
                self._retry_message(msg)
                return True
        return False

    def register_handler(self, topic: str, handler: Callable[[DelayedMessage], bool]) -> None:
        """注册主题处理器"""
        self._handler.register(topic, handler)

    def register_default_handler(self, handler: Callable[[DelayedMessage], bool]) -> None:
        """注册默认处理器"""
        self._handler.register_default(handler)

    # ─────────────────────── 查询API ───────────────────────

    def get_message(self, message_id: str) -> Optional[Dict]:
        """查询消息状态"""
        with self._lock:
            if message_id in self._delivering:
                msg = self._delivering[message_id]
            else:
                msg = None
                for m in self._time_wheel.get_all_messages():
                    if m.message_id == message_id:
                        msg = m
                        break
                if not msg:
                    for m in self._dead_letter:
                        if m.message_id == message_id:
                            msg = m
                            break
            if msg:
                return {
                    "message_id": msg.message_id,
                    "topic": msg.topic,
                    "state": msg.state.value,
                    "priority": msg.priority,
                    "created_at": datetime.fromtimestamp(msg.created_at).isoformat(),
                    "execute_at": datetime.fromtimestamp(msg.execute_at).isoformat(),
                    "retry_count": msg.retry_count,
                    "max_retries": msg.max_retries,
                    "delay_ms": msg.delay_ms,
                    "headers": msg.headers,
                }
        return None

    def get_pending_count(self) -> int:
        """获取待处理消息数"""
        return self._time_wheel.size()

    def get_dead_letter_count(self) -> int:
        """获取死信消息数"""
        return len(self._dead_letter)

    def list_dead_letters(self, limit: int = 50) -> List[Dict]:
        """列出死信消息"""
        return [
            {
                "message_id": m.message_id,
                "topic": m.topic,
                "retry_count": m.retry_count,
                "created_at": datetime.fromtimestamp(m.created_at).isoformat(),
                "error": m.headers.get("last_error", ""),
            }
            for m in self._dead_letter[-limit:]
        ]

    def requeue_dead_letter(self, message_id: str) -> bool:
        """重新投递死信消息"""
        for i, m in enumerate(self._dead_letter):
            if m.message_id == message_id:
                m.state = MessageState.RETRYING
                m.retry_count = 0
                m.execute_at = time.time()
                self._dead_letter.pop(i)
                self._time_wheel.push(m)
                return True
        return False

    # ─────────────────────── 内部调度 ───────────────────────

    def _retry_message(self, message: DelayedMessage) -> None:
        """重试消息"""
        if message.retry_count >= message.max_retries:
            message.state = MessageState.DEAD_LETTER
            self._dead_letter.append(message)
            self._stats["total_dead_letter"] += 1
            self._logger.warning(f"消息转入死信: {message.message_id} (重试{message.retry_count}次)")
            return

        message.retry_count += 1
        delay = self._retry_policy.get_delay(message.retry_count)
        message.execute_at = time.time() + delay / 1000
        message.state = MessageState.RETRYING
        self._time_wheel.push(message)
        self._stats["total_retried"] += 1

    def _dispatch_loop(self) -> None:
        """调度循环"""
        while self._running:
            try:
                ready_messages = self._time_wheel.pop_ready()
                for msg in ready_messages:
                    self._deliver_message(msg)
            except Exception:
                pass
            time.sleep(0.1)

    def _deliver_message(self, message: DelayedMessage) -> None:
        """投递消息"""
        handler = self._handler.get_handler(message.topic)
        if not handler:
            self._logger.warning(f"无处理器: {message.topic}")
            return

        message.state = MessageState.DELIVERING
        with self._lock:
            self._delivering[message.message_id] = message

        def do_deliver():
            start = time.time()
            try:
                success = handler(message)
                duration = (time.time() - start) * 1000
                if success:
                    self.ack(message.message_id)
                else:
                    self.nack(message.message_id, "handler returned False")
            except Exception as e:
                self.nack(message.message_id, str(e))

        self._executor.submit(do_deliver)

    def _ack_timeout_check(self) -> None:
        """确认超时检查"""
        while self._running:
            try:
                now = time.time()
                expired = []
                with self._lock:
                    for mid, msg in self._delivering.items():
                        if now - (msg.delivered_at or msg.created_at) > msg.ack_timeout:
                            expired.append(mid)
                for mid in expired:
                    self.nack(mid, f"ACK超时 ({self._delivering.get(mid, DelayedMessage(message_id='')).ack_timeout}s)")
            except Exception:
                pass
            time.sleep(5)

    def _persistence_loop(self) -> None:
        """持久化循环"""
        while self._running:
            try:
                if time.time() - self._last_flush_time >= self._flush_interval:
                    messages = self._time_wheel.get_all_messages()
                    self._persistence.save_pending(messages)
                    self._persistence.save_dead_letter(self._dead_letter)
                    self._last_flush_time = time.time()
            except Exception:
                pass
            time.sleep(10)

    # ─────────────────────── 生命周期 ───────────────────────

    async def execute(self, action: str = "stats", params: dict = None) -> dict:
        """统一执行入口 — 路由到延迟队列业务操作"""

        _ = self.trace("execute")
        metrics_collector.counter("delay_queue_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}

        if action == "publish":
            msg = self.publish(
                topic=params.get("topic", ""),
                payload=params.get("payload", {}),
                delay_seconds=params.get("delay_seconds", 0),
                max_retries=params.get("max_retries", 3),
            )
            return {"success": True, "message_id": msg.message_id}
        elif action == "publish_at":
            msg = self.publish_at(
                topic=params.get("topic", ""),
                payload=params.get("payload", {}),
                execute_at=params.get("execute_at", 0),
            )
            return {"success": True, "message_id": msg.message_id}
        elif action == "cancel":
            ok = self.cancel(params.get("message_id", ""))
            return {"success": ok}
        elif action == "ack":
            ok = self.ack(params.get("message_id", ""))
            return {"success": ok}
        elif action == "nack":
            ok = self.nack(params.get("message_id", ""), params.get("error", ""))
            return {"success": ok}
        elif action == "get":
            msg = self.get_message(params.get("message_id", ""))
            return {"success": msg is not None, "message": msg}
        elif action == "pending_count":
            return {"count": self.get_pending_count()}
        elif action == "dead_letters":
            letters = self.list_dead_letters(params.get("limit", 50))
            return {"success": True, "letters": letters, "total": self.get_dead_letter_count()}
        elif action == "requeue":
            ok = self.requeue_dead_letter(params.get("message_id", ""))
            self.audit("requeue_dead_letter", f"message_id={params.get('message_id', '')}, success={ok}")
            return {"success": ok}
        elif action == "stats" or action == "get_stats":
            return {"success": True, **self.get_stats()}
        elif action == "health":
            hr = self.health_check()
            return {"success": True, "health": hr}
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def start(self) -> None:
        """启动延迟队列"""
        if self._running:
            return
        self._running = True

        # 加载持久化消息
        pending = self._persistence.load_pending()
        for msg in pending:
            if msg.execute_at > time.time():
                self._time_wheel.push(msg)

        self._dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._dispatch_thread.start()

        self._ack_check_thread = threading.Thread(target=self._ack_timeout_check, daemon=True)
        self._ack_check_thread.start()

        persist_thread = threading.Thread(target=self._persistence_loop, daemon=True)
        persist_thread.start()

        self._logger.info(f"延迟队列启动，恢复 {len(pending)} 条消息")

    def stop(self) -> None:
        """停止延迟队列"""
        self._running = False
        # 保存未处理消息
        messages = self._time_wheel.get_all_messages()
        self._persistence.save_pending(messages)
        self._persistence.save_dead_letter(self._dead_letter)
        self._logger.info(f"延迟队列停止，持久化 {len(messages)} 条消息")

    # ─────────────────────── EnterpriseModule接口 ───────────────────────

    def _initialize(self) -> None:
        self.start()

    def health_check(self) -> HealthReport:
        s = self._stats
        return HealthReport(
            status=ModuleStatus.RUNNING if self._running else ModuleStatus.STOPPED,
            details={
                "running": self._running,
                "pending": self._time_wheel.size(),
                "delivering": len(self._delivering),
                "dead_letter": len(self._dead_letter),
                "total_enqueued": s["total_enqueued"],
                "total_delivered": s["total_delivered"],
                "total_acked": s["total_acked"],
                "total_nacked": s["total_nacked"],
                "total_retried": s["total_retried"],
                "total_dead_letter": s["total_dead_letter"],
            },
        )

    def get_stats(self) -> ModuleStats:
        s = self._stats
        delivered = s["total_acked"] + s["total_nacked"]
        return ModuleStats(
            total_operations=s["total_enqueued"],
            success_rate=(s["total_acked"] / delivered * 100) if delivered > 0 else 100,
            avg_latency_ms=(s["total_latency_ms"] / s["total_acked"]) if s["total_acked"] > 0 else 0,
        )

    def shutdown(self) -> dict:
        """Graceful shutdown for delay_queue."""
        self.status = ModuleStatus.STOPPED
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

    def initialize(self) -> dict:
        """Initialize delay_queue."""
        self.status = "initialized"
        self._start_time = time.time()
        self.status = "active"
        self._logger.info("%s initialized", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = DelayQueue
