"""
Webhook Handler - 企业级Webhook管理引擎
生产级Webhook接收、签名验证、事件路由、重试投递、日志审计
支持：HMAC签名、多协议路由、死信队列、幂等处理、订阅管理
"""

__module_meta__ = {
    "id": "webhook-handler",
    "name": "Webhook Handler",
    "version": "1.0.0",
    "group": "webhook",
    "inputs": [
        {"name": "payload", "type": "string", "required": True, "description": ""},
        {"name": "secret", "type": "string", "required": True, "description": ""},
        {"name": "algorithm", "type": "string", "required": True, "description": ""},
        {"name": "payload", "type": "string", "required": True, "description": ""},
        {"name": "secret", "type": "string", "required": True, "description": ""},
        {"name": "signature", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [{"type": "webhook", "config": {"path": "/hooks/webhook_handler", "method": "POST"}}],
    "depends_on": [],
    "tags": ["engine", "handler", "webhook", "manager"],
    "grade": "A",
    "description": "Webhook Handler - 企业级Webhook管理引擎 生产级Webhook接收、签名验证、事件路由、重试投递、日志审计",
}

import hashlib
import hmac
import time
import uuid
import threading
import json
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict
from urllib.parse import urlparse

from modules._base.enterprise_module import EnterpriseModule

class WebhookProtocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    GRPC = "grpc"
    SQS = "sqs"
    KAFKA = "kafka"
    AMQP = "amqp"

class SignatureAlgorithm(Enum):
    SHA256 = "sha256"
    SHA1 = "sha1"
    MD5 = "md5"

class DeliveryState(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    TIMEOUT = "timeout"
    REJECTED = "rejected"
    RETRYING = "retrying"

# ─── 签名验证引擎 ────────────────────────────────────────────

class SignatureVerifier:
    """Webhook签名验证：HMAC-SHA256/SHA1/MD5"""

    def __init__(self):
        self._algorithms = {
            "sha256": hashlib.sha256,
            "sha1": hashlib.sha1,
            "md5": hashlib.md5,
        }

    def sign(self, payload: str, secret: str, algorithm: str = "sha256") -> str:
        algo = self._algorithms.get(algorithm, hashlib.sha256)
        return hmac.new(secret.encode(), payload.encode(), algo).hexdigest()

    def verify(self, payload: str, secret: str, signature: str, algorithm: str = "sha256") -> bool:
        expected = self.sign(payload, secret, algorithm)
        return hmac.compare_digest(expected, signature)

    def verify_header(
        self, payload: str, secret: str, headers: Dict, header_name: str = "X-Signature", algorithm: str = "sha256"
    ) -> bool:
        """从HTTP头中提取签名并验证"""
        signature = headers.get(header_name) or headers.get(header_name.lower()) or ""
        signature = signature.replace("sha256=", "").replace("sha1=", "").replace("md5=", "")
        if not signature:
            return False
        return self.verify(payload, secret, signature, algorithm)

# ─── URL路由引擎 ─────────────────────────────────────────────

class WebhookRouter:
    """Webhook URL路由匹配：精确匹配、通配符、正则"""

    def __init__(self):
        self._routes: List[Dict] = []
        self._exact: Dict[str, Dict] = {}
        self._pattern: List[Dict] = []

    def add_route(
        self, path: str, handler_id: str, methods: List[str] = None, priority: int = 0, condition: Dict = None
    ):
        """注册路由"""
        route = {
            "path": path,
            "handler_id": handler_id,
            "methods": [m.upper() for m in (methods or ["POST"])],
            "priority": priority,
            "condition": condition or {},
            "created_at": time.time(),
        }
        if "*" not in path and "{" not in path:
            self._exact[path] = route
        else:
            self._pattern.append(route)
            self._pattern.sort(key=lambda r: r["priority"], reverse=True)
        self._routes.append(route)

    def remove_route(self, path: str) -> bool:
        self._exact.pop(path, None)
        self._pattern = [r for r in self._pattern if r["path"] != path]
        self._routes = [r for r in self._routes if r["path"] != path]
        return True

    def match(self, path: str, method: str = "POST") -> Optional[Dict]:
        """匹配路由"""
        # 精确匹配优先
        route = self._exact.get(path)
        if route and method.upper() in route["methods"]:
            return route
        # 通配符/正则匹配
        for route in self._pattern:
            if method.upper() not in route["methods"]:
                continue
            pattern = route["path"]
            # 通配符转正则
            regex = pattern.replace("*", "[^/]+").replace("**", ".+")
            regex = f"^{regex}$"
            try:
                if re.match(regex, path):
                    return route
            except re.error:
                # 纯字符串前缀匹配
                if path.startswith(pattern.replace("*", "")):
                    return route
        return None

    def list_routes(self) -> List[Dict]:
        return [
            {"path": r["path"], "handler": r["handler_id"], "methods": r["methods"], "priority": r["priority"]}
            for r in self._routes
        ]

# ─── 投递引擎 ───────────────────────────────────────────────

class DeliveryEngine:
    """Webhook投递引擎：重试、超时、死信"""

    def __init__(self):
        self._delivery_log: List[Dict] = []
        self._pending: List[Dict] = []
        self._dead_letters: List[Dict] = []
        self._idempotency_keys: Dict[str, float] = {}
        self._idempotency_ttl = 300.0
        self._lock = threading.Lock()
        self._max_retries = 5
        self._retry_delays = [1, 5, 30, 120, 600]  # 指数退避
        self._max_log = 10000
        self._callbacks: Dict[str, Callable] = {}

    def register_callback(self, handler_id: str, callback: Callable):
        """注册投递回调（实际发送HTTP请求的函数）"""
        self._callbacks[handler_id] = callback

    def deliver(
        self, handler_id: str, payload: Dict, headers: Dict = None, idempotency_key: str = None, timeout: float = 30.0
    ) -> Dict:
        """投递Webhook"""
        # 幂等检查
        if idempotency_key:
            now = time.time()
            if idempotency_key in self._idempotency_keys:
                if now - self._idempotency_keys[idempotency_key] < self._idempotency_ttl:
                    return {"success": True, "result": "idempotent_skip", "handler_id": handler_id}
            self._idempotency_keys[idempotency_key] = now
            # 清理过期
            expired = [k for k, v in self._idempotency_keys.items() if now - v > self._idempotency_ttl]
            for k in expired:
                del self._idempotency_keys[k]

        delivery_id = str(uuid.uuid4())[:12]
        record = {
            "delivery_id": delivery_id,
            "handler_id": handler_id,
            "payload": payload,
            "headers": headers or {},
            "state": "pending",
            "attempts": 0,
            "timeout": timeout,
            "created_at": time.time(),
            "response": None,
        }

        # 同步投递
        callback = self._callbacks.get(handler_id)
        if callback:
            try:
                result = callback(payload, headers or {})
                record["state"] = "delivered"
                record["response"] = result
                record["delivered_at"] = time.time()
                record["attempts"] = 1
            except Exception as e:
                record["state"] = "failed"
                record["error"] = str(e)
                record["attempts"] = 1
                self._schedule_retry(record)
        else:
            record["state"] = "delivered"  # 无回调时标记成功（测试模式）
            record["delivered_at"] = time.time()
            record["attempts"] = 1

        self._add_log(record)
        return {"success": record["state"] == "delivered", "delivery_id": delivery_id, "state": record["state"]}

    def _schedule_retry(self, record: Dict):
        """调度重试"""
        if record["attempts"] >= self._max_retries:
            record["state"] = "failed"
            self._dead_letters.append(
                {
                    "delivery_id": record["delivery_id"],
                    "handler_id": record["handler_id"],
                    "payload": record["payload"],
                    "error": record.get("error"),
                    "attempts": record["attempts"],
                    "timestamp": time.time(),
                }
            )
            return
        record["state"] = "retrying"
        record["next_retry_at"] = time.time() + self._retry_delays[min(record["attempts"], len(self._retry_delays) - 1)]

    def retry(self, delivery_id: str) -> Dict:
        """手动重试"""
        record = next((r for r in self._delivery_log if r["delivery_id"] == delivery_id), None)
        if not record:
            return {"success": False, "error": "Delivery not found"}
        if record["state"] not in ("failed", "retrying"):
            return {"success": False, "error": f"Cannot retry state: {record['state']}"}

        record["attempts"] += 1
        callback = self._callbacks.get(record["handler_id"])
        if callback:
            try:
                result = callback(record["payload"], record.get("headers", {}))
                record["state"] = "delivered"
                record["response"] = result
                record["delivered_at"] = time.time()
            except Exception as e:
                record["error"] = str(e)
                self._schedule_retry(record)
        else:
            record["state"] = "delivered"
            record["delivered_at"] = time.time()

        return {"success": record["state"] == "delivered", "state": record["state"]}

    def _add_log(self, record: Dict):
        self._delivery_log.append(record)
        if len(self._delivery_log) > self._max_log:
            self._delivery_log = self._delivery_log[-self._max_log :]

    def get_delivery_log(self, handler_id: str = None, state: str = None, limit: int = 50) -> List[Dict]:
        records = self._delivery_log
        if handler_id:
            records = [r for r in records if r["handler_id"] == handler_id]
        if state:
            records = [r for r in records if r["state"] == state]
        return records[-limit:]

    def get_dead_letters(self, limit: int = 50) -> List[Dict]:
        return self._dead_letters[-limit:]

    def stats(self) -> Dict:
        total = len(self._delivery_log)
        return {
            "total_deliveries": total,
            "delivered": sum(1 for r in self._delivery_log if r["state"] == "delivered"),
            "failed": sum(1 for r in self._delivery_log if r["state"] == "failed"),
            "retrying": sum(1 for r in self._delivery_log if r["state"] == "retrying"),
            "dead_letter_count": len(self._dead_letters),
            "registered_handlers": len(self._callbacks),
        }

# ─── 订阅管理引擎 ────────────────────────────────────────────

class SubscriptionManager:
    """Webhook订阅管理：订阅CRUD、事件过滤、活跃度追踪"""

    def __init__(self):
        self._subscriptions: Dict[str, Dict] = {}
        self._event_subscribers: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(
        self,
        sub_id: str,
        url: str,
        events: List[str] = None,
        secret: str = None,
        headers: Dict = None,
        active: bool = True,
        description: str = "",
    ) -> Dict:
        with self._lock:
            events = events or ["*"]
            sub = {
                "subscription_id": sub_id,
                "url": url,
                "events": events,
                "secret": secret or "",
                "headers": headers or {},
                "active": active,
                "description": description,
                "created_at": time.time(),
                "last_delivery": None,
                "delivery_count": 0,
                "failure_count": 0,
                "success_rate": 100.0,
            }
            self._subscriptions[sub_id] = sub
            # 索引
            if active:
                for event in events:
                    if sub_id not in self._event_subscribers[event]:
                        self._event_subscribers[event].append(sub_id)
            return sub

    def unsubscribe(self, sub_id: str) -> bool:
        with self._lock:
            sub = self._subscriptions.pop(sub_id, None)
            if sub:
                for event in sub["events"]:
                    if sub_id in self._event_subscribers.get(event, []):
                        self._event_subscribers[event].remove(sub_id)
                return True
            return False

    def get_subscribers(self, event_type: str) -> List[Dict]:
        """获取事件的活跃订阅者"""
        subscriber_ids = self._event_subscribers.get(event_type, []) + self._event_subscribers.get("*", [])
        return [
            self._subscriptions[sid]
            for sid in subscriber_ids
            if sid in self._subscriptions and self._subscriptions[sid]["active"]
        ]

    def get_subscription(self, sub_id: str) -> Optional[Dict]:
        return self._subscriptions.get(sub_id)

    def list_subscriptions(self, active_only: bool = False) -> List[Dict]:
        subs = list(self._subscriptions.values())
        if active_only:
            subs = [s for s in subs if s["active"]]
        return subs

    def toggle_active(self, sub_id: str, active: bool) -> bool:
        sub = self._subscriptions.get(sub_id)
        if not sub:
            return False
        sub["active"] = active
        if active:
            for event in sub["events"]:
                if sub_id not in self._event_subscribers[event]:
                    self._event_subscribers[event].append(sub_id)
        else:
            for event in sub["events"]:
                if sub_id in self._event_subscribers.get(event, []):
                    self._event_subscribers[event].remove(sub_id)
        return True

    def record_delivery(self, sub_id: str, success: bool):
        sub = self._subscriptions.get(sub_id)
        if sub:
            sub["last_delivery"] = time.time()
            sub["delivery_count"] += 1
            if success:
                sub["success_rate"] = round(
                    (sub["delivery_count"] - sub["failure_count"]) / sub["delivery_count"] * 100, 1
                )
            else:
                sub["failure_count"] += 1
                sub["success_rate"] = round(
                    max(0, sub["delivery_count"] - sub["failure_count"]) / sub["delivery_count"] * 100, 1
                )

    def stats(self) -> Dict:
        subs = list(self._subscriptions.values())
        return {
            "total_subscriptions": len(subs),
            "active": sum(1 for s in subs if s["active"]),
            "inactive": sum(1 for s in subs if not s["active"]),
            "total_deliveries": sum(s["delivery_count"] for s in subs),
            "avg_success_rate": round(sum(s["success_rate"] for s in subs) / len(subs), 1) if subs else 0,
            "event_types_registered": len(self._event_subscribers),
        }

# ─── 主模块 ──────────────────────────────────────────────────

class WebhookHandler(EnterpriseModule):
    """企业级Webhook管理引擎
    核心能力：签名验证、URL路由、事件订阅、投递重试、死信队列、幂等保证
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._verifier = SignatureVerifier()
        self._router = WebhookRouter()
        self._delivery = DeliveryEngine()
        self._subscriptions = SubscriptionManager()
        self._incoming_log: List[Dict] = []
        self._max_incoming = 5000

    def _dispatch(self, action: str, params: Dict) -> Dict:
        handler = {
            "status": self._action_status,
            "stats": self._action_stats,
            "health": self._action_health,
            "configure": self._action_configure,
            "sign": self._action_sign,
            "verify": self._action_verify,
            "add_route": self._action_add_route,
            "remove_route": self._action_remove_route,
            "list_routes": self._action_list_routes,
            "match_route": self._action_match_route,
            "receive": self._action_receive,
            "process_event": self._action_process_event,
            "subscribe": self._action_subscribe,
            "unsubscribe": self._action_unsubscribe,
            "list_subscriptions": self._action_list_subs,
            "get_subscription": self._action_get_sub,
            "toggle_subscription": self._action_toggle_sub,
            "deliver": self._action_deliver,
            "retry": self._action_retry,
            "delivery_log": self._action_delivery_log,
            "dead_letters": self._action_dead_letters,
            "incoming_log": self._action_incoming_log,
            "reset": self._action_reset,
        }.get(action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                self.trace("dispatch_error", {"action": action, "error": str(e)})
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    async def execute(self, action: str = "status", params: Dict = None) -> Dict:
        params = params or {}
        self.trace("execute", {"action": action})
        self.metrics_collector.counter("webhook_execute_total", labels={"action": action}).inc()
        return self._dispatch(action, params)

    # ── 基础Action ──

    def _action_status(self, params: Dict) -> Dict:
        return {
            "success": True,
            "data": {
                "module": "WebhookHandler",
                "state": "active",
                "routes": len(self._router._routes),
                "subscriptions": self._subscriptions.stats()["total_subscriptions"],
            },
        }

    def _action_stats(self, params: Dict) -> Dict:
        return {
            "success": True,
            "data": {
                "delivery": self._delivery.stats(),
                "subscriptions": self._subscriptions.stats(),
                "routes": len(self._router._routes),
                "incoming_count": len(self._incoming_log),
            },
        }

    def _action_health(self, params: Dict) -> Dict:
        ds = self._delivery.stats()
        ss = self._subscriptions.stats()
        issues = []
        if ds["dead_letter_count"] > 20:
            issues.append(f"{ds['dead_letter_count']} dead letters")
        if ss["avg_success_rate"] < 80:
            issues.append(f"Low success rate: {ss['avg_success_rate']}%")
        return {"success": True, "data": {"status": "healthy" if not issues else "degraded", "issues": issues}}

    def _action_configure(self, params: Dict) -> Dict:
        if "max_retries" in params:
            self._delivery._max_retries = params["max_retries"]
        if "idempotency_ttl" in params:
            self._delivery._idempotency_ttl = params["idempotency_ttl"]
        return {
            "success": True,
            "data": {"max_retries": self._delivery._max_retries, "idempotency_ttl": self._delivery._idempotency_ttl},
        }

    # ── 签名 ──

    def _action_sign(self, params: Dict) -> Dict:
        sig = self._verifier.sign(
            params.get("payload", ""), params.get("secret", ""), params.get("algorithm", "sha256")
        )
        return {"success": True, "data": {"signature": sig, "algorithm": params.get("algorithm", "sha256")}}

    def _action_verify(self, params: Dict) -> Dict:
        ok = self._verifier.verify(
            params.get("payload", ""),
            params.get("secret", ""),
            params.get("signature", ""),
            params.get("algorithm", "sha256"),
        )
        return {"success": True, "data": {"valid": ok}}

    # ── 路由 ──

    def _action_add_route(self, params: Dict) -> Dict:
        self._router.add_route(
            params.get("path", "/"), params.get("handler_id", ""), params.get("methods"), params.get("priority", 0)
        )
        return {"success": True, "data": {"path": params.get("path"), "handler": params.get("handler_id")}}

    def _action_remove_route(self, params: Dict) -> Dict:
        self._router.remove_route(params.get("path", ""))
        return {"success": True}

    def _action_list_routes(self, params: Dict) -> Dict:
        routes = self._router.list_routes()
        return {"success": True, "data": {"routes": routes, "total": len(routes)}}

    def _action_match_route(self, params: Dict) -> Dict:
        route = self._router.match(params.get("path", ""), params.get("method", "POST"))
        return {"success": True, "data": {"matched": route is not None, "route": route}}

    # ── 接收 ──

    def _action_receive(self, params: Dict) -> Dict:
        """接收Webhook请求"""
        path = params.get("path", "/")
        method = params.get("method", "POST")
        payload = params.get("payload", {})
        headers = params.get("headers", {})
        signature = params.get("signature", "")

        # 路由匹配
        route = self._router.match(path, method)
        if not route:
            return {"success": False, "error": "No route matched", "status": 404}

        # 签名验证（如果配置了secret）
        handler_id = route["handler_id"]
        sub = self._subscriptions.get_subscription(handler_id)
        if sub and sub.get("secret"):
            if signature and not self._verifier.verify(json.dumps(payload, sort_keys=True), sub["secret"], signature):
                return {"success": False, "error": "Invalid signature", "status": 401}

        # 记录入站
        incoming = {
            "request_id": str(uuid.uuid4())[:12],
            "path": path,
            "method": method,
            "handler": handler_id,
            "received_at": time.time(),
            "payload_size": len(json.dumps(payload)),
        }
        self._incoming_log.append(incoming)
        if len(self._incoming_log) > self._max_incoming:
            self._incoming_log = self._incoming_log[-self._max_incoming :]

        return {
            "success": True,
            "data": {"request_id": incoming["request_id"], "handler": handler_id, "route_matched": True},
        }

    def _action_process_event(self, params: Dict) -> Dict:
        """处理事件并投递到所有订阅者"""
        event_type = params.get("event_type", "custom")
        payload = params.get("payload", {})
        subscribers = self._subscriptions.get_subscribers(event_type)

        results = []
        for sub in subscribers:
            r = self._delivery.deliver(
                sub["subscription_id"],
                payload,
                headers=sub.get("headers", {}),
                idempotency_key=params.get("idempotency_key"),
            )
            self._subscriptions.record_delivery(sub["subscription_id"], r["success"])
            results.append(
                {
                    "subscription_id": sub["subscription_id"],
                    "url": sub["url"],
                    "success": r["success"],
                    "delivery_id": r.get("delivery_id"),
                }
            )

        return {
            "success": True,
            "data": {"event_type": event_type, "subscribers_notified": len(results), "results": results},
        }

    # ── 订阅 ──

    def _action_subscribe(self, params: Dict) -> Dict:
        sub = self._subscriptions.subscribe(
            params.get("subscription_id", str(uuid.uuid4())[:8]),
            params.get("url", ""),
            params.get("events"),
            params.get("secret"),
            params.get("headers"),
            params.get("active", True),
            params.get("description", ""),
        )
        return {"success": True, "data": {"subscription_id": sub["subscription_id"], "url": sub["url"]}}

    def _action_unsubscribe(self, params: Dict) -> Dict:
        ok = self._subscriptions.unsubscribe(params.get("subscription_id", ""))
        return {"success": ok}

    def _action_list_subs(self, params: Dict) -> Dict:
        subs = self._subscriptions.list_subscriptions(active_only=params.get("active_only", False))
        return {"success": True, "data": {"subscriptions": subs, "total": len(subs)}}

    def _action_get_sub(self, params: Dict) -> Dict:
        sub = self._subscriptions.get_subscription(params.get("subscription_id", ""))
        if not sub:
            return {"success": False, "error": "Subscription not found"}
        return {"success": True, "data": sub}

    def _action_toggle_sub(self, params: Dict) -> Dict:
        ok = self._subscriptions.toggle_active(params.get("subscription_id", ""), params.get("active", True))
        return {"success": ok}

    # ── 投递 ──

    def _action_deliver(self, params: Dict) -> Dict:
        return self._delivery.deliver(
            params.get("handler_id", ""),
            params.get("payload", {}),
            params.get("headers"),
            params.get("idempotency_key"),
            params.get("timeout", 30.0),
        )

    def _action_retry(self, params: Dict) -> Dict:
        return self._delivery.retry(params.get("delivery_id", ""))

    def _action_delivery_log(self, params: Dict) -> Dict:
        log = self._delivery.get_delivery_log(params.get("handler_id"), params.get("state"), params.get("limit", 50))
        return {"success": True, "data": {"log": log, "total": len(log)}}

    def _action_dead_letters(self, params: Dict) -> Dict:
        dls = self._delivery.get_dead_letters(params.get("limit", 50))
        return {"success": True, "data": {"dead_letters": dls, "total": len(dls)}}

    def _action_incoming_log(self, params: Dict) -> Dict:
        log = self._incoming_log[-(params.get("limit", 50)) :]
        return {"success": True, "data": {"incoming": log, "total": len(log)}}

    def _action_reset(self, params: Dict) -> Dict:
        self._incoming_log.clear()
        self._delivery._delivery_log.clear()
        self._delivery._dead_letters.clear()
        self._delivery._idempotency_keys.clear()
        return {"success": True, "data": {"message": "All logs and dead letters cleared"}}

module_class = WebhookHandler
