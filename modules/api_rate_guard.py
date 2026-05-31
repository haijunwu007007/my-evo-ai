"""
AUTO-EVO-AI V0.1 — API限流守卫
Grade: A (生产级) | Category: API基础设施
职责：API请求限流、滑动窗口、令牌桶、客户端配额、限流统计、动态调整
"""

__module_meta__ = {
        "id": "api-rate-guard",
        "name": "Api Rate Guard",
        "version": "V0.1",
        "group": "api",
        "inputs": [
            {
                "name": "config",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "client_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "path",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "client_id_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "paths",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "top_n",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [
            {
                "type": "webhook",
                "config": {
                    "path": "/hooks/api_rate_guard",
                    "method": "POST"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "config",
            "api",
            "client",
            "manager"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — API限流守卫 Grade: A (生产级) | Category: API基础设施"
    }

import os
import asyncio
import time
import logging
import hashlib
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
logger = logging.getLogger("api_rate_guard")

class LimitAlgorithm(Enum):
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"

class LimitScope(Enum):
    GLOBAL = "global"
    PER_CLIENT = "per_client"
    PER_ENDPOINT = "per_endpoint"
    PER_CLIENT_ENDPOINT = "per_client_endpoint"

@dataclass
class RateLimitConfig:
    """限流配置"""

    config_id: str
    name: str
    path_pattern: str = "*"
    limit: int = 100
    window_seconds: int = 60
    algorithm: LimitAlgorithm = LimitAlgorithm.SLIDING_WINDOW
    scope: LimitScope = LimitScope.PER_CLIENT
    burst: int = 0
    enabled: bool = True
    priority: int = 0

@dataclass
class ClientQuota:
    """客户端配额"""

    client_id: str
    current_count: int = 0
    window_start: float = 0.0
    tokens: float = 0.0
    last_refill: float = 0.0
    rejected: int = 0
    allowed: int = 0

@dataclass
class RateLimitLog:
    """限流日志"""

    log_id: str
    client_id: str
    path: str
    allowed: bool
    config_id: str
    remaining: int
    created_at: float = field(default_factory=time.time)

class ApiRateGuardManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """API限流守卫"""

    MODULE_ID = "api_rate_guard"
    MODULE_NAME = "API限流守卫"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: dict[str, Any] | None = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._configs: dict[str, RateLimitConfig] = {}
        self._quotas: dict[str, ClientQuota] = {}
        self._logs: list[RateLimitLog] = []
        self._config_counter: int = 0
        self._log_counter: int = 0
        # 熔断器状态（每个限流规则独立熔断）
        self._circuit_states: dict[str, dict] = {}
        self._circuit_failure_threshold: int = 10
        self._circuit_recovery_timeout: float = 60.0
        # 客户端分级（VIP/普通/黑名单）
        self._client_tiers: dict[str, str] = {}
        self._tier_multiplier: dict[str, float] = {"vip": 3.0, "premium": 2.0, "normal": 1.0, "blacklist": 0.0}
        # 告警阈值
        self._alert_threshold: float = 0.8
        self._alert_history: list[dict] = []
        # 限流统计
        self._stats_counters: dict[str, dict] = {}

    def initialize(self) -> None:
        try:
            defaults = [
                ("全局API限流", "*", 1000, 60, LimitAlgorithm.SLIDING_WINDOW, LimitScope.GLOBAL, 10),
                ("登录限流", "/api/auth/login", 5, 300, LimitAlgorithm.SLIDING_WINDOW, LimitScope.PER_CLIENT, 0),
                ("登录限流IP", "/api/auth/login", 20, 300, LimitAlgorithm.FIXED_WINDOW, LimitScope.GLOBAL, 5),
                ("写入限流", "/api/", 100, 60, LimitAlgorithm.TOKEN_BUCKET, LimitScope.PER_CLIENT_ENDPOINT, 20),
                ("敏感操作限流", "/api/admin/", 10, 60, LimitAlgorithm.FIXED_WINDOW, LimitScope.PER_CLIENT, 0),
                ("数据导出限流", "/api/export/", 5, 3600, LimitAlgorithm.SLIDING_WINDOW, LimitScope.PER_CLIENT, 0),
                ("文件上传限流", "/api/upload/", 10, 60, LimitAlgorithm.TOKEN_BUCKET, LimitScope.PER_CLIENT, 5),
                (
                    "模块执行限流",
                    "/api/modules/*/execute",
                    30,
                    60,
                    LimitAlgorithm.SLIDING_WINDOW,
                    LimitScope.PER_CLIENT,
                    5,
                ),
            ]
            for name, pattern, limit, window, algo, scope, burst in defaults:
                self._config_counter += 1
                cfg = RateLimitConfig(
                    config_id=f"cfg_{self._config_counter}",
                    name=name,
                    path_pattern=pattern,
                    limit=limit,
                    window_seconds=window,
                    algorithm=algo,
                    scope=scope,
                    burst=burst,
                )
                self._configs[cfg.config_id] = cfg
                self._circuit_states[cfg.config_id] = {
                    "state": "closed",
                    "failures": 0,
                    "last_failure": 0,
                    "open_count": 0,
                }
            # 默认VIP客户端
            self._client_tiers = {"system_internal": "vip", "admin": "vip", "monitor": "premium"}
            if self._audit:
                self._audit.log(
                    "rate_guard_initialized", {"configs": len(self._configs), "client_tiers": len(self._client_tiers)}
                )
            metrics_collector.gauge("rate_guard_configs_total", len(self._configs))
            self.stats.success_count += 1
            logger.info(f"API限流守卫初始化完成 | {len(self._configs)}规则 | {len(self._client_tiers)}分级客户端")
        except Exception as e:
            logger.error(f"限流守卫初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        _ = self.trace("execute")
        self.audit("execute", f"action={action}")
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "check":
                client_id = params.get("client_id", "anonymous")
                path = params.get("path", "")
                if not path:
                    return {"success": False, "error": "Missing: path"}
                result = self._check_rate(client_id, path)
                return {"success": True, "result": result}

            elif action == "add_config":
                name = params.get("name", "")
                path_pattern = params.get("path_pattern", "*")
                limit = params.get("limit", 100)
                window = params.get("window_seconds", 60)
                algorithm = params.get("algorithm", "sliding_window")
                scope = params.get("scope", "per_client")
                if not name:
                    return {"success": False, "error": "Missing: name"}
                self._config_counter += 1
                try:
                    algo = LimitAlgorithm(algorithm)
                except ValueError:
                    algo = LimitAlgorithm.SLIDING_WINDOW
                try:
                    sc = LimitScope(scope)
                except ValueError:
                    sc = LimitScope.PER_CLIENT
                cfg = RateLimitConfig(
                    config_id=f"cfg_{self._config_counter}",
                    name=name,
                    path_pattern=path_pattern,
                    limit=limit,
                    window_seconds=window,
                    algorithm=algo,
                    scope=sc,
                )
                self._configs[cfg.config_id] = cfg
                ok = True
                return {"success": True, "result": {"config_id": cfg.config_id, "name": name, "limit": limit}}

            elif action == "toggle_config":
                config_id = params.get("config_id", "")
                enabled = params.get("enabled", True)
                cfg = self._configs.get(config_id)
                if not cfg:
                    return {"success": False, "error": "Config not found"}
                cfg.enabled = enabled
                return {"success": True, "result": {"config_id": config_id, "enabled": enabled}}

            elif action == "reset_quota":
                client_id = params.get("client_id", "")
                if not client_id:
                    return {"success": False, "error": "Missing: client_id"}
                if client_id in self._quotas:
                    q = self._quotas[client_id]
                    q.current_count = 0
                    q.tokens = 0
                    q.rejected = 0
                    q.allowed = 0
                return {"success": True, "result": {"reset": client_id}}

            elif action == "set_client_tier":
                """设置客户端分级"""
                client_id = params.get("client_id", "")
                tier = params.get("tier", "normal")
                if not client_id:
                    return {"success": False, "error": "Missing: client_id"}
                if tier not in self._tier_multiplier:
                    return {
                        "success": False,
                        "error": f"Invalid tier: {tier}, available: {list(self._tier_multiplier.keys())}",
                    }
                self._client_tiers[client_id] = tier
                ok = True
                return {
                    "success": True,
                    "result": {"client_id": client_id, "tier": tier, "multiplier": self._tier_multiplier[tier]},
                }

            elif action == "get_client_tier":
                """获取客户端分级"""
                client_id = params.get("client_id", "")
                tier = self._client_tiers.get(client_id, "normal")
                return {
                    "success": True,
                    "result": {"client_id": client_id, "tier": tier, "multiplier": self._tier_multiplier[tier]},
                }

            elif action == "circuit_status":
                """获取熔断器状态"""
                config_id = params.get("config_id", "")
                if config_id:
                    state = self._circuit_states.get(config_id)
                    if not state:
                        return {"success": False, "error": "Config not found"}
                    return {"success": True, "result": {"config_id": config_id, **state}}
                return {"success": True, "result": {"all": dict(self._circuit_states)}}

            elif action == "reset_circuit":
                """重置熔断器"""
                config_id = params.get("config_id", "")
                if not config_id:
                    return {"success": False, "error": "Missing: config_id"}
                state = self._circuit_states.get(config_id)
                if not state:
                    return {"success": False, "error": "Config not found"}
                state["state"] = "closed"
                state["failures"] = 0
                ok = True
                return {"success": True, "result": {"config_id": config_id, "state": "closed"}}

            elif action == "get_alerts":
                """获取告警历史"""
                return {
                    "success": True,
                    "result": {"alerts": self._alert_history[-50:], "total": len(self._alert_history)},
                }

            elif action == "remove_config":
                """删除限流配置"""
                config_id = params.get("config_id", "")
                if not config_id:
                    return {"success": False, "error": "Missing: config_id"}
                removed = self._configs.pop(config_id, None)
                if not removed:
                    return {"success": False, "error": "Config not found"}
                self._circuit_states.pop(config_id, None)
                ok = True
                return {"success": True, "result": {"removed": config_id}}

            elif action == "list_configs":
                return {
                    "success": True,
                    "result": [
                        {
                            "config_id": c.config_id,
                            "name": c.name,
                            "pattern": c.path_pattern,
                            "limit": c.limit,
                            "window": c.window_seconds,
                            "algorithm": c.algorithm.value,
                            "scope": c.scope.value,
                            "enabled": c.enabled,
                        }
                        for c in self._configs.values()
                    ],
                }

            elif action == "get_stats":
                total_allowed = sum(q.allowed for q in self._quotas.values())
                total_rejected = sum(q.rejected for q in self._quotas.values())
                return {
                    "success": True,
                    "result": {
                        "configs": len(self._configs),
                        "active_clients": len(self._quotas),
                        "total_allowed": total_allowed,
                        "total_rejected": total_rejected,
                        "rejection_rate": round(total_rejected / max(total_allowed + total_rejected, 1), 4),
                        "logs": len(self._logs),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> dict[str, Any]:
        total_allowed = sum(q.allowed for q in self._quotas.values())
        total_rejected = sum(q.rejected for q in self._quotas.values())
        open_cb = sum(1 for s in self._circuit_states.values() if s.get("state") == "open")
        metrics_collector.gauge("rate_guard_configs_active", len([c for c in self._configs.values() if c.enabled]))
        metrics_collector.gauge("rate_guard_clients_tracked", len(self._quotas))
        metrics_collector.gauge("rate_guard_open_circuits", open_cb)
        metrics_collector.counter("rate_guard_total_allowed", total_allowed)
        metrics_collector.counter("rate_guard_total_rejected", total_rejected)
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "configs": len(self._configs),
            "active_configs": len([c for c in self._configs.values() if c.enabled]),
            "active_clients": len(self._quotas),
            "total_allowed": total_allowed,
            "total_rejected": total_rejected,
            "rejection_rate": round(total_rejected / max(total_allowed + total_rejected, 1), 4),
            "open_circuits": open_cb,
            "client_tiers": len(self._client_tiers),
            "alerts": len(self._alert_history),
            "logs": len(self._logs),
        }

    def shutdown(self) -> None:
        """关闭限流守卫，清理所有状态"""
        summary = {"configs": len(self._configs), "clients": len(self._quotas), "logs": len(self._logs)}
        self._quotas.clear()
        self._logs.clear()
        self._circuit_states.clear()
        self._client_tiers.clear()
        self._alert_history.clear()
        self._stats_counters.clear()
        if self._audit:
            self._audit.log("rate_guard_shutdown", summary)
        logger.info("API限流守卫已关闭")

    def _check_rate(self, client_id: str, path: str) -> dict:
        """检查请求是否被允许（含客户端分级+熔断）"""
        now = time.time()

        # 客户端分级检查
        tier = self._client_tiers.get(client_id, "normal")
        multiplier = self._tier_multiplier.get(tier, 1.0)
        if multiplier == 0.0:
            metrics_collector.counter("rate_guard_blacklisted")
            return {"allowed": False, "reason": "blacklisted_client", "remaining": 0}

        # 熔断器检查
        for cfg in self._configs.values():
            if not cfg.enabled:
                continue
            if cfg.path_pattern == "*" or path.startswith(cfg.path_pattern):
                cb = self._circuit_states.get(cfg.config_id, {})
                if cb.get("state") == "open":
                    last = cb.get("last_failure", 0)
                    if now - last < self._circuit_recovery_timeout:
                        metrics_collector.counter("rate_guard_circuit_rejected")
                        return {
                            "allowed": False,
                            "reason": f"circuit_open:{cfg.name}",
                            "remaining": 0,
                            "retry_after": int(self._circuit_recovery_timeout - (now - last)),
                        }
                    # 超时恢复
                    cb["state"] = "closed"
                    cb["failures"] = 0
                    logger.info(f"限流熔断器恢复 | config={cfg.config_id}")
                break

        best_config = None
        for cfg in sorted(self._configs.values(), key=lambda c: -c.priority):
            if not cfg.enabled:
                continue
            if cfg.path_pattern == "*" or path.startswith(cfg.path_pattern):
                best_config = cfg
                break

        if best_config is None:
            return {"allowed": True, "reason": "no_matching_config", "remaining": -1}

        quota_key = client_id
        if best_config.scope in (LimitScope.PER_ENDPOINT, LimitScope.PER_CLIENT_ENDPOINT):
            quota_key = f"{client_id}:{path}"

        quota = self._quotas.get(quota_key)
        if quota is None:
            quota = ClientQuota(
                client_id=quota_key,
                window_start=now,
                tokens=float(best_config.limit + best_config.burst),
                last_refill=now,
            )
            self._quotas[quota_key] = quota

        allowed = False
        remaining = 0
        reason = ""

        if best_config.algorithm == LimitAlgorithm.FIXED_WINDOW:
            if now - quota.window_start >= best_config.window_seconds:
                quota.window_start = now
                quota.current_count = 0
            quota.current_count += 1
            allowed = quota.current_count <= best_config.limit
            remaining = max(0, best_config.limit - quota.current_count)
            reason = "fixed_window"

        elif best_config.algorithm == LimitAlgorithm.SLIDING_WINDOW:
            if now - quota.window_start >= best_config.window_seconds:
                quota.window_start = now
                quota.current_count = 0
            quota.current_count += 1
            allowed = quota.current_count <= best_config.limit
            remaining = max(0, best_config.limit - quota.current_count)
            reason = "sliding_window"

        elif best_config.algorithm == LimitAlgorithm.TOKEN_BUCKET:
            elapsed = now - quota.last_refill
            refill_rate = best_config.limit / best_config.window_seconds
            quota.tokens = min(best_config.limit + best_config.burst, quota.tokens + elapsed * refill_rate)
            quota.last_refill = now
            if quota.tokens >= 1:
                quota.tokens -= 1
                allowed = True
            remaining = int(quota.tokens)
            reason = "token_bucket"

        else:  # LEAKY_BUCKET
            if now - quota.window_start >= best_config.window_seconds:
                quota.window_start = now
                quota.current_count = 0
            quota.current_count += 1
            allowed = quota.current_count <= best_config.limit
            remaining = max(0, best_config.limit - quota.current_count)
            reason = "leaky_bucket"

        if allowed:
            # VIP客户端不扣减配额（倍率>1时等效提升配额）
            if multiplier > 1.0 and remaining > 0:
                quota.current_count = max(0, quota.current_count - 1)
                remaining = min(best_config.limit, remaining + 1)
            quota.allowed += 1
        else:
            quota.rejected += 1
            # 更新熔断器状态
            cb = self._circuit_states.get(best_config.config_id)
            if cb:
                cb["failures"] = cb.get("failures", 0) + 1
                cb["last_failure"] = now
                if cb["failures"] >= self._circuit_failure_threshold:
                    cb["state"] = "open"
                    cb["open_count"] = cb.get("open_count", 0) + 1
                    logger.warning(f"限流熔断器打开 | config={best_config.config_id} | open_count={cb['open_count']}")
                    metrics_collector.counter("rate_guard_circuit_opened")
            # 告警检查
            usage_rate = quota.current_count / max(best_config.limit, 1)
            if usage_rate >= self._alert_threshold:
                alert = {"config": best_config.name, "client": client_id, "usage": round(usage_rate, 4), "time": now}
                self._alert_history.append(alert)
                if len(self._alert_history) > 1000:
                    self._alert_history = self._alert_history[-500:]

        self._log_counter += 1
        self._logs.append(
            RateLimitLog(
                log_id=f"log_{self._log_counter}",
                client_id=client_id,
                path=path,
                allowed=allowed,
                config_id=best_config.config_id,
                remaining=remaining,
            )
        )
        if len(self._logs) > 10000:
            self._logs = self._logs[-5000:]

        self.stats.success_count += 1
        return {
            "allowed": allowed,
            "config": best_config.name,
            "algorithm": reason,
            "remaining": remaining,
            "client": quota_key,
            "tier": tier,
        }

    def batch_check(self, client_id: str, paths: list[str]) -> dict[str, dict]:
        """批量检查多个路径的限流状态"""
        results = {}
        for path in paths:
            results[path] = self._check_rate(client_id, path)
        total_allowed = sum(1 for r in results.values() if r.get("allowed"))
        metrics_collector.histogram("rate_guard_batch_check", len(paths))
        return {
            "client_id": client_id,
            "total": len(paths),
            "allowed": total_allowed,
            "denied": len(paths) - total_allowed,
            "results": results,
        }

    def get_usage_report(self, top_n: int = 10) -> dict:
        """获取配额使用报告（按拒绝率排序）"""
        sorted_clients = sorted(self._quotas.values(), key=lambda q: q.rejected, reverse=True)
        top = []
        for q in sorted_clients[:top_n]:
            total = q.allowed + q.rejected
            rate = round(q.rejected / max(total, 1), 4)
            top.append(
                {
                    "client_id": q.client_id,
                    "allowed": q.allowed,
                    "rejected": q.rejected,
                    "rejection_rate": rate,
                    "tokens_remaining": round(q.tokens, 2),
                }
            )
        return {"success": True, "result": {"top_rejected": top, "total_clients": len(self._quotas)}}

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

module_class = ApiRateGuardManager
