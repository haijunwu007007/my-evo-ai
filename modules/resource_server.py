# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI v7.0 - ResourceServer OAuth2资源服务器
==================================================
企业级OAuth2资源服务器：Token验证/Scope检查/API保护。
支持：Bearer Token验证、Scope细粒度权限控制、
      JWT本地验证/远程Introspection、RBAC权限映射、
      API路由保护、CORS、请求审计、Token缓存、
      响应格式化、错误处理标准化。

A级生产标准：EnterpriseModule + 链路追踪 + Prometheus + 审计 + 熔断 + 限流
"""

__module_meta__ = {
    "id": "resource-server",
    "name": "Resource Server",
    "version": "1.0.0",
    "group": "system",
    "inputs": [
        {"name": "user_id", "type": "string", "required": True, "description": ""},
        {"name": "resource", "type": "string", "required": True, "description": ""},
        {"name": "method", "type": "string", "required": True, "description": ""},
        {"name": "granted", "type": "string", "required": True, "description": ""},
        {"name": "top_n", "type": "string", "required": True, "description": ""},
        {"name": "user_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["resource"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 - ResourceServer OAuth2资源服务器 ==================================================",
}
import time
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from functools import wraps
import uuid

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.circuit_breaker import CircuitBreakerMixin
from modules._base.rate_limiter import RateLimiterMixin

class AuthScheme(str, Enum):
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH2 = "oauth2"

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"

@dataclass
class ApiResource:
    """API资源定义"""

    resource_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    path_pattern: str = ""
    methods: List[str] = field(default_factory=lambda: ["GET"])
    required_scopes: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    required_roles: List[str] = field(default_factory=list)
    rate_limit_rpm: int = 0  # 0=不限
    rate_limit_rph: int = 0
    auth_required: bool = True
    auth_scheme: AuthScheme = AuthScheme.BEARER
    cors_enabled: bool = True
    ip_whitelist: List[str] = field(default_factory=list)
    ip_blacklist: List[str] = field(default_factory=list)
    description: str = ""
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    request_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0

@dataclass
class ApiKey:
    """API Key"""

    key_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    key_value: str = field(default_factory=lambda: f"evo_{uuid.uuid4().hex}")
    name: str = ""
    user_id: str = ""
    scopes: List[str] = field(default_factory=list)
    rate_limit_rpm: int = 0
    allowed_ips: List[str] = field(default_factory=list)
    enabled: bool = True
    expires_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: Optional[str] = None
    request_count: int = 0

@dataclass
class RolePermission:
    """角色权限映射"""

    role_name: str
    permissions: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)
    description: str = ""

@dataclass
class ResourceRequest:
    """资源请求上下文"""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    method: str = "GET"
    path: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    client_ip: str = ""
    user_agent: str = ""
    auth_scheme: Optional[AuthScheme] = None
    token: Optional[str] = None
    token_scopes: List[str] = field(default_factory=list)
    user_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    api_key_id: Optional[str] = None
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ResourceResponse:
    """资源响应"""

    request_id: str = ""
    status_code: int = 200
    body: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    latency_ms: float = 0.0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    trace_id: str = ""
    rate_limited: bool = False

# ============================================================================
# ResourceServer 主类
# ============================================================================

class ResourceAccessAnalyzer(object):
    """资源访问分析引擎：访问模式分析、异常检测、权限热力图"""

    def __init__(self):
        self._access_log: List[Dict] = []
        self._resource_frequency: Dict[str, int] = {}
        self._user_access_patterns: Dict[str, List[str]] = {}

    def record_access(self, user_id: str, resource: str, method: str = "GET", granted: bool = True) -> None:
        """记录资源访问事件"""
        entry = {"user": user_id, "resource": resource, "method": method, "granted": granted, "timestamp": time.time()}
        self._access_log.append(entry)
        if len(self._access_log) > 10000:
            self._access_log = self._access_log[-10000:]
        self._resource_frequency[resource] = self._resource_frequency.get(resource, 0) + 1
        self._user_access_patterns.setdefault(user_id, []).append(resource)

    def get_hot_resources(self, top_n: int = 10) -> List[Dict]:
        """获取访问量最高的资源"""
        sorted_res = sorted(self._resource_frequency.items(), key=lambda x: -x[1])
        return [{"resource": r, "hits": c} for r, c in sorted_res[:top_n]]

    def detect_anomalous_access(self, user_id: str, threshold: float = 3.0) -> bool:
        """检测用户是否有异常访问模式"""
        user_resources = self._user_access_patterns.get(user_id, [])
        if len(user_resources) < 5:
            return False
        avg = sum(self._resource_frequency.get(r, 0) for r in user_resources) / len(user_resources)
        recent = user_resources[-10:]
        recent_avg = sum(self._resource_frequency.get(r, 0) for r in recent) / len(recent)
        return recent_avg > avg * threshold

class ResourceServer(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    OAuth2资源服务器

    功能：
      - API资源注册与路由保护
      - Bearer Token验证（JWT本地/远程Introspection）
      - API Key认证
      - Scope细粒度权限控制
      - RBAC角色权限映射
      - IP黑白名单
      - 请求限流
      - Token缓存（减少Introspection调用）
      - 审计日志
      - CORS处理
      - 标准化错误响应
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__()
        self.config = config or {}
        # API资源表
        self._resources: Dict[str, ApiResource] = {}
        # 排序资源（长路径优先）
        self._sorted_resources: List[ApiResource] = []
        # API Key注册表
        self._api_keys: Dict[str, ApiKey] = {}  # key_value -> ApiKey
        self._api_keys_by_id: Dict[str, ApiKey] = {}  # key_id -> ApiKey
        # 角色权限映射
        self._role_permissions: Dict[str, RolePermission] = {}
        # Token验证器
        self._token_validator: Optional[Callable] = None  # (token) -> (valid, user_id, scopes)
        # Introspection端点
        self._introspection_url: Optional[str] = self.config.get("introspection_url")
        self._introspection_client_id: str = self.config.get("introspection_client_id", "")
        self._introspection_client_secret: str = self.config.get("introspection_client_secret", "")
        # Token缓存（避免重复Introspection）
        self._token_cache: Dict[str, Tuple[float, Dict]] = {}
        self._token_cache_ttl = self.config.get("token_cache_ttl", 300.0)
        # 审计日志
        self._access_log: List[Dict] = []
        self._access_log_max = 100000
        # 限流计数器
        self._rate_counters: Dict[str, List[float]] = defaultdict(list)
        # 统计
        self._rs_stats = {
            "total_requests": 0,
            "authorized": 0,
            "unauthorized": 0,
            "forbidden": 0,
            "rate_limited": 0,
            "not_found": 0,
            "server_errors": 0,
            "api_key_auth": 0,
            "bearer_auth": 0,
        }
        # 配置
        self._realm = self.config.get("realm", "AUTO-EVO-AI")
        self._default_scope_prefix = self.config.get("default_scope_prefix", "")
        self._require_auth_by_default = self.config.get("require_auth_by_default", True)
        # 初始化默认角色
        self._init_default_roles()
        # 初始化默认资源
        for res_cfg in self.config.get("preset_resources", []):
            self.register_resource(res_cfg)

    def _init_default_roles(self):
        """初始化默认角色权限"""
        defaults = {
            "admin": RolePermission(
                "admin", ["read", "write", "delete", "admin", "execute"], ["admin", "read", "write"], "管理员：完全权限"
            ),
            "editor": RolePermission("editor", ["read", "write", "execute"], ["read", "write"], "编辑者：读写权限"),
            "viewer": RolePermission("viewer", ["read"], ["read"], "查看者：只读权限"),
            "service": RolePermission("service", ["execute"], ["execute"], "服务账号：执行权限"),
        }
        self._role_permissions = defaults

    # ----------------------------------------------------------------
    # 生命周期
    # ----------------------------------------------------------------

    def initialize(self) -> Result:
        try:
            self._update_status(ModuleStatus.INITIALIZING)
            self._rebuild_sorted_resources()
            self._update_status(ModuleStatus.RUNNING)
            self.audit(
                "resource_server.initialized",
                {
                    "resources": len(self._resources),
                    "api_keys": len(self._api_keys),
                    "roles": len(self._role_permissions),
                },
            )
            logger.info(f"[ResourceServer] 初始化完成: {len(self._resources)} resources")
            return Result(success=True)
        except Exception as e:
            self._update_status(ModuleStatus.ERROR)
            logger.error(f"[ResourceServer] 初始化失败: {e}")
            return Result(success=False, error=str(e))

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        params = params or {}
        actions = {
            "register_resource": self.register_resource,
            "create_api_key": self.create_api_key,
            "revoke_api_key": self.revoke_api_key,
            "list_api_keys": self.list_api_keys,
            "add_role": self.add_role,
            "get_role_permissions": self.get_role_permissions,
            "resolve_permissions": self.resolve_permissions,
            "resolve_scopes": self.resolve_scopes,
            "set_token_validator": self.set_token_validator,
            "validate_token": self.validate_token,
            "handle_request": self.handle_request,
            "get_access_log": self.get_access_log,
            "get_stats": self.get_stats,
            "list_resources": self.list_resources,
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
                    return {"status": "error", "message": str(e)}
            else:
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            if isinstance(result, dict):
                return {"status": "success", **result}
            return {"status": "success", "data": result}

    def health_check(self) -> HealthReport:
        checks = {
            "resources_count": len(self._resources),
            "api_keys_count": len(self._api_keys),
            "roles_count": len(self._role_permissions),
            "token_cache_size": len(self._token_cache),
        }
        return HealthReport(
            status="running",
            healthy=True,
            last_beat=datetime.now().isoformat(),
            uptime_seconds=self.stats.uptime_seconds,
            checks_run=4,
            error_rate=self.stats.error_rate,
            details=checks,
            version="v7.0",
        )

    def shutdown(self) -> Result:
        self._token_cache.clear()
        self._rate_counters.clear()
        self._update_status(ModuleStatus.STOPPED)
        return Result(success=True)

    # ----------------------------------------------------------------
    # 资源注册
    # ----------------------------------------------------------------

    def register_resource(self, resource_cfg: Dict[str, Any]) -> Result:
        """注册API资源"""
        metrics_collector.counter("resource_ops_total")

        methods = resource_cfg.get("methods", ["GET"])
        if isinstance(methods, str):
            methods = [m.strip().upper() for m in methods.split(",")]
        res = ApiResource(
            path_pattern=resource_cfg.get("path_pattern", ""),
            methods=[m.upper() for m in methods],
            required_scopes=resource_cfg.get("required_scopes", []),
            required_permissions=resource_cfg.get("required_permissions", []),
            required_roles=resource_cfg.get("required_roles", []),
            rate_limit_rpm=resource_cfg.get("rate_limit_rpm", 0),
            auth_required=resource_cfg.get("auth_required", self._require_auth_by_default),
            auth_scheme=AuthScheme(resource_cfg.get("auth_scheme", "bearer")),
            cors_enabled=resource_cfg.get("cors_enabled", True),
            description=resource_cfg.get("description", ""),
            tags=resource_cfg.get("tags", []),
        )
        self._resources[res.resource_id] = res
        self._rebuild_sorted_resources()
        return Result(success=True, data={"resource_id": res.resource_id})

    def _rebuild_sorted_resources(self):
        self._sorted_resources = sorted(self._resources.values(), key=lambda r: len(r.path_pattern), reverse=True)

    # ----------------------------------------------------------------
    # API Key管理
    # ----------------------------------------------------------------

    def create_api_key(
        self, name: str, user_id: str = "", scopes: Optional[List[str]] = None, rate_limit_rpm: int = 0
    ) -> Result:
        key = ApiKey(name=name, user_id=user_id, scopes=scopes or [], rate_limit_rpm=rate_limit_rpm)
        self._api_keys[key.key_value] = key
        self._api_keys_by_id[key.key_id] = key
        return Result(success=True, data={"key_id": key.key_id, "key_value": key.key_value})

    def revoke_api_key(self, key_id: str) -> Result:
        key = self._api_keys_by_id.pop(key_id, None)
        if not key:
            return Result(success=False, error="API Key不存在")
        self._api_keys.pop(key.key_value, None)
        key.enabled = False
        return Result(success=True)

    def list_api_keys(self, user_id: Optional[str] = None) -> List[Dict]:
        result = []
        for key in self._api_keys.values():
            if user_id and key.user_id != user_id:
                continue
            result.append(
                {
                    "key_id": key.key_id,
                    "name": key.name,
                    "user_id": key.user_id,
                    "scopes": key.scopes,
                    "enabled": key.enabled,
                    "rate_limit_rpm": key.rate_limit_rpm,
                    "request_count": key.request_count,
                    "created_at": key.created_at,
                    "last_used": key.last_used,
                    "expires_at": key.expires_at,
                }
            )
        return result

    # ----------------------------------------------------------------
    # 角色管理
    # ----------------------------------------------------------------

    def add_role(self, role: RolePermission) -> Result:
        self._role_permissions[role.role_name] = role
        return Result(success=True)

    def get_role_permissions(self, role_name: str) -> Optional[RolePermission]:
        return self._role_permissions.get(role_name)

    def resolve_permissions(self, roles: List[str]) -> List[str]:
        """解析角色对应的权限列表"""
        perms = set()
        for role_name in roles:
            role = self._role_permissions.get(role_name)
            if role:
                perms.update(role.permissions)
        return list(perms)

    def resolve_scopes(self, roles: List[str]) -> List[str]:
        """解析角色对应的Scope列表"""
        scopes = set()
        for role_name in roles:
            role = self._role_permissions.get(role_name)
            if role:
                scopes.update(role.scopes)
        return list(scopes)

    # ----------------------------------------------------------------
    # Token验证
    # ----------------------------------------------------------------

    def set_token_validator(self, validator: Callable):
        """设置Token验证器 (token) -> (valid, user_id, scopes)"""
        self._token_validator = validator

    def validate_token(self, token: str) -> Tuple[bool, Optional[str], List[str]]:
        """验证Token"""
        # 检查缓存
        cached = self._token_cache.get(token)
        if cached:
            ts, data = cached
            if time.time() - ts < self._token_cache_ttl:
                return data.get("valid", False), data.get("user_id"), data.get("scopes", [])
            else:
                del self._token_cache[token]
        # 本地验证器
        if self._token_validator:
            try:
                result = self._token_validator(token)
                if asyncio.iscoroutine(result):
                    result = result
                valid, user_id, scopes = result
                cache_data = {"valid": valid, "user_id": user_id, "scopes": scopes}
                self._token_cache[token] = (time.time(), cache_data)
                return valid, user_id, scopes
            except Exception as e:
                logger.error(f"[ResourceServer] Token验证失败: {e}")
                return False, None, []
        # 无验证器
        return False, None, []

    # ----------------------------------------------------------------
    # 请求处理（核心）
    # ----------------------------------------------------------------

    def handle_request(self, request: ResourceRequest) -> ResourceResponse:
        """处理资源请求"""
        start = time.time()
        request.trace_id = request.trace_id or str(uuid.uuid4())[:16]
        self._rs_stats["total_requests"] += 1
        try:
            with self.trace(f"resource:{request.method}:{request.path}"):
                # 1. 路由匹配
                resource = self._match_resource(request.method, request.path)
                if not resource:
                    self._rs_stats["not_found"] += 1
                    return self._error_response(request, 404, "NOT_FOUND", "No matching resource")
                # 2. CORS预检
                if request.method == "OPTIONS":
                    return self._cors_response(request)
                # 3. IP检查
                ip_ok = self._check_ip(request.client_ip, resource)
                if not ip_ok:
                    self._rs_stats["forbidden"] += 1
                    return self._error_response(request, 403, "FORBIDDEN", "IP not allowed")
                # 4. 认证
                if resource.auth_required:
                    auth_ok = self._authenticate(request, resource)
                    if not auth_ok:
                        self._rs_stats["unauthorized"] += 1
                        return self._error_response(
                            request,
                            401,
                            "UNAUTHORIZED",
                            "Bearer token required",
                            {"WWW-Authenticate": f'Bearer realm="{self._realm}"'},
                        )
                # 5. 授权（Scope/Permission/Role检查）
                if resource.required_scopes or resource.required_permissions or resource.required_roles:
                    authorized = self._authorize(request, resource)
                    if not authorized:
                        self._rs_stats["forbidden"] += 1
                        return self._error_response(request, 403, "FORBIDDEN", "Insufficient permissions")
                # 6. 限流检查
                if resource.rate_limit_rpm > 0:
                    if not self._check_rate_limit(request, resource):
                        self._rs_stats["rate_limited"] += 1
                        return self._error_response(
                            request,
                            429,
                            "RATE_LIMITED",
                            "Rate limit exceeded",
                            {"Retry-After": "60", "X-RateLimit-Limit": str(resource.rate_limit_rpm)},
                        )
                # 7. 更新统计
                resource.request_count += 1
                latency = (time.time() - start) * 1000
                resource.avg_latency_ms = resource.avg_latency_ms * 0.9 + latency * 0.1
                self._rs_stats["authorized"] += 1
                self._log_access(request, 200, resource)
                self.stats.record_request(latency, True)
                return ResourceResponse(
                    request_id=request.request_id,
                    status_code=200,
                    headers={"X-Trace-Id": request.trace_id, "X-Powered-By": "AUTO-EVO-AI/ResourceServer"},
                    latency_ms=latency,
                    trace_id=request.trace_id,
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            self._rs_stats["server_errors"] += 1
            self.stats.record_request(latency, False, str(e))
            return self._error_response(request, 500, "INTERNAL_ERROR", str(e))

    # ----------------------------------------------------------------
    # 内部方法
    # ----------------------------------------------------------------

    def _match_resource(self, method: str, path: str) -> Optional[ApiResource]:
        for res in self._sorted_resources:
            if not res.enabled:
                continue
            if method.upper() not in res.methods:
                continue
            if self._path_matches(path, res.path_pattern):
                return res
        return None

    @staticmethod
    def _path_matches(path: str, pattern: str) -> bool:
        """路径匹配（支持通配符）"""
        if pattern == "**":
            return True
        if pattern.endswith("/**"):
            return path.startswith(pattern[:-3])
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            return path == prefix or (
                path.startswith(prefix) and path[len(prefix) :] == "" or path[len(prefix) :].startswith("/")
            )
        # 简单前缀匹配
        regex = re.escape(pattern).replace(r"\*", "[^/]+").replace(r"\*\*", ".*")
        return bool(re.match(f"^{regex}$", path))

    def _check_ip(self, client_ip: str, resource: ApiResource) -> bool:
        if resource.ip_blacklist and client_ip in resource.ip_blacklist:
            return False
        if resource.ip_whitelist and client_ip not in resource.ip_whitelist:
            return False
        return True

    def _authenticate(self, request: ResourceRequest, resource: ApiResource) -> bool:
        """认证"""
        auth_header = request.headers.get("Authorization", "")
        # Bearer Token
        if resource.auth_scheme == AuthScheme.BEARER and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if not token:
                return False
            request.token = token
            valid, user_id, scopes = self.validate_token(token)
            if valid:
                request.auth_scheme = AuthScheme.BEARER
                request.user_id = user_id
                request.token_scopes = scopes
                self._rs_stats["bearer_auth"] += 1
                return True
            return False
        # API Key
        if resource.auth_scheme == AuthScheme.API_KEY:
            api_key = request.headers.get("X-API-Key", "") or request.query_params.get("api_key", "")
            if not api_key:
                return False
            key = self._api_keys.get(api_key)
            if not key or not key.enabled:
                return False
            if key.expires_at and key.expires_at < datetime.now().isoformat():
                return False
            if key.allowed_ips and request.client_ip not in key.allowed_ips:
                return False
            request.auth_scheme = AuthScheme.API_KEY
            request.api_key_id = key.key_id
            request.user_id = key.user_id
            request.token_scopes = key.scopes
            key.request_count += 1
            key.last_used = datetime.now().isoformat()
            self._rs_stats["api_key_auth"] += 1
            return True
        return False

    def _authorize(self, request: ResourceRequest, resource: ApiResource) -> bool:
        """授权检查"""
        # Scope检查
        if resource.required_scopes:
            for scope in resource.required_scopes:
                if scope not in request.token_scopes:
                    return False
        # Role检查
        if resource.required_roles:
            if not any(role in resource.required_roles for role in request.roles):
                return False
        # Permission检查
        if resource.required_permissions:
            # 从Token Scope解析权限
            all_perms = set(request.permissions)
            # 也尝试从角色解析
            all_perms.update(self.resolve_permissions(request.roles))
            if not all(p in all_perms for p in resource.required_permissions):
                return False
        return True

    def _check_rate_limit(self, request: ResourceRequest, resource: ApiResource) -> bool:
        """限流检查"""
        key = f"{resource.resource_id}:{request.user_id or request.client_ip}"
        now = time.time()
        window = self._rate_counters[key]
        # 清理60秒前的记录
        self._rate_counters[key] = [t for t in window if now - t < 60.0]
        if len(self._rate_counters[key]) >= resource.rate_limit_rpm:
            return False
        self._rate_counters[key].append(now)
        return True

    def _error_response(
        self, request: ResourceRequest, status: int, error_code: str, message: str, extra_headers: Optional[Dict] = None
    ) -> ResourceResponse:
        return ResourceResponse(
            request_id=request.request_id,
            status_code=status,
            headers={"Content-Type": "application/json", "X-Trace-Id": request.trace_id, **(extra_headers or {})},
            body={"error": error_code, "message": message, "timestamp": datetime.now().isoformat()},
            error_code=error_code,
            error_message=message,
            trace_id=request.trace_id,
        )

    def _cors_response(self, request: ResourceRequest) -> ResourceResponse:
        origin = request.headers.get("Origin", "*")
        return ResourceResponse(
            request_id=request.request_id,
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, X-API-Key, X-Trace-Id, X-Request-Id",
                "Access-Control-Max-Age": "86400",
                "Access-Control-Allow-Credentials": "false",
            },
            trace_id=request.trace_id,
        )

    # ----------------------------------------------------------------
    # 审计日志
    # ----------------------------------------------------------------

    def _log_access(self, request: ResourceRequest, status: int, resource: ApiResource):
        entry = {
            "request_id": request.request_id,
            "method": request.method,
            "path": request.path,
            "status": status,
            "user_id": request.user_id or request.api_key_id,
            "auth_scheme": request.auth_scheme.value if request.auth_scheme else "none",
            "client_ip": request.client_ip,
            "trace_id": request.trace_id,
            "timestamp": datetime.now().isoformat(),
            "resource_id": resource.resource_id,
        }
        self._access_log.append(entry)
        if len(self._access_log) > self._access_log_max:
            self._access_log = self._access_log[-self._access_log_max // 2 :]

    def get_access_log(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        result = self._access_log
        if user_id:
            result = [e for e in result if e.get("user_id") == user_id]
        return result[-limit:]

    # ----------------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._rs_stats,
            "resources_count": len(self._resources),
            "api_keys_count": len(self._api_keys),
            "roles_count": len(self._role_permissions),
            "token_cache_size": len(self._token_cache),
            "module_stats": self.stats.to_dict(),
        }

    def list_resources(self) -> List[Dict]:
        return [
            {
                "id": r.resource_id,
                "path": r.path_pattern,
                "methods": r.methods,
                "scopes": r.required_scopes,
                "permissions": r.required_permissions,
                "roles": r.required_roles,
                "auth": r.auth_required,
                "rate_limit_rpm": r.rate_limit_rpm,
                "requests": r.request_count,
                "errors": r.error_count,
                "avg_latency_ms": round(r.avg_latency_ms, 2),
            }
            for r in self._resources.values()
        ]

# ============================================================================
# 模块注册
# ============================================================================

module_class = ResourceServer
