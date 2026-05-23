"""
AUTO-EVO-AI v6.38 — Enterprise Lifecycle Policy Manager
Production-grade resource lifecycle management with state machines, TTL enforcement,
automated transitions, compliance gating, and audit trail for上市企业生产级标准.
"""

__module_meta__ = {
    "id": "lifecycle-policy",
    "name": "Lifecycle Policy",
    "version": "1.0.0",
    "group": "storage",
    "inputs": [
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "resource_id", "type": "string", "required": True, "description": ""},
        {"name": "resource_type", "type": "string", "required": True, "description": ""},
        {"name": "policy_id", "type": "string", "required": True, "description": ""},
        {"name": "metadata", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["lifecycle", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI v6.38 — Enterprise Lifecycle Policy Manager Production-grade resource lifecycle management with state machines, TTL enforcement,",
}
import time
import json
import re
import logging
import threading
import hashlib
from typing import Any, Optional, Dict, List, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta

from modules._base.enterprise_module import EnterpriseModule
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.circuit_breaker import CircuitBreakerMixin
from modules._base.rate_limiter import RateLimiterMixin

class LifecycleState(Enum):
    """Standard lifecycle states aligned with ITIL/ISO20000."""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    DRAINING = "draining"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    TERMINATED = "terminated"

class TransitionTrigger(Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    TTL_EXPIRED = "ttl_expired"
    HEALTH_CHECK = "health_check"
    COMPLIANCE = "compliance"
    ALERT = "alert"
    API_CALL = "api_call"
    CRITICAL = "critical"

class PolicyAction(Enum):
    NOTIFY = "notify"
    TAG = "tag"
    SCALE_DOWN = "scale_down"
    BACKUP = "backup"
    MIGRATE = "migrate"
    CLEANUP = "cleanup"
    BLOCK = "block"
    ESCALATE = "escalate"

@dataclass
class TransitionRule:
    """Defines allowed state transitions with conditions."""

    from_state: LifecycleState
    to_state: LifecycleState
    trigger: TransitionTrigger = TransitionTrigger.MANUAL
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: List[PolicyAction] = field(default_factory=list)
    requires_approval: bool = False
    approval_roles: List[str] = field(default_factory=list)
    cooldown_seconds: int = 0
    max_per_hour: int = 0

@dataclass
class LifecyclePolicy:
    """A named policy governing resource lifecycle."""

    policy_id: str = ""
    name: str = ""
    description: str = ""
    resource_types: List[str] = field(default_factory=list)
    initial_state: LifecycleState = LifecycleState.PENDING
    default_ttl_seconds: int = 0
    transitions: List[TransitionRule] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    priority: int = 100
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1

@dataclass
class ResourceRecord:
    """Tracks a resource's lifecycle state."""

    resource_id: str
    resource_type: str
    policy_id: str
    state: LifecycleState
    entered_at: float = field(default_factory=time.time)
    ttl_seconds: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)
    transition_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_transition_at: float = 0.0
    terminated_at: float = 0.0
    version: int = 1

@dataclass
class TransitionEvent:
    """Audit record for state transitions."""

    event_id: str
    resource_id: str
    policy_id: str
    from_state: LifecycleState
    to_state: LifecycleState
    trigger: TransitionTrigger
    initiated_by: str
    timestamp: float = field(default_factory=time.time)
    actions_taken: List[str] = field(default_factory=list)
    duration_in_state: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""

MIXIN_AVAILABLE = True

class LifecyclePolicyManager(
    EnterpriseModule,
    CircuitBreakerMixin if MIXIN_AVAILABLE else object,
    RateLimiterMixin if MIXIN_AVAILABLE else object,
):
    """
    Enterprise lifecycle policy manager.

    Features:
    - State machine with configurable transitions
    - TTL-based automatic state transitions
    - Compliance gating with approval workflows
    - Rate limiting on transitions
    - Full audit trail
    - Resource tagging and labeling
    - Scheduled policy enforcement
    """

    def __init__(self):
        super().__init__()
        self._lock = threading.RLock()
        self._policies: Dict[str, LifecyclePolicy] = {}
        self._resources: Dict[str, ResourceRecord] = {}
        self._events: List[TransitionEvent] = []
        self._event_index: Dict[str, List[int]] = defaultdict(list)
        self._state_index: Dict[LifecycleState, Set[str]] = defaultdict(set)
        self._policy_index: Dict[str, Set[str]] = defaultdict(set)
        self._type_index: Dict[str, Set[str]] = defaultdict(set)
        self._transition_rules: Dict[str, Dict[Tuple[LifecycleState, LifecycleState], TransitionRule]] = {}
        self._rate_counter: Dict[str, List[float]] = defaultdict(list)
        self._approval_requests: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            "total_transitions": 0,
            "total_policies": 0,
            "total_resources": 0,
            "failed_transitions": 0,
            "auto_transitions": 0,
            "compliance_blocks": 0,
            "ttl_expirations": 0,
        }
        self._max_events = 10000
        self._max_audit_events = 5000
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._lock:
            self._create_default_policies()
            self._create_transition_rules()
            self._initialized = True
            logger.info("LifecyclePolicyManager initialized with %d policies", len(self._policies))

    def _create_default_policies(self) -> None:
        defaults = [
            (
                "compute_instance",
                "Compute Instance Lifecycle",
                "Standard VM/container lifecycle with health-based transitions",
                ["vm", "container", "pod"],
                LifecycleState.ACTIVE,
                86400 * 30,
            ),
            (
                "database",
                "Database Lifecycle",
                "Database lifecycle with backup and migration policies",
                ["database", "rds", "redis"],
                LifecycleState.ACTIVE,
                0,
            ),
            (
                "storage_object",
                "Storage Object Lifecycle",
                "Storage lifecycle with archive and cleanup policies",
                ["bucket", "object", "file"],
                LifecycleState.ACTIVE,
                86400 * 90,
            ),
            (
                "api_endpoint",
                "API Endpoint Lifecycle",
                "API lifecycle with deprecation and versioning policies",
                ["api", "endpoint", "route"],
                LifecycleState.ACTIVE,
                0,
            ),
            (
                "service",
                "Microservice Lifecycle",
                "Service lifecycle with draining and migration policies",
                ["service", "microservice", "deployment"],
                LifecycleState.ACTIVE,
                0,
            ),
        ]
        for pid, name, desc, types, init_state, ttl in defaults:
            policy = LifecyclePolicy(
                policy_id=pid,
                name=name,
                description=desc,
                resource_types=types,
                initial_state=init_state,
                default_ttl_seconds=ttl,
            )
            self._policies[pid] = policy
            self._stats["total_policies"] += 1

    def _create_transition_rules(self) -> None:
        standard = [
            (LifecycleState.PENDING, LifecycleState.PROVISIONING, TransitionTrigger.API_CALL),
            (LifecycleState.PROVISIONING, LifecycleState.ACTIVE, TransitionTrigger.MANUAL),
            (LifecycleState.PROVISIONING, LifecycleState.TERMINATED, TransitionTrigger.MANUAL),
            (LifecycleState.ACTIVE, LifecycleState.DEGRADED, TransitionTrigger.HEALTH_CHECK),
            (LifecycleState.ACTIVE, LifecycleState.MAINTENANCE, TransitionTrigger.SCHEDULED),
            (LifecycleState.ACTIVE, LifecycleState.DRAINING, TransitionTrigger.MANUAL),
            (LifecycleState.ACTIVE, LifecycleState.DEPRECATED, TransitionTrigger.COMPLIANCE),
            (LifecycleState.DEGRADED, LifecycleState.ACTIVE, TransitionTrigger.HEALTH_CHECK),
            (LifecycleState.DEGRADED, LifecycleState.MAINTENANCE, TransitionTrigger.ALERT),
            (LifecycleState.DEGRADED, LifecycleState.TERMINATED, TransitionTrigger.CRITICAL),
            (LifecycleState.MAINTENANCE, LifecycleState.ACTIVE, TransitionTrigger.MANUAL),
            (LifecycleState.MAINTENANCE, LifecycleState.DRAINING, TransitionTrigger.SCHEDULED),
            (LifecycleState.DRAINING, LifecycleState.ARCHIVED, TransitionTrigger.MANUAL),
            (LifecycleState.DRAINING, LifecycleState.TERMINATED, TransitionTrigger.MANUAL),
            (LifecycleState.DEPRECATED, LifecycleState.ARCHIVED, TransitionTrigger.TTL_EXPIRED),
            (LifecycleState.DEPRECATED, LifecycleState.TERMINATED, TransitionTrigger.MANUAL),
            (LifecycleState.ARCHIVED, LifecycleState.ACTIVE, TransitionTrigger.MANUAL),
            (LifecycleState.ARCHIVED, LifecycleState.TERMINATED, TransitionTrigger.SCHEDULED),
        ]
        for pid in self._policies:
            self._transition_rules[pid] = {}
            for from_s, to_s, trigger in standard:
                rule = TransitionRule(
                    from_state=from_s,
                    to_state=to_s,
                    trigger=trigger,
                    cooldown_seconds=60 if to_s == LifecycleState.ACTIVE else 0,
                    max_per_hour=10 if to_s == LifecycleState.DRAINING else 0,
                )
                self._transition_rules[pid][(from_s, to_s)] = rule

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一执行入口 — 资源生命周期管理操作路由"""
        _ = self.trace("execute")
        metrics_collector.counter("lifecycle_policy_ops_total", labels={"action": action})
        params = params or {}

        if action == "register":
            result = self.register_resource(
                params.get("resource_id", ""),
                params.get("resource_type", ""),
                params.get("policy_id", ""),
                params.get("metadata"),
            )
            self.audit(
                "register_resource",
                f"resource_id={params.get('resource_id', '')}, type={params.get('resource_type', '')}",
            )
            return result
        elif action == "transition":
            result = self.transition(
                params.get("resource_id", ""),
                LifecycleState(params.get("target_state", "active")),
                params.get("reason", ""),
                params.get("operator", "system"),
            )
            self.audit(
                "transition_resource",
                f"resource_id={params.get('resource_id', '')}, target={params.get('target_state', '')}",
            )
            return result
        elif action == "enforce_ttl":
            result = self.enforce_ttl()
            self.audit("enforce_ttl", f"expired_resources={result.get('expired_count', 0)}")
            return result
        elif action == "compliance_report":
            result = self.generate_compliance_report(params.get("policy_id", ""))
            return result
        elif action == "get_resource":
            return self.get_resource(params.get("resource_id", ""))
        elif action == "get_events":
            return self.get_events(params.get("resource_id"), params.get("state_filter"), params.get("limit", 50))
        elif action == "health":
            return self.health_check()
        elif action == "batch_get":
            return self.batch_get_resources(params.get("state"), params.get("limit", 100))
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def register_resource(
        self,
        resource_id: str,
        resource_type: str,
        policy_id: str,
        metadata: Optional[Dict] = None,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            policy = self._policies.get(policy_id)
            if not policy:
                return {"success": False, "error": f"Policy {policy_id} not found"}
            if resource_id in self._resources:
                return {"success": False, "error": f"Resource {resource_id} already registered"}
            record = ResourceRecord(
                resource_id=resource_id,
                resource_type=resource_type,
                policy_id=policy_id,
                state=policy.initial_state,
                ttl_seconds=ttl or policy.default_ttl_seconds,
                metadata=metadata or {},
            )
            self._resources[resource_id] = record
            self._state_index[record.state].add(resource_id)
            self._policy_index[policy_id].add(resource_id)
            self._type_index[resource_type].add(resource_id)
            self._stats["total_resources"] += 1
            return {"success": True, "resource_id": resource_id, "state": record.state.value}

    def transition(
        self,
        resource_id: str,
        target_state: LifecycleState,
        trigger: TransitionTrigger = TransitionTrigger.MANUAL,
        initiated_by: str = "system",
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            record = self._resources.get(resource_id)
            if not record:
                return {"success": False, "error": f"Resource {resource_id} not found"}
            rules = self._transition_rules.get(record.policy_id, {})
            rule = rules.get((record.state, target_state))
            if not rule:
                self._stats["failed_transitions"] += 1
                return {"success": False, "error": f"Transition {record.state.value}->{target_state.value} not allowed"}
            if rule.requires_approval:
                req_id = hashlib.md5(f"{resource_id}:{target_state.value}:{time.time()}".encode()).hexdigest()[:12]
                self._approval_requests[req_id] = {
                    "resource_id": resource_id,
                    "target_state": target_state,
                    "trigger": trigger,
                    "initiated_by": initiated_by,
                    "required_roles": rule.approval_roles,
                    "created_at": time.time(),
                }
                self._stats["compliance_blocks"] += 1
                return {"success": False, "action": "approval_required", "request_id": req_id}
            now = time.time()
            if rule.cooldown_seconds and record.last_transition_at:
                elapsed = now - record.last_transition_at
                if elapsed < rule.cooldown_seconds:
                    return {
                        "success": False,
                        "error": f"Cooldown active, {rule.cooldown_seconds - elapsed:.0f}s remaining",
                    }
            if rule.max_per_hour:
                key = f"{resource_id}:{target_state.value}"
                cutoff = now - 3600
                recent = [t for t in self._rate_counter[key] if t > cutoff]
                if len(recent) >= rule.max_per_hour:
                    return {"success": False, "error": f"Rate limit: max {rule.max_per_hour}/hour"}
                self._rate_counter[key] = recent
            old_state = record.state
            duration = now - record.entered_at
            record.state = target_state
            record.entered_at = now
            record.last_transition_at = now
            record.transition_count += 1
            record.version += 1
            self._state_index[old_state].discard(resource_id)
            self._state_index[target_state].add(resource_id)
            if target_state == LifecycleState.TERMINATED:
                record.terminated_at = now
            event_id = hashlib.md5(f"{resource_id}:{now}:{record.transition_count}".encode()).hexdigest()[:16]
            event = TransitionEvent(
                event_id=event_id,
                resource_id=resource_id,
                policy_id=record.policy_id,
                from_state=old_state,
                to_state=target_state,
                trigger=trigger,
                initiated_by=initiated_by,
                duration_in_state=duration,
                metadata=metadata or {},
            )
            self._events.append(event)
            self._event_index[resource_id].append(len(self._events) - 1)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_audit_events :]
            self._rate_counter[f"{resource_id}:{target_state.value}"].append(now)
            self._stats["total_transitions"] += 1
            if trigger in (TransitionTrigger.TTL_EXPIRED, TransitionTrigger.HEALTH_CHECK, TransitionTrigger.SCHEDULED):
                self._stats["auto_transitions"] += 1
            return {
                "success": True,
                "event_id": event_id,
                "from": old_state.value,
                "to": target_state.value,
                "duration": round(duration, 2),
            }

    def approve_transition(self, request_id: str, approver: str, approved: bool) -> Dict[str, Any]:
        with self._lock:
            req = self._approval_requests.pop(request_id, None)
            if not req:
                return {"success": False, "error": "Request not found or already processed"}
            if not approved:
                return {"success": True, "action": "rejected", "resource_id": req["resource_id"]}
            result = self.transition(
                req["resource_id"], req["target_state"], trigger=req["trigger"], initiated_by=approver
            )
            result["approval_id"] = request_id
            return result

    def enforce_ttl(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            expired = []
            for rid, record in self._resources.items():
                if record.ttl_seconds > 0 and record.state in (LifecycleState.ACTIVE, LifecycleState.DEPRECATED):
                    elapsed = now - record.entered_at
                    if elapsed >= record.ttl_seconds:
                        target = (
                            LifecycleState.DEPRECATED
                            if record.state == LifecycleState.ACTIVE
                            else LifecycleState.ARCHIVED
                        )
                        result = self.transition(rid, target, TransitionTrigger.TTL_EXPIRED)
                        if result["success"]:
                            expired.append({"resource_id": rid, "to": target.value})
                            self._stats["ttl_expirations"] += 1
            return {"processed": len(expired), "transitions": expired}

    def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        record = self._resources.get(resource_id)
        if not record:
            return None
        return {
            "resource_id": record.resource_id,
            "resource_type": record.resource_type,
            "policy_id": record.policy_id,
            "state": record.state.value,
            "entered_at": record.entered_at,
            "ttl_seconds": record.ttl_seconds,
            "transition_count": record.transition_count,
            "version": record.version,
            "tags": record.tags,
            "labels": record.labels,
            "metadata": record.metadata,
        }

    def get_resources_by_state(self, state: LifecycleState) -> List[str]:
        return list(self._state_index.get(state, set()))

    def get_events(self, resource_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if resource_id:
            indices = self._event_index.get(resource_id, [])
            events = [self._events[i] for i in indices if i < len(self._events)]
        else:
            events = self._events[-limit:]
        return [
            {
                "event_id": e.event_id,
                "resource_id": e.resource_id,
                "from": e.from_state.value,
                "to": e.to_state.value,
                "trigger": e.trigger.value,
                "initiated_by": e.initiated_by,
                "timestamp": e.timestamp,
                "duration": round(e.duration_in_state, 2),
            }
            for e in events[-limit:]
        ]

    def health_check(self) -> Dict[str, Any]:
        active = len(self._state_index.get(LifecycleState.ACTIVE, set()))
        total = len(self._resources)
        degraded = len(self._state_index.get(LifecycleState.DEGRADED, set()))
        return {
            "healthy": True,
            "status": "healthy",
            "module": "lifecycle_policy",
            "total_policies": len(self._policies),
            "total_resources": total,
            "active_resources": active,
            "degraded_resources": degraded,
            "state_distribution": {s.value: len(v) for s, v in self._state_index.items()},
            "total_transitions": self._stats["total_transitions"],
            "failed_transitions": self._stats["failed_transitions"],
            "auto_transitions": self._stats["auto_transitions"],
            "ttl_expirations": self._stats["ttl_expirations"],
            "pending_approvals": len(self._approval_requests),
            "uptime_ratio": active / total if total > 0 else 1.0,
            "timestamp": time.time(),
        }

    def generate_compliance_report(self, policy_id: str) -> Dict[str, Any]:
        """生成策略合规报告 - 统计资源状态分布、过期率、异常率"""
        policy = self._policies.get(policy_id)
        if not policy:
            return {"error": f"Policy {policy_id} not found"}
        resources = self._resource_policy_index.get(policy_id, [])
        now = time.time()
        expired = sum(1 for r in resources if hasattr(r, "ttl_end") and r.ttl_end and r.ttl_end < now)
        state_dist = {}
        for r in resources:
            s = r.state.value if hasattr(r.state, "value") else str(r.state)
            state_dist[s] = state_dist.get(s, 0) + 1
        return {
            "policy_id": policy_id,
            "total_resources": len(resources),
            "expired": expired,
            "active": len(resources) - expired,
            "state_distribution": state_dist,
            "compliance_rate": round((len(resources) - expired) / max(len(resources), 1), 4),
        }

    def batch_get_resources(self, state: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """批量查询资源"""
        results = []
        seen = set()
        for r in self._resources.values():
            if state and (r.state.value if hasattr(r.state, "value") else str(r.state)) != state:
                continue
            if r.resource_id in seen:
                continue
            seen.add(r.resource_id)
            results.append(
                {
                    "id": r.resource_id,
                    "state": r.state.value if hasattr(r.state, "value") else str(r.state),
                    "created": r.created_at.isoformat() if hasattr(r, "created_at") else None,
                }
            )
            if len(results) >= limit:
                break
        return results

    def get_transition_history(self, resource_id: str, limit: int = 20) -> List[Dict]:
        """获取资源状态变更历史"""
        events = [e for e in self._transition_log if hasattr(e, "resource_id") and e.resource_id == resource_id]
        return [
            {
                "from": e.from_state.value if hasattr(e.from_state, "value") else str(e.from_state),
                "to": e.to_state.value if hasattr(e.to_state, "value") else str(e.to_state),
                "timestamp": e.timestamp.isoformat() if hasattr(e, "timestamp") else None,
            }
            for e in events[-limit:]
        ]

    def shutdown(self) -> dict:
        """Graceful shutdown for lifecycle_policy."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

    def shutdown(self) -> dict:
        """Graceful shutdown for lifecycle_policy."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = LifecyclePolicyManager
