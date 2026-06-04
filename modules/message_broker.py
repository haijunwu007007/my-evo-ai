# Grade: A

"""
AUTO-EVO-AI V0.1 - MessageBroker 消息代理服务
===============================================
企业级消息代理：Topic/Queue/PubSub/持久化/确认机制/消费者管理。
支持：点对点队列、发布订阅、消息持久化、ACK/NACK、
      延迟消息、优先级队列、消息TTL、死信路由、消费者偏移量。

A级生产标准：EnterpriseModule + 链路追踪 + Prometheus + 审计 + 熔断 + 限流
"""

__module_meta__ = {
        "id": "message-broker",
        "name": "Message Broker",
        "version": "V0.1",
        "group": "messaging",
        "inputs": [
            {
                "name": "pattern",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "destinations",
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
                "name": "message_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "config",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "action",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "results",
                "type": "list[dict]",
                "description": "结果列表"
            },
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [
            {
                "type": "event",
                "config": {
                    "on": "message_broker.trigger"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "engine",
            "message"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 - MessageBroker 消息代理服务 ==============================================="
    }
from modules._base import Result
import time
import asyncio
import json
import logging
import heapq
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import uuid

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.circuit_breaker import CircuitBreakerMixin
from modules._base.rate_limiter import RateLimiterMixin

class MessageStatus(str, Enum):
    CREATED = "created"
    ENQUEUED = "enqueued"
    DELIVERING = "delivering"
    ACKED = "acked"
    NACKED = "nacked"
    REQUEUED = "requeued"
    EXPIRED = "expired"
    DEAD_LETTER = "dead_letter"

class DeliveryMode(str, Enum):
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"

@dataclass(order=True)
class BrokerMessage:
    """代理消息"""

    priority: int = field(default=0, compare=True)
    created_at: float = field(default_factory=time.time, compare=True)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    topic: str = field(default="", compare=False)
    payload: Any = field(default=None, compare=False)
    headers: dict[str, str] = field(default_factory=dict, compare=False)
    status: MessageStatus = field(default=MessageStatus.CREATED, compare=False)
    delivery_mode: DeliveryMode = field(default=DeliveryMode.AT_LEAST_ONCE, compare=False)
    ttl_seconds: float | None = field(default=None, compare=False)
    delay_seconds: float = field(default=0.0, compare=False)
    deliver_at: float = field(default=0.0, compare=False)
    delivery_count: int = field(default=0, compare=False)
    max_deliveries: int = field(default=3, compare=False)
    producer_id: str = field(default="", compare=False)
    consumer_id: str | None = field(default=None, compare=False)
    trace_id: str | None = field(default=None, compare=False)
    correlation_id: str | None = field(default=None, compare=False)
    expires_at: float | None = field(default=None, compare=False)
    size_bytes: int = field(default=0, compare=False)
    body: str = field(default="", compare=False)

    def __post_init__(self):
        if self.deliver_at == 0.0 and self.delay_seconds > 0:
            self.deliver_at = time.time() + self.delay_seconds
        elif self.deliver_at == 0.0:
            self.deliver_at = time.time()
        if self.ttl_seconds:
            self.expires_at = time.time() + self.ttl_seconds
        if isinstance(self.payload, (dict, list)):
            self.body = json.dumps(self.payload, ensure_ascii=False, default=str)
        elif self.payload is not None:
            self.body = str(self.payload)
        self.size_bytes = len(self.body.encode("utf-8")) if self.body else 0

@dataclass
class Consumer:
    """消费者"""

    consumer_id: str
    topic: str
    handler: Callable
    consumer_group: str = "default"
    prefetch_count: int = 10
    auto_ack: bool = False
    active: bool = True
    delivered: int = 0
    acked: int = 0
    nacked: int = 0
    errors: int = 0
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class TopicStats:
    """Topic统计"""

    topic: str
    messages_total: int = 0
    messages_pending: int = 0
    messages_delivered: int = 0
    messages_acked: int = 0
    messages_dead_letter: int = 0
    consumers_count: int = 0
    avg_latency_ms: float = 0.0
    total_size_bytes: int = 0

# ============================================================================
# MessageBroker 主类
# ============================================================================

class MessageRouterEngine:
    """消息路由引擎：主题匹配、负载均衡、消息分发"""

    def __init__(self):
        self._routes: dict[str, list[str]] = {}
        self._routing_count = 0
        self._dead_letter_count = 0

    def add_route(self, pattern: str, destinations: list[str]) -> None:
        """添加路由规则"""
        self._routes[pattern] = destinations

    def route_message(self, topic: str, message_id: str) -> list[str]:
        """根据主题匹配路由目标，返回目标队列列表"""
        self._routing_count += 1
        matched = []
        for pattern, dests in self._routes.items():
            if pattern == "*" or pattern in topic or topic in pattern:
                matched.extend(dests)
        if not matched:
            self._dead_letter_count += 1
            matched = ["__dead_letter__"]
        return list(set(matched))

    def get_router_stats(self) -> dict:
        return {
            "total_routes": len(self._routes),
            "routing_count": self._routing_count,
            "dead_letter_count": self._dead_letter_count,
        }

class MessageBroker(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    消息代理服务

    功能：
      - Topic管理（创建/删除/查询）
      - 生产者发送消息
      - 消费者订阅/取消订阅
      - 点对点队列模式（同一group内竞争消费）
      - 发布订阅模式（同一group内广播）
      - 消息ACK/NACK机制
      - 延迟消息
      - 消息TTL过期
      - 优先级队列
      - 死信路由
      - 消费者偏移量管理
      - 消息持久化（内存）
    """

    def __init__(self, config: dict[str, Any] | None = None):

        super().__init__()
        self.config = config or {}
        # Topic -> 优先级堆
        self._queues: dict[str, list[BrokerMessage]] = defaultdict(list)
        # Topic -> 消费者列表
        self._consumers: dict[str, list[Consumer]] = defaultdict(list)
        # 消费者组 -> topic -> Consumer（点对点模式）
        self._consumer_groups: dict[str, dict[str, list[Consumer]]] = defaultdict(lambda: defaultdict(list))
        # 死信Topic
        self._dead_letter_topic = self.config.get("dead_letter_topic", "dlq.default")
        self._dead_letters: list[BrokerMessage] = []
        # 消息存储（已投递+未ACK）
        self._inflight: dict[str, BrokerMessage] = {}
        # 已完成消息（保留最近N条）
        self._completed: deque = deque(maxlen=50000)
        # 投递统计
        self._topic_stats: dict[str, TopicStats] = {}
        # 全局统计
        self._broker_stats = {
            "messages_published": 0,
            "messages_consumed": 0,
            "messages_acked": 0,
            "messages_nacked": 0,
            "messages_expired": 0,
            "messages_dead_letter": 0,
        }
        # 调度协程
        self._scheduler_task: asyncio.Task | None = None
        self._ttl_checker_task: asyncio.Task | None = None
        # 配置
        self._max_queue_size = self.config.get("max_queue_size", 1000000)
        self._default_prefetch = self.config.get("default_prefetch", 10)
        self._schedule_interval = self.config.get("schedule_interval", 0.1)

    # ----------------------------------------------------------------
    # 生命周期
    # ----------------------------------------------------------------

    def initialize(self) -> Result:
        """初始化：启动调度器和TTL检查器"""
        try:
            self._update_status(ModuleStatus.INITIALIZING)
            self._scheduler_task = asyncio.create_task(self._schedule_loop())
            self._ttl_checker_task = asyncio.create_task(self._ttl_check_loop())
            # 预创建Topic
            for topic in self.config.get("preset_topics", []):
                self._queues[topic]
                self._topic_stats[topic] = TopicStats(topic=topic)
            self._update_status(ModuleStatus.RUNNING)
            self.audit("broker.initialized", {"topics": len(self._queues)})
            logger.info(f"[MessageBroker] 初始化完成, {len(self._queues)} topics")
            return Result(success=True, data={"topics": list(self._queues.keys())})
        except Exception as e:
            self._update_status(ModuleStatus.ERROR)
            logger.error(f"[MessageBroker] 初始化失败: {e}")
            return Result(success=False, error=str(e))

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        self._metrics = self.record_metrics("message_broker_executed", 1)
        metrics_collector.counter("message_broker_ops_total", labels={"action": action})
        params = params or {}
        actions = {
            "create_topic": self.create_topic,
            "delete_topic": self.delete_topic,
            "list_topics": self.list_topics,
            "publish": self.publish,
            "subscribe": self.subscribe,
            "unsubscribe": self.unsubscribe,
            "ack": self.ack,
            "nack": self.nack,
            "get_stats": self.get_stats,
            "get_topic_detail": self.get_topic_detail,
            "get_dead_letters": self.get_dead_letters,
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
                    self.metrics_collector.counter(
                        "execute_error",
                        1,
                        tags={"action": action, "error_type": type(e).__name__, "module": "message_broker"},
                    )
                    return {"status": "error", "message": str(e)}
            else:
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    self.metrics_collector.counter(
                        "execute_error",
                        1,
                        tags={"action": action, "error_type": type(e).__name__, "module": "message_broker"},
                    )
                    return {"status": "error", "message": str(e)}
            self.metrics_collector.counter(
                "execute_total", 1, tags={"action": action, "status": "success", "module": "message_broker"}
            )
            if isinstance(result, dict):
                return {"status": "success", **result}
            return {"status": "success", "data": result}

    def health_check(self) -> HealthReport:
        """健康检查"""
        checks = {
            "scheduler_alive": self._scheduler_task and not self._scheduler_task.done(),
            "ttl_checker_alive": self._ttl_checker_task and not self._ttl_checker_task.done(),
            "topics_count": len(self._queues),
            "consumers_count": sum(len(v) for v in self._consumers.values()),
            "inflight_count": len(self._inflight),
            "dead_letter_count": len(self._dead_letters),
        }
        healthy = checks["scheduler_alive"] and checks["ttl_checker_alive"]
        return HealthReport(
            status="running" if healthy else "degraded",
            healthy=healthy,
            last_beat=datetime.now().isoformat(),
            uptime_seconds=self.stats.uptime_seconds,
            checks_run=6,
            error_rate=self.stats.error_rate,
            details=checks,
            version="V0.1",
        )

    def shutdown(self) -> Result:
        """优雅关闭"""
        try:
            self._update_status(ModuleStatus.STOPPING)
            if self._scheduler_task:
                self._scheduler_task.cancel()
            if self._ttl_checker_task:
                self._ttl_checker_task.cancel()
            asyncio.gather(self._scheduler_task, self._ttl_checker_task, return_exceptions=True)
            self._update_status(ModuleStatus.STOPPED)
            self.audit("broker.shutdown", {"inflight": len(self._inflight)})
            logger.info("[MessageBroker] 关闭完成")
            return Result(success=True)
        except Exception as e:
            return Result(success=False, error=str(e))

    # ----------------------------------------------------------------
    # Topic管理
    # ----------------------------------------------------------------

    def create_topic(self, topic: str) -> Result:
        """创建Topic"""
        if topic in self._queues:
            return Result(success=False, error=f"Topic已存在: {topic}")
        self._queues[topic] = []
        self._topic_stats[topic] = TopicStats(topic=topic)
        self.audit("topic.created", {"topic": topic})
        return Result(success=True, data={"topic": topic})

    def delete_topic(self, topic: str, force: bool = False) -> Result:
        """删除Topic"""
        if topic not in self._queues:
            return Result(success=False, error=f"Topic不存在: {topic}")
        if self._queues[topic] and not force:
            return Result(success=False, error=f"Topic非空: {topic}, 待处理消息 {len(self._queues[topic])}")
        del self._queues[topic]
        self._consumers.pop(topic, None)
        self._topic_stats.pop(topic, None)
        self.audit("topic.deleted", {"topic": topic, "force": force})
        return Result(success=True)

    def list_topics(self) -> list[dict]:
        """列出所有Topic及统计"""
        result = []
        for topic, stats in self._topic_stats.items():
            stats.messages_pending = len(self._queues.get(topic, []))
            stats.consumers_count = len(self._consumers.get(topic, []))
            result.append(
                {
                    "topic": topic,
                    "pending": stats.messages_pending,
                    "total": stats.messages_total,
                    "delivered": stats.messages_delivered,
                    "acked": stats.messages_acked,
                    "dead_letter": stats.messages_dead_letter,
                    "consumers": stats.consumers_count,
                    "size_bytes": stats.total_size_bytes,
                }
            )
        return result

    # ----------------------------------------------------------------
    # 生产者
    # ----------------------------------------------------------------

    def publish(
        self,
        topic: str,
        payload: Any,
        *,
        headers: dict[str, str] | None = None,
        priority: int = 0,
        ttl: float | None = None,
        delay: float = 0.0,
        delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE,
        producer_id: str = "",
        correlation_id: str | None = None,
    ) -> Result:
        """发送消息到Topic"""
        start = time.time()
        try:
            with self.trace("publish"):
                if not self.rate_limit(f"pub:{topic}"):
                    return Result(success=False, error="rate_limited")
                if topic not in self._queues:
                    return Result(success=False, error=f"Topic不存在: {topic}")
                # 队列容量检查
                if len(self._queues[topic]) >= self._max_queue_size:
                    return Result(success=False, error="queue_full")
                msg = BrokerMessage(
                    topic=topic,
                    payload=payload,
                    headers=headers or {},
                    priority=priority,
                    ttl_seconds=ttl,
                    delay_seconds=delay,
                    delivery_mode=delivery_mode,
                    producer_id=producer_id,
                    correlation_id=correlation_id,
                )
                msg.status = MessageStatus.ENQUEUED
                heapq.heappush(self._queues[topic], msg)
                # 更新统计
                ts = self._topic_stats[topic]
                ts.messages_total += 1
                ts.total_size_bytes += msg.size_bytes
                self._broker_stats["messages_published"] += 1
                latency = (time.time() - start) * 1000
                self.stats.record_request(latency, True)
                return Result(success=True, data={"message_id": msg.message_id})
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.stats.record_request(latency, False, str(e))
            return Result(success=False, error=str(e))

    # ----------------------------------------------------------------
    # 消费者
    # ----------------------------------------------------------------

    def subscribe(
        self,
        topic: str,
        handler: Callable,
        *,
        consumer_group: str = "default",
        consumer_id: str | None = None,
        prefetch: int = 0,
        auto_ack: bool = False,
    ) -> str:
        """订阅Topic"""
        cid = consumer_id or str(uuid.uuid4())[:8]
        consumer = Consumer(
            consumer_id=cid,
            topic=topic,
            handler=handler,
            consumer_group=consumer_group,
            prefetch_count=prefetch or self._default_prefetch,
            auto_ack=auto_ack,
        )
        self._consumers[topic].append(consumer)
        self._consumer_groups[consumer_group][topic].append(consumer)
        self.audit("consumer.subscribed", {"consumer_id": cid, "topic": topic, "group": consumer_group})
        return cid

    def unsubscribe(self, consumer_id: str) -> Result:
        """取消订阅"""
        for topic, consumers in self._consumers.items():
            for i, c in enumerate(consumers):
                if c.consumer_id == consumer_id:
                    c.active = False
                    consumers.pop(i)
                    self.audit("consumer.unsubscribed", {"consumer_id": consumer_id})
                    return Result(success=True)
        return Result(success=False, error=f"消费者不存在: {consumer_id}")

    def ack(self, message_id: str) -> Result:
        """确认消息"""
        msg = self._inflight.pop(message_id, None)
        if not msg:
            return Result(success=False, error=f"消息不在投递中: {message_id}")
        msg.status = MessageStatus.ACKED
        self._completed.append(msg)
        self._broker_stats["messages_acked"] += 1
        ts = self._topic_stats.get(msg.topic)
        if ts:
            ts.messages_acked += 1
        return Result(success=True, data={"message_id": message_id})

    def nack(self, message_id: str, requeue: bool = True) -> Result:
        """拒绝消息"""
        msg = self._inflight.pop(message_id, None)
        if not msg:
            return Result(success=False, error=f"消息不在投递中: {message_id}")
        msg.status = MessageStatus.NACKED
        self._broker_stats["messages_nacked"] += 1
        if requeue and msg.delivery_count < msg.max_deliveries:
            msg.status = MessageStatus.REQUEUED
            heapq.heappush(self._queues.get(msg.topic, []), msg)
        else:
            self._route_to_dead_letter(msg)
        return Result(success=True, data={"message_id": message_id, "requeued": requeue})

    def _route_to_dead_letter(self, msg: BrokerMessage):
        """路由到死信队列"""
        msg.status = MessageStatus.DEAD_LETTER
        self._dead_letters.append(msg)
        if len(self._dead_letters) > 10000:
            self._dead_letters = self._dead_letters[-5000:]
        self._broker_stats["messages_dead_letter"] += 1
        ts = self._topic_stats.get(msg.topic)
        if ts:
            ts.messages_dead_letter += 1
        logger.warning(f"[MessageBroker] 死信: {msg.message_id} topic={msg.topic}")

    # ----------------------------------------------------------------
    # 调度循环
    # ----------------------------------------------------------------

    def _schedule_loop(self):
        """消息调度循环"""
        while True:
            try:
                time.sleep(self._schedule_interval)
                now = time.time()
                for topic, queue in list(self._queues.items()):
                    if not queue:
                        continue
                    consumers = [c for c in self._consumers.get(topic, []) if c.active]
                    if not consumers:
                        continue
                    # 按消费者组处理
                    groups = defaultdict(list)
                    for c in consumers:
                        groups[c.consumer_group].append(c)
                    for group_name, group_consumers in groups.items():
                        delivered_in_round = 0
                        while queue and delivered_in_round < len(group_consumers):
                            if not queue or queue[0].deliver_at > now:
                                break
                            msg = heapq.heappop(queue)
                            # TTL检查
                            if msg.expires_at and msg.expires_at <= now:
                                msg.status = MessageStatus.EXPIRED
                                self._completed.append(msg)
                                self._broker_stats["messages_expired"] += 1
                                continue
                            # 选择消费者（轮询）
                            idx = msg.delivery_count % len(group_consumers)
                            consumer = group_consumers[idx]
                            msg.status = MessageStatus.DELIVERING
                            msg.delivery_count += 1
                            msg.consumer_id = consumer.consumer_id
                            if not consumer.auto_ack:
                                self._inflight[msg.message_id] = msg
                            # 调用handler
                            try:
                                result = consumer.handler(msg)
                                if asyncio.iscoroutine(result):
                                    result
                                consumer.delivered += 1
                                consumer.last_active = datetime.now().isoformat()
                                ts = self._topic_stats.get(topic)
                                if ts:
                                    ts.messages_delivered += 1
                                if consumer.auto_ack:
                                    msg.status = MessageStatus.ACKED
                                    self._completed.append(msg)
                                    self._broker_stats["messages_acked"] += 1
                                    consumer.acked += 1
                                self._broker_stats["messages_consumed"] += 1
                            except Exception as e:
                                consumer.errors += 1
                                logger.error(f"[MessageBroker] 消费失败: {consumer.consumer_id}, {e}")
                                if msg.delivery_count >= msg.max_deliveries:
                                    self._route_to_dead_letter(msg)
                                else:
                                    heapq.heappush(queue, msg)
                            delivered_in_round += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MessageBroker] 调度异常: {e}")

    def _ttl_check_loop(self):
        """TTL过期检查"""
        while True:
            try:
                time.sleep(5.0)
                now = time.time()
                for topic, queue in self._queues.items():
                    while queue and queue[0].expires_at and queue[0].expires_at <= now:
                        msg = heapq.heappop(queue)
                        msg.status = MessageStatus.EXPIRED
                        self._completed.append(msg)
                        self._broker_stats["messages_expired"] += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MessageBroker] TTL检查异常: {e}")

    # ----------------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """获取代理统计"""
        total_pending = sum(len(q) for q in self._queues.values())
        return {
            **self._broker_stats,
            "topics_count": len(self._queues),
            "consumers_count": sum(len(v) for v in self._consumers.values()),
            "pending_messages": total_pending,
            "inflight_messages": len(self._inflight),
            "dead_letter_count": len(self._dead_letters),
            "completed_count": len(self._completed),
            "module_stats": self.stats.to_dict(),
        }

    def get_topic_detail(self, topic: str) -> dict | None:
        """获取Topic详情"""
        if topic not in self._topic_stats:
            return None
        ts = self._topic_stats[topic]
        return {
            "topic": topic,
            "pending": len(self._queues.get(topic, [])),
            "consumers": [
                {
                    "id": c.consumer_id,
                    "group": c.consumer_group,
                    "active": c.active,
                    "delivered": c.delivered,
                    "acked": c.acked,
                    "errors": c.errors,
                }
                for c in self._consumers.get(topic, [])
            ],
            "stats": {
                "total": ts.messages_total,
                "delivered": ts.messages_delivered,
                "acked": ts.messages_acked,
                "dead_letter": ts.messages_dead_letter,
                "size_bytes": ts.total_size_bytes,
            },
        }

    def get_dead_letters(self, limit: int = 50) -> list[dict]:
        """查看死信"""
        return [
            {
                "message_id": m.message_id,
                "topic": m.topic,
                "deliveries": m.delivery_count,
                "size_bytes": m.size_bytes,
                "created_at": datetime.fromtimestamp(m.created_at).isoformat(),
            }
            for m in self._dead_letters[-limit:]
        ]

# ============================================================================
# 模块注册
# ============================================================================

module_class = MessageBroker
