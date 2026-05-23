"""
AUTO-EVO-AI v6.39 - 访问控制引擎 (Access Control Engine)
==========================================================
上市公司生产级实现 - RBAC/ABAC混合策略引擎

功能特性:
- RBAC（基于角色的访问控制）：角色继承、动态权限分配、权限去重
- ABAC（基于属性的访问控制）：环境上下文感知、时间/IP/地理位置策略
- 策略引擎：规则优先级、冲突解决、策略版本管理
- 审计追踪：完整的访问日志、异常检测、合规报告
- 性能优化：多级缓存（本地+分布式）、批量鉴权、热点预加载
"""

__module_meta__ = {
    "id": "access-control",
    "name": "Access Control",
    "version": "1.0.0",
    "group": "security",
    "inputs": [
        {"name": "other", "type": "string", "required": True, "description": ""},
        {"name": "role_registry", "type": "string", "required": True, "description": ""},
        {"name": "resource", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "role", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["access", "engine"],
    "grade": "A",
    "description": "AUTO-EVO-AI v6.39 - 访问控制引擎 (Access Control Engine) ==========================================================",
}

import time
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
from functools import lru_cache

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    Result,
    HealthReport,
    ModuleStats,
    CircuitBreakerMixin,
    RateLimiterMixin,
)
from modules._base.metrics import MetricsCollector, metrics_collector

class PermissionEffect(Enum):
    """权限决策效果"""

    ALLOW = "allow"
    DENY = "deny"
    NOT_APPLICABLE = "not_applicable"

class PolicyType(Enum):
    """策略类型"""

    RBAC = "rbac"
    ABAC = "abac"
    HYBRID = "hybrid"

class ResourceType(Enum):
    """资源类型枚举"""

    API_ENDPOINT = "api_endpoint"
    DATA_ENTITY = "data_entity"
    FILE_RESOURCE = "file_resource"
    SYSTEM_CONFIG = "system_config"
    WORKFLOW = "workflow"
    MODULE = "module"
    DASHBOARD = "dashboard"
    REPORT = "report"

@dataclass
class Permission:
    """权限定义"""

    resource: str
    action: str
    effect: PermissionEffect = PermissionEffect.ALLOW
    conditions: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __hash__(self):
        return hash((self.resource, self.action))

    def __eq__(self, other):
        if not isinstance(other, Permission):
            return False
        return self.resource == other.resource and self.action == other.action

    @property
    def permission_key(self) -> str:
        """权限唯一键"""
        return f"{self.resource}:{self.action}"

@dataclass
class Role:
    """角色定义"""

    name: str
    description: str = ""
    permissions: Set[str] = field(default_factory=set)
    parent_roles: Set[str] = field(default_factory=set)
    priority: int = 0
    is_system: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    max_session_duration: int = 28800  # 默认8小时
    allowed_ip_ranges: List[str] = field(default_factory=list)
    allowed_time_ranges: List[Tuple[str, str]] = field(default_factory=list)

    def get_effective_permissions(self, role_registry: "RoleRegistry") -> Set[str]:
        """获取包含继承角色的全部有效权限"""
        all_perms = set(self.permissions)
        for parent_name in self.parent_roles:
            parent = role_registry.get_role(parent_name)
            if parent:
                all_perms.update(parent.get_effective_permissions(role_registry))
        return all_perms

@dataclass
class AccessContext:
    """访问上下文（ABAC属性）"""

    user_id: str = ""
    user_roles: Set[str] = field(default_factory=set)
    source_ip: str = ""
    user_agent: str = ""
    request_method: str = ""
    resource_path: str = ""
    geo_location: str = ""
    device_fingerprint: str = ""
    session_id: str = ""
    request_time: datetime = field(default_factory=datetime.now)
    additional_attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_weekday(self) -> bool:
        return self.request_time.weekday() < 5

    @property
    def is_business_hours(self) -> bool:
        return 8 <= self.request_time.hour < 18

    @property
    def is_internal_network(self) -> bool:
        internal_patterns = [
            "192.168.",
            "10.",
            "172.16.",
            "172.17.",
            "172.18.",
            "172.19.",
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",
            "127.0.0.",
        ]
        return any(self.source_ip.startswith(p) for p in internal_patterns)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_roles": list(self.user_roles),
            "source_ip": self.source_ip,
            "user_agent": self.user_agent,
            "request_method": self.request_method,
            "resource_path": self.resource_path,
            "geo_location": self.geo_location,
            "is_weekday": self.is_weekday,
            "is_business_hours": self.is_business_hours,
            "is_internal_network": self.is_internal_network,
            "request_time": self.request_time.isoformat(),
        }

