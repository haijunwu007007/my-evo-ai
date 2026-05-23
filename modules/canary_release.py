"""
AUTO-EVO-AI v7.0 - Canary Release Module (Grade: A Production)
金丝雀发布：渐进式发布、流量分配、指标监控、自动回滚
"""

__module_meta__ = {
    "id": "canary-release",
    "name": "Canary Release",
    "version": "1.0.0",
    "group": "devops",
    "inputs": [
        {"name": "canary_id", "type": "string", "required": True, "description": ""},
        {"name": "canary_pct", "type": "string", "required": True, "description": ""},
        {"name": "total_pct", "type": "string", "required": True, "description": ""},
        {"name": "user_id", "type": "string", "required": True, "description": ""},
        {"name": "canary_id", "type": "string", "required": True, "description": ""},
        {"name": "canary_pct", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["engine", "canary", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 - Canary Release Module (Grade: A Production) 金丝雀发布：渐进式发布、流量分配、指标监控、自动回滚",
}

import os
import asyncio
import time
import logging
import uuid
import hashlib

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector, prometheus_timer
    from modules._base.audit import AuditLogger
except ImportError:

    class EnterpriseModule:
        def __init__(self):
            self._initialized = False
            self.logger = logging.getLogger(__name__)

        def initialize(self):
            self._initialized = True

        def shutdown(self):
            self._initialized = False

        def health_check(self):
            return {"status": "ok"}

    class CircuitBreakerMixin:
        pass

    class RateLimiterMixin:
        pass

    trace_operation = lambda x: lambda f: f
    prometheus_timer = lambda x: lambda f: f
    metrics_collector = None

    class AuditLogger:
        def log(self, *a, **k):
            pass

logger = logging.getLogger(__name__)

class ReleaseState(Enum):
    PENDING = "pending"
    STAGING = "staging"
    CANARY = "canary"
    RAMPING = "ramping"
    FULL = "full"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"
    COMPLETED = "completed"

class MetricType(Enum):
    ERROR_RATE = "error_rate"
    LATENCY_P99 = "latency_p99"
    LATENCY_P50 = "latency_p50"
    THROUGHPUT = "throughput"
    CPU = "cpu"
    MEMORY = "memory"

@dataclass
class CanaryRule:
    """金丝雀规则"""

    rule_id: str
    metric: MetricType
    threshold: float
    comparison: str = "gt"  # gt, lt, gte, lte
    window_seconds: int = 300
    description: str = ""

@dataclass
class ReleaseMetric:
    """发布指标"""

    release_id: str
    metric_type: MetricType
    value: float
    baseline_value: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CanaryRelease:
    """金丝雀发布"""

    release_id: str = field(default_factory=lambda: f"rel_{uuid.uuid4().hex[:8]}")
    app_name: str = ""
    version: str = ""
    previous_version: str = ""
    state: ReleaseState = ReleaseState.PENDING
    canary_pct: int = 0
    target_pct: int = 100
    step_pct: int = 10
    step_interval_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metrics: List[ReleaseMetric] = field(default_factory=list)
    rules: List[CanaryRule] = field(default_factory=list)
    violations: List[Dict[str, Any]] = field(default_factory=list)
    rollback_reason: str = ""
    success: Optional[bool] = None

class TrafficSplitEngine(object):
    """流量分配引擎 - 权重计算、用户分桶、渐进式调整"""

    def __init__(self):
        self._current_weights: Dict[str, float] = {}
        self._bucket_assignments: Dict[str, str] = {}

    def calculate_split(self, canary_id: str, canary_pct: float, total_pct: float = 100.0) -> Dict:
        canary_pct = max(0.0, min(canary_pct, total_pct))
        stable_pct = total_pct - canary_pct
        return {"canary_id": canary_id, "canary_weight": canary_pct, "stable_weight": stable_pct}

    def assign_bucket(self, user_id: str, canary_id: str, canary_pct: float) -> str:
        h = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100
        return canary_id if h < canary_pct else "stable"

    def get_current_weights(self) -> Dict[str, float]:
        return dict(self._current_weights)

    def update_weight(self, canary_id: str, weight: float) -> None:
        self._current_weights[canary_id] = weight

    def gradual_increase(self, canary_id: str, step_pct: float, max_pct: float) -> Dict:
        """渐进式增加金丝雀流量"""
        current = self._current_weights.get(canary_id, 0.0)
        new_weight = min(current + step_pct, max_pct)
        self._current_weights[canary_id] = new_weight
        return {"canary_id": canary_id, "previous_weight": current, "new_weight": new_weight}

    def evaluate_rollback(self, canary_id: str, error_rate: float, threshold: float = 5.0) -> bool:
        """根据错误率评估是否需要回滚"""
        if error_rate > threshold:
            self._current_weights[canary_id] = 0.0
            return True
        return False

    def get_distribution_summary(self) -> Dict:
        """获取所有金丝雀发布的流量分布摘要"""
        total = sum(self._current_weights.values()) + max(0, 100.0 - sum(self._current_weights.values()))
        canary_total = sum(self._current_weights.values())
        return {
            "total_canary_weight": round(canary_total, 2),
            "stable_weight": round(100.0 - canary_total, 2),
            "active_releases": len(self._current_weights),
        }

class CanaryReleaseManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    def __init__(self):
        self._initialized = False

    """金丝雀发布管理器"""

    def __init__(self):

        super().__init__()
        self.module_name = "canary_release"
        self.module_id = self.module_name
        self.module_version = "7.0.0"
        self._releases: Dict[str, CanaryRelease] = {}
        self._audit = AuditLogger()
        self._total_releases = 0
        self._total_rollbacks = 0
        self._active_releases: List[str] = []
        self._default_rules = self._setup_default_rules()

    def _setup_default_rules(self) -> List[CanaryRule]:
        return [
            CanaryRule("rule_err_rate", MetricType.ERROR_RATE, 0.05, "gt", 300, "错误率超过5%"),
            CanaryRule("rule_latency_p99", MetricType.LATENCY_P99, 500, "gt", 300, "P99延迟超过500ms"),
            CanaryRule("rule_latency_p50", MetricType.LATENCY_P50, 200, "gt", 300, "P50延迟超过200ms"),
            CanaryRule("rule_cpu", MetricType.CPU, 80, "gt", 60, "CPU使用率超过80%"),
            CanaryRule("rule_memory", MetricType.MEMORY, 85, "gt", 60, "内存使用率超过85%"),
        ]

    def initialize(self):
        logger.info("canary_release initialized")

    async def execute(self, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("canary_release_ops_total", labels={"operation": operation})
        self.audit("execute", f"operation={operation}")
        params = params or {}
        if operation == "create_release":
            return self._create_release(params)
        elif operation == "start_release":
            return self._start_release(params)
        elif operation == "advance":
            return self._advance(params)
        elif operation == "report_metric":
            return self._report_metric(params)
        elif operation == "evaluate":
            return self._evaluate(params)
        elif operation == "rollback":
            return self._rollback(params)
        elif operation == "pause":
            return self._pause(params)
        elif operation == "get_release":
            return self._get_release(params)
        elif operation == "list_releases":
            return self._list_releases(params)
        elif operation == "get_status":
            return self._get_status(params)
        elif operation == "add_rule":
            return self._add_rule(params)
        else:
            return {
                "success": False,
                "error": f"unknown op: {operation}",
                "available": [
                    "create_release",
                    "start_release",
                    "advance",
                    "report_metric",
                    "evaluate",
                    "rollback",
                    "pause",
                    "get_release",
                    "list_releases",
                    "get_status",
                    "add_rule",
                ],
            }

    def _create_release(self, p: Dict) -> Dict:
        app_name = p.get("app_name", "")
        version = p.get("version", "")
        previous_version = p.get("previous_version", "")
        target_pct = p.get("target_pct", 100)
        step_pct = p.get("step_pct", 10)
        step_interval = p.get("step_interval_seconds", 300)

        if not app_name or not version:
            return {"success": False, "error": "missing app_name or version"}

        release = CanaryRelease(
            app_name=app_name,
            version=version,
            previous_version=previous_version,
            target_pct=target_pct,
            step_pct=step_pct,
            step_interval_seconds=step_interval,
        )
        release.rules = list(self._default_rules)
        self._releases[release.release_id] = release
        self._total_releases += 1
        self._audit.log("release_created", {"release_id": release.release_id, "app": app_name, "version": version})

        return {
            "success": True,
            "result": {
                "release_id": release.release_id,
                "app_name": app_name,
                "version": version,
                "target_pct": target_pct,
                "step_pct": step_pct,
                "rules": len(release.rules),
            },
        }

    def _start_release(self, p: Dict) -> Dict:
        rid = p.get("release_id")
        if not rid or rid not in self._releases:
            return {"success": False, "error": "release not found"}
        rel = self._releases[rid]
        if rel.state not in (ReleaseState.PENDING, ReleaseState.PAUSED):
            return {"success": False, "error": f"cannot start from state {rel.state.value}"}

        rel.state = ReleaseState.CANARY
        rel.canary_pct = rel.step_pct
        rel.updated_at = datetime.now()
        self._active_releases.append(rid)
        self._audit.log("release_started", {"release_id": rid, "pct": rel.canary_pct})

        return {
            "success": True,
            "result": {
                "release_id": rid,
                "state": rel.state.value,
                "canary_pct": rel.canary_pct,
                "remaining_steps": (rel.target_pct - rel.canary_pct) // rel.step_pct,
            },
        }

    def _advance(self, p: Dict) -> Dict:
        rid = p.get("release_id")
        if not rid or rid not in self._releases:
            return {"success": False, "error": "release not found"}
        rel = self._releases[rid]
        if rel.state != ReleaseState.CANARY:
            return {"success": False, "error": f"not in canary state: {rel.state.value}"}

        old_pct = rel.canary_pct
        rel.canary_pct = min(rel.canary_pct + rel.step_pct, rel.target_pct)
        rel.updated_at = datetime.now()

        if rel.canary_pct >= rel.target_pct:
            rel.state = ReleaseState.FULL
            rel.success = True
            rel.state = ReleaseState.COMPLETED
            if rid in self._active_releases:
                self._active_releases.remove(rid)
            self._audit.log("release_completed", {"release_id": rid, "pct": rel.canary_pct})
        else:
            self._audit.log("release_advanced", {"release_id": rid, "pct": f"{old_pct}->{rel.canary_pct}"})

        return {
            "success": True,
            "result": {
                "release_id": rid,
                "state": rel.state.value,
                "canary_pct": rel.canary_pct,
                "prev_pct": old_pct,
            },
        }

    def _report_metric(self, p: Dict) -> Dict:
        rid = p.get("release_id")
        metric_type = p.get("metric_type", "error_rate")
        value = p.get("value", 0)
        baseline = p.get("baseline_value", 0)

        if not rid or rid not in self._releases:
            return {"success": False, "error": "release not found"}

        try:
            mt = MetricType(metric_type)
        except ValueError:
            mt = MetricType.ERROR_RATE

        rel = self._releases[rid]
        rm = ReleaseMetric(release_id=rid, metric_type=mt, value=float(value), baseline_value=float(baseline))
        rel.metrics.append(rm)
        rel.updated_at = datetime.now()

        return {
            "success": True,
            "result": {
                "release_id": rid,
                "metric": mt.value,
                "value": value,
                "baseline": baseline,
                "degradation": "yes" if self._is_degraded(mt, float(value), float(baseline)) else "no",
            },
        }

    def _evaluate(self, p: Dict) -> Dict:
        rid = p.get("release_id")
        if not rid or rid not in self._releases:
            return {"success": False, "error": "release not found"}
        rel = self._releases[rid]

        if not rel.metrics:
            return {"success": True, "result": {"status": "no_metrics", "can_continue": True}}

        violations = []
        latest_metrics: Dict[MetricType, ReleaseMetric] = {}
        for m in rel.metrics:
            if m.metric_type not in latest_metrics or m.timestamp > latest_metrics[m.metric_type].timestamp:
                latest_metrics[m.metric_type] = m

        for rule in rel.rules:
            if rule.metric in latest_metrics:
                lm = latest_metrics[rule.metric]
                triggered = False
                if rule.comparison == "gt" and lm.value > rule.threshold:
                    triggered = True
                elif rule.comparison == "lt" and lm.value < rule.threshold:
                    triggered = True
                elif rule.comparison == "gte" and lm.value >= rule.threshold:
                    triggered = True
                elif rule.comparison == "lte" and lm.value <= rule.threshold:
                    triggered = True
                if triggered:
                    violations.append(
                        {
                            "rule_id": rule.rule_id,
                            "metric": rule.metric.value,
                            "value": lm.value,
                            "threshold": rule.threshold,
                            "description": rule.description,
                        }
                    )

        rel.violations = violations
        can_continue = len(violations) == 0

        return {
            "success": True,
            "result": {
                "status": "healthy" if can_continue else "degraded",
                "can_continue": can_continue,
                "violations": violations,
                "metrics_evaluated": len(latest_metrics),
            },
        }

    def _rollback(self, p: Dict) -> Dict:
        rid = p.get("release_id")
        reason = p.get("reason", "manual")
        if not rid or rid not in self._releases:
            return {"success": False, "error": "release not found"}
        rel = self._releases[rid]
        if rel.state == ReleaseState.COMPLETED:
            return {"success": False, "error": "already completed"}

        old_state = rel.state.value
        rel.state = ReleaseState.ROLLED_BACK
        rel.rollback_reason = reason
        rel.success = False
        rel.updated_at = datetime.now()
        if rid in self._active_releases:
            self._active_releases.remove(rid)
        self._total_rollbacks += 1
        self._audit.log("release_rollback", {"release_id": rid, "reason": reason, "from": old_state})

        return {
            "success": True,
            "result": {
                "release_id": rid,
                "state": rel.state.value,
                "previous_state": old_state,
                "reason": reason,
                "canary_pct": rel.canary_pct,
            },
        }

    def _pause(self, p: Dict) -> Dict:
        rid = p.get("release_id")
        if not rid or rid not in self._releases:
            return {"success": False, "error": "release not found"}
        rel = self._releases[rid]
        if rel.state != ReleaseState.CANARY:
            return {"success": False, "error": f"cannot pause from {rel.state.value}"}

        rel.state = ReleaseState.PAUSED
        rel.updated_at = datetime.now()
        self._audit.log("release_paused", {"release_id": rid})
        return {"success": True, "result": {"release_id": rid, "state": "paused", "canary_pct": rel.canary_pct}}

    def _get_release(self, p: Dict) -> Dict:
        rid = p.get("release_id")
        if not rid or rid not in self._releases:
            return {"success": False, "error": "release not found"}
        rel = self._releases[rid]
        return {
            "success": True,
            "result": {
                "release_id": rel.release_id,
                "app_name": rel.app_name,
                "version": rel.version,
                "previous_version": rel.previous_version,
                "state": rel.state.value,
                "canary_pct": rel.canary_pct,
                "target_pct": rel.target_pct,
                "step_pct": rel.step_pct,
                "created_at": rel.created_at.isoformat(),
                "updated_at": rel.updated_at.isoformat(),
                "metrics_count": len(rel.metrics),
                "violations_count": len(rel.violations),
                "success": rel.success,
            },
        }

    def _list_releases(self, p: Dict) -> Dict:
        limit = p.get("limit", 20)
        app_name = p.get("app_name")
        releases = list(self._releases.values())
        if app_name:
            releases = [r for r in releases if r.app_name == app_name]
        releases = releases[-limit:]
        return {
            "success": True,
            "result": [
                {
                    "release_id": r.release_id,
                    "app_name": r.app_name,
                    "version": r.version,
                    "state": r.state.value,
                    "canary_pct": r.canary_pct,
                    "success": r.success,
                    "created_at": r.created_at.isoformat(),
                }
                for r in releases
            ],
            "total": len(releases),
        }

    def _get_status(self, p: Dict) -> Dict:
        active = [self._releases[rid] for rid in self._active_releases if rid in self._releases]
        return {
            "success": True,
            "result": {
                "active_releases": len(active),
                "total_releases": self._total_releases,
                "total_rollbacks": self._total_rollbacks,
                "active_details": [
                    {
                        "release_id": r.release_id,
                        "app": r.app_name,
                        "version": r.version,
                        "pct": r.canary_pct,
                        "violations": len(r.violations),
                    }
                    for r in active
                ],
            },
        }

    def _add_rule(self, p: Dict) -> Dict:
        rid = p.get("release_id")
        metric_type = p.get("metric_type", "error_rate")
        threshold = p.get("threshold", 5.0)
        comparison = p.get("comparison", "gt")

        try:
            mt = MetricType(metric_type)
        except ValueError:
            return {"success": False, "error": f"invalid metric type: {metric_type}"}

        rule = CanaryRule(
            rule_id=f"rule_{uuid.uuid4().hex[:8]}",
            metric=mt,
            threshold=threshold,
            comparison=comparison,
            description=p.get("description", ""),
        )
        if rid and rid in self._releases:
            self._releases[rid].rules.append(rule)
            return {"success": True, "result": {"rule_id": rule.rule_id, "added_to": rid}}
        self._default_rules.append(rule)
        return {"success": True, "result": {"rule_id": rule.rule_id, "added_to": "default"}}

    def _is_degraded(self, mt: MetricType, value: float, baseline: float) -> bool:
        if baseline <= 0:
            return value > 0
        ratio = (value - baseline) / baseline
        return ratio > 0.5  # degradation if 50% worse than baseline

    def shutdown(self):
        self._initialized = False
        self._audit.log("shutdown", "canary_release shutdown")

    def get_release_dashboard(self) -> Dict[str, Any]:
        """发布仪表盘概览：活跃发布数、成功/回滚/暂停统计"""
        releases = self._releases if hasattr(self, "_releases") else {}
        total = len(releases)
        active = len(self._active_releases) if hasattr(self, "_active_releases") else 0
        states = {}
        for r in releases.values():
            state = r.state.value if hasattr(r.state, "value") else str(r.state)
            states[state] = states.get(state, 0) + 1
        recent = sorted(releases.values(), key=lambda x: x.updated_at, reverse=True)[:5]
        recent_summary = [
            {
                "id": r.release_id,
                "app": r.app_name,
                "state": r.state.value if hasattr(r.state, "value") else str(r.state),
                "pct": r.canary_pct,
            }
            for r in recent
        ]
        return {
            "total_releases": total,
            "active": active,
            "rollbacks": self._total_rollbacks if hasattr(self, "_total_rollbacks") else 0,
            "state_distribution": states,
            "recent": recent_summary,
        }

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy" if self._initialized else "not_initialized",
                "total_releases": self._total_releases,
                "active_releases": len(self._active_releases),
                "total_rollbacks": self._total_rollbacks,
                "rules": len(self._default_rules),
            }
        )
        return result

    def batch_update_weights(self, updates: List[Dict]) -> Dict[str, float]:
        """批量更新金丝雀流量权重"""
        results = {}
        for u in updates:
            cid = u.get("canary_id", "")
            weight = u.get("weight", 0.0)
            self._traffic_engine.update_weight(cid, weight)
            results[cid] = weight
        return results

    def get_release_timeline(self, release_id: str) -> List[Dict]:
        """获取发布时间线（用于审计和分析）"""
        release = self._releases.get(release_id)
        if not release:
            return []
        timeline = []
        if hasattr(release, "created_at"):
            timeline.append(
                {
                    "event": "created",
                    "timestamp": release.created_at.isoformat()
                    if hasattr(release.created_at, "isoformat")
                    else str(release.created_at),
                }
            )
        if hasattr(release, "started_at") and release.started_at:
            timeline.append(
                {
                    "event": "started",
                    "timestamp": release.started_at.isoformat()
                    if hasattr(release.started_at, "isoformat")
                    else str(release.started_at),
                }
            )
        return timeline

module_class = CanaryReleaseManager
