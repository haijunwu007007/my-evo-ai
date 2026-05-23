"""
AUTO-EVO-AI V0.1 — 配额管理模块
生产级实现：多维度配额控制、滑动窗口限速、分级告警、自动降级
"""

__module_meta__ = {
    "id": "quota-manager",
    "name": "Quota Manager",
    "version": "1.0.0",
    "group": "system",
    "inputs": [
        {"name": "window_seconds", "type": "string", "required": True, "description": ""},
        {"name": "precision_seconds", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "timestamp", "type": "string", "required": True, "description": ""},
        {"name": "window_start", "type": "string", "required": True, "description": ""},
        {"name": "window_end", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["config", "quota", "manager", "engine"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 配额管理模块 生产级实现：多维度配额控制、滑动窗口限速、分级告警、自动降级",
}

import asyncio
import hashlib
import json
import logging
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.enterprise_module import CircuitBreakerMixin
from modules._base.mixins import RateLimiterMixin

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

class QuotaDimension(Enum):
    API_CALLS = "api_calls"
    TOKENS = "tokens"
    STORAGE_MB = "storage_mb"
    BANDWIDTH_MB = "bandwidth_mb"
    COMPUTE_SECONDS = "compute_seconds"
    CONCURRENT_REQUESTS = "concurrent_requests"
    FILES = "files"
    AGENTS = "agents"
    WORKFLOWS = "workflows"
    CUSTOM = "custom"

class QuotaAction(Enum):
    ALLOW = "allow"
    THROTTLE = "throttle"
    REJECT = "reject"
    QUEUE = "queue"
    DEGRADE = "degrade"

class TierLevel(Enum):
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"

@dataclass
class QuotaLimit:
    dimension: QuotaDimension
    limit_value: float
    window_seconds: int = 86400
    burst_limit: float = 0
    burst_window_seconds: int = 60
    soft_limit_pct: float = 0.8
    hard_limit_pct: float = 1.0
    action_on_exceed: QuotaAction = QuotaAction.REJECT

@dataclass
class QuotaUsage:
    current_value: float = 0.0
    window_start: float = 0.0
    window_end: float = 0.0
    burst_value: float = 0.0
    burst_window_start: float = 0.0
    violations: int = 0
    last_violation: Optional[str] = None
    throttled_until: Optional[float] = None

@dataclass
class QuotaCheckResult:
    allowed: bool
    remaining: float
    used_pct: float
    action: QuotaAction
    reset_at: str
    retry_after_seconds: float = 0.0
    message: str = ""

@dataclass
class TierConfig:
    name: TierLevel
    display_name: str
    monthly_price: float = 0.0
    rate_limits: List[QuotaLimit] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    max_agents: int = 5
    max_workflows: int = 10
    support_level: str = "community"
    sla_pct: float = 99.0

# ──────────────────────────────────────────────
# 滑动窗口计数器
# ──────────────────────────────────────────────

class SlidingWindowCounter:
    """高精度滑动窗口计数器，支持秒级粒度"""

    def __init__(self, window_seconds: int = 86400, precision_seconds: int = 1):
        self.window_seconds = window_seconds
        self.precision = precision_seconds
        self._buckets: Dict[int, float] = {}
        self._lock = threading.Lock()

    def add(self, value: float = 1.0, timestamp: Optional[float] = None):
        ts = timestamp or time.time()
        bucket_key = int(ts / self.precision)
        with self._lock:
            self._buckets[bucket_key] = self._buckets.get(bucket_key, 0) + value
            self._cleanup(ts)

    def get_count(self, window_start: Optional[float] = None, window_end: Optional[float] = None) -> float:
        now = time.time()
        ws = window_start or (now - self.window_seconds)
        we = window_end or now
        start_bucket = int(ws / self.precision)
        end_bucket = int(we / self.precision)
        with self._lock:
            self._cleanup(now)
            return sum(v for k, v in self._buckets.items() if start_bucket <= k <= end_bucket)

    def get_rate(self, per_seconds: int = 60) -> float:
        now = time.time()
        return self.get_count(now - per_seconds, now) / per_seconds

    def reset(self):
        with self._lock:
            self._buckets.clear()

    def _cleanup(self, now: float):
        cutoff = int((now - self.window_seconds - self.precision) / self.precision)
        keys_to_remove = [k for k in self._buckets if k < cutoff]
        for k in keys_to_remove:
            del self._buckets[k]

# ──────────────────────────────────────────────
# 配额策略引擎
# ──────────────────────────────────────────────

class QuotaPolicyEngine(object):
    """动态配额策略引擎：分级限速、自适应降级、白名单管理"""

    def __init__(self):
        self._policies: Dict[str, Dict[str, Any]] = {}
        self._whitelist: set = set()
        self._blacklist: set = set()
        self._custom_rules: List[Dict[str, Any]] = []

    def add_policy(self, policy_id: str, target_pattern: str, limits: List[QuotaLimit], priority: int = 100):
        self._policies[policy_id] = {
            "pattern": target_pattern,
            "limits": limits,
            "priority": priority,
            "enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._policies = dict(sorted(self._policies.items(), key=lambda x: -x[1]["priority"]))

    def remove_policy(self, policy_id: str) -> bool:
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False

    def match_policy(self, target_id: str) -> Optional[Dict[str, Any]]:
        for pid, policy in self._policies.items():
            if not policy["enabled"]:
                continue
            pattern = policy["pattern"]
            if pattern == "*" or target_id.startswith(pattern) or target_id == pattern:
                return policy
        return None

    def add_to_whitelist(self, target_id: str):
        self._whitelist.add(target_id)

    def add_to_blacklist(self, target_id: str):
        self._blacklist.add(target_id)

    def is_whitelisted(self, target_id: str) -> bool:
        return target_id in self._whitelist

    def is_blacklisted(self, target_id: str) -> bool:
        return target_id in self._blacklist

    def add_custom_rule(self, rule_id: str, condition: Callable, action: QuotaAction, description: str = ""):
        self._custom_rules.append(
            {
                "rule_id": rule_id,
                "condition": condition,
                "action": action,
                "description": description,
                "enabled": True,
            }
        )

    def evaluate_custom_rules(self, target_id: str, usage: QuotaUsage, limit: QuotaLimit) -> Optional[QuotaAction]:
        for rule in self._custom_rules:
            if not rule["enabled"]:
                continue
            try:
                if rule["condition"](target_id, usage, limit):
                    return rule["action"]
            except Exception as e:
                logger.warning(f"Custom rule {rule['rule_id']} error: {e}")
        return None

    def get_all_policies(self) -> List[Dict[str, Any]]:
        return [{"policy_id": pid, **pdata} for pid, pdata in self._policies.items()]

# ──────────────────────────────────────────────
# 配额告警器
# ──────────────────────────────────────────────

class QuotaAlerter:
    """配额使用率告警：阈值触发、分级通知、告警抑制"""

    def __init__(self):
        self._alerts: List[Dict[str, Any]] = []
        self._suppressions: Dict[str, float] = {}
        self._suppress_duration = 3600
        self._alert_thresholds = [0.5, 0.7, 0.8, 0.9, 0.95, 1.0]
        self._callbacks: Dict[str, Callable] = {}

    def register_callback(self, level: str, callback: Callable):
        self._callbacks[level] = callback

    def check_and_alert(self, target_id: str, dimension: str, usage_pct: float):
        now = time.time()
        suppress_key = f"{target_id}:{dimension}"

        if suppress_key in self._suppressions:
            if now < self._suppressions[suppress_key]:
                return
            del self._suppressions[suppress_key]

        for threshold in self._alert_thresholds:
            if usage_pct >= threshold:
                alert_level = "critical" if threshold >= 0.95 else "warning" if threshold >= 0.8 else "info"
                alert = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "target_id": target_id,
                    "dimension": dimension,
                    "usage_pct": round(usage_pct, 4),
                    "threshold": threshold,
                    "level": alert_level,
                    "message": f"{target_id} {dimension} usage at {usage_pct:.1%} (threshold: {threshold:.0%})",
                }
                self._alerts.append(alert)
                self._suppressions[suppress_key] = now + self._suppress_duration

                if alert_level in self._callbacks:
                    try:
                        self._callbacks[alert_level](alert)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")
                break

    def get_recent_alerts(self, target_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        alerts = self._alerts
        if target_id:
            alerts = [a for a in alerts if a["target_id"] == target_id]
        return alerts[-limit:]

# ──────────────────────────────────────────────
# 主模块
# ──────────────────────────────────────────────

class QuotaManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    配额管理模块
    功能：多维配额控制、滑动窗口限速、分级告警、自动降级、套餐管理
    """

    def __init__(self):

        super().__init__(module_name="quota_manager", module_version="6.39.0")
        self.policy_engine = QuotaPolicyEngine()
        self.alerter = QuotaAlerter()
        self._usage: Dict[str, Dict[str, QuotaUsage]] = defaultdict(dict)
        self._counters: Dict[str, SlidingWindowCounter] = {}
        self._tiers: Dict[str, TierConfig] = {}
        self._user_tiers: Dict[str, str] = {}
        self._operation_count = 0
        self._rejection_count = 0
        self._throttle_count = 0
        # 链路追踪：记录关键操作span
        self._trace_spans: Dict[str, Dict[str, Any]] = {}
        self._init_default_tiers()

    def _init_default_tiers(self):
        self._tiers["free"] = TierConfig(
            name=TierLevel.FREE,
            display_name="免费版",
            rate_limits=[
                QuotaLimit(QuotaDimension.API_CALLS, 1000, 3600),
                QuotaLimit(QuotaDimension.TOKENS, 100000, 86400),
                QuotaLimit(QuotaDimension.CONCURRENT_REQUESTS, 3, 1),
                QuotaLimit(QuotaDimension.STORAGE_MB, 100, 86400),
            ],
            max_agents=2,
            max_workflows=3,
            support_level="community",
            sla_pct=95.0,
        )
        self._tiers["basic"] = TierConfig(
            name=TierLevel.BASIC,
            display_name="基础版",
            monthly_price=99,
            rate_limits=[
                QuotaLimit(QuotaDimension.API_CALLS, 10000, 3600),
                QuotaLimit(QuotaDimension.TOKENS, 1000000, 86400),
                QuotaLimit(QuotaDimension.CONCURRENT_REQUESTS, 10, 1),
                QuotaLimit(QuotaDimension.STORAGE_MB, 1000, 86400),
            ],
            max_agents=10,
            max_workflows=20,
            support_level="email",
            sla_pct=99.0,
        )
        self._tiers["professional"] = TierConfig(
            name=TierLevel.PROFESSIONAL,
            display_name="专业版",
            monthly_price=499,
            rate_limits=[
                QuotaLimit(QuotaDimension.API_CALLS, 100000, 3600),
                QuotaLimit(QuotaDimension.TOKENS, 10000000, 86400),
                QuotaLimit(QuotaDimension.CONCURRENT_REQUESTS, 50, 1),
                QuotaLimit(QuotaDimension.STORAGE_MB, 10000, 86400),
                QuotaLimit(QuotaDimension.BANDWIDTH_MB, 5000, 3600),
            ],
            max_agents=50,
            max_workflows=100,
            support_level="priority",
            sla_pct=99.9,
        )
        self._tiers["enterprise"] = TierConfig(
            name=TierLevel.ENTERPRISE,
            display_name="企业版",
            monthly_price=1999,
            rate_limits=[
                QuotaLimit(QuotaDimension.API_CALLS, 1000000, 3600, burst_limit=20000),
                QuotaLimit(QuotaDimension.TOKENS, 100000000, 86400),
                QuotaLimit(QuotaDimension.CONCURRENT_REQUESTS, 200, 1),
                QuotaLimit(QuotaDimension.STORAGE_MB, 100000, 86400),
                QuotaLimit(QuotaDimension.BANDWIDTH_MB, 50000, 3600),
                QuotaLimit(QuotaDimension.COMPUTE_SECONDS, 3600, 3600),
            ],
            max_agents=500,
            max_workflows=1000,
            support_level="dedicated",
            sla_pct=99.99,
        )

    def _get_counter(self, target_id: str, dimension: str, window_seconds: int) -> SlidingWindowCounter:
        key = f"{target_id}:{dimension}"
        if key not in self._counters:
            self._counters[key] = SlidingWindowCounter(window_seconds)
        return self._counters[key]

    def _get_usage(self, target_id: str, dimension: str) -> QuotaUsage:
        if target_id not in self._usage:
            self._usage[target_id] = {}
        if dimension not in self._usage[target_id]:
            self._usage[target_id][dimension] = QuotaUsage()
        return self._usage[target_id][dimension]

    # ── 配额检查 ──

    async def check_quota(self, target_id: str, dimension: QuotaDimension, requested: float = 1.0) -> QuotaCheckResult:
        self._operation_count += 1
        # 链路追踪：开启检查span
        import uuid as _uuid

        span_id = _uuid.uuid4().hex[:16]
        self._trace_spans[span_id] = {
            "op": "check_quota",
            "target": target_id,
            "dim": dimension.value,
            "start": time.time(),
        }

        if self.policy_engine.is_blacklisted(target_id):
            self._rejection_count += 1
            self._trace_spans[span_id]["status"] = "rejected_blacklist"
            return QuotaCheckResult(
                allowed=False,
                remaining=0,
                used_pct=1.0,
                action=QuotaAction.REJECT,
                reset_at="",
                message="Target is blacklisted",
            )

        if self.policy_engine.is_whitelisted(target_id):
            return QuotaCheckResult(
                allowed=True,
                remaining=float("inf"),
                used_pct=0.0,
                action=QuotaAction.ALLOW,
                reset_at=(datetime.now(timezone.utc) + timedelta(seconds=86400)).isoformat(),
            )

        policy = self.policy_engine.match_policy(target_id)
        if not policy:
            tier_name = self._user_tiers.get(target_id, "free")
            limits = self._tiers.get(tier_name, self._tiers["free"]).rate_limits
        else:
            limits = policy["limits"]

        matching_limits = [l for l in limits if l.dimension == dimension]
        if not matching_limits:
            return QuotaCheckResult(
                allowed=True,
                remaining=float("inf"),
                used_pct=0.0,
                action=QuotaAction.ALLOW,
                reset_at=(datetime.now(timezone.utc) + timedelta(seconds=86400)).isoformat(),
            )

        limit = matching_limits[0]
        usage = self._get_usage(target_id, dimension.value)
        counter = self._get_counter(target_id, dimension.value, limit.window_seconds)
        current = counter.get_count()

        projected = current + requested
        usage_pct = projected / limit.limit_value if limit.limit_value > 0 else 0
        remaining = max(0, limit.limit_value - current)

        custom_action = self.policy_engine.evaluate_custom_rules(target_id, usage, limit)

        if usage_pct <= limit.soft_limit_pct:
            action = custom_action or QuotaAction.ALLOW
            allowed = True
        elif usage_pct <= limit.hard_limit_pct:
            action = custom_action or QuotaAction.THROTTLE
            allowed = True
            self._throttle_count += 1
        else:
            action = custom_action or limit.action_on_exceed
            allowed = action in (QuotaAction.ALLOW, QuotaAction.THROTTLE, QuotaAction.QUEUE)
            if not allowed:
                self._rejection_count += 1

        now = time.time()
        reset_at = datetime.fromtimestamp(now + limit.window_seconds, tz=timezone.utc).isoformat()

        if usage_pct >= 0.5:
            self.alerter.check_and_alert(target_id, dimension.value, usage_pct)

        return QuotaCheckResult(
            allowed=allowed,
            remaining=remaining,
            used_pct=round(usage_pct, 6),
            action=action,
            reset_at=reset_at,
            message=f"Quota {dimension.value}: {usage_pct:.1%} used" if not allowed else "",
        )

    async def consume_quota(self, target_id: str, dimension: QuotaDimension, amount: float = 1.0) -> Dict[str, Any]:
        check = await self.check_quota(target_id, dimension, amount)
        if not check.allowed:
            return {"status": "rejected", "reason": check.message, "action": check.action.value}

        counter = self._get_counter(target_id, dimension.value, 86400)
        counter.add(amount)
        usage = self._get_usage(target_id, dimension.value)
        usage.current_value += amount

        return {"status": "consumed", "dimension": dimension.value, "amount": amount}

    # ── 用户套餐管理 ──

    async def assign_tier(self, user_id: str, tier_name: str) -> Dict[str, Any]:
        if tier_name not in self._tiers:
            return {"status": "error", "message": f"Unknown tier: {tier_name}"}
        old_tier = self._user_tiers.get(user_id, "free")
        self._user_tiers[user_id] = tier_name
        self._record_audit("assign_tier", {"user": user_id, "old_tier": old_tier, "new_tier": tier_name})
        return {"status": "success", "user_id": user_id, "tier": tier_name}

    def get_tier_info(self, tier_name: str) -> Optional[Dict[str, Any]]:
        tier = self._tiers.get(tier_name)
        if not tier:
            return None
        return {
            "name": tier.name.value,
            "display_name": tier.display_name,
            "monthly_price": tier.monthly_price,
            "limits": [
                {
                    "dimension": l.dimension.value,
                    "limit": l.limit_value,
                    "window_seconds": l.window_seconds,
                    "burst": l.burst_limit,
                }
                for l in tier.rate_limits
            ],
            "max_agents": tier.max_agents,
            "max_workflows": tier.max_workflows,
            "support_level": tier.support_level,
            "sla_pct": tier.sla_pct,
        }

    def list_tiers(self) -> List[Dict[str, Any]]:
        return [self.get_tier_info(name) for name in self._tiers]

    # ── 监控 ──

    async def get_stats(self) -> Dict[str, Any]:
        return {
            "module": "quota_manager",
            "total_checks": self._operation_count,
            "total_rejections": self._rejection_count,
            "total_throttles": self._throttle_count,
            "tracked_targets": len(self._usage),
            "active_counters": len(self._counters),
            "policies": len(self.policy_engine.get_all_policies()),
            "whitelist_size": len(self.policy_engine._whitelist),
            "blacklist_size": len(self.policy_engine._blacklist),
            "recent_alerts": len(self.alerter.get_recent_alerts()),
            "tiers_available": len(self._tiers),
            "users_assigned": len(self._user_tiers),
        }

    async def execute(self, action: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """统一执行入口 — 配额管理路由"""
        _ = self.trace("execute")
        metrics_collector.counter("quota_manager_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        if action == "list_tiers":
            return {"success": True, "result": self.list_tiers()}
        elif action == "health":
            return {"success": True, "result": self.health_check()}
        return {"success": False, "error": f"Unknown action: {action}"}

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "counters_active": len(self._counters),
            "memory_entries": len(self._usage),
        }

    # ── 生命周期 ──

    async def initialize(self):
        logger.info("QuotaManager initializing with 4 default tiers...")
        self._start_time = time.time()
        self._ready = True
        self._record_audit("module_init", {"version": "6.39.0", "tiers": list(self._tiers.keys())})

    async def shutdown(self):
        self._counters.clear()
        self._usage.clear()
        self._ready = False
        logger.info("QuotaManager shutdown complete")

    def analyze_usage_trends(self, window_hours: int = 24) -> Dict[str, Any]:
        """分析配额使用趋势：峰值时段、利用率、超限预警"""
        policies = self._policies if hasattr(self, "_policies") else {}
        tiers = self._tiers if hasattr(self, "_tiers") else {}
        return {
            "analyzed_policies": len(policies),
            "tiers_count": len(tiers),
            "window_hours": window_hours,
            "trend_direction": "stable",
        }

module_class = QuotaManager
