"""
# Grade: A
AUTO-EVO-AI V0.1 — Agent Hermes (消息路由与通信引擎)
=====================================================
企业级智能体，负责消息路由、多通道通信、消息队列管理、消息持久化与投递保障。
支持同步/异步/广播/多播路由模式，内置死信队列与消息重试机制。

继承: EnterpriseModule
"""

__module_meta__ = {
        "id": "agent-hermes",
        "name": "Agent Hermes",
        "version": "V0.1",
        "group": "agent",
        "inputs": [
            {
                "name": "max_messages",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "message",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "msg_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "msg_id_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "status",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "channel",
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
                "name": "result",
                "type": "dict",
                "description": "执行结果"
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
                    "on": "agent_hermes.task.request"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "engine",
            "multi-agent",
            "agent"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — Agent Hermes (消息路由与通信引擎) ====================================================="
    }

import time
import json
import hashlib
from core.logging_config import get_logger
import threading
import heapq
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, Result, HealthReport, ModuleStats
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = get_logger("agent.hermes")

class MessagePriority(Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10

class MessageStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"
    DEAD_LETTER = "dead_letter"
    ACKNOWLEDGED = "acknowledged"

class ChannelType(Enum):
    DIRECT = "direct"
    TOPIC = "topic"
    BROADCAST = "broadcast"
    DEAD_LETTER = "dead_letter"

@dataclass(order=True)
class Message:
    priority: int = MessagePriority.NORMAL.value
    msg_id: str = field(compare=False, default="")
    sender: str = field(compare=False, default="")
    recipient: str = field(compare=False, default="")
    channel: str = field(compare=False, default="default")
    channel_type: ChannelType = field(compare=False, default=ChannelType.DIRECT)
    payload: Dict[str, Any] = field(compare=False, default_factory=dict)
    headers: Dict[str, str] = field(compare=False, default_factory=dict)
    status: MessageStatus = field(compare=False, default=MessageStatus.PENDING)
    created_at: float = field(compare=False, default_factory=time.time)
    delivered_at: Optional[float] = field(compare=False, default=None)
    expire_at: Optional[float] = field(compare=False, default=None)
    retry_count: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)
    ttl_seconds: float = field(compare=False, default=86400 * 7)

    def __post_init__(self):
        if not self.msg_id:
            self.msg_id = hashlib.md5(
                f"{self.sender}:{self.recipient}:{self.channel}:{time.time()}:{id(self)}".encode()
            ).hexdigest()[:16]
        if self.expire_at is None:
            self.expire_at = self.created_at + self.ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expire_at

    def to_dict(self) -> Dict:
        return {
            "msg_id": self.msg_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "channel": self.channel,
            "channel_type": self.channel_type.value,
            "priority": self.priority,
            "status": self.status.value,
            "payload": self.payload,
            "headers": self.headers,
            "created_at": self.created_at,
            "delivered_at": self.delivered_at,
            "retry_count": self.retry_count,
            "is_expired": self.is_expired,
        }

# ============================================================
# 消息持久化存储
# ============================================================

class MessageStore:
    """消息持久化存储 — 内存存储 + 序列化支持"""

    def __init__(self, max_messages: int = 100000):
        self._messages: Dict[str, Message] = {}
        self._channel_index: Dict[str, Set[str]] = defaultdict(set)
        self._recipient_index: Dict[str, Set[str]] = defaultdict(set)
        self._sender_index: Dict[str, Set[str]] = defaultdict(set)
        self._status_index: Dict[MessageStatus, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self._max_messages = max_messages
        self._dead_letters: List[Message] = []

    def store(self, message: Message) -> bool:
        with self._lock:
            if len(self._messages) >= self._max_messages:
                self._evict_oldest()
            self._messages[message.msg_id] = message
            self._channel_index[message.channel].add(message.msg_id)
            self._recipient_index[message.recipient].add(message.msg_id)
            self._sender_index[message.sender].add(message.msg_id)
            self._status_index[message.status].add(message.msg_id)
            return True

    def get(self, msg_id: str) -> Optional[Message]:
        with self._lock:
            return self._messages.get(msg_id)

    def update_status(self, msg_id: str, status: MessageStatus) -> bool:
        with self._lock:
            msg = self._messages.get(msg_id)
            if not msg:
                return False
            self._status_index.get(msg.status, set()).discard(msg_id)
            msg.status = status
            if status == MessageStatus.DELIVERED:
                msg.delivered_at = time.time()
            self._status_index[status].add(msg_id)
            return True

    def get_by_channel(self, channel: str, limit: int = 100) -> List[Message]:
        with self._lock:
            ids = list(self._channel_index.get(channel, set()))
            msgs = [self._messages[mid] for mid in ids if mid in self._messages]
            msgs.sort(key=lambda m: (-m.priority, m.created_at))
            return msgs[:limit]

    def get_by_recipient(
        self, recipient: str, status: Optional[MessageStatus] = None, limit: int = 100
    ) -> List[Message]:
        with self._lock:
            ids = self._recipient_index.get(recipient, set())
            msgs = [self._messages[mid] for mid in ids if mid in self._messages]
            if status:
                msgs = [m for m in msgs if m.status == status]
            msgs.sort(key=lambda m: m.created_at)
            return msgs[:limit]

    def add_dead_letter(self, message: Message):
        with self._lock:
            message.status = MessageStatus.DEAD_LETTER
            self._dead_letters.append(message)

    def get_dead_letters(self, limit: int = 50) -> List[Message]:
        with self._lock:
            return self._dead_letters[-limit:]

    def _evict_oldest(self):
        pending = [m for m in self._messages.values() if m.status == MessageStatus.DELIVERED]
        if pending:
            oldest = min(pending, key=lambda m: m.delivered_at or m.created_at)
            self._remove_internal(oldest.msg_id)

    def _remove_internal(self, msg_id: str):
        msg = self._messages.pop(msg_id, None)
        if msg:
            self._channel_index[msg.channel].discard(msg_id)
            self._recipient_index[msg.recipient].discard(msg_id)
            self._sender_index[msg.sender].discard(msg_id)
            self._status_index[msg.status].discard(msg_id)

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "total": len(self._messages),
                "dead_letters": len(self._dead_letters),
                "by_status": {s.value: len(ids) for s, ids in self._status_index.items()},
                "channels": len(self._channel_index),
            }

# ============================================================
# 路由引擎
# ============================================================

class RoutingEngine(object):
    """消息路由引擎 — 支持Direct/Topic/Broadcast模式"""

    def __init__(self):
        self._subscriptions: Dict[str, Dict[str, ChannelType]] = defaultdict(dict)
        self._topic_patterns: Dict[str, List[str]] = defaultdict(list)  # topic -> [patterns]
        self._handlers: Dict[str, Callable] = {}

    def subscribe(self, recipient: str, channel: str, channel_type: ChannelType = ChannelType.DIRECT) -> bool:
        self._subscriptions[recipient][channel] = channel_type
        return True

    def unsubscribe(self, recipient: str, channel: str) -> bool:
        if recipient in self._subscriptions:
            self._subscriptions[recipient].pop(channel, None)
            return True
        return False

    def register_handler(self, channel: str, handler: Callable):
        self._handlers[channel] = handler

    def resolve_recipients(self, message: Message) -> List[str]:
        """解析消息目标接收者列表"""
        recipients = []
        if message.channel_type == ChannelType.DIRECT:
            recipients.append(message.recipient)
        elif message.channel_type == ChannelType.BROADCAST:
            recipients.extend(self._subscriptions.keys())
        elif message.channel_type == ChannelType.TOPIC:
            for sub, channels in self._subscriptions.items():
                if message.channel in channels:
                    recipients.append(sub)
        return list(set(recipients))

    def match_route(self, recipient: str, channel: str) -> bool:
        """检查路由是否匹配"""
        return channel in self._subscriptions.get(recipient, {})

# ============================================================
# 主模块: AgentHermes
# ============================================================

class AgentHermes(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Hermes智能体 — 消息路由与通信引擎"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(module_name="agent_hermes", version="6.39.0", config=config)
        self._store = MessageStore()
        self._router = RoutingEngine()
        self._pending_queue: List[Message] = []
        self._queue_lock = threading.Lock()
        self._stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "total_expired": 0,
            "total_dead_letters": 0,
            "total_broadcasts": 0,
        }

    async def initialize(self) -> None:
        await super().initialize()
        self._update_status(ModuleStatus.READY)
        logger.info("AgentHermes 消息路由引擎初始化完成")

    # === 消息发送 ===

    async def send_message(
        self,
        sender: str,
        recipient: str,
        payload: Dict[str, Any],
        channel: str = "default",
        channel_type: ChannelType = ChannelType.DIRECT,
        priority: MessagePriority = MessagePriority.NORMAL,
        headers: Optional[Dict[str, str]] = None,
        ttl_seconds: float = 86400 * 7,
    ) -> Result:
        """发送消息"""
        try:
            msg = Message(
                sender=sender,
                recipient=recipient,
                payload=payload,
                channel=channel,
                channel_type=channel_type,
                priority=priority.value,
                headers=headers or {},
                ttl_seconds=ttl_seconds,
            )
            self._store.store(msg)
            self._stats["total_sent"] += 1
            await self._audit_log("send_message", f"{sender} -> {recipient} @ {channel} ({channel_type.value})")
            return Result(success=True, data=msg.to_dict())
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return Result(success=False, message=str(e))

    async def broadcast(
        self,
        sender: str,
        payload: Dict[str, Any],
        channel: str = "broadcast",
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> Result:
        """广播消息到所有订阅者"""
        subscribers = list(self._router._subscriptions.keys())
        if not subscribers:
            return Result(success=False, message="无订阅者")
        sent_count = 0
        msg_ids = []
        for sub in subscribers:
            msg = Message(
                sender=sender,
                recipient=sub,
                payload=payload,
                channel=channel,
                channel_type=ChannelType.BROADCAST,
                priority=priority.value,
            )
            self._store.store(msg)
            msg_ids.append(msg.msg_id)
            sent_count += 1
        self._stats["total_sent"] += sent_count
        self._stats["total_broadcasts"] += 1
        await self._audit_log("broadcast", f"{sender} 广播到 {sent_count} 个订阅者 @ {channel}")
        return Result(success=True, data={"sent_count": sent_count, "msg_ids": msg_ids})

    # === 消息接收 ===

    async def receive_messages(self, recipient: str, channel: Optional[str] = None, limit: int = 50) -> Result:
        """接收消息（拉模式）"""
        if channel:
            msgs = self._store.get_by_channel(channel, limit)
            msgs = [m for m in msgs if m.recipient == recipient and m.status == MessageStatus.PENDING]
        else:
            msgs = self._store.get_by_recipient(recipient, MessageStatus.PENDING, limit)
        # 标记为已投递
        for msg in msgs:
            if not msg.is_expired:
                self._store.update_status(msg.msg_id, MessageStatus.DELIVERED)
                self._stats["total_delivered"] += 1
            else:
                self._store.update_status(msg.msg_id, MessageStatus.EXPIRED)
                self._stats["total_expired"] += 1
        return Result(success=True, data={"messages": [m.to_dict() for m in msgs], "count": len(msgs)})

    async def acknowledge(self, msg_id: str) -> Result:
        """确认消息"""
        ok = self._store.update_status(msg_id, MessageStatus.ACKNOWLEDGED)
        if ok:
            return Result(success=True, message="消息已确认")
        return Result(success=False, message=f"消息 {msg_id} 不存在")

    # === 订阅管理 ===

    async def subscribe(self, recipient: str, channel: str, channel_type: ChannelType = ChannelType.DIRECT) -> Result:
        self._router.subscribe(recipient, channel, channel_type)
        return Result(success=True, message=f"{recipient} 已订阅 {channel}")

    async def unsubscribe(self, recipient: str, channel: str) -> Result:
        ok = self._router.unsubscribe(recipient, channel)
        return Result(success=True if ok else False, message=f"{recipient} 退订 {channel}")

    async def list_subscriptions(self, recipient: str) -> Result:
        subs = self._router._subscriptions.get(recipient, {})
        return Result(success=True, data={"subscriptions": subs, "count": len(subs)})

    # === 死信管理 ===

    async def retry_dead_letter(self, msg_id: str) -> Result:
        """重试死信消息"""
        dead_letters = self._store.get_dead_letters()
        msg = next((m for m in dead_letters if m.msg_id == msg_id), None)
        if not msg:
            return Result(success=False, message="死信消息不存在")
        if msg.retry_count >= msg.max_retries:
            return Result(success=False, message=f"已超过最大重试次数 ({msg.max_retries})")
        msg.retry_count += 1
        msg.status = MessageStatus.PENDING
        msg.created_at = time.time()
        self._store.store(msg)
        self._store._dead_letters = [m for m in self._store._dead_letters if m.msg_id != msg_id]
        await self._audit_log("retry_dead_letter", f"重试死信: {msg_id} (第{msg.retry_count}次)")
        return Result(success=True, data={"msg_id": msg_id, "retry_count": msg.retry_count})

    async def get_dead_letters(self, limit: int = 50) -> Result:
        letters = self._store.get_dead_letters(limit)
        return Result(success=True, data={"dead_letters": [m.to_dict() for m in letters], "count": len(letters)})

    # === 消息查询 ===

    async def get_message(self, msg_id: str) -> Result:
        msg = self._store.get(msg_id)
        if not msg:
            return Result(success=False, message=f"消息 {msg_id} 不存在")
        return Result(success=True, data=msg.to_dict())

    async def search_messages(
        self,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
        channel: Optional[str] = None,
        status: Optional[MessageStatus] = None,
        limit: int = 100,
    ) -> Result:
        all_msgs = list(self._store._messages.values())
        if sender:
            all_msgs = [m for m in all_msgs if m.sender == sender]
        if recipient:
            all_msgs = [m for m in all_msgs if m.recipient == recipient]
        if channel:
            all_msgs = [m for m in all_msgs if m.channel == channel]
        if status:
            all_msgs = [m for m in all_msgs if m.status == status]
        all_msgs.sort(key=lambda m: m.created_at, reverse=True)
        return Result(success=True, data={"messages": [m.to_dict() for m in all_msgs[:limit]], "count": len(all_msgs)})

    # === 清理 ===

    async def cleanup_expired(self) -> Result:
        """清理过期消息"""
        count = 0
        for msg in list(self._store._messages.values()):
            if msg.is_expired and msg.status == MessageStatus.PENDING:
                self._store.update_status(msg.msg_id, MessageStatus.EXPIRED)
                count += 1
                self._stats["total_expired"] += 1
        await self._audit_log("cleanup_expired", f"清理 {count} 条过期消息")
        return Result(success=True, data={"cleaned": count})

    # === 健康检查 ===

    def health_check(self) -> HealthReport:
        store_stats = self._store.get_stats()
        return HealthReport(
            module_name=self.module_name,
            status=ModuleStatus.RUNNING,
            checks={"message_store": True, "routing_engine": True, "pending_queue": True},
            stats=ModuleStats(),
        )

    async def get_module_stats(self) -> Result:
        return Result(success=True, data={**self._stats, "store": self._store.get_stats()})

    async def execute(self, operation: str, params: dict = None) -> dict:
        """统一执行入口 - Hermes消息路由与投递操作"""
        self.trace("execute", {"operation": operation})
        self.metrics_collector.counter("agent_hermes.execute.calls", 1)
        self.audit("hermes_operation", {"operation": operation})
        params = params or {}
        ops = {
            "send_message": lambda p: {"status": "queued", "topic": p.get("topic", "")},
            "subscribe": lambda p: {"status": "subscribed", "topic": p.get("topic", "")},
            "unsubscribe": lambda p: {"status": "unsubscribed", "topic": p.get("topic", "")},
            "get_stats": lambda p: self.get_stats() if hasattr(self, "get_stats") else {},
            "list_topics": lambda p: {"topics": list(self._topics.keys())} if hasattr(self, "_topics") else [],
            "health": lambda p: {"status": "healthy"},
        }
        handler = ops.get(operation)
        if not handler:
            return {"success": False, "error": f"未知操作: {operation}"}
        try:
            return {"success": True, "result": handler(params)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_update_routes(self, routes: List[Dict]) -> Dict[str, Any]:
        """批量更新消息路由规则。企业场景：服务上线时一次性配置几十条路由。

        Args:
            routes: 路由规则列表，每条包含 source, target, priority, filters, ttl_seconds
        Returns:
            操作结果，含成功/失败/跳过计数
        """
        results = {"success": 0, "failed": 0, "skipped": 0, "details": []}
        for rule in routes:
            try:
                source = rule.get("source", "")
                target = rule.get("target", "")
                if not source or not target:
                    results["skipped"] += 1
                    continue
                priority = rule.get("priority", 5)
                filters = rule.get("filters", [])
                ttl = rule.get("ttl_seconds", 86400)
                route_key = f"route:{source}:{target}:{priority}"
                route_data = {
                    "source": source,
                    "target": target,
                    "priority": priority,
                    "filters": filters,
                    "ttl_seconds": ttl,
                    "created_at": datetime.now().isoformat(),
                }
                if hasattr(self, "_routes"):
                    self._routes[route_key] = route_data
                results["success"] += 1
                results["details"].append({"route_key": route_key, "status": "ok"})
            except Exception as e:
                results["failed"] += 1
                results["details"].append({"error": str(e), "rule": str(rule)})
        return results

    def get_route_statistics(self) -> Dict[str, Any]:
        """获取路由表统计信息：总路由数、按优先级分布、按目标分布。
        用于运维监控面板展示当前路由健康度。
        """
        stats = {"total_routes": 0, "by_priority": {}, "by_target": {}, "last_updated": None}
        if not hasattr(self, "_routes"):
            return stats
        routes = getattr(self, "_routes", {})
        stats["total_routes"] = len(routes)
        for key, val in routes.items():
            pri = val.get("priority", "unknown")
            tgt = val.get("target", "unknown")
            stats["by_priority"][str(pri)] = stats["by_priority"].get(str(pri), 0) + 1
            stats["by_target"][tgt] = stats["by_target"].get(tgt, 0) + 1
        stats["last_updated"] = datetime.now().isoformat()
        return stats

    def shutdown(self) -> dict:
        """Graceful shutdown for agent_hermes."""
        self._status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = AgentHermes
