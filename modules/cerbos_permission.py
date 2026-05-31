"""
AUTO-EVO-AI V0.1 — Cerbos权限策略引擎模块
Grade: A (生产级) | Category: 安全与权限
职责：基于策略的细粒度访问控制，支持ABAC/RBAC混合模型，资源级权限校验
"""

__module_meta__ = {
        "id": "cerbos-permission",
        "name": "Cerbos Permission",
        "version": "V0.1",
        "group": "security",
        "inputs": [
            {
                "name": "operation",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "params",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "condition",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "principal",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "resource",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "principal_2",
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
                "name": "success",
                "type": "bool",
                "description": "是否成功"
            },
            {
                "name": "results",
                "type": "list[dict]",
                "description": "结果列表"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "cerbos",
            "manager"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — Cerbos权限策略引擎模块 Grade: A (生产级) | Category: 安全与权限"
    }

import os
import asyncio
import time
import logging
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from modules._base.enterprise_module import EnterpriseModule
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger(__name__)

class Effect(Enum):
    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"

class ConditionOp(Enum):
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NOT_IN = "not_in"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    MATCHES = "matches"
    CONTAINS = "contains"

@dataclass
class Condition:
    field: str
    op: ConditionOp
    value: Any
    negate: bool = False

@dataclass
class PolicyRule:
    rule_id: str
    name: str
    resource: str
    action: str
    effect: Effect
    roles: List[str] = field(default_factory=list)
    conditions: List[Condition] = field(default_factory=list)
    derived_roles: List[str] = field(default_factory=list)
    priority: int = 100
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class RoleDefinition:
    role_id: str
    name: str
    description: str = ""
    parent_roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DerivedRole:
    role_id: str
    name: str
    condition: Condition = None

@dataclass
class Principal:
    id: str
    roles: List[str] = field(default_factory=list)
    attr: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Resource:
    id: str
    kind: str
    attr: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AccessLog:
    log_id: str
    timestamp: datetime
    principal_id: str
    resource_kind: str
    resource_id: str
    action: str
    effect: str
    matched_policy: str
    decision_ms: float

class CerbosPermissionManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    Cerbos风格权限策略管理器
    功能：策略管理、权限评估、角色继承、属性条件、访问审计
    """

    def __init__(self):

        super().__init__()
        self._audit = None

        self.module_name = "cerbos_permission"
        self.module_id = self.module_name
        self.module_version = "2.0.0"
        self._initialized = False
        self._policies: Dict[str, PolicyRule] = {}
        self._roles: Dict[str, RoleDefinition] = {}
        self._derived_roles: Dict[str, DerivedRole] = {}
        self._access_logs: List[AccessLog] = []
        self._decision_cache: Dict[str, Tuple[str, float]] = {}
        self._cache_ttl = 300
        self._eval_count = 0
        self._allow_count = 0
        self._deny_count = 0

    def initialize(self) -> None:
        if self._initialized:
            return
        # 初始化默认角色
        default_roles = {
            "admin": RoleDefinition("admin", "系统管理员", "拥有全部权限", permissions=["*:*"]),
            "manager": RoleDefinition(
                "manager",
                "管理者",
                "管理资源",
                parent_roles=["viewer"],
                permissions=["resource:*", "user:read", "user:write"],
            ),
            "viewer": RoleDefinition("viewer", "查看者", "只读权限", permissions=["*:read", "*:list"]),
            "editor": RoleDefinition(
                "editor",
                "编辑者",
                "编辑内容",
                parent_roles=["viewer"],
                permissions=["content:write", "content:delete", "media:*"],
            ),
            "auditor": RoleDefinition(
                "auditor", "审计员", "审计日志访问", permissions=["audit:read", "audit:export", "log:*"]
            ),
            "api_user": RoleDefinition("api_user", "API用户", "API访问权限", permissions=["api:access", "api:read"]),
        }
        self._roles.update(default_roles)

        # 初始化派生角色
        self._derived_roles["resource_owner"] = DerivedRole(
            "resource_owner", "资源所有者", Condition("resource.attr.owner_id", ConditionOp.EQ, "principal.id")
        )
        self._derived_roles["department_member"] = DerivedRole(
            "department_member",
            "同部门成员",
            Condition("principal.attr.department", ConditionOp.EQ, "resource.attr.department"),
        )

        # 初始化默认策略
        default_policies = [
            PolicyRule("p-admin-all", "管理员全权限", "*", "*", Effect.ALLOW, roles=["admin"], priority=1),
            PolicyRule(
                "p-viewer-read",
                "查看者只读",
                "*",
                "read|list",
                Effect.ALLOW,
                roles=["viewer", "manager", "editor"],
                priority=50,
            ),
            PolicyRule(
                "p-editor-content",
                "编辑内容权限",
                "content|media",
                "write|delete",
                Effect.ALLOW,
                roles=["editor", "manager"],
                priority=20,
            ),
            PolicyRule(
                "p-manager-resource", "管理资源权限", "resource", "*", Effect.ALLOW, roles=["manager"], priority=30
            ),
            PolicyRule(
                "p-owner-write",
                "所有者写入",
                "*",
                "write|delete",
                Effect.ALLOW,
                derived_roles=["resource_owner"],
                priority=5,
            ),
            PolicyRule(
                "p-dept-read", "同部门读取", "*", "read", Effect.ALLOW, derived_roles=["department_member"], priority=10
            ),
            PolicyRule(
                "p-audit-log", "审计员日志", "audit|log", "read|export", Effect.ALLOW, roles=["auditor"], priority=15
            ),
            PolicyRule(
                "p-deny-sensitive",
                "敏感数据限制",
                "user_profile|salary|secret",
                "*",
                Effect.DENY,
                roles=["viewer", "api_user"],
                priority=3,
            ),
            PolicyRule(
                "p-api-access", "API访问", "api", "access|read", Effect.ALLOW, roles=["api_user", "admin"], priority=40
            ),
            PolicyRule(
                "p-user-manage", "用户管理", "user", "write|delete|create", Effect.ALLOW, roles=["admin"], priority=2
            ),
        ]
        for p in default_policies:
            self._policies[p.rule_id] = p

        self._initialized = True
        logger.info(
            f"[{self.module_name}] 初始化完成，策略:{len(self._policies)} 角色:{len(self._roles)} 派生角色:{len(self._derived_roles)}"
        )

    async def execute(self, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("cerbos_ops_total", labels={"action": operation})
        self.audit("execute", f"operation={operation}")
        params = params or {}
        ops = {
            "check_permission": self._check_permission,
            "check_batch": self._check_batch,
            "add_policy": self._add_policy,
            "remove_policy": self._remove_policy,
            "list_policies": self._list_policies,
            "add_role": self._add_role,
            "remove_role": self._remove_role,
            "list_roles": self._list_roles,
            "assign_role": self._assign_role,
            "check_attribute": self._check_attribute,
            "get_access_logs": self._get_access_logs,
            "get_stats": self._get_stats,
            "simulate": self._simulate,
        }
        handler = ops.get(operation)
        if not handler:
            return {"success": False, "error": f"未知操作: {operation}"}
        try:
            if asyncio.iscoroutinefunction(handler):
                return handler(**params)
            return handler(**params)
        except Exception as e:
            logger.error(f"[{self.module_name}] 操作 {operation} 异常: {e}")
            return {"success": False, "error": str(e)}

    def _evaluate_condition(self, condition: Condition, principal: Principal, resource: Resource) -> bool:
        """评估条件表达式"""
        field_path = condition.field
        value = condition.value

        # 解析字段路径
        if field_path.startswith("principal."):
            obj = principal
            field_path = field_path[len("principal.") :]
        elif field_path.startswith("resource."):
            obj = resource
            field_path = field_path[len("resource.") :]
        else:
            obj = resource

        parts = field_path.split(".")
        actual = obj
        for p in parts:
            if isinstance(actual, dict):
                actual = actual.get(p)
            elif hasattr(actual, p):
                actual = getattr(actual, p)
            else:
                actual = None
                break

        result = False
        op = condition.op
        try:
            if op == ConditionOp.EQ:
                result = actual == value
            elif op == ConditionOp.NEQ:
                result = actual != value
            elif op == ConditionOp.IN:
                result = actual in value if isinstance(value, list) else False
            elif op == ConditionOp.NOT_IN:
                result = actual not in value if isinstance(value, list) else True
            elif op == ConditionOp.GT:
                result = float(actual) > float(value) if actual else False
            elif op == ConditionOp.GTE:
                result = float(actual) >= float(value) if actual else False
            elif op == ConditionOp.LT:
                result = float(actual) < float(value) if actual else False
            elif op == ConditionOp.LTE:
                result = float(actual) <= float(value) if actual else False
            elif op == ConditionOp.MATCHES:
                result = bool(re.match(str(value), str(actual))) if actual else False
            elif op == ConditionOp.CONTAINS:
                result = value in str(actual) if actual else False
        except (TypeError, ValueError):
            result = False

        return not result if condition.negate else result

    def _match_derived_roles(self, principal: Principal, resource: Resource) -> List[str]:
        """计算派生角色"""
        matched = []
        for role_id, dr in self._derived_roles.items():
            if dr.condition:
                try:
                    if self._evaluate_condition(dr.condition, principal, resource):
                        matched.append(role_id)
                except Exception:
                    pass
        return matched

    def _resolve_roles(self, role_ids: List[str]) -> Set[str]:
        """递归解析角色继承"""
        resolved = set()
        queue = list(role_ids)
        while queue:
            rid = queue.pop()
            if rid in resolved:
                continue
            resolved.add(rid)
            if rid in self._roles:
                for parent in self._roles[rid].parent_roles:
                    if parent not in resolved:
                        queue.append(parent)
        return resolved

    def _evaluate_single(self, principal: Principal, resource: Resource, action: str) -> Tuple[Effect, str]:
        """评估单个权限请求"""
        # 按优先级排序策略
        sorted_policies = sorted(self._policies.values(), key=lambda p: p.priority)

        # 计算派生角色
        derived = self._match_derived_roles(principal, resource)
        all_roles = self._resolve_roles(principal.roles)
        effective_roles = all_roles | set(derived)

        # 先检查DENY（最高优先级）
        for policy in sorted_policies:
            if not policy.enabled or policy.effect != Effect.DENY:
                continue
            # 匹配资源
            if policy.resource != "*" and not re.match(policy.resource, resource.kind):
                continue
            # 匹配动作
            if policy.action != "*" and not re.match(policy.action, action):
                continue
            # 匹配角色
            role_match = bool(set(policy.roles) & effective_roles)
            derived_match = bool(set(policy.derived_roles) & set(derived))
            if not (role_match or derived_match):
                continue
            # 评估条件
            conditions_met = all(self._evaluate_condition(c, principal, resource) for c in policy.conditions)
            if conditions_met:
                return Effect.DENY, policy.rule_id

        # 再检查ALLOW
        for policy in sorted_policies:
            if not policy.enabled or policy.effect != Effect.ALLOW:
                continue
            if policy.resource != "*" and not re.match(policy.resource, resource.kind):
                continue
            if policy.action != "*" and not re.match(policy.action, action):
                continue
            role_match = bool(set(policy.roles) & effective_roles)
            derived_match = bool(set(policy.derived_roles) & set(derived))
            if not (role_match or derived_match):
                continue
            conditions_met = all(self._evaluate_condition(c, principal, resource) for c in policy.conditions)
            if conditions_met:
                return Effect.ALLOW, policy.rule_id

        return Effect.DENY, "default_deny"

    def _check_permission(
        self,
        principal_id: str,
        roles: List[str],
        resource_kind: str,
        resource_id: str,
        action: str = "read",
        principal_attr: Dict = None,
        resource_attr: Dict = None,
    ) -> Dict:
        t0 = time.time()
        principal = Principal(principal_id, roles, principal_attr or {})
        resource = Resource(resource_id, resource_kind, resource_attr or {})

        # 检查缓存
        cache_key = f"{principal_id}:{resource_kind}:{resource_id}:{action}"
        if cache_key in self._decision_cache:
            cached_effect, cached_time = self._decision_cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                self._eval_count += 1
                return {
                    "success": True,
                    "result": {
                        "effect": cached_effect,
                        "principal": principal_id,
                        "resource": f"{resource_kind}:{resource_id}",
                        "action": action,
                        "cached": True,
                        "decision_ms": round((time.time() - t0) * 1000, 2),
                    },
                }

        effect, matched_policy = self._evaluate_single(principal, resource, action)
        decision_ms = round((time.time() - t0) * 1000, 2)
        self._decision_cache[cache_key] = (effect.value, time.time())
        self._eval_count += 1
        if effect == Effect.ALLOW:
            self._allow_count += 1
        else:
            self._deny_count += 1

        # 记录日志
        log = AccessLog(
            log_id=f"acl_{int(time.time() * 1000)}",
            timestamp=datetime.now(),
            principal_id=principal_id,
            resource_kind=resource_kind,
            resource_id=resource_id,
            action=action,
            effect=effect.value,
            matched_policy=matched_policy,
            decision_ms=decision_ms,
        )
        self._access_logs.append(log)

        return {
            "success": True,
            "result": {
                "effect": effect.value,
                "principal": principal_id,
                "resource": f"{resource_kind}:{resource_id}",
                "action": action,
                "matched_policy": matched_policy,
                "cached": False,
                "decision_ms": decision_ms,
            },
        }

    def _check_batch(self, requests: List[Dict]) -> Dict:
        results = []
        for req in requests:
            r = self._check_permission(**req)
            results.append(r["result"])
        return {"success": True, "result": results, "total": len(results)}

    def _add_policy(
        self,
        rule_id: str,
        name: str,
        resource: str,
        action: str,
        effect: str,
        roles: List[str] = None,
        derived_roles: List[str] = None,
        conditions: List[Dict] = None,
        priority: int = 100,
    ) -> Dict:
        if rule_id in self._policies:
            return {"success": False, "error": f"策略 {rule_id} 已存在"}
        cond_list = []
        for c in conditions or []:
            cond_list.append(Condition(c["field"], ConditionOp(c["op"]), c["value"], negate=c.get("negate", False)))
        policy = PolicyRule(
            rule_id,
            name,
            resource,
            action,
            Effect(effect),
            roles=roles or [],
            derived_roles=derived_roles or [],
            conditions=cond_list,
            priority=priority,
        )
        self._policies[rule_id] = policy
        return {"success": True, "result": {"policy_id": rule_id, "effect": effect}}

    def _remove_policy(self, rule_id: str) -> Dict:
        if rule_id not in self._policies:
            return {"success": False, "error": f"策略 {rule_id} 不存在"}
        del self._policies[rule_id]
        return {"success": True, "result": {"policy_id": rule_id, "removed": True}}

    def _list_policies(self, resource: str = None) -> Dict:
        policies = list(self._policies.values())
        if resource:
            policies = [p for p in policies if p.resource == resource or p.resource == "*"]
        result = [
            {
                "policy_id": p.rule_id,
                "name": p.name,
                "resource": p.resource,
                "action": p.action,
                "effect": p.effect.value,
                "roles": p.roles,
                "derived_roles": p.derived_roles,
                "conditions": len(p.conditions),
                "priority": p.priority,
                "enabled": p.enabled,
            }
            for p in sorted(policies, key=lambda p: p.priority)
        ]
        return {"success": True, "result": {"policies": result, "total": len(result)}}

    def _add_role(
        self,
        role_id: str,
        name: str,
        description: str = "",
        parent_roles: List[str] = None,
        permissions: List[str] = None,
    ) -> Dict:
        if role_id in self._roles:
            return {"success": False, "error": f"角色 {role_id} 已存在"}
        role = RoleDefinition(
            role_id, name, description, parent_roles=parent_roles or [], permissions=permissions or []
        )
        self._roles[role_id] = role
        return {"success": True, "result": {"role_id": role_id, "name": name}}

    def _remove_role(self, role_id: str) -> Dict:
        if role_id not in self._roles:
            return {"success": False, "error": f"角色 {role_id} 不存在"}
        del self._roles[role_id]
        return {"success": True, "result": {"role_id": role_id, "removed": True}}

    def _list_roles(self) -> Dict:
        result = [
            {
                "role_id": r.role_id,
                "name": r.name,
                "description": r.description,
                "parents": r.parent_roles,
                "permissions": r.permissions,
            }
            for r in self._roles.values()
        ]
        return {"success": True, "result": {"roles": result, "total": len(result)}}

    def _assign_role(self, principal_id: str, role_id: str) -> Dict:
        if role_id not in self._roles:
            return {"success": False, "error": f"角色 {role_id} 不存在"}
        return {
            "success": True,
            "result": {
                "principal": principal_id,
                "role": role_id,
                "inherited": self._roles[role_id].parent_roles,
            },
        }

    def _check_attribute(
        self,
        principal_id: str,
        roles: List[str],
        resource_kind: str,
        resource_id: str,
        action: str,
        field: str,
        op: str,
        value: Any,
    ) -> Dict:
        principal = Principal(principal_id, roles)
        resource = Resource(resource_id, resource_kind, {field: value})
        condition = Condition(field, ConditionOp(op), value)
        result = self._evaluate_condition(condition, principal, resource)
        return {"success": True, "result": {"condition_met": result, "field": field, "op": op, "value": value}}

    def _get_access_logs(self, principal_id: str = None, limit: int = 50) -> Dict:
        logs = self._access_logs
        if principal_id:
            logs = [l for l in logs if l.principal_id == principal_id]
        logs = logs[-limit:]
        result = [
            {
                "log_id": l.log_id,
                "principal": l.principal_id,
                "resource": f"{l.resource_kind}:{l.resource_id}",
                "action": l.action,
                "effect": l.effect,
                "policy": l.matched_policy,
                "ms": l.decision_ms,
                "timestamp": l.timestamp.isoformat(),
            }
            for l in logs
        ]
        return {"success": True, "result": {"logs": result, "total": len(result)}}

    def _get_stats(self) -> Dict:
        return {
            "success": True,
            "result": {
                "total_evaluations": self._eval_count,
                "allowed": self._allow_count,
                "denied": self._deny_count,
                "allow_rate": round(self._allow_count / max(self._eval_count, 1) * 100, 1),
                "policies": len(self._policies),
                "roles": len(self._roles),
                "derived_roles": len(self._derived_roles),
                "cache_entries": len(self._decision_cache),
                "log_entries": len(self._access_logs),
            },
        }

    def _simulate(
        self,
        principal_id: str,
        roles: List[str],
        resource_kind: str,
        resource_id: str,
        actions: List[str] = None,
        principal_attr: Dict = None,
        resource_attr: Dict = None,
    ) -> Dict:
        actions = actions or ["read", "write", "delete", "list"]
        results = []
        for action in actions:
            r = self._check_permission(
                principal_id=principal_id,
                roles=roles,
                resource_kind=resource_kind,
                resource_id=resource_id,
                action=action,
                principal_attr=principal_attr,
                resource_attr=resource_attr,
            )
            results.append({"action": action, "effect": r["result"]["effect"], "policy": r["result"]["matched_policy"]})
        return {
            "success": True,
            "result": {
                "principal": principal_id,
                "resource": f"{resource_kind}:{resource_id}",
                "effective_roles": list(self._resolve_roles(roles)),
                "decisions": results,
            },
        }

    def shutdown(self) -> None:
        self._decision_cache.clear()
        self._initialized = False
        logger.info(f"[{self.module_name}] 已关闭")

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check() if hasattr(super(), "health_check") else None
        result = dict(base) if base else {}
        result.update(
            {
                "status": "healthy" if self._initialized else "uninitialized",
                "module": self.module_name,
                "version": self.module_version,
                "policies": len(self._policies),
                "roles": len(self._roles),
                "derived_roles": len(self._derived_roles),
                "evaluations": self._eval_count,
                "cache_entries": len(self._decision_cache),
            }
        )
        return result

module_class = CerbosPermissionManager
