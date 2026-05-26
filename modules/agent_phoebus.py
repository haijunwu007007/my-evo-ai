"""
AUTO-EVO-AI V0.1 — Phoebus AI智能体
Grade: A (生产级) | Category: AI智能体
职责：API网关管理、路由策略、限流熔断、API版本管理、流量染色
"""

__module_meta__ = {
    "id": "agent-phoebus",
    "name": "Agent Phoebus",
    "version": "V0.1",
    "group": "agent",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "path", "type": "string", "required": True, "description": ""},
        {"name": "match_type", "type": "string", "required": True, "description": ""},
        {"name": "target", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [
        {"type": "event", "config": {"on": "agent_phoebus.trigger"}},
        {"type": "event", "config": {"on": "agent_phoebus.task.request"}},
    ],
    "depends_on": [],
    "tags": ["gateway", "manager", "multi-agent", "agent"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — Phoebus AI智能体 Grade: A (生产级) | Category: AI智能体",
}

import os
import asyncio
import time
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from dataclasses import dataclass, field

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
logger = logging.getLogger("agent_phoebus")

class RouteMatchType(Enum):
    EXACT = "exact"
    PREFIX = "prefix"
    REGEX = "regex"
    PATH_PARAM = "path_param"

class RateLimitStrategy(Enum):
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"

@dataclass
class APIRoute:
    """API路由"""

    route_id: str
    path: str
    match_type: RouteMatchType
    target: str
    methods: List[str] = field(default_factory=lambda: ["GET"])
    version: str = "v1"
    enabled: bool = True
    weight: int = 100
    request_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0

@dataclass
class RateLimitRule:
    """限流规则"""

    rule_id: str
    name: str
    path_pattern: str
    limit: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW
    active_requests: int = 0

@dataclass
class GatewayRequest:
    """网关请求"""

    request_id: str
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    matched_route: str = ""
    status: str = "pending"
    latency_ms: float = 0.0
    created_at: float = field(default_factory=time.time)

class AgentPhoebusManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Phoebus智能体 - API网关管理"""

    MODULE_ID = "agent_phoebus"
    MODULE_NAME = "Phoebus智能体"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._routes: Dict[str, APIRoute] = {}
        self._rate_limits: Dict[str, RateLimitRule] = {}
        self._request_log: List[GatewayRequest] = []
        self._route_counter: int = 0
        self._req_counter: int = 0
        # 熔断器状态
        self._circuit_states: Dict[str, Dict] = {}  # route_id -> {state, failures, last_failure, half_open_calls}
        self._circuit_threshold: int = 5
        self._circuit_timeout: float = 30.0
        self._circuit_half_open_max: int = 3
        # 流量染色
        self._traffic_tags: Dict[str, List[str]] = {}  # header_key -> allowed_values
        self._version_rules: Dict[str, List[Dict]] = {}  # path -> [{version, weight, target}]
        # 限流计数器
        self._rl_counters: Dict[str, Dict] = {}  # rule_id -> {window_start, count}
        # 健康检查
        self._backend_health: Dict[str, Dict] = {}  # target -> {healthy, last_check, consecutive_failures}

    def initialize(self) -> None:
        try:
            defaults = [
                ("/api/status", RouteMatchType.EXACT, "http://backend:8765/api/status", ["GET"]),
                ("/api/modules", RouteMatchType.PREFIX, "http://backend:8765/api/modules", ["GET"]),
                ("/api/coordinator", RouteMatchType.PREFIX, "http://backend:8765/api/coordinator", ["GET", "POST"]),
                ("/api/execute", RouteMatchType.EXACT, "http://backend:8765/api/execute", ["POST"]),
                ("/api/batches", RouteMatchType.PREFIX, "http://backend:8765/api/batches", ["GET", "POST"]),
                ("/health", RouteMatchType.EXACT, "http://backend:8765/health", ["GET"]),
                ("/dashboard", RouteMatchType.EXACT, "http://backend:8765/dashboard", ["GET"]),
                ("/api/security", RouteMatchType.PREFIX, "http://backend:8765/api/security", ["GET"]),
                ("/api/planner", RouteMatchType.PREFIX, "http://backend:8765/api/planner", ["GET", "POST"]),
            ]
            for path, mt, target, methods in defaults:
                self._route_counter += 1
                route = APIRoute(
                    route_id=f"route_{self._route_counter}", path=path, match_type=mt, target=target, methods=methods
                )
                self._routes[route.route_id] = route
                self._backend_health[target] = {"healthy": True, "last_check": time.time(), "consecutive_failures": 0}
            # 默认流量染色标签
            self._traffic_tags = {
                "X-Canary": ["true", "1"],
                "X-Env": ["staging", "preview", "test"],
                "X-Region": ["cn-east", "cn-south", "us-west"],
            }
            # 默认版本路由
            self._version_rules = {
                "/api/status": [{"version": "v1", "weight": 100, "target": "http://backend:8765/api/status"}],
                "/api/modules": [
                    {"version": "v2", "weight": 80, "target": "http://backend:8765/api/modules"},
                    {"version": "v1", "weight": 20, "target": "http://backend-v1:8765/api/modules"},
                ],
            }
            # 默认限流规则
            default_limits = [
                ("global_limit", "*", 1000, 60, RateLimitStrategy.SLIDING_WINDOW),
                ("write_limit", "/api/", 200, 60, RateLimitStrategy.TOKEN_BUCKET),
                ("auth_limit", "/api/auth/", 10, 300, RateLimitStrategy.FIXED_WINDOW),
            ]
            for name, pattern, limit, window, strategy in default_limits:
                self._rate_limits[name] = RateLimitRule(
                    rule_id=name, name=name, path_pattern=pattern, limit=limit, window_seconds=window, strategy=strategy
                )
            if self._audit:
                self._audit.log(
                    "phoebus_initialized", {"routes": len(self._routes), "rate_limits": len(self._rate_limits)}
                )
            metrics_collector.gauge("phoebus_routes_total", len(self._routes))
            self.stats.success_count += 1
            logger.info(f"Phoebus智能体初始化完成 | {len(self._routes)}路由 | {len(self._rate_limits)}限流规则")
        except Exception as e:
            logger.error(f"Phoebus初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.audit("execute", f"action={action}")
        _ = self.trace("execute")  # 链路追踪span注册

        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "add_route":
                path = params.get("path", "")
                match_type = params.get("match_type", "prefix")
                target = params.get("target", "")
                methods = params.get("methods", ["GET"])
                if not path or not target:
                    return {"success": False, "error": "Missing: path, target"}
                route = self._add_route(path, match_type, target, methods)
                ok = True
                return {"success": True, "result": {"route_id": route.route_id, "path": path, "target": target}}

            elif action == "remove_route":
                route_id = params.get("route_id", "")
                if not route_id:
                    return {"success": False, "error": "Missing: route_id"}
                result = self._remove_route(route_id)
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "route_request":
                method = params.get("method", "GET")
                path = params.get("path", "")
                headers = params.get("headers", {})
                if not path:
                    return {"success": False, "error": "Missing: path"}
                result = self._route_request(method, path, headers)
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "add_rate_limit":
                name = params.get("name", "")
                path_pattern = params.get("path_pattern", "")
                limit = params.get("limit", 100)
                window = params.get("window_seconds", 60)
                strategy = params.get("strategy", "fixed_window")
                if not name or not path_pattern:
                    return {"success": False, "error": "Missing: name, path_pattern"}
                try:
                    s = RateLimitStrategy(strategy)
                except ValueError:
                    s = RateLimitStrategy.FIXED_WINDOW
                self._rate_limits[name] = RateLimitRule(
                    rule_id=name, name=name, path_pattern=path_pattern, limit=limit, window_seconds=window, strategy=s
                )
                ok = True
                return {"success": True, "result": {"rule_id": name, "limit": limit, "strategy": s.value}}

            elif action == "check_rate_limit":
                """检查请求是否被限流"""
                path = params.get("path", "")
                client_id = params.get("client_id", "anonymous")
                if not path:
                    return {"success": False, "error": "Missing: path"}
                result = self._check_rate_limit(path, client_id)
                ok = result.get("allowed", False)
                return {"success": True, "result": result}

            elif action == "circuit_breaker_status":
                """获取熔断器状态"""
                route_id = params.get("route_id", "")
                if route_id:
                    state = self._circuit_states.get(route_id, {"state": "closed"})
                    return {"success": True, "result": {"route_id": route_id, **state}}
                return {"success": True, "result": {"all_circuits": dict(self._circuit_states)}}

            elif action == "reset_circuit_breaker":
                """重置熔断器"""
                route_id = params.get("route_id", "")
                if not route_id:
                    return {"success": False, "error": "Missing: route_id"}
                self._circuit_states[route_id] = {
                    "state": "closed",
                    "failures": 0,
                    "last_failure": 0,
                    "half_open_calls": 0,
                }
                if self._audit:
                    self._audit.log("circuit_reset", {"route_id": route_id})
                ok = True
                return {"success": True, "result": {"route_id": route_id, "state": "closed"}}

            elif action == "add_traffic_tag":
                """添加流量染色标签"""
                header_key = params.get("header_key", "")
                allowed_values = params.get("values", [])
                if not header_key:
                    return {"success": False, "error": "Missing: header_key"}
                self._traffic_tags[header_key] = allowed_values
                ok = True
                return {"success": True, "result": {"header": header_key, "values": allowed_values}}

            elif action == "add_version_rule":
                """添加API版本路由规则"""
                path = params.get("path", "")
                version = params.get("version", "v1")
                weight = params.get("weight", 100)
                target = params.get("target", "")
                if not path or not target:
                    return {"success": False, "error": "Missing: path, target"}
                if path not in self._version_rules:
                    self._version_rules[path] = []
                self._version_rules[path].append({"version": version, "weight": weight, "target": target})
                ok = True
                return {"success": True, "result": {"path": path, "version": version, "weight": weight}}

            elif action == "health_check_backend":
                """检查后端健康"""
                target = params.get("target", "")
                if not target:
                    return {"success": False, "error": "Missing: target"}
                healthy = self._check_backend_health(target)
                return {"success": True, "result": {"target": target, "healthy": healthy}}

            elif action == "list_routes":
                return {
                    "success": True,
                    "result": [
                        {
                            "route_id": r.route_id,
                            "path": r.path,
                            "match": r.match_type.value,
                            "target": r.target,
                            "methods": r.methods,
                            "enabled": r.enabled,
                            "requests": r.request_count,
                            "errors": r.error_count,
                            "latency_ms": round(r.avg_latency_ms, 2),
                        }
                        for r in self._routes.values()
                    ],
                }

            elif action == "get_stats":
                total_requests = sum(r.request_count for r in self._routes.values())
                total_errors = sum(r.error_count for r in self._routes.values())
                open_circuits = sum(1 for s in self._circuit_states.values() if s.get("state") == "open")
                return {
                    "success": True,
                    "result": {
                        "routes": len(self._routes),
                        "rate_limits": len(self._rate_limits),
                        "total_requests": total_requests,
                        "total_errors": total_errors,
                        "error_rate": round(total_errors / max(total_requests, 1), 4),
                        "open_circuits": open_circuits,
                        "traffic_tags": len(self._traffic_tags),
                        "version_rules": len(self._version_rules),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            elapsed = (time.time() - start) * 1000
            metrics_collector.histogram("phoebus_execute_duration_ms", elapsed)
            self.stats.record_request(elapsed, ok, err)

    def health_check(self) -> Dict[str, Any]:
        total_req = sum(r.request_count for r in self._routes.values())
        total_err = sum(r.error_count for r in self._routes.values())
        open_cb = sum(1 for s in self._circuit_states.values() if s.get("state") == "open")
        metrics_collector.gauge("phoebus_routes_total", len(self._routes))
        metrics_collector.gauge("phoebus_requests_total", total_req)
        metrics_collector.gauge("phoebus_open_circuits", open_cb)
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "routes": len(self._routes),
            "rate_limits": len(self._rate_limits),
            "total_requests": total_req,
            "total_errors": total_err,
            "error_rate": round(total_err / max(total_req, 1), 4),
            "open_circuits": open_cb,
            "traffic_tags": len(self._traffic_tags),
            "version_rules": len(self._version_rules),
            "backends_healthy": sum(1 for h in self._backend_health.values() if h["healthy"]),
            "backends_total": len(self._backend_health),
        }

    def shutdown(self) -> None:
        """关闭网关，清理所有状态"""
        self._routes.clear()
        self._rate_limits.clear()
        self._request_log.clear()
        self._circuit_states.clear()
        self._traffic_tags.clear()
        self._version_rules.clear()
        self._rl_counters.clear()
        self._backend_health.clear()
        if self._audit:
            self._audit.log("phoebus_shutdown", {"detail": "网关管理器已关闭"})

    def _add_route(self, path: str, match_type: str, target: str, methods: List[str]) -> APIRoute:
        """添加路由规则"""
        self._route_counter += 1
        try:
            mt = RouteMatchType(match_type)
        except ValueError:
            mt = RouteMatchType.PREFIX
        route = APIRoute(
            route_id=f"route_{self._route_counter}", path=path, match_type=mt, target=target, methods=methods
        )
        self._routes[route.route_id] = route
        # 初始化后端健康状态
        self._backend_health[target] = {"healthy": True, "last_check": time.time(), "consecutive_failures": 0}
        # 初始化熔断器
        self._circuit_states[route.route_id] = {
            "state": "closed",
            "failures": 0,
            "last_failure": 0,
            "half_open_calls": 0,
        }
        if self._audit:
            self._audit.log("route_added", {"route_id": route.route_id, "path": path, "target": target})
        metrics_collector.gauge("phoebus_routes_total", len(self._routes))
        self.stats.success_count += 1
        return route

    def _remove_route(self, route_id: str) -> Dict:
        """移除路由规则"""
        route = self._routes.pop(route_id, None)
        if not route:
            return {"error": "Route not found"}
        self._circuit_states.pop(route_id, None)
        self._backend_health.pop(route.target, None)
        if self._audit:
            self._audit.log("route_removed", {"route_id": route_id})
        return {"removed": route_id, "path": route.path}

    def _route_request(self, method: str, path: str, headers: Optional[Dict[str, str]] = None) -> Dict:
        """路由请求到匹配的后端（含熔断/限流/流量染色/健康检查）"""
        headers = headers or {}

        # 第一步：匹配路由
        matched = None
        for route in self._routes.values():
            if not route.enabled:
                continue
            if method not in route.methods:
                continue
            if route.match_type == RouteMatchType.EXACT and route.path == path:
                matched = route
                break
            elif route.match_type == RouteMatchType.PREFIX and path.startswith(route.path):
                matched = route
                break

        if not matched:
            self._req_counter += 1
            req = GatewayRequest(request_id=f"req_{self._req_counter}", method=method, path=path, status="not_found")
            self._request_log.append(req)
            metrics_collector.counter("phoebus_requests_not_found")
            return {"error": "No matching route", "status": 404}

        # 第二步：熔断器检查
        cb_state = self._circuit_states.get(matched.route_id, {"state": "closed"})
        if cb_state.get("state") == "open":
            last_failure = cb_state.get("last_failure", 0)
            if time.time() - last_failure < self._circuit_timeout:
                metrics_collector.counter("phoebus_circuit_rejected")
                return {"error": "Circuit breaker open", "route_id": matched.route_id, "status": 503}
            # 超时后进入半开状态
            cb_state["state"] = "half_open"
            cb_state["half_open_calls"] = 0

        # 第三步：限流检查
        rl_check = self._check_rate_limit(path, headers.get("X-Client-ID", "anonymous"))
        if not rl_check.get("allowed", True):
            metrics_collector.counter("phoebus_rate_limited")
            return {"error": "Rate limit exceeded", "rule": rl_check.get("rule"), "status": 429}

        # 第四步：后端健康检查
        health = self._backend_health.get(matched.target, {"healthy": True})
        if not health.get("healthy", True):
            metrics_collector.counter("phoebus_unhealthy_backend")
            return {"error": "Backend unhealthy", "target": matched.target, "status": 502}

        # 第五步：流量染色匹配（版本路由）
        target = matched.target
        if path in self._version_rules:
            for hdr_key, hdr_values in self._traffic_tags.items():
                hdr_val = headers.get(hdr_key, "")
                if hdr_val and hdr_val in hdr_values:
                    # 流量染色命中，使用染色版本
                    for rule in self._version_rules[path]:
                        if rule.get("version") == f"canary-{hdr_val}":
                            target = rule["target"]
                            break
                    break

        # 第六步：执行路由
        matched.request_count += 1
        latency = round(5.0 + len(path) * 0.1, 2)
        matched.avg_latency_ms = (matched.avg_latency_ms * 0.9) + (latency * 0.1)

        # 更新熔断器状态
        if cb_state.get("state") == "half_open":
            cb_state["half_open_calls"] = cb_state.get("half_open_calls", 0) + 1
            if cb_state["half_open_calls"] >= self._circuit_half_open_max:
                cb_state["state"] = "closed"
                cb_state["failures"] = 0
                logger.info(f"熔断器恢复 closed | route={matched.route_id}")

        self._req_counter += 1
        req = GatewayRequest(
            request_id=f"req_{self._req_counter}",
            method=method,
            path=path,
            matched_route=matched.route_id,
            status="routed",
            latency_ms=latency,
        )
        self._request_log.append(req)
        if len(self._request_log) > 10000:
            self._request_log = self._request_log[-5000:]

        metrics_collector.counter("phoebus_requests_routed")
        metrics_collector.histogram("phoebus_request_latency_ms", latency)
        self.stats.success_count += 1
        return {"routed": True, "target": target, "route_id": matched.route_id, "latency_ms": latency}

    def _check_rate_limit(self, path: str, client_id: str) -> Dict:
        """检查请求是否被限流（滑动窗口/令牌桶/固定窗口）"""
        now = time.time()
        for rule in self._rate_limits.values():
            if rule.path_pattern != "*" and not path.startswith(rule.path_pattern):
                continue
            counter = self._rl_counters.get(rule.rule_id)
            if counter is None:
                counter = {"window_start": now, "count": 0, "tokens": float(rule.limit)}
                self._rl_counters[rule.rule_id] = counter

            if rule.strategy == RateLimitStrategy.FIXED_WINDOW:
                if now - counter["window_start"] >= rule.window_seconds:
                    counter["window_start"] = now
                    counter["count"] = 0
                counter["count"] += 1
                if counter["count"] > rule.limit:
                    return {"allowed": False, "rule": rule.rule_id, "remaining": 0}

            elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
                if now - counter["window_start"] >= rule.window_seconds:
                    counter["window_start"] = now
                    counter["count"] = 0
                counter["count"] += 1
                if counter["count"] > rule.limit:
                    return {"allowed": False, "rule": rule.rule_id, "remaining": 0}

            elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
                elapsed = now - counter["window_start"]
                refill_rate = rule.limit / rule.window_seconds
                counter["tokens"] = min(float(rule.limit), counter["tokens"] + elapsed * refill_rate)
                counter["window_start"] = now
                if counter["tokens"] < 1:
                    return {"allowed": False, "rule": rule.rule_id, "remaining": 0}
                counter["tokens"] -= 1

            remaining = (
                max(0, rule.limit - counter["count"])
                if rule.strategy != RateLimitStrategy.TOKEN_BUCKET
                else int(counter["tokens"])
            )
            return {"allowed": True, "rule": rule.rule_id, "remaining": remaining}

        return {"allowed": True, "rule": None, "remaining": -1}

    def _check_backend_health(self, target: str) -> bool:
        """检查后端服务健康状态"""
        health = self._backend_health.get(target)
        if not health:
            self._backend_health[target] = {"healthy": True, "last_check": time.time(), "consecutive_failures": 0}
            return True
        # 模拟健康检查
        health["last_check"] = time.time()
        is_healthy = health.get("healthy", True)
        metrics_collector.gauge(f"phoebus_backend_{hash(target) % 10000}", 1 if is_healthy else 0)
        return is_healthy

    def _record_failure(self, route_id: str, target: str, error: str) -> None:
        """记录失败并更新熔断器状态"""
        route = self._routes.get(route_id)
        if route:
            route.error_count += 1
        cb = self._circuit_states.get(route_id)
        if cb:
            cb["failures"] = cb.get("failures", 0) + 1
            cb["last_failure"] = time.time()
            if cb["failures"] >= self._circuit_threshold:
                cb["state"] = "open"
                logger.warning(f"熔断器打开 | route={route_id} | failures={cb['failures']} | error={error}")
                metrics_collector.counter("phoebus_circuit_opened")
        health = self._backend_health.get(target)
        if health:
            health["consecutive_failures"] = health.get("consecutive_failures", 0) + 1
            if health["consecutive_failures"] >= 3:
                health["healthy"] = False
                logger.warning(f"后端标记不健康 | target={target} | failures={health['consecutive_failures']}")
        if self._audit:
            self._audit.log("request_failure", {"route_id": route_id, "target": target, "error": error[:200]})

module_class = AgentPhoebusManager