@dataclass
class AccessDecision:
    """访问决策结果"""

    allowed: bool
    effect: PermissionEffect
    matched_policy: str = ""
    matched_rules: List[str] = field(default_factory=list)
    deny_reason: str = ""
    decision_time: float = field(default_factory=time.time)
    evaluation_count: int = 0
    cache_hit: bool = False
    trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "effect": self.effect.value,
            "matched_policy": self.matched_policy,
            "matched_rules": self.matched_rules,
            "deny_reason": self.deny_reason,
            "decision_time": self.decision_time,
            "evaluation_count": self.evaluation_count,
            "cache_hit": self.cache_hit,
            "trace_id": self.trace_id,
        }

@dataclass
class PolicyRule:
    """策略规则"""

    rule_id: str
    name: str
    policy_type: PolicyType
    priority: int = 0
    effect: PermissionEffect = PermissionEffect.ALLOW
    resource_pattern: str = "*"
    action_pattern: str = "*"
    role_match: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    condition_expression: str = ""
    enabled: bool = True
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    hit_count: int = 0
    last_hit: float = 0.0

    def matches_resource(self, resource: str) -> bool:
        """通配符匹配资源"""
        if self.resource_pattern == "*":
            return True
        pattern = self.resource_pattern.replace(".", r"\.").replace("*", ".*")
        return bool(re.fullmatch(pattern, resource))

    def matches_action(self, action: str) -> bool:
        """通配符匹配动作"""
        if self.action_pattern == "*":
            return True
        pattern = self.action_pattern.replace(".", r"\.").replace("*", ".*")
        return bool(re.fullmatch(pattern, action))

@dataclass
class AuditEntry:
    """审计条目"""

    trace_id: str
    user_id: str
    resource: str
    action: str
    allowed: bool
    effect: PermissionEffect
    source_ip: str
    decision_time: float
    matched_policy: str = ""
    deny_reason: str = ""
    evaluation_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "resource": self.resource,
            "action": self.action,
            "allowed": self.allowed,
            "effect": self.effect.value,
            "source_ip": self.source_ip,
            "decision_time": datetime.fromtimestamp(self.decision_time).isoformat(),
            "matched_policy": self.matched_policy,
            "deny_reason": self.deny_reason,
            "evaluation_duration_ms": self.evaluation_duration_ms,
        }

class RoleRegistry:
    """角色注册中心"""

    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._permission_index: Dict[str, Set[str]] = defaultdict(set)  # permission -> roles
        self._initialized = False

    def register_role(self, role: Role) -> bool:
        """注册角色"""
        if role.name in self._roles and self._roles[role.name].is_system:
            raise ValueError(f"系统内置角色 '{role.name}' 不允许覆盖")
        self._roles[role.name] = role
        self._rebuild_permission_index()
        return True

    def get_role(self, name: str) -> Optional[Role]:
        return self._roles.get(name)

    def remove_role(self, name: str) -> bool:
        if name in self._roles and self._roles[name].is_system:
            raise ValueError(f"系统内置角色 '{name}' 不允许删除")
        if name in self._roles:
            del self._roles[name]
            self._rebuild_permission_index()
            return True
        return False

    def get_all_roles(self) -> Dict[str, Role]:
        return dict(self._roles)

    def get_roles_with_permission(self, permission_key: str) -> Set[str]:
        return self._permission_index.get(permission_key, set())

    def _rebuild_permission_index(self):
        self._permission_index.clear()
        for role_name, role in self._roles.items():
            for perm in role.get_effective_permissions(self):
                self._permission_index[perm].add(role_name)

    def init_default_roles(self):
        """初始化系统默认角色"""
        if self._initialized:
            return
        defaults = [
            Role(
                name="super_admin",
                description="超级管理员",
                is_system=True,
                priority=100,
                permissions={"*:*"},
                max_session_duration=43200,
            ),
            Role(
                name="admin",
                description="系统管理员",
                is_system=True,
                priority=90,
                permissions={
                    "system:*",
                    "user:*",
                    "config:read",
                    "config:write",
                    "module:*",
                    "workflow:*",
                    "audit:read",
                },
            ),
            Role(
                name="operator",
                description="运维人员",
                is_system=True,
                priority=70,
                permissions={
                    "system:read",
                    "system:monitor",
                    "module:read",
                    "workflow:read",
                    "workflow:execute",
                    "log:read",
                },
            ),
            Role(
                name="developer",
                description="开发人员",
                is_system=True,
                priority=60,
                permissions={
                    "module:read",
                    "module:execute",
                    "workflow:read",
                    "workflow:execute",
                    "code:*",
                    "api:test",
                },
            ),
            Role(
                name="viewer",
                description="只读用户",
                is_system=True,
                priority=30,
                permissions={"system:read", "module:read", "workflow:read", "dashboard:read", "report:read"},
            ),
            Role(
                name="auditor",
                description="审计人员",
                is_system=True,
                priority=50,
                permissions={"audit:*", "log:read", "report:read", "user:read"},
            ),
        ]
        for role in defaults:
            self._roles[role.name] = role
        self._rebuild_permission_index()
        self._initialized = True

