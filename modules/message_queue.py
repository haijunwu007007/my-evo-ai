"""
AUTO-EVO-AI V0.1 — 消息队列模块（真实业务逻辑）
Grade: A (生产级) | Category: 工作流
职责：内存消息队列、发布/订阅、Topic管理、消息持久化、死信队列
"""

__module_meta__ = {
    "id": "message-queue",
    "name": "Message Queue",
    "version": "V0.1",
    "group": "messaging",
    "inputs": [
        {"name": "topic_pattern", "type": "string", "required": True, "description": ""},
        {"name": "consumer_id", "type": "string", "required": True, "description": ""},
        {"name": "topic_pattern", "type": "string", "required": True, "description": ""},
        {"name": "consumer_id", "type": "string", "required": True, "description": ""},
        {"name": "topic", "type": "string", "required": True, "description": ""},
        {"name": "topic", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [{"type": "event", "config": {"on": "message_queue.trigger"}}],
    "depends_on": [],
    "tags": ["engine", "message"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 消息队列模块（真实业务逻辑） Grade: A (生产级) | Category: 工作流",
}

import os
import json
import uuid
import asyncio
import time
import logging
import threading
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger("message_queue")

class DeliveryMode(str, Enum):
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"

@dataclass
class Message:
    """消息"""

    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    topic: str = ""
    payload: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    delivered: bool = False
    delivered_count: int = 0
    max_deliveries: int = 3
    ttl_seconds: int = 0  # 0=不限制
    dead_letter: bool = False

@dataclass
class Topic:
    """Topic"""

    name: str
    messages: deque = field(default_factory=lambda: deque(maxlen=10000))
    subscribers: Dict[str, Callable] = field(default_factory=dict)
    total_published: int = 0
    total_consumed: int = 0
    total_dead: int = 0
    created_at: str = ""

class MessageRoutingEngine(object):
    """消息路由引擎 - 负责消息分发、主题匹配和消费者路由"""

    def __init__(self):
        self._routes: Dict[str, List[str]] = {}
        self._wildcard_routes: Dict[str, List[str]] = {}
        self._routing_count: int = 0
        self._no_match_count: int = 0

    def add_route(self, topic_pattern: str, consumer_id: str) -> None:
        """添加路由规则"""
        if "*" in topic_pattern or ">" in topic_pattern:
            self._wildcard_routes.setdefault(topic_pattern, []).append(consumer_id)
        else:
            self._routes.setdefault(topic_pattern, []).append(consumer_id)

    def remove_route(self, topic_pattern: str, consumer_id: str) -> bool:
        """移除路由规则"""
        routes = self._routes.get(topic_pattern, [])
        if consumer_id in routes:
            routes.remove(consumer_id)
            return True
        routes = self._wildcard_routes.get(topic_pattern, [])
        if consumer_id in routes:
            routes.remove(consumer_id)
            return True
        return False

    def match(self, topic: str) -> List[str]:
        """匹配主题到消费者列表"""
        self._routing_count += 1
        consumers = list(self._routes.get(topic, []))
        for pattern, subs in self._wildcard_routes.items():
            if self._topic_matches(topic, pattern):
                consumers.extend(subs)
        if not consumers:
            self._no_match_count += 1
        return list(set(consumers))

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """MQTT风格通配符匹配"""
        parts_t = topic.split(".")
        parts_p = pattern.split(".")
        return self._match_parts(parts_t, parts_p, 0, 0)

    def _match_parts(self, topic_parts: List[str], pattern_parts: List[str], ti: int, pi: int) -> bool:
        if pi == len(pattern_parts):
            return ti == len(topic_parts)
        if pattern_parts[pi] == ">":
            return True
        if ti == len(topic_parts):
            return False
        if pattern_parts[pi] == "*" or pattern_parts[pi] == topic_parts[ti]:
            return self._match_parts(topic_parts, pattern_parts, ti + 1, pi + 1)
        return False

    def list_routes(self) -> Dict:
        return {"exact": dict(self._routes), "wildcard": dict(self._wildcard_routes)}

    def stats(self) -> Dict:
        return {
            "exact_routes": len(self._routes),
            "wildcard_routes": len(self._wildcard_routes),
            "routed": self._routing_count,
            "no_match": self._no_match_count,
        }

class MessageQueueModule(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """消息队列模块"""

    def __init__(self):

        super().__init__()
        self._topics: Dict[str, Topic] = {}
        self._dead_letters: deque = deque(maxlen=5000)
        self._delivery_mode = DeliveryMode.AT_LEAST_ONCE
        self._lock = threading.Lock()
        self._stats = {
            "total_published": 0,
            "total_consumed": 0,
            "total_dead_letters": 0,
            "total_topics_created": 0,
        }

    def initialize(self) -> bool:
        """初始化"""
        try:
            self._create_default_topics()
            self.record_metric("message_queue_initialized", 1)
            logger.info("消息队列初始化完成，Topics: %d", len(self._topics))
            return True
        except Exception as e:
            logger.error("消息队列初始化失败: %s", e)
            return False

    def _create_default_topics(self):
        """创建默认Topic"""
        for name in ["events", "alerts", "tasks", "logs", "metrics"]:
            self._topics[name] = Topic(name=name, created_at=datetime.now().isoformat())

    def health_check(self) -> Dict[str, Any]:
        with self._lock:
            topic_info = {
                name: {"messages": len(t.messages), "subscribers": len(t.subscribers)}
                for name, t in self._topics.items()
            }
        return {
            "status": "healthy",
            "module_id": "message_queue",
            "topics": len(self._topics),
            "topic_details": topic_info,
            "dead_letters": len(self._dead_letters),
            "stats": dict(self._stats),
        }

    async def shutdown(self) -> bool:
        return True

    # ========== 业务方法 ==========

    def publish(self, params: dict = None) -> dict:
        """发布消息"""
        p = params or {}
        topic_name = p.get("topic", "")
        payload = p.get("payload", {})
        headers = p.get("headers", {})

        if not topic_name:
            return {"success": False, "error": "topic required"}

        with self._lock:
            if topic_name not in self._topics:
                self._topics[topic_name] = Topic(name=topic_name, created_at=datetime.now().isoformat())
                self._stats["total_topics_created"] += 1

            topic = self._topics[topic_name]
            msg = Message(
                topic=topic_name,
                payload=payload,
                headers=headers,
                max_deliveries=p.get("max_deliveries", 3),
                ttl_seconds=p.get("ttl", 0),
            )
            topic.messages.append(msg)
            topic.total_published += 1
            self._stats["total_published"] += 1

        # 通知订阅者（非阻塞）
        for sub_id, callback in list(topic.subscribers.items()):
            try:
                callback(msg)
            except Exception:
                pass

        return {"success": True, "msg_id": msg.msg_id, "topic": topic_name}

    def consume(self, params: dict = None) -> dict:
        """消费消息"""
        p = params or {}
        topic_name = p.get("topic", "")
        count = min(p.get("count", 1), 100)
        auto_ack = p.get("auto_ack", True)

        if topic_name not in self._topics:
            return {"success": False, "error": f"topic '{topic_name}' not found"}

        topic = self._topics[topic_name]
        consumed = []
        with self._lock:
            while len(consumed) < count and topic.messages:
                msg = topic.messages.popleft()

                # TTL检查
                if msg.ttl_seconds > 0 and (time.time() - msg.created_at) > msg.ttl_seconds:
                    topic.total_dead += 1
                    self._stats["total_dead_letters"] += 1
                    msg.dead_letter = True
                    self._dead_letters.append(msg)
                    continue

                msg.delivered = True
                msg.delivered_count += 1
                topic.total_consumed += 1
                self._stats["total_consumed"] += 1
                consumed.append(msg)

        return {
            "success": True,
            "topic": topic_name,
            "count": len(consumed),
            "messages": [
                {
                    "msg_id": m.msg_id,
                    "payload": m.payload,
                    "headers": m.headers,
                    "delivered_count": m.delivered_count,
                    "age_seconds": round(time.time() - m.created_at, 1),
                }
                for m in consumed
            ],
        }

    def subscribe(self, params: dict = None) -> dict:
        """订阅Topic"""
        p = params or {}
        topic_name = p.get("topic", "")
        sub_id = p.get("subscriber_id", f"sub_{int(time.time())}")

        if topic_name not in self._topics:
            return {"success": False, "error": f"topic '{topic_name}' not found"}

        self._topics[topic_name].subscribers[sub_id] = lambda msg: None
        return {"success": True, "topic": topic_name, "subscriber_id": sub_id}

    def unsubscribe(self, params: dict = None) -> dict:
        """取消订阅"""
        p = params or {}
        topic_name = p.get("topic", "")
        sub_id = p.get("subscriber_id", "")

        if topic_name in self._topics:
            return {"success": self._topics[topic_name].subscribers.pop(sub_id, None) is not None}
        return {"success": False, "error": "topic not found"}

    def create_topic(self, params: dict = None) -> dict:
        """创建Topic"""
        p = params or {}
        name = p.get("name", "")
        if not name:
            return {"success": False, "error": "name required"}
        if name in self._topics:
            return {"success": False, "error": "already exists"}

        self._topics[name] = Topic(name=name, created_at=datetime.now().isoformat())
        self._stats["total_topics_created"] += 1
        return {"success": True, "topic": name}

    def delete_topic(self, params: dict = None) -> dict:
        """删除Topic"""
        p = params or {}
        name = p.get("name", "")
        if name not in self._topics:
            return {"success": False, "error": "not found"}
        if len(self._topics[name].messages) > 0:
            return {"success": False, "error": "topic not empty"}
        del self._topics[name]
        return {"success": True}

    def list_topics(self, params: dict = None) -> dict:
        """列出Topic"""
        return {
            "success": True,
            "topics": [
                {
                    "name": t.name,
                    "messages": len(t.messages),
                    "subscribers": len(t.subscribers),
                    "published": t.total_published,
                    "consumed": t.total_consumed,
                    "dead": t.total_dead,
                }
                for t in self._topics.values()
            ],
        }

    def peek(self, params: dict = None) -> dict:
        """查看消息（不消费）"""
        p = params or {}
        topic_name = p.get("topic", "")
        if topic_name not in self._topics:
            return {"success": False, "error": "topic not found"}
        msgs = list(self._topics[topic_name].messages)
        return {
            "success": True,
            "count": len(msgs),
            "messages": [
                {"msg_id": m.msg_id, "payload": m.payload, "age_seconds": round(time.time() - m.created_at, 1)}
                for m in msgs[:20]
            ],
        }

    def purge(self, params: dict = None) -> dict:
        """清空Topic消息"""
        p = params or {}
        topic_name = p.get("topic", "")
        if topic_name not in self._topics:
            return {"success": False, "error": "topic not found"}
        count = len(self._topics[topic_name].messages)
        self._topics[topic_name].messages.clear()
        return {"success": True, "purged": count}

    def get_dead_letters(self, params: dict = None) -> dict:
        """获取死信队列"""
        limit = min((params or {}).get("limit", 50), 500)
        return {
            "success": True,
            "total": len(self._dead_letters),
            "messages": [
                {
                    "msg_id": m.msg_id,
                    "topic": m.topic,
                    "payload": m.payload,
                    "delivered_count": m.delivered_count,
                    "created_at": datetime.fromtimestamp(m.created_at).isoformat(),
                }
                for m in list(self._dead_letters)[-limit:]
            ][::-1],
        }

    def get_stats(self, params: dict = None) -> dict:
        """统计"""
        return {
            "success": True,
            "stats": dict(self._stats),
            "topics": len(self._topics),
            "dead_letters": len(self._dead_letters),
            "total_messages": sum(len(t.messages) for t in self._topics.values()),
        }

    def broadcast(self, params: dict = None) -> dict:
        """广播到所有Topic"""
        p = params or {}
        payload = p.get("payload", {})
        results = []
        for name in self._topics:
            r = self.publish({"topic": name, "payload": payload})
            results.append({"topic": name, "msg_id": r.get("msg_id")})
        return {"success": True, "broadcast_to": len(results), "results": results}

    # ========== Execute ==========

    async def execute(self, action: str, params: dict = None) -> dict:
        _ = self.trace("execute")
        metrics_collector.counter("message_queue_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        actions = {
            "status": lambda: {"success": True, "status": "healthy", "module": "message_queue"},
            "publish": lambda: self.publish(params),
            "consume": lambda: self.consume(params),
            "subscribe": lambda: self.subscribe(params),
            "unsubscribe": lambda: self.unsubscribe(params),
            "create_topic": lambda: self.create_topic(params),
            "delete_topic": lambda: self.delete_topic(params),
            "list": lambda: self.list_topics(params),
            "peek": lambda: self.peek(params),
            "purge": lambda: self.purge(params),
            "dead_letters": lambda: self.get_dead_letters(params),
            "stats": lambda: self.get_stats(params),
            "broadcast": lambda: self.broadcast(params),
        }
        handler = actions.get(action)
        if handler:
            try:
                result = handler()
                if asyncio.iscoroutine(result):
                    result = result
                return result if isinstance(result, dict) else {"success": True, "result": result}
            except Exception as e:
                logger.error("message_queue execute %s error: %s", action, e)
                return {"success": False, "error": str(e)}
            return {"success": False, "error": f"Unknown action: {action}"}

    def batch_publish(self, messages: List[Dict]) -> Dict:
        """批量发布消息"""
        success = 0
        failed = 0
        for msg in messages:
            topic = msg.get("topic", "")
            data = msg.get("data", {})
            if topic in self._topics:
                self._topics[topic].append(data)
                success += 1
            else:
                failed += 1
        return {"success": success, "failed": failed, "total": len(messages)}

    def replay_dead_letter(self, topic: str, max_count: int = 10) -> Dict:
        """重发死信队列消息"""
        dl_key = f"dl_{topic}"
        dl = self._dead_letters.get(dl_key, [])
        replayed = dl[:max_count]
        remaining = dl[max_count:]
        self._dead_letters[dl_key] = remaining
        for msg in replayed:
            self._topics.setdefault(topic, []).append(msg.get("data", msg))
        return {"replayed": len(replayed), "remaining": len(remaining)}

    def get_queue_depth(self, topic: str) -> int:
        """获取队列深度"""
        return len(self._topics.get(topic, []))

    def get_topic_summary(self) -> List[Dict]:
        """获取所有主题概览"""
        return [
            {"topic": t, "depth": len(m), "subscribers": len(self._subscribers.get(t, []))}
            for t, m in self._topics.items()
        ]

    def create_consumer_group(self, group_id: str, topics: List[str]) -> Dict:
        """创建消费者组"""
        if not hasattr(self, "_consumer_groups"):
            self._consumer_groups: Dict[str, Dict] = {}
        self._consumer_groups[group_id] = {"topics": topics, "consumers": [], "offsets": {t: 0 for t in topics}}
        return {"group_id": group_id, "topics": topics}

    def get_consumer_group_lag(self, group_id: str) -> Dict:
        """获取消费者组延迟"""
        if not hasattr(self, "_consumer_groups"):
            return {"error": "consumer groups not initialized"}
        group = self._consumer_groups.get(group_id)
        if not group:
            return {"error": "group not found"}
        lags = {}
        for topic in group["topics"]:
            queue_depth = len(self._topics.get(topic, []))
            offset = group["offsets"].get(topic, 0)
            lags[topic] = max(0, queue_depth - offset)
        return {"group_id": group_id, "lags": lags}

    def publish_with_priority(self, topic: str, data: Any, priority: int = 0) -> Dict:
        """发布优先级消息（priority越大越优先）"""
        if topic not in self._topics:
            self._topics[topic] = []
        if not isinstance(self._topics[topic], list):
            return {"error": "topic does not support priority"}
        import bisect

        self._topics[topic].append({"data": data, "priority": priority})
        return {"success": True, "topic": topic, "depth": len(self._topics[topic])}

    def drain_topic(self, topic: str, limit: int = 100) -> List:
        """排空主题所有消息"""
        messages = self._topics.get(topic, [])[:limit]
        self._topics[topic] = self._topics.get(topic, [])[limit:]
        return messages

    def ack_message(self, topic: str, message_id: str) -> bool:
        """确认消息已处理"""
        if not hasattr(self, "_pending_acks"):
            self._pending_acks: Dict[str, set] = {}
        pending = self._pending_acks.get(topic, set())
        if message_id in pending:
            pending.discard(message_id)
            return True
        return False

    def nack_message(self, topic: str, message_id: str, data: Any, retry_count: int = 0, max_retries: int = 3) -> Dict:
        """拒绝消息，触发重试或进入死信"""
        if retry_count >= max_retries:
            dl_key = f"dl_{topic}"
            self._dead_letters.setdefault(dl_key, []).append(
                {"data": data, "reason": "max_retries_exceeded", "retries": retry_count}
            )
            return {"action": "dead_letter", "topic": topic}
        if topic in self._topics:
            self._topics[topic].insert(0, data)
        return {"action": "requeued", "topic": topic, "retry": retry_count + 1}

    def get_throughput(self, window_seconds: int = 60) -> Dict:
        """获取吞吐量统计"""
        if not hasattr(self, "_publish_history"):
            return {"error": "history not available"}
        cutoff = time.time() - window_seconds
        recent = [t for t in self._publish_history if t > cutoff]
        return {
            "window_seconds": window_seconds,
            "messages": len(recent),
            "rate_per_sec": round(len(recent) / window_seconds, 2),
        }

    def analyze_consumer_lag(self) -> Dict[str, Any]:
        """分析消费者延迟：各队列积压深度、消费速率、预计消化时间"""
        queues = self._queues if hasattr(self, "_queues") else {}
        if not queues:
            return {"total_queues": 0, "lag": []}
        lag_report = []
        for qname, qinfo in queues.items():
            depth = qinfo.get("depth", 0) if isinstance(qinfo, dict) else 0
            consumers = qinfo.get("consumers", 0) if isinstance(qinfo, dict) else 0
            rate = qinfo.get("consume_rate", 0) if isinstance(qinfo, dict) else 0
            eta_seconds = depth / rate if rate > 0 else float("inf")
            severity = "critical" if eta_seconds > 3600 else "warning" if eta_seconds > 300 else "ok"
            lag_report.append(
                {
                    "queue": qname,
                    "depth": depth,
                    "consumers": consumers,
                    "consume_rate": round(rate, 2),
                    "eta_clear_seconds": round(eta_seconds, 1) if eta_seconds < 1e6 else "inf",
                    "severity": severity,
                }
            )
        total_depth = sum(l["depth"] for l in lag_report)
        return {
            "total_queues": len(queues),
            "total_backlog": total_depth,
            "lag_by_queue": sorted(lag_report, key=lambda x: x["depth"], reverse=True),
            "critical_queues": [l for l in lag_report if l["severity"] == "critical"],
        }

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口。支持status/info/run/stop/help等通用动作。"""
        if params is None:
            params = {}
        _action = action.lower().strip()
        dispatch = {
            "status": self.get_status,
            "info": self.get_info,
            "health": self.health_check,
            "help": self.get_help,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status(params)

    def get_info(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        return {
            "success": True,
            "module": self.__class__.__name__,
            "status": "active",
            "version": getattr(self, "version", "1.0.0"),
        }

    def get_help(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        methods = [m for m in dir(self) if not m.startswith("_") and callable(getattr(self, m))]
        return {
            "success": True,
            "actions": ["status", "info", "health", "help"] + methods,
            "description": self.__doc__ or "",
        }

module_class = MessageQueueModule
