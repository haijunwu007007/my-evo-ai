"""
AUTO-EVO-AI V0.1 — CORS运行时管理器
Grade: A (生产级) | Category: 安全中间件
职责：CORS中间件执行、请求拦截/响应注入、动态规则热更新、指标采集
与cors_config模块互补：config负责策略配置，manager负责运行时执行
"""

__module_meta__ = {
        "id": "cors-manager",
        "name": "Cors Manager",
        "version": "V0.1",
        "group": "api",
        "inputs": [
            {
                "name": "method",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "origin",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "origin_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "is_preflight",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "days",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "origin_3",
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
                "name": "success_2",
                "type": "bool",
                "description": "是否成功"
            },
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "config",
            "manager",
            "cors"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — CORS运行时管理器 Grade: A (生产级) | Category: 安全中间件"
    }

import os
import time
import uuid
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

class MiddlewareAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    PASS = "pass"  # 不处理，交给下游

@dataclass
class ResponseHeaders:
    access_control_allow_origin: str = ""
    access_control_allow_methods: str = ""
    access_control_allow_headers: str = ""
    access_control_allow_credentials: str = ""
    access_control_expose_headers: str = ""
    access_control_max_age: str = ""
    vary_origin: bool = False

@dataclass
class RequestLog:
    log_id: str = ""
    origin: str = ""
    method: str = ""
    path: str = ""
    is_preflight: bool = False
    action: str = "pass"
    processing_time_ms: float = 0.0
    client_ip: str = ""
    timestamp: float = 0.0

@dataclass
class RouteConfig:
    route_id: str = ""
    path_pattern: str = ""
    cors_enabled: bool = True
    strict_mode: bool = False
    allowed_methods_override: list[str] | None = None
    max_age_override: int | None = None

class CORSManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    MODULE_ID = "cors_manager"
    MODULE_NAME = "cors_manager"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "cors_manager",
                "version": "7.0.0",
                "description": "CORS运行时管理器：中间件执行/请求处理/动态更新/指标采集",
            }
        )
        self._middleware_enabled = True
        self._strict_mode = False
        self._global_allowed_origins: list[str] = ["*"]
        self._global_allowed_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        self._global_allowed_headers: list[str] = ["Content-Type", "Authorization", "X-Request-ID", "X-API-Key"]
        self._global_expose_headers: list[str] = ["X-Request-ID", "X-RateLimit-Remaining"]
        self._global_allow_credentials = False
        self._global_max_age = 86400
        self._route_configs: dict[str, RouteConfig] = {}
        self._origin_stats: dict[str, dict] = defaultdict(lambda: {"requests": 0, "blocked": 0, "preflight": 0})
        self._request_log: list[RequestLog] = []
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        now = time.time()
        for rid, pattern, strict in [
            ("api_routes", "/api/*", False),
            ("admin_routes", "/admin/*", True),
            ("auth_routes", "/auth/*", True),
            ("public_routes", "/public/*", False),
            ("ws_routes", "/ws/*", False),
        ]:
            self._route_configs[rid] = RouteConfig(
                route_id=rid, path_pattern=pattern, cors_enabled=True, strict_mode=strict
            )

    def _is_preflight(self, method: str) -> bool:
        return method.upper() == "OPTIONS"

    def _check_origin(self, origin: str) -> tuple[bool, str]:
        if not origin:
            return False, "Missing Origin header"
        if "*" in self._global_allowed_origins:
            return True, ""
        if origin in self._global_allowed_origins:
            return True, ""
        for o in self._global_allowed_origins:
            if o.endswith("*") and origin.startswith(o[:-1]):
                return True, ""
        if not self._strict_mode:
            return True, "non-strict-allow"
        return False, f"Origin {origin} not in whitelist"

    def _build_response_headers(self, origin: str, is_preflight: bool = False) -> ResponseHeaders:
        headers = ResponseHeaders()
        if "*" in self._global_allowed_origins:
            headers.access_control_allow_origin = "*"
        elif self._check_origin(origin)[0]:
            headers.access_control_allow_origin = origin
            headers.vary_origin = True
        headers.access_control_allow_methods = ", ".join(self._global_allowed_methods)
        headers.access_control_allow_headers = ", ".join(self._global_allowed_headers)
        if self._global_allow_credentials:
            headers.access_control_allow_credentials = "true"
        if is_preflight:
            headers.access_control_max_age = str(self._global_max_age)
        if not is_preflight:
            headers.access_control_expose_headers = ", ".join(self._global_expose_headers)
        return headers

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.trace("execute", {"module": "cors_manager"})
        self.metrics_collector.counter("cors_manager.execute.calls", 1)
        self.audit("execute", {"module": "cors_manager"})
        params = params or {}
        try:
            if action == "process_request":
                start = time.time()
                origin = params.get("origin", "")
                method = params.get("method", "GET")
                path = params.get("path", "/")
                headers_list = params.get("headers", [])
                client_ip = params.get("client_ip", "")
                is_pflight = self._is_preflight(method)

                if not self._middleware_enabled:
                    dt = (time.time() - start) * 1000
                    log = RequestLog(
                        log_id=f"log_{uuid.uuid4().hex[:8]}",
                        origin=origin,
                        method=method,
                        path=path,
                        is_preflight=is_pflight,
                        action="pass",
                        processing_time_ms=dt,
                        client_ip=client_ip,
                        timestamp=time.time(),
                    )
                    self._request_log.append(log)
                    return {"success": True, "result": {"action": "pass", "headers": {}}}

                allowed, reason = self._check_origin(origin)
                self._origin_stats[origin]["requests"] += 1
                if is_pflight:
                    self._origin_stats[origin]["preflight"] += 1

                if not allowed:
                    self._origin_stats[origin]["blocked"] += 1
                    dt = (time.time() - start) * 1000
                    log = RequestLog(
                        log_id=f"log_{uuid.uuid4().hex[:8]}",
                        origin=origin,
                        method=method,
                        path=path,
                        is_preflight=is_pflight,
                        action="deny",
                        processing_time_ms=dt,
                        client_ip=client_ip,
                        timestamp=time.time(),
                    )
                    self._request_log.append(log)
                    return {
                        "success": True,
                        "result": {"action": "deny", "reason": reason, "headers": {}, "status_code": 403},
                    }

                resp = self._build_response_headers(origin, is_pflight)
                dt = (time.time() - start) * 1000
                log = RequestLog(
                    log_id=f"log_{uuid.uuid4().hex[:8]}",
                    origin=origin,
                    method=method,
                    path=path,
                    is_preflight=is_pflight,
                    action="allow",
                    processing_time_ms=dt,
                    client_ip=client_ip,
                    timestamp=time.time(),
                )
                self._request_log.append(log)
                if len(self._request_log) > 10000:
                    self._request_log = self._request_log[-5000:]

                return {
                    "success": True,
                    "result": {
                        "action": "allow",
                        "headers": {
                            "Access-Control-Allow-Origin": resp.access_control_allow_origin,
                            "Access-Control-Allow-Methods": resp.access_control_allow_methods,
                            "Access-Control-Allow-Headers": resp.access_control_allow_headers,
                            "Access-Control-Allow-Credentials": resp.access_control_allow_credentials,
                            "Access-Control-Max-Age": resp.access_control_max_age,
                            "Access-Control-Expose-Headers": resp.access_control_expose_headers,
                            "Vary": "Origin" if resp.vary_origin else "",
                        },
                        "is_preflight": is_pflight,
                        "status_code": 204 if is_pflight else 200,
                    },
                }

            elif action == "configure":
                if "allowed_origins" in params:
                    self._global_allowed_origins = params["allowed_origins"]
                if "allowed_methods" in params:
                    self._global_allowed_methods = params["allowed_methods"]
                if "allowed_headers" in params:
                    self._global_allowed_headers = params["allowed_headers"]
                if "expose_headers" in params:
                    self._global_expose_headers = params["expose_headers"]
                if "allow_credentials" in params:
                    self._global_allow_credentials = params["allow_credentials"]
                if "max_age" in params:
                    self._global_max_age = params["max_age"]
                if "strict_mode" in params:
                    self._strict_mode = params["strict_mode"]
                if "middleware_enabled" in params:
                    self._middleware_enabled = params["middleware_enabled"]
                return {"success": True, "result": {"configured": True}}

            elif action == "add_route_config":
                rid = params.get("route_id") or f"route_{uuid.uuid4().hex[:8]}"
                self._route_configs[rid] = RouteConfig(
                    route_id=rid,
                    path_pattern=params.get("path_pattern", ""),
                    cors_enabled=params.get("cors_enabled", True),
                    strict_mode=params.get("strict_mode", False),
                    allowed_methods_override=params.get("allowed_methods_override"),
                    max_age_override=params.get("max_age_override"),
                )
                return {"success": True, "result": {"route_id": rid}}

            elif action == "list_routes":
                return {
                    "success": True,
                    "result": [
                        {
                            "route_id": r.route_id,
                            "path_pattern": r.path_pattern,
                            "cors_enabled": r.cors_enabled,
                            "strict_mode": r.strict_mode,
                        }
                        for r in self._route_configs.values()
                    ],
                }

            elif action == "get_config":
                return {
                    "success": True,
                    "result": {
                        "middleware_enabled": self._middleware_enabled,
                        "strict_mode": self._strict_mode,
                        "allowed_origins": self._global_allowed_origins,
                        "allowed_methods": self._global_allowed_methods,
                        "allowed_headers": self._global_allowed_headers,
                        "expose_headers": self._global_expose_headers,
                        "allow_credentials": self._global_allow_credentials,
                        "max_age": self._global_max_age,
                    },
                }

            elif action == "origin_stats":
                sorted_stats = sorted(self._origin_stats.items(), key=lambda x: x[1]["requests"], reverse=True)[:20]
                return {"success": True, "result": [{"origin": o, **s} for o, s in sorted_stats]}

            elif action == "request_log":
                limit = params.get("limit", 50)
                return {
                    "success": True,
                    "result": [
                        {
                            "origin": l.origin,
                            "method": l.method,
                            "path": l.path,
                            "is_preflight": l.is_preflight,
                            "action": l.action,
                            "time_ms": round(l.processing_time_ms, 2),
                            "timestamp": datetime.fromtimestamp(l.timestamp).isoformat(),
                        }
                        for l in self._request_log[-limit:]
                    ],
                }

            elif action == "get_stats":
                total = sum(s["requests"] for s in self._origin_stats.values())
                blocked = sum(s["blocked"] for s in self._origin_stats.values())
                pflight = sum(s["preflight"] for s in self._origin_stats.values())
                return {
                    "success": True,
                    "result": {
                        "total_requests": total,
                        "blocked": blocked,
                        "preflight": pflight,
                        "unique_origins": len(self._origin_stats),
                        "block_rate": round(blocked / max(total, 1) * 100, 1),
                        "routes": len(self._route_configs),
                    },
                }

            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"[CORSManager] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        base.update(
            {
                "status": "healthy",
                "middleware_enabled": self._middleware_enabled,
                "strict_mode": self._strict_mode,
                "origins": len(self._origin_stats),
                "routes": len(self._route_configs),
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False

    def get_origin_access_report(self, days: int = 7) -> dict[str, Any]:
        """来源域访问报告。企业场景：安全审计查看哪些外部域名在调用API，
        识别未授权的来源域名，辅助CORS白名单配置。
        """
        stats = getattr(self, "_origin_stats", {})
        cutoff = time.time() - days * 86400
        report = []
        for origin, data in stats.items():
            last_access = data.get("last_access", 0)
            recent_requests = [r for r in data.get("requests", []) if r.get("ts", 0) > cutoff]
            report.append(
                {
                    "origin": origin,
                    "total_requests": data.get("total", 0),
                    "recent_requests": len(recent_requests),
                    "allowed": data.get("allowed", False),
                    "blocked": data.get("blocked", 0),
                }
            )
        report.sort(key=lambda x: -x["recent_requests"])
        return {
            "success": True,
            "period_days": days,
            "total_origins": len(report),
            "allowed_origins": sum(1 for r in report if r["allowed"]),
            "blocked_origins": sum(1 for r in report if not r["allowed"] and r["recent_requests"] > 0),
            "top_origins": report[:20],
        }

    def validate_cors_config(self) -> dict[str, Any]:
        """CORS配置安全检查。企业场景：上线前安全扫描，检查是否存在
        通配符域名、不安全的HTTP方法、缺少凭证限制等安全风险。
        """
        issues = []
        configs = getattr(self, "_route_configs", {})
        for route, config in configs.items():
            allowed = config.get("allow_origins", [])
            if "*" in allowed:
                issues.append(
                    {"route": route, "severity": "high", "issue": "允许所有来源 (*)", "fix": "限制为具体域名"}
                )
            methods = config.get("allow_methods", [])
            if "DELETE" in methods and not config.get("require_auth", True):
                issues.append(
                    {
                        "route": route,
                        "severity": "medium",
                        "issue": "DELETE方法未要求认证",
                        "fix": "为DELETE/PUT/PATCH方法添加认证要求",
                    }
                )
            if config.get("allow_credentials", False) and "*" in allowed:
                issues.append(
                    {
                        "route": route,
                        "severity": "high",
                        "issue": "credentials + 通配符不安全",
                        "fix": "指定具体域名或禁用credentials",
                    }
                )
        return {
            "success": True,
            "total_routes": len(configs),
            "issues_found": len(issues),
            "issues": issues,
            "secure": len(issues) == 0,
        }

    def add_temporary_origin(self, origin: str, ttl_minutes: int = 60) -> dict[str, Any]:
        """添加临时CORS白名单。企业场景：第三方集成测试时临时开放跨域访问，
        过期自动移除，避免长期开放安全风险。
        """
        temp = getattr(self, "_temp_origins", {})
        temp[origin] = {"added_at": time.time(), "ttl_minutes": ttl_minutes}
        self._temp_origins = temp
        return {"success": True, "origin": origin, "expires_at": time.time() + ttl_minutes * 60}

    def cleanup_expired_origins(self) -> dict[str, Any]:
        """清理过期的临时CORS白名单。企业场景：定时任务清理已过期的临时域名。"""
        temp = getattr(self, "_temp_origins", {})
        now = time.time()
        expired = [o for o, info in temp.items() if now > info.get("added_at", 0) + info.get("ttl_minutes", 60) * 60]
        for o in expired:
            del temp[o]
        self._temp_origins = temp
        return {"success": True, "expired_removed": len(expired), "remaining": len(temp)}

    def get_origin_access_report(self, days: int = 7) -> dict[str, Any]:
        """来源访问报告。企业场景：安全团队周报统计各域名跨域请求数，
        识别异常来源（未注册域名高频访问）。
        """
        logs = getattr(self, "_access_logs", [])
        cutoff = time.time() - days * 86400
        recent = [l for l in logs if l.get("timestamp", 0) > cutoff]
        origin_counts = {}
        for l in recent:
            origin = l.get("origin", "unknown")
            origin_counts[origin] = origin_counts.get(origin, 0) + 1
        registered = getattr(self, "_origins", set())
        unregistered = {o: c for o, c in origin_counts.items() if o not in registered}
        sorted_origins = sorted(origin_counts.items(), key=lambda x: -x[1])
        return {
            "success": True,
            "period_days": days,
            "total_requests": len(recent),
            "unique_origins": len(origin_counts),
            "registered_origins": len(registered),
            "unregistered_origins": list(unregistered.keys())[:10],
            "top_origins": [{"origin": o, "requests": c} for o, c in sorted_origins[:20]],
        }

    def evaluate_origin(self, origin: str) -> dict[str, Any]:
        """评估来源安全性。企业场景：新前端域名接入前，安全团队审查其
        是否符合CORS策略（是否在白名单、是否有通配符风险）。
        """
        config = getattr(self, "_config", {})
        allowed = config.get("allowed_origins", [])
        # 检查是否已注册
        exact_match = origin in allowed
        # 检查通配符匹配
        wildcard_match = False
        for pattern in allowed:
            if "*" in pattern:
                prefix = pattern.replace("*", "")
                if origin.startswith(prefix) or origin.endswith(prefix):
                    wildcard_match = True
                    break
        # 安全评估
        risks = []
        if wildcard_match and not exact_match:
            risks.append("仅匹配通配符规则，建议添加精确域名")
        if origin.startswith("http://"):
            risks.append("使用HTTP协议，建议升级为HTTPS")
        if ":" not in origin.split("//")[-1].split("/")[0]:
            risks.append("缺少端口号，默认端口可能被劫持")
        risk_level = "high" if len(risks) >= 2 else ("medium" if risks else "low")
        return {
            "success": True,
            "origin": origin,
            "allowed": exact_match or wildcard_match,
            "exact_match": exact_match,
            "wildcard_match": wildcard_match,
            "risk_level": risk_level,
            "risks": risks,
            "recommendation": "允许接入" if exact_match else ("需安全审查" if wildcard_match else "拒绝接入"),
        }

    def export_config(self, format: str = "json") -> dict[str, Any]:
        """导出CORS配置。企业场景：环境迁移时导出当前CORS策略，
        导入到新环境。支持JSON和Nginx格式。
        """
        config = getattr(self, "_config", {})
        allowed = config.get("allowed_origins", [])
        methods = config.get("allowed_methods", ["GET", "POST"])
        headers = config.get("allowed_headers", [])
        max_age = config.get("max_age", 3600)
        credentials = config.get("allow_credentials", False)
        if format == "nginx":
            lines = []
            if allowed:
                for o in allowed:
                    lines.append(f'    add_header Access-Control-Allow-Origin "{o}" always;')
            if credentials:
                lines.append('    add_header Access-Control-Allow-Credentials "true" always;')
            if methods:
                lines.append(f'    add_header Access-Control-Allow-Methods "{",".join(methods)}" always;')
            if headers:
                lines.append(f'    add_header Access-Control-Allow-Headers "{",".join(headers)}" always;')
            lines.append(f"    add_header Access-Control-Max-Age {max_age} always;")
            return {"success": True, "format": "nginx", "config": "
".join(lines), "origin_count": len(allowed)}
        return {
            "success": True,
            "format": "json",
            "allowed_origins": allowed,
            "allowed_methods": methods,
            "allowed_headers": headers,
            "max_age": max_age,
            "allow_credentials": credentials,
            "origin_count": len(allowed),
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

module_class = CORSManager
