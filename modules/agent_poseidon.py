"""
AUTO-EVO-AI V0.1 — Poseidon AI智能体
Grade: A (生产级) | Category: AI智能体
职责：流量管理、负载均衡、限流熔断、服务发现、网关策略
"""

__module_meta__ = {
    "id": "agent-poseidon",
    "name": "Agent Poseidon",
    "version": "1.0.0",
    "group": "agent",
    "inputs": [
        {"name": "path_prefix", "type": "string", "required": True, "description": ""},
        {"name": "upstream", "type": "string", "required": True, "description": ""},
        {"name": "strategy", "type": "string", "required": True, "description": ""},
        {"name": "rate_limit", "type": "string", "required": True, "description": ""},
        {"name": "host", "type": "string", "required": True, "description": ""},
        {"name": "port", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "event", "config": {"on": "agent_poseidon.task.request"}}],
    "depends_on": [],
    "tags": ["manager", "multi-agent", "agent"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — Poseidon AI智能体 Grade: A (生产级) | Category: AI智能体",
}

import os
import asyncio
import time
import time as tmod
import logging
from typing import Any, Dict, List, Optional
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
logger = logging.getLogger("agent_poseidon")

class LBStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONN = "least_connections"
    RANDOM = "random"

class RouteRule:
    """路由规则"""

    def __init__(
        self, path_prefix: str, upstream: str, strategy: LBStrategy = LBStrategy.ROUND_ROBIN, rate_limit: int = 1000
    ):
        self.path_prefix = path_prefix
        self.upstream = upstream
        self.strategy = strategy
        self.rate_limit = rate_limit
        self.request_count: int = 0
        self.error_count: int = 0
        self.created_at = time.time()

class BackendInstance:
    """后端实例"""

    def __init__(self, host: str, port: int, weight: int = 1, healthy: bool = True):
        self.host = host
        self.port = port
        self.weight = weight
        self.healthy = healthy
        self.connections: int = 0
        self.requests: int = 0
        self.errors: int = 0

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

class AgentPoseidonManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Poseidon智能体 - 流量管理与网关"""

    MODULE_ID = "agent_poseidon"
    MODULE_NAME = "Poseidon智能体"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._routes: Dict[str, RouteRule] = {}
        self._backends: Dict[str, List[BackendInstance]] = {}
        self._rr_index: Dict[str, int] = {}
        # 熔断器状态（每个upstream独立）
        self._circuit_states: Dict[str, Dict] = {}
        self._circuit_threshold: int = 5
        self._circuit_timeout: float = 30.0
        # 健康检查
        self._health_history: Dict[str, List[Dict]] = {}
        self._health_check_interval: float = 10.0
        self._last_health_check: float = 0.0
        # 限流计数器
        self._rl_counters: Dict[str, Dict] = {}
        # 连接池管理
        self._max_connections_per_backend: int = 100
        # 请求日志
        self._request_log: List[Dict] = []
        self._max_request_log: int = 10000

    def initialize(self) -> None:
        try:
            self._routes["/api/"] = RouteRule("/api/", "default", LBStrategy.ROUND_ROBIN, 1000)
            self._routes["/api/auth/"] = RouteRule("/api/auth/", "auth-service", LBStrategy.WEIGHTED, 500)
            self._routes["/api/data/"] = RouteRule("/api/data/", "data-service", LBStrategy.LEAST_CONN, 2000)
            self._routes["/api/modules/"] = RouteRule("/api/modules/", "module-service", LBStrategy.ROUND_ROBIN, 1500)
            self._routes["/api/execute"] = RouteRule("/api/execute", "exec-service", LBStrategy.WEIGHTED, 300)
            self._backends["default"] = [BackendInstance("127.0.0.1", 8100), BackendInstance("127.0.0.1", 8101)]
            self._backends["auth-service"] = [
                BackendInstance("127.0.0.1", 8200, weight=3),
                BackendInstance("127.0.0.1", 8201, weight=2),
            ]
            self._backends["data-service"] = [BackendInstance("127.0.0.1", 8300, weight=5)]
            self._backends["module-service"] = [
                BackendInstance("127.0.0.1", 8400, weight=3),
                BackendInstance("127.0.0.1", 8401, weight=2),
            ]
            self._backends["exec-service"] = [BackendInstance("127.0.0.1", 8500, weight=5)]
            # 初始化熔断器
            for upstream in self._backends:
                self._circuit_states[upstream] = {"state": "closed", "failures": 0, "last_failure": 0, "open_count": 0}
            if self._audit:
                self._audit.log("poseidon_initialized", {"routes": len(self._routes), "backends": len(self._backends)})
            metrics_collector.gauge("poseidon_routes_total", len(self._routes))
            metrics_collector.gauge("poseidon_backends_total", sum(len(v) for v in self._backends.values()))
            self.stats.success_count += 1
            logger.info(
                f"Poseidon智能体初始化完成 | {len(self._routes)}路由 | {sum(len(v) for v in self._backends.values())}后端"
            )
        except Exception as e:
            logger.error(f"Poseidon初始化失败: {e}")
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
            if action == "route_request":
                path = params.get("path", "/")
                result = self._route(path)
                ok = True
                return {"success": True, "result": result}

            elif action == "add_route":
                prefix = params.get("prefix")
                upstream = params.get("upstream")
                strategy = params.get("strategy", "round_robin")
                rate_limit = params.get("rate_limit", 1000)
                if not prefix or not upstream:
                    return {"success": False, "error": "Missing: prefix, upstream"}
                self._routes[prefix] = RouteRule(prefix, upstream, LBStrategy(strategy), rate_limit)
                ok = True
                return {"success": True, "result": {"prefix": prefix, "upstream": upstream, "strategy": strategy}}

            elif action == "add_backend":
                upstream = params.get("upstream")
                host = params.get("host")
                port = params.get("port")
                weight = params.get("weight", 1)
                if not all([upstream, host, port]):
                    return {"success": False, "error": "Missing: upstream, host, port"}
                if upstream not in self._backends:
                    self._backends[upstream] = []
                inst = BackendInstance(host, int(port), weight)
                self._backends[upstream].append(inst)
                ok = True
                return {"success": True, "result": {"upstream": upstream, "address": inst.address}}

            elif action == "set_health":
                upstream = params.get("upstream")
                host = params.get("host")
                port = params.get("port")
                healthy = params.get("healthy", True)
                for inst in self._backends.get(upstream, []):
                    if inst.host == host and inst.port == int(port or 0):
                        inst.healthy = healthy
                        ok = True
                        return {"success": True, "result": {"address": inst.address, "healthy": healthy}}
                return {"success": False, "error": "Backend not found"}

            elif action == "get_routes":
                return {
                    "success": True,
                    "result": [
                        {
                            "prefix": r.path_prefix,
                            "upstream": r.upstream,
                            "strategy": r.strategy.value,
                            "rate_limit": r.rate_limit,
                            "requests": r.request_count,
                        }
                        for r in self._routes.values()
                    ],
                }

            elif action == "get_backends":
                upstream = params.get("upstream", "")
                result = {}
                targets = {upstream: self._backends.get(upstream)} if upstream else self._backends
                for name, insts in targets.items():
                    if insts:
                        cb = self._circuit_states.get(name, {})
                        result[name] = [
                            {
                                "address": i.address,
                                "weight": i.weight,
                                "healthy": i.healthy,
                                "connections": i.connections,
                                "requests": i.requests,
                                "errors": i.errors,
                            }
                            for i in insts
                        ]
                        result[name + "_circuit"] = cb
                return {"success": True, "result": result}

            elif action == "circuit_status":
                upstream = params.get("upstream", "")
                if upstream:
                    state = self._circuit_states.get(upstream, {})
                    return {"success": True, "result": {"upstream": upstream, **state}}
                return {"success": True, "result": {"all": dict(self._circuit_states)}}

            elif action == "reset_circuit":
                upstream = params.get("upstream", "")
                if not upstream:
                    return {"success": False, "error": "Missing: upstream"}
                if upstream in self._circuit_states:
                    self._circuit_states[upstream] = {
                        "state": "closed",
                        "failures": 0,
                        "last_failure": 0,
                        "open_count": 0,
                    }
                    ok = True
                    return {"success": True, "result": {"upstream": upstream, "state": "closed"}}
                return {"success": False, "error": "Upstream not found"}

            elif action == "health_check_backends":
                """主动健康检查所有后端"""
                results = {}
                for upstream, insts in self._backends.items():
                    results[upstream] = []
                    for inst in insts:
                        was_healthy = inst.healthy
                        # 模拟健康检查
                        inst.healthy = inst.errors < 10
                        if not was_healthy and inst.healthy:
                            logger.info(f"后端恢复健康 | {inst.address}")
                        results[upstream].append({"address": inst.address, "healthy": inst.healthy})
                self._last_health_check = time.time()
                metrics_collector.counter("poseidon_health_checks")
                ok = True
                return {"success": True, "result": results}

            elif action == "get_stats":
                total_requests = sum(r.request_count for r in self._routes.values())
                total_errors = sum(r.error_count for r in self._routes.values())
                open_cb = sum(1 for s in self._circuit_states.values() if s.get("state") == "open")
                total_conns = sum(i.connections for v in self._backends.values() for i in v)
                return {
                    "success": True,
                    "result": {
                        "routes": len(self._routes),
                        "backends": sum(len(v) for v in self._backends.values()),
                        "total_requests": total_requests,
                        "total_errors": total_errors,
                        "open_circuits": open_cb,
                        "active_connections": total_conns,
                        "request_log_size": len(self._request_log),
                    },
                }

            elif action == "remove_route":
                prefix = params.get("prefix", "")
                if not prefix or prefix not in self._routes:
                    return {"success": False, "error": "Route not found"}
                del self._routes[prefix]
                ok = True
                return {"success": True, "result": {"removed": prefix}}

            elif action == "remove_backend":
                upstream = params.get("upstream", "")
                host = params.get("host", "")
                port = params.get("port", 0)
                if not upstream:
                    return {"success": False, "error": "Missing: upstream"}
                insts = self._backends.get(upstream, [])
                self._backends[upstream] = [i for i in insts if not (i.host == host and i.port == int(port))]
                ok = True
                return {
                    "success": True,
                    "result": {"removed": f"{host}:{port}", "remaining": len(self._backends.get(upstream, []))},
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        total_backends = sum(len(v) for v in self._backends.values())
        unhealthy = sum(1 for v in self._backends.values() for i in v if not i.healthy)
        open_cb = sum(1 for s in self._circuit_states.values() if s.get("state") == "open")
        total_conns = sum(i.connections for v in self._backends.values() for i in v)
        metrics_collector.gauge("poseidon_routes_total", len(self._routes))
        metrics_collector.gauge("poseidon_backends_total", total_backends)
        metrics_collector.gauge("poseidon_unhealthy_backends", unhealthy)
        metrics_collector.gauge("poseidon_open_circuits", open_cb)
        metrics_collector.gauge("poseidon_active_connections", total_conns)
        return {
            "status": "healthy" if unhealthy == 0 and open_cb == 0 else "degraded",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "routes": len(self._routes),
            "backends_total": total_backends,
            "backends_unhealthy": unhealthy,
            "open_circuits": open_cb,
            "active_connections": total_conns,
        }

    def shutdown(self) -> None:
        summary = {"routes": len(self._routes), "backends": sum(len(v) for v in self._backends.values())}
        self._rr_index.clear()
        self._circuit_states.clear()
        self._health_history.clear()
        self._rl_counters.clear()
        self._request_log.clear()
        if self._audit:

            def get_backend_health_summary(self) -> Dict[str, Any]:
                """获取后端健康概览：各后端可用率、平均延迟、熔断状态"""

        backends = self._backends if hasattr(self, "_backends") else {}
        circuits = self._circuit_states if hasattr(self, "_circuit_states") else {}
        summary = []
        for name, instances in backends.items():
            healthy = sum(1 for inst in instances if getattr(inst, "healthy", True))
            total = len(instances)
            cb_state = circuits.get(name, "closed")
            summary.append(
                {
                    "backend": name,
                    "instances": total,
                    "healthy": healthy,
                    "availability": round(healthy / max(total, 1), 2),
                    "circuit_state": cb_state,
                }
            )
        return {
            "backends": summary,
            "total_backends": len(backends),
            "healthy_backends": sum(1 for b in summary if b["availability"] >= 0.5),
        }
        self.audit("poseidon_shutdown", summary)
        logger.info("Poseidon智能体已关闭")

    def _route(self, path: str) -> Dict:
        """路由请求到后端（含熔断/限流/连接池检查）"""
        matched_rule = None
        for prefix, rule in self._routes.items():
            if path.startswith(prefix):
                if matched_rule is None or len(prefix) > len(matched_rule.path_prefix):
                    matched_rule = rule
        if not matched_rule:
            return {"status": "no_route", "path": path}
        matched_rule.request_count += 1
        upstream = matched_rule.upstream

        # 熔断器检查
        cb = self._circuit_states.get(upstream, {})
        if cb.get("state") == "open":
            last = cb.get("last_failure", 0)
            if time.time() - last < self._circuit_timeout:
                metrics_collector.counter("poseidon_circuit_rejected")
                return {"status": "circuit_open", "upstream": upstream}
            cb["state"] = "half_open"
            cb["failures"] = 0
            logger.info(f"熔断器半开 | upstream={upstream}")

        # 限流检查
        rl_key = upstream
        counter = self._rl_counters.get(rl_key)
        now = time.time()
        if counter is None:
            counter = {"window_start": now, "count": 0}
            self._rl_counters[rl_key] = counter
        if now - counter["window_start"] >= 60:
            counter["window_start"] = now
            counter["count"] = 0
        counter["count"] += 1
        if counter["count"] > matched_rule.rate_limit:
            metrics_collector.counter("poseidon_rate_limited")
            return {"status": "rate_limited", "upstream": upstream, "limit": matched_rule.rate_limit}

        instances = [i for i in self._backends.get(upstream, []) if i.healthy]
        if not instances:
            return {"status": "no_healthy_backend", "upstream": upstream}
        selected = self._select(upstream, instances, matched_rule.strategy)
        # 连接池检查
        if selected.connections >= self._max_connections_per_backend:
            return {"status": "max_connections", "backend": selected.address, "max": self._max_connections_per_backend}
        selected.requests += 1
        selected.connections += 1
        # 熔断器恢复
        if cb.get("state") == "half_open":
            cb["state"] = "closed"
            logger.info(f"熔断器恢复 | upstream={upstream}")
        # 记录请求日志
        self._request_log.append({"path": path, "upstream": upstream, "backend": selected.address, "time": now})
        if len(self._request_log) > self._max_request_log:
            self._request_log = self._request_log[-self._max_request_log // 2 :]
        metrics_collector.counter("poseidon_requests_routed")
        metrics_collector.gauge(f"poseidon_backend_{hash(upstream) % 10000}_conns", selected.connections)
        self.stats.success_count += 1
        return {
            "status": "routed",
            "path": path,
            "upstream": upstream,
            "backend": selected.address,
            "strategy": matched_rule.strategy.value,
            "connections": selected.connections,
        }

    def _record_failure(self, upstream: str, backend_addr: str, error: str) -> None:
        """记录失败并更新熔断器"""
        cb = self._circuit_states.get(upstream)
        if cb:
            cb["failures"] = cb.get("failures", 0) + 1
            cb["last_failure"] = time.time()
            if cb["failures"] >= self._circuit_threshold:
                cb["state"] = "open"
                cb["open_count"] = cb.get("open_count", 0) + 1
                logger.warning(f"熔断器打开 | upstream={upstream} | open_count={cb['open_count']}")
                metrics_collector.counter("poseidon_circuit_opened")
        for inst in self._backends.get(upstream, []):
            if inst.address == backend_addr:
                inst.errors += 1
                inst.connections = max(0, inst.connections - 1)
                if inst.errors >= 10:
                    inst.healthy = False
                    logger.warning(f"后端不健康 | {inst.address} | errors={inst.errors}")
                break
        if self._audit:
            self._audit.log("route_failure", {"upstream": upstream, "backend": backend_addr, "error": error[:200]})

    def release_connection(self, upstream: str, backend_addr: str) -> None:
        """释放后端连接"""
        for inst in self._backends.get(upstream, []):
            if inst.address == backend_addr:
                inst.connections = max(0, inst.connections - 1)
                break
        metrics_collector.gauge(
            f"poseidon_backend_{hash(upstream) % 10000}_conns",
            sum(i.connections for i in self._backends.get(upstream, [])),
        )

    def batch_route(self, paths: List[str]) -> List[Dict]:
        """批量路由多个路径"""
        results = []
        for path in paths:
            results.append(self._route(path))
        routed = sum(1 for r in results if r.get("status") == "routed")
        metrics_collector.histogram("poseidon_batch_route", len(paths))
        return {"total": len(paths), "routed": routed, "failed": len(paths) - routed, "results": results}

    def get_top_routes(self, n: int = 10) -> List[Dict]:
        """获取请求量最高的路由"""
        sorted_routes = sorted(self._routes.values(), key=lambda r: r.request_count, reverse=True)
        return [
            {
                "prefix": r.path_prefix,
                "upstream": r.upstream,
                "requests": r.request_count,
                "errors": r.error_count,
                "error_rate": round(r.error_count / max(r.request_count, 1), 4),
            }
            for r in sorted_routes[:n]
        ]

    def _select(self, upstream: str, instances: List[BackendInstance], strategy: LBStrategy) -> BackendInstance:
        if strategy == LBStrategy.ROUND_ROBIN:
            idx = self._rr_index.get(upstream, 0) % len(instances)
            self._rr_index[upstream] = idx + 1
            return instances[idx]
        elif strategy == LBStrategy.WEIGHTED:
            total_w = sum(i.weight for i in instances)
            if total_w == 0:
                return instances[0]
            import time as tmod

            r = (int(tmod.time()*1000000)%1000000/1000000) * total_w
            cum = 0
            for inst in instances:
                cum += inst.weight
                if r <= cum:
                    return inst
            return instances[-1]
        elif strategy == LBStrategy.LEAST_CONN:
            return min(instances, key=lambda i: i.connections)
        else:
            import time as tmod

            return (instances)[0]

module_class = AgentPoseidonManager