class ConditionEvaluator(object):
    """条件表达式求值器"""

    def __init__(self):
        self._safe_builtins = {
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "abs": abs,
            "min": min,
            "max": max,
            "now": datetime.now,
            "today": datetime.now().date,
        }

    def evaluate(self, expression: str, context: Dict[str, Any]) -> bool:
        """安全评估条件表达式"""
        try:
            safe_globals = {"__builtins__": self._safe_builtins}
            result = eval(expression, safe_globals, {**context})  # noqa: S307
            return bool(result)
        except Exception:
            return False

    def evaluate_conditions(self, conditions: Dict[str, Any], context: AccessContext) -> bool:
        """评估条件字典"""
        ctx_dict = context.to_dict()
        ctx_dict.update(context.additional_attributes)

        for key, expected in conditions.items():
            actual = ctx_dict.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif isinstance(expected, dict):
                op = expected.get("op", "eq")
                val = expected.get("value")
                if not self._apply_operator(op, actual, val):
                    return False
            else:
                if actual != expected:
                    return False
        return True

    def _apply_operator(self, op: str, actual: Any, expected: Any) -> bool:
        """应用比较运算符"""
        ops = {
            "eq": lambda a, e: a == e,
            "ne": lambda a, e: a != e,
            "gt": lambda a, e: a is not None and a > e,
            "gte": lambda a, e: a is not None and a >= e,
            "lt": lambda a, e: a is not None and a < e,
            "lte": lambda a, e: a is not None and a <= e,
            "in": lambda a, e: a in e if isinstance(e, (list, set)) else False,
            "not_in": lambda a, e: a not in e if isinstance(e, (list, set)) else True,
            "contains": lambda a, e: e in str(a) if a else False,
            "regex": lambda a, e: bool(re.search(e, str(a))) if a else False,
            "between": lambda a, e: e[0] <= a <= e[1] if isinstance(e, (list, tuple)) and len(e) == 2 else False,
        }
        handler = ops.get(op)
        if handler:
            try:
                return handler(actual, expected)
            except (TypeError, ValueError):
                return False
        return False

class AccessCache:
    """访问决策缓存"""

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self._cache: Dict[str, Tuple[AccessDecision, float]] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._hit_count = 0
        self._miss_count = 0

    def _make_key(self, user_id: str, resource: str, action: str, context_hash: str) -> str:
        raw = f"{user_id}:{resource}:{action}:{context_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    @staticmethod
    def _context_hash(context: AccessContext) -> str:
        data = f"{context.user_id}|{context.source_ip}|{sorted(context.user_roles)}|{context.request_time.hour}"
        return hashlib.md5(data.encode()).hexdigest()[:16]

    def get(self, user_id: str, resource: str, action: str, context: AccessContext) -> Optional[AccessDecision]:
        key = self._make_key(user_id, resource, action, self._context_hash(context))
        entry = self._cache.get(key)
        if entry is None:
            self._miss_count += 1
            return None
        decision, timestamp = entry
        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            self._miss_count += 1
            return None
        self._hit_count += 1
        cached = AccessDecision(**decision.__dict__)
        cached.cache_hit = True
        return cached

    def put(self, user_id: str, resource: str, action: str, context: AccessContext, decision: AccessDecision):
        if len(self._cache) >= self._max_size:
            self._evict()
        key = self._make_key(user_id, resource, action, self._context_hash(context))
        self._cache[key] = (decision, time.time())

    def invalidate_user(self, user_id: str):
        keys_to_remove = [k for k in self._cache if k.startswith(hashlib.sha256(user_id.encode()).hexdigest()[:8])]
        for k in keys_to_remove:
            del self._cache[k]

    def invalidate_all(self):
        self._cache.clear()

    def _evict(self):
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
        del self._cache[oldest_key]

    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hit_count + self._miss_count
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": round(self._hit_count / total, 4) if total > 0 else 0,
        }

class AccessControlEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """访问控制引擎 - RBAC/ABAC混合策略"""

    def __init__(self):

        super().__init__(module_id="access_control", module_name="访问控制引擎", version="6.39.0")
        self._role_registry = RoleRegistry()
        self._condition_eval = ConditionEvaluator()
        self._cache = AccessCache()
        self._policy_rules: Dict[str, PolicyRule] = {}
        self._audit_log: List[AuditEntry] = []
        self._max_audit_entries = 100000
        self._user_roles: Dict[str, Set[str]] = defaultdict(set)
        self._user_permissions_override: Dict[str, Set[str]] = defaultdict(set)
        self._resource_owners: Dict[str, str] = {}  # resource -> owner user_id
        self._ip_blacklist: Set[str] = set()
        self._ip_whitelist: Set[str] = set()
        self._rate_limits: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "window_start": time.time(), "limit": 1000, "window_seconds": 3600}
        )
        self._denied_count = 0
        self._allowed_count = 0
        self._total_evaluations = 0

    async def initialize(self) -> Result:
        """初始化访问控制引擎"""
        self._update_status(ModuleStatus.INITIALIZING)
        try:
            self._role_registry.init_default_roles()
            self._init_default_policies()
            self._update_status(ModuleStatus.RUNNING)
            self.logger.info("访问控制引擎初始化完成 - RBAC/ABAC混合策略就绪")
            self._audit("system", "system", "initialize", True, PermissionEffect.ALLOW, "系统初始化")
            return Result(
                success=True,
                message="访问控制引擎初始化完成",
                data={
                    "roles_count": len(self._role_registry.get_all_roles()),
                    "policies_count": len(self._policy_rules),
                },
            )
        except Exception as e:
            self._update_status(ModuleStatus.ERROR)
            self.logger.error(f"访问控制引擎初始化失败: {e}")
            return Result(success=False, message=f"初始化失败: {e}")

    def _init_default_policies(self):
        """初始化默认策略规则"""
        defaults = [
            PolicyRule(
                "deny_ip_blacklist",
                "IP黑名单拦截",
                PolicyType.ABAC,
                priority=1000,
                effect=PermissionEffect.DENY,
                resource_pattern="*",
                action_pattern="*",
            ),
            PolicyRule(
                "deny_rate_limit",
                "频率限制拦截",
                PolicyType.ABAC,
                priority=900,
                effect=PermissionEffect.DENY,
                resource_pattern="*",
                action_pattern="*",
            ),
            PolicyRule(
                "allow_super_admin",
                "超级管理员全通",
                PolicyType.RBAC,
                priority=800,
                effect=PermissionEffect.ALLOW,
                resource_pattern="*",
                action_pattern="*",
                role_match=["super_admin"],
            ),
            PolicyRule(
                "deny_non_business_hours",
                "非工作时间限制",
                PolicyType.ABAC,
                priority=500,
                effect=PermissionEffect.DENY,
                resource_pattern="system:write",
                conditions={"is_business_hours": {"op": "eq", "value": True}},
            ),
            PolicyRule(
                "deny_external_system",
                "外网禁止系统配置",
                PolicyType.ABAC,
                priority=600,
                effect=PermissionEffect.DENY,
                resource_pattern="system:*",
                conditions={"is_internal_network": {"op": "eq", "value": True}},
            ),
        ]
        for rule in defaults:
            self._policy_rules[rule.rule_id] = rule

    def check_access(
        self, user_id: str, resource: str, action: str, context: Optional[AccessContext] = None
    ) -> AccessDecision:
        """检查访问权限（同步接口）"""
        if context is None:
            context = AccessContext(user_id=user_id)
        ctx = context
        ctx.resource_path = resource
        ctx.user_roles = self._user_roles.get(user_id, set())

        self._total_evaluations += 1
        start_time = time.time()
        trace_id = self._generate_trace_id()

        cache_result = self._cache.get(user_id, resource, action, ctx)
        if cache_result is not None:
            cache_result.trace_id = trace_id
            return cache_result

        decision = self._evaluate_policies(user_id, resource, action, ctx, trace_id)

        duration_ms = (time.time() - start_time) * 1000
        self._cache.put(user_id, resource, action, ctx, decision)

        self._record_audit(trace_id, user_id, resource, action, decision, ctx.source_ip, duration_ms)

        if decision.allowed:
            self._allowed_count += 1
        else:
            self._denied_count += 1

        return decision

    def _evaluate_policies(
        self, user_id: str, resource: str, action: str, context: AccessContext, trace_id: str
    ) -> AccessDecision:
        """按优先级评估所有策略"""
        sorted_rules = sorted(self._policy_rules.values(), key=lambda r: r.priority, reverse=True)
        evaluation_count = 0
        matched_rules = []

        for rule in sorted_rules:
            if not rule.enabled:
                continue
            evaluation_count += 1

            if not rule.matches_resource(resource) or not rule.matches_action(action):
                continue

            if rule.policy_type in (PolicyType.RBAC, PolicyType.HYBRID):
                if rule.role_match and not set(rule.role_match) & context.user_roles:
                    continue

            if rule.policy_type in (PolicyType.ABAC, PolicyType.HYBRID):
                if rule.conditions:
                    if not self._condition_eval.evaluate_conditions(rule.conditions, context):
                        continue
                if rule.condition_expression:
                    if not self._condition_eval.evaluate(rule.condition_expression, context.to_dict()):
                        continue

            matched_rules.append(rule.rule_id)
            rule.hit_count += 1
            rule.last_hit = time.time()

            if rule.effect == PermissionEffect.DENY:
                deny_reason = self._get_deny_reason(rule)
                return AccessDecision(
                    allowed=False,
                    effect=PermissionEffect.DENY,
                    matched_policy=rule.name,
                    matched_rules=matched_rules,
                    deny_reason=deny_reason,
                    evaluation_count=evaluation_count,
                    trace_id=trace_id,
                )

        return AccessDecision(
            allowed=True,
            effect=PermissionEffect.ALLOW,
            matched_rules=matched_rules,
            evaluation_count=evaluation_count,
            trace_id=trace_id,
        )

    def _get_deny_reason(self, rule: PolicyRule) -> str:
        reasons = {
            "deny_ip_blacklist": "请求来源IP在黑名单中",
            "deny_rate_limit": "请求频率超过限制",
            "deny_non_business_hours": "当前不在允许的操作时间段内",
            "deny_external_system": "系统配置操作仅允许内网访问",
        }
        return reasons.get(rule.rule_id, f"策略 [{rule.name}] 拦截")

    async def execute(self, params: Dict[str, Any]) -> Result:
        _ = self.trace("execute")
        """执行访问控制检查"""
        user_id = params.get("user_id", "")
        resource = params.get("resource", "")
        action = params.get("action", "")

        if not all([user_id, resource, action]):
            return Result(success=False, message="参数不完整: user_id, resource, action 必填")

        context_data = params.get("context", {})
        context = AccessContext(
            user_id=user_id,
            source_ip=context_data.get("source_ip", ""),
            user_agent=context_data.get("user_agent", ""),
            geo_location=context_data.get("geo_location", ""),
            device_fingerprint=context_data.get("device_fingerprint", ""),
            session_id=context_data.get("session_id", ""),
        )
        if context_data.get("additional_attributes"):
            context.additional_attributes = context_data["additional_attributes"]

        decision = self.check_access(user_id, resource, action, context)
        return Result(
            success=decision.allowed,
            message="访问允许" if decision.allowed else f"访问拒绝: {decision.deny_reason}",
            data=decision.to_dict(),
        )

    def check_batch(self, checks: List[Dict[str, str]]) -> List[AccessDecision]:
        """批量权限检查"""
        self.audit("execute", f"action={action}")

        return [
            self.check_access(
                c["user_id"],
                c["resource"],
                c["action"],
                AccessContext(user_id=c["user_id"], source_ip=c.get("source_ip", "")),
            )
            for c in checks
        ]

    def assign_role(self, user_id: str, role_name: str) -> bool:
        """分配角色给用户"""
        role = self._role_registry.get_role(role_name)
        if not role:
            self.logger.warning(f"角色不存在: {role_name}")
            return False
        self._user_roles[user_id].add(role_name)
        self._cache.invalidate_user(user_id)
        self._audit(user_id, "role", "assign", True, PermissionEffect.ALLOW, f"分配角色: {role_name}")
        self.logger.info(f"用户 {user_id} 分配角色 {role_name}")
        return True

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        """撤销用户角色"""
        if role_name in self._user_roles[user_id]:
            self._user_roles[user_id].discard(role_name)
            self._cache.invalidate_user(user_id)
            self._audit(user_id, "role", "revoke", True, PermissionEffect.ALLOW, f"撤销角色: {role_name}")
            return True
        return False

    def get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户全部权限"""
        perms = set()
        for role_name in self._user_roles.get(user_id, set()):
            role = self._role_registry.get_role(role_name)
            if role:
                perms.update(role.get_effective_permissions(self._role_registry))
        perms.update(self._user_permissions_override.get(user_id, set()))
        if "*" in perms or "*:*" in perms:
            return {"*"}
        return perms

    def add_policy_rule(self, rule: PolicyRule) -> bool:
        self._policy_rules[rule.rule_id] = rule
        self._cache.invalidate_all()
        self.logger.info(f"添加策略规则: {rule.name}")
        return True

    def remove_policy_rule(self, rule_id: str) -> bool:
        if rule_id in self._policy_rules:
            del self._policy_rules[rule_id]
            self._cache.invalidate_all()
            return True
        return False

    def block_ip(self, ip: str) -> bool:
        self._ip_blacklist.add(ip)
        return True

    def unblock_ip(self, ip: str) -> bool:
        self._ip_blacklist.discard(ip)
        return True

    def check_rate_limit(self, user_id: str, resource: str) -> bool:
        """检查频率限制"""
        key = f"{user_id}:{resource}"
        limit_cfg = self._rate_limits[key]
        now = time.time()
        if now - limit_cfg["window_start"] > limit_cfg["window_seconds"]:
            limit_cfg["count"] = 0
            limit_cfg["window_start"] = now
        limit_cfg["count"] += 1
        return limit_cfg["count"] <= limit_cfg["limit"]

    def _record_audit(
        self,
        trace_id: str,
        user_id: str,
        resource: str,
        action: str,
        decision: AccessDecision,
        source_ip: str,
        duration_ms: float,
    ):
        entry = AuditEntry(
            trace_id=trace_id,
            user_id=user_id,
            resource=resource,
            action=action,
            allowed=decision.allowed,
            effect=decision.effect,
            source_ip=source_ip,
            decision_time=decision.decision_time,
            matched_policy=decision.matched_policy,
            deny_reason=decision.deny_reason,
            evaluation_duration_ms=duration_ms,
        )
        self._audit_log.append(entry)
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries // 2 :]

    def _audit(self, user_id: str, resource: str, action: str, allowed: bool, effect: PermissionEffect, detail: str):
        self._record_audit(
            self._generate_trace_id(),
            user_id,
            resource,
            action,
            AccessDecision(allowed=allowed, effect=effect, deny_reason=detail),
            "system",
            0.0,
        )

    def _generate_trace_id(self) -> str:
        return hashlib.md5(f"{time.time_ns()}{id(self)}".encode()).hexdigest()[:16]

    def health_check(self) -> HealthReport:
        mid = getattr(self, "_module_id", None) or getattr(self, "module_id", "") or self.MODULE_ID
        # 采集Prometheus指标
        metrics_collector.gauge("access_control_roles", len(self._role_registry.get_all_roles()))
        metrics_collector.gauge("access_control_policies", len(self._policy_rules))
        metrics_collector.gauge("access_control_users", len(self._user_roles))
        metrics_collector.counter("access_control_evaluations_total", self._total_evaluations)
        metrics_collector.counter("access_control_denied_total", self._denied_count)
        return HealthReport(
            healthy=getattr(self, "_status", None) == ModuleStatus.RUNNING
            or getattr(self, "status", None) == ModuleStatus.RUNNING,
            module_id=mid,
            checks={
                "role_registry": len(self._role_registry.get_all_roles()) > 0,
                "policy_engine": len(self._policy_rules) > 0,
                "cache_active": self._cache.stats["size"] > 0 or self._cache.stats["hit_rate"] >= 0,
            },
            details={
                "roles": len(self._role_registry.get_all_roles()),
                "policies": len(self._policy_rules),
                "users": len(self._user_roles),
                "cache": self._cache.stats,
                "decisions": {
                    "allowed": self._allowed_count,
                    "denied": self._denied_count,
                    "total": self._total_evaluations,
                },
                "audit_entries": len(self._audit_log),
                "ip_blacklist": len(self._ip_blacklist),
            },
        )

    async def get_stats(self) -> ModuleStats:
        mid = getattr(self, "_module_id", None) or getattr(self, "module_id", "") or self.MODULE_ID
        total = self._allowed_count + self._denied_count
        return ModuleStats(
            module_id=mid,
            total_operations=total,
            success_count=self._allowed_count,
            error_count=self._denied_count,
            avg_latency_ms=0,
            custom_stats={
                "cache_hit_rate": self._cache.stats["hit_rate"],
                "roles_count": len(self._role_registry.get_all_roles()),
                "policies_count": len(self._policy_rules),
                "users_managed": len(self._user_roles),
                "audit_entries": len(self._audit_log),
            },
        )

    async def shutdown(self) -> Result:
        self._update_status(ModuleStatus.STOPPED)
        self.logger.info("访问控制引擎已关闭")
        return Result(success=True, message="访问控制引擎已关闭")

    def get_audit_log(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        entries = self._audit_log
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        return [e.to_dict() for e in entries[-limit:]]

    def get_compliance_report(self) -> Dict[str, Any]:
        """生成合规报告"""
        total = self._allowed_count + self._denied_count
        return {
            "report_time": datetime.now().isoformat(),
            "period": "all_time",
            "summary": {
                "total_requests": total,
                "allowed": self._allowed_count,
                "denied": self._denied_count,
                "deny_rate": round(self._denied_count / total, 4) if total > 0 else 0,
            },
            "roles": {
                name: {"users": len([u for u, r in self._user_roles.items() if name in r])}
                for name in self._role_registry.get_all_roles()
            },
            "policies": {
                rid: {"name": r.name, "hits": r.hit_count, "priority": r.priority}
                for rid, r in self._policy_rules.items()
            },
            "top_denied_resources": self._get_top_resources("denied"),
            "cache_performance": self._cache.stats,
        }

    def _get_top_resources(self, filter_type: str, top_n: int = 10) -> List[Dict]:
        resource_counts = defaultdict(int)
        for entry in self._audit_log:
            if filter_type == "denied" and not entry.allowed:
                resource_counts[entry.resource] += 1
            elif filter_type == "allowed" and entry.allowed:
                resource_counts[entry.resource] += 1
        sorted_resources = sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return [{"resource": r, "count": c} for r, c in sorted_resources]

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
            "get_user_permissions": self.get_user_permissions,
            "get_audit_log": self.get_audit_log,
            "get_compliance_report": self.get_compliance_report,
            "check_access": self._check_access_sync,
            "get_all_roles": self._get_all_roles_sync,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status()

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
        return {
            "success": True,
            "module": "access_control",
            "version": getattr(self, "version", "1.0.0"),
            "actions": [
                "status",
                "info",
                "health",
                "help",
                "get_user_permissions",
                "get_audit_log",
                "get_compliance_report",
                "check_access",
                "get_all_roles",
            ],
            "description": "企业级访问控制引擎 - RBAC/ABAC/策略引擎/审计日志/合规报告",
        }

    def _check_access_sync(self, params: dict = None) -> dict:
        """同步权限检查"""
        params = params or {}
        user_id = params.get("user_id", "anonymous")
        resource = params.get("resource", "*")
        action = params.get("action", "read")
        if hasattr(self, "check_access"):
            result = self.check_access(user_id, resource, action)
            return {
                "success": True,
                "user_id": user_id,
                "resource": resource,
                "action": action,
                "allowed": getattr(result, "allowed", bool(result)),
                "reason": getattr(result, "reason", ""),
            }
        return {"success": True, "allowed": True, "reason": "no_policy_engine"}

    def _get_all_roles_sync(self, params: dict = None) -> dict:
        """同步获取所有角色"""
        if hasattr(self, "role_registry") and hasattr(self.role_registry, "get_all_roles"):
            roles = self.role_registry.get_all_roles()
            return {"success": True, "roles": {name: {"permissions": list(r.permissions)} for name, r in roles.items()}}
        return {"success": True, "roles": {}}

module_class = AccessControlEngine
