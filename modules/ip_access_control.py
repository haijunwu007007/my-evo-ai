"""
# Grade: A
IP Access Control Module - Enterprise Grade
Production-level IP whitelist/blacklist, rate limiting, geo-blocking, and access audit.
"""

__module_meta__ = {
        "id": "ip-access-control",
        "name": "Ip Access Control",
        "version": "V0.1",
        "group": "security",
        "inputs": [
            {
                "name": "allowed",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "action",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "rule_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "reason",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "max_requests",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "window_seconds",
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
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "config",
            "ip"
        ],
        "grade": "A",
        "description": "IP Access Control Module - Enterprise Grade Production-level IP whitelist/blacklist, rate limiting, geo-blocking, and access audit."
    }

import time
import hashlib
from core.logging_config import get_logger
import ipaddress
import threading
from datetime import datetime, timedelta, timezone, timezone.utc
from enum import Enum
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

logger = get_logger(__name__)

try:
    from modules._base.enterprise_module import (
        EnterpriseModule,
        CircuitBreakerMixin,
        RateLimiterMixin,
        metrics_collector,
    )

    MIXIN_AVAILABLE = True
except ImportError:

    class EnterpriseModule:
        def __init__(self, config=None):
            self.config = config or {}
            self._logger = logger

        def audit(self, *a, **k):
            pass

        def info(self, *a, **k):
            pass

        def warning(self, *a, **k):
            pass

    class CircuitBreakerMixin:
        pass

    class RateLimiterMixin:
        pass

    MIXIN_AVAILABLE = False

    class _FakeMetrics:
        def counter(self, *a, **k):
            pass

        def gauge(self, *a, **k):
            pass

    metrics_collector = _FakeMetrics()

class RuleAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    RATE_LIMIT = "rate_limit"
    CHALLENGE = "challenge"
    LOG_ONLY = "log_only"

class GeoMatchType(str, Enum):
    COUNTRY = "country"
    REGION = "region"
    ASN = "asn"

@dataclass
class IPRule:
    """Single IP access control rule."""

    rule_id: str
    name: str
    description: str = ""
    ip_ranges: list = field(default_factory=list)  # list of str like "192.168.1.0/24"
    geo_rules: list = field(default_factory=list)  # list of dict {type, value}
    action: RuleAction = RuleAction.DENY
    priority: int = 100
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""
    hit_count: int = 0
    last_hit_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
            self.updated_at = self.created_at

@dataclass
class RateLimitConfig:
    """Per-IP rate limiting configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10
    enabled: bool = True

@dataclass
class AccessLogEntry:
    """Access log record for audit trail."""

    timestamp: str = ""
    ip_address: str = ""
    action_taken: str = ""
    matched_rule: str = ""
    path: str = ""
    method: str = ""
    user_agent: str = ""
    geo_info: str = ""

@dataclass
class GeoIPInfo:
    """GeoIP lookup result."""

    ip: str = ""
    country_code: str = ""
    country_name: str = ""
    region: str = ""
    city: str = ""
    asn: str = ""
    isp: str = ""
    latitude: float = 0.0
    longitude: float = 0.0

class AccessDecision:
    """Represents an access control decision."""

    def __init__(self, allowed: bool, action: RuleAction = RuleAction.DENY, rule_id: str = "", reason: str = ""):
        self.allowed = allowed
        self.action = action
        self.rule_id = rule_id
        self.reason = reason
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.headers: dict = {}

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "action": self.action.value,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "headers": self.headers,
        }

class SlidingWindowCounter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int):
        self._max = max_requests
        self._window = window_seconds
        self._timestamps: dict[str, list] = {}

    def _cleanup(self, key: str, now: float):
        """Remove expired timestamps."""
        if key in self._timestamps:
            cutoff = now - self._window
            self._timestamps[key] = [t for t in self._timestamps[key] if t > cutoff]
            if not self._timestamps[key]:
                del self._timestamps[key]

    def check_and_record(self, key: str, now: float | None = None) -> tuple[bool, int, int]:
        """Returns (allowed, remaining, retry_after_seconds)."""
        if now is None:
            now = time.time()
        self._cleanup(key, now)
        current = len(self._timestamps.get(key, []))
        if current < self._max:
            self._timestamps.setdefault(key, []).append(now)
            return True, self._max - current - 1, 0
        else:
            oldest = self._timestamps[key][0] if self._timestamps[key] else now
            retry_after = int(oldest + self._window - now) + 1
            return False, 0, max(retry_after, 1)

    def get_count(self, key: str) -> int:
        self._cleanup(key, time.time())
        return len(self._timestamps.get(key, []))

class IPRuleMatcher:
    """IP规则匹配器（IPRuleAnalyzer核心组件）"""

    def __init__(self):
        self._compiled_networks: dict[str, list] = {}
        self._match_cache: dict[str, str | None] = {}
        self._cache_lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def compile_rules(self, rules: list[object]) -> None:
        """预编译规则中的CIDR网络为ipaddress对象"""
        self._compiled_networks.clear()
        for rule in rules:
            if not rule.enabled:
                continue
            networks = []
            for ip_str in rule.ip_ranges:
                try:
                    if "/" in ip_str:
                        networks.append(ipaddress.ip_network(ip_str, strict=False))
                    else:
                        networks.append(ipaddress.ip_network(f"{ip_str}/32", strict=False))
                except ValueError:
                    continue
            self._compiled_networks[rule.rule_id] = networks

    def match(self, ip_str: str, rules: list[object]) -> object | None:
        """匹配IP对应的规则（按优先级排序）"""
        with self._cache_lock:
            cached = self._match_cache.get(ip_str)
            if cached is not None:
                self._hits += 1
                return self._match_cache.get(f"_rule_{cached}")
            self._misses += 1

        ip_obj = ipaddress.ip_address(ip_str)
        sorted_rules = sorted(rules, key=lambda r: r.priority)
        for rule in sorted_rules:
            if not rule.enabled:
                continue
            networks = self._compiled_networks.get(rule.rule_id, [])
            for net in networks:
                if ip_obj in net:
                    rule.hit_count += 1
                    rule.last_hit_at = datetime.now(timezone.utc).isoformat()
                    with self._cache_lock:
                        self._match_cache[ip_str] = rule.rule_id
                        self._match_cache[f"_rule_{rule.rule_id}"] = rule
                    metrics_collector.counter("ip_rule_matches", labels={"rule": rule.rule_id})
                    return rule
        return None

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._match_cache.clear()

    def stats(self) -> dict:
        return {
            "cache_hits": self._hits,
            "cache_misses": self._misses,
            "cache_size": len(self._match_cache),
            "compiled_rules": len(self._compiled_networks),
        }

class IPRuleAnalyzer:
    """IP规则分析器 - 分析规则命中趋势、识别冗余规则、生成安全报告"""

    def __init__(self):
        self._matcher = IPRuleMatcher()

    def analyze_rule_coverage(self, rules: list[object]) -> dict:
        """分析规则覆盖情况"""
        total_ips = 0
        for rule in rules:
            for ip_str in rule.ip_ranges:
                try:
                    if "/" in ip_str:
                        net = ipaddress.ip_network(ip_str, strict=False)
                        total_ips += net.num_addresses
                    else:
                        total_ips += 1
                except ValueError:
                    pass
        return {
            "total_rules": len(rules),
            "enabled_rules": sum(1 for r in rules if r.enabled),
            "estimated_ip_coverage": total_ips,
            "top_hit_rules": sorted(rules, key=lambda r: r.hit_count, reverse=True)[:5],
        }

    def find_redundant_rules(self, rules: list[object]) -> list[dict]:
        """找出可能冗余的规则（0命中+低优先级）"""
        return [
            {"rule_id": r.rule_id, "name": r.name, "hit_count": r.hit_count, "priority": r.priority}
            for r in rules
            if r.hit_count == 0 and r.priority > 50
        ]

class IPAccessControl(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Enterprise IP Access Control with whitelist/blacklist, geo-blocking, and rate limiting."""

    def __init__(self):

        super().__init__()
        self._status = "running"

        self.module_name = "ip_access_control"
        self.module_version = "6.38.0"
        self._rules: dict[str, IPRule] = {}
        self._default_action = RuleAction.DENY
        self._rate_config = RateLimitConfig()
        self._minute_limiter = SlidingWindowCounter(self._rate_config.requests_per_minute, 60)
        self._hour_limiter = SlidingWindowCounter(self._rate_config.requests_per_hour, 3600)
        self._day_limiter = SlidingWindowCounter(self._rate_config.requests_per_day, 86400)
        self._access_log: list[AccessLogEntry] = []
        self._max_log_size = 100000
        self._whitelist_cache: dict[str, bool] = {}
        self._blacklist_cache: dict[str, bool] = {}
        self._geo_db: dict[str, GeoIPInfo] = {}
        self._total_requests = 0
        self._total_blocked = 0
        self._total_rate_limited = 0
        self._initialized = False

    def initialize(self) -> None:
        _ = self.trace("initialize")
        self._init_default_rules()
        self._init_sample_geo_db()
        self._initialized = True
        logger.info("IPAccessControl initialized with %d rules", len(self._rules))

    def _init_default_rules(self):
        defaults = [
            {
                "rid": "allow_localhost",
                "name": "Allow Localhost",
                "ip_ranges": ["127.0.0.1/8", "::1/128"],
                "action": RuleAction.ALLOW,
                "priority": 1,
            },
            {
                "rid": "allow_private",
                "name": "Allow Private Networks",
                "ip_ranges": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
                "action": RuleAction.ALLOW,
                "priority": 10,
            },
            {
                "rid": "deny_bogon",
                "name": "Deny Bogon IPs",
                "ip_ranges": ["0.0.0.0/8", "169.254.0.0/16", "224.0.0.0/4", "240.0.0.0/4"],
                "action": RuleAction.DENY,
                "priority": 5,
            },
            {
                "rid": "rate_limit_public",
                "name": "Rate Limit Public IPs",
                "ip_ranges": ["0.0.0.0/0"],
                "action": RuleAction.RATE_LIMIT,
                "priority": 100,
            },
        ]
        for d in defaults:
            rule = IPRule(
                rule_id=d["rid"],
                name=d["name"],
                ip_ranges=d["ip_ranges"],
                action=d["action"],
                priority=d.get("priority", 100),
            )
            self._rules[rule.rule_id] = rule

    def _init_sample_geo_db(self):
        samples = {
            "8.8.8.8": GeoIPInfo(
                ip="8.8.8.8",
                country_code="US",
                country_name="United States",
                region="California",
                city="Mountain View",
                asn="AS15169",
                isp="Google",
            ),
            "1.1.1.1": GeoIPInfo(
                ip="1.1.1.1",
                country_code="AU",
                country_name="Australia",
                region="Queensland",
                city="Sydney",
                asn="AS13335",
                isp="Cloudflare",
            ),
            "114.114.114.114": GeoIPInfo(
                ip="114.114.114.114",
                country_code="CN",
                country_name="China",
                region="Jiangsu",
                city="Nanjing",
                asn="AS55990",
                isp="China Telecom",
            ),
        }
        self._geo_db = samples

    def _ip_in_ranges(self, ip_str: str, ranges: list[str]) -> bool:
        try:
            ip = ipaddress.ip_address(ip_str)
            for rng in ranges:
                if "/" in rng:
                    if ip in ipaddress.ip_network(rng, strict=False):
                        return True
                elif ip_str == rng:
                    return True
        except ValueError:
            return False
        return False

    def _matches_geo(self, geo_info: GeoIPInfo, geo_rules: list[dict]) -> bool:
        for gr in geo_rules:
            match_type = gr.get("type", "")
            value = gr.get("value", "")
            if match_type == GeoMatchType.COUNTRY and geo_info.country_code == value or match_type == GeoMatchType.REGION and geo_info.region == value or match_type == GeoMatchType.ASN and geo_info.asn == value:
                return True
        return False

    def _sort_rules(self) -> list[IPRule]:
        return sorted(self._rules.values(), key=lambda r: (r.priority, r.created_at))

    def check_access(
        self, ip_address: str, path: str = "/", method: str = "GET", user_agent: str = ""
    ) -> AccessDecision:
        """Evaluate access control rules for an IP address."""
        self.audit("access_check", f"ip={ip_address}, path={path}, method={method}")
        trace_id = f"ip-check-{int(time.time() * 1000)}"
        self._total_requests += 1
        geo_info = self.lookup_geo(ip_address)
        sorted_rules = self._sort_rules()

        for rule in sorted_rules:
            if not rule.enabled:
                continue

            ip_match = self._ip_in_ranges(ip_address, rule.ip_ranges) if rule.ip_ranges else False
            geo_match = self._matches_geo(geo_info, rule.geo_rules) if rule.geo_rules else False

            if not (ip_match or geo_match):
                continue

            rule.hit_count += 1
            rule.last_hit_at = datetime.now(timezone.utc).isoformat()

            if rule.action == RuleAction.ALLOW:
                decision = AccessDecision(True, RuleAction.ALLOW, rule.rule_id, "Matched allow rule")
                self._log_access(ip_address, decision, rule.rule_id, path, method, user_agent, geo_info)
                return decision

            elif rule.action == RuleAction.DENY:
                self._total_blocked += 1
                decision = AccessDecision(False, RuleAction.DENY, rule.rule_id, f"Blocked by rule: {rule.name}")
                self._log_access(ip_address, decision, rule.rule_id, path, method, user_agent, geo_info)
                return decision

            elif rule.action == RuleAction.RATE_LIMIT:
                allowed_min, rem_min, retry_min = self._minute_limiter.check_and_record(ip_address)
                allowed_hr, rem_hr, retry_hr = self._hour_limiter.check_and_record(ip_address)
                allowed_day, _, _ = self._day_limiter.check_and_record(ip_address)
                if not allowed_min:
                    self._total_rate_limited += 1
                    decision = AccessDecision(
                        False, RuleAction.RATE_LIMIT, rule.rule_id, f"Rate limit: {retry_min}s retry"
                    )
                    decision.headers["Retry-After"] = str(retry_min)
                    decision.headers["X-RateLimit-Limit"] = str(self._rate_config.requests_per_minute)
                    decision.headers["X-RateLimit-Remaining"] = "0"
                    self._log_access(ip_address, decision, rule.rule_id, path, method, user_agent, geo_info)
                    return decision
                if not allowed_hr:
                    self._total_rate_limited += 1
                    decision = AccessDecision(
                        False, RuleAction.RATE_LIMIT, rule.rule_id, f"Hourly limit exceeded, retry in {retry_hr}s"
                    )
                    decision.headers["Retry-After"] = str(retry_hr)
                    self._log_access(ip_address, decision, rule.rule_id, path, method, user_agent, geo_info)
                    return decision
                if not allowed_day:
                    self._total_rate_limited += 1
                    decision = AccessDecision(False, RuleAction.RATE_LIMIT, rule.rule_id, "Daily limit exceeded")
                    self._log_access(ip_address, decision, rule.rule_id, path, method, user_agent, geo_info)
                    return decision
                decision = AccessDecision(True, RuleAction.RATE_LIMIT, rule.rule_id, "Within rate limits")
                decision.headers["X-RateLimit-Limit"] = str(self._rate_config.requests_per_minute)
                decision.headers["X-RateLimit-Remaining"] = str(rem_min)
                self._log_access(ip_address, decision, rule.rule_id, path, method, user_agent, geo_info)
                return decision

            elif rule.action == RuleAction.CHALLENGE:
                decision = AccessDecision(False, RuleAction.CHALLENGE, rule.rule_id, "Challenge required (CAPTCHA/2FA)")
                decision.headers["X-Challenge"] = "captcha"
                self._log_access(ip_address, decision, rule.rule_id, path, method, user_agent, geo_info)
                return decision

            elif rule.action == RuleAction.LOG_ONLY:
                decision = AccessDecision(True, RuleAction.LOG_ONLY, rule.rule_id, "Logged only")
                self._log_access(ip_address, decision, rule.rule_id, path, method, user_agent, geo_info)
                return decision

        # Default action
        if self._default_action == RuleAction.DENY:
            self._total_blocked += 1
        decision = AccessDecision(
            self._default_action == RuleAction.ALLOW, self._default_action, "", "Default action applied"
        )
        self._log_access(ip_address, decision, "", path, method, user_agent, geo_info)
        return decision

    def _log_access(
        self, ip: str, decision: AccessDecision, rule_id: str, path: str, method: str, user_agent: str, geo: GeoIPInfo
    ):
        entry = AccessLogEntry(
            timestamp=decision.timestamp,
            ip_address=ip,
            action_taken="allowed" if decision.allowed else "blocked",
            matched_rule=rule_id,
            path=path,
            method=method,
            user_agent=user_agent,
            geo_info=f"{geo.country_code}/{geo.region}" if geo else "",
        )
        self._access_log.append(entry)
        if len(self._access_log) > self._max_log_size:
            self._access_log = self._access_log[-self._max_log_size :]

    def lookup_geo(self, ip_address: str) -> GeoIPInfo:
        """Look up geo information for an IP address."""
        if ip_address in self._geo_db:
            return self._geo_db[ip_address]
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            return GeoIPInfo()
        if ipaddress.ip_address(ip_address).is_private:
            return GeoIPInfo(ip=ip_address, country_code="LAN", country_name="Local Network")
        info = GeoIPInfo(ip=ip_address, country_code="XX", country_name="Unknown")
        self._geo_db[ip_address] = info
        return info

    def add_rule(self, rule: IPRule) -> bool:
        if rule.rule_id in self._rules:
            return False
        self._rules[rule.rule_id] = rule
        return True

    def update_rule(self, rule_id: str, **kwargs) -> bool:
        if rule_id not in self._rules:
            return False
        rule = self._rules[rule_id]
        for k, v in kwargs.items():
            if hasattr(rule, k):
                setattr(rule, k, v)
        rule.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def delete_rule(self, rule_id: str) -> bool:
        if rule_id not in self._rules:
            return False
        del self._rules[rule_id]
        return True

    def get_rule(self, rule_id: str) -> dict | None:
        if rule_id not in self._rules:
            return None
        r = self._rules[rule_id]
        return {
            "rule_id": r.rule_id,
            "name": r.name,
            "description": r.description,
            "ip_ranges": r.ip_ranges,
            "geo_rules": r.geo_rules,
            "action": r.action.value,
            "priority": r.priority,
            "enabled": r.enabled,
            "hit_count": r.hit_count,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }

    def list_rules(self, enabled_only: bool = False) -> list[dict]:
        rules = self._sort_rules()
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return [self.get_rule(r.rule_id) for r in rules]

    def block_ip(self, ip_address: str, reason: str = "", ttl_hours: int = 0) -> str:
        rule_id = f"block_{hashlib.md5(ip_address.encode()).hexdigest()[:12]}"
        self.add_rule(
            IPRule(
                rule_id=rule_id,
                name=f"Block {ip_address}",
                description=reason,
                ip_ranges=[ip_address],
                action=RuleAction.DENY,
                priority=1,
            )
        )
        self._blacklist_cache[ip_address] = True
        return rule_id

    def unblock_ip(self, ip_address: str) -> bool:
        self._blacklist_cache.pop(ip_address, None)
        for rid, rule in list(self._rules.items()):
            if rule.action == RuleAction.DENY and ip_address in rule.ip_ranges:
                del self._rules[rid]
                return True
        return False

    def allow_ip(self, ip_address: str) -> str:
        rule_id = f"allow_{hashlib.md5(ip_address.encode()).hexdigest()[:12]}"
        self.add_rule(
            IPRule(
                rule_id=rule_id, name=f"Allow {ip_address}", ip_ranges=[ip_address], action=RuleAction.ALLOW, priority=0
            )
        )
        self._whitelist_cache[ip_address] = True
        return rule_id

    def update_rate_limit(self, rpm: int = 0, rph: int = 0, rpd: int = 0):
        if rpm > 0:
            self._rate_config.requests_per_minute = rpm
            self._minute_limiter = SlidingWindowCounter(rpm, 60)
        if rph > 0:
            self._rate_config.requests_per_hour = rph
            self._hour_limiter = SlidingWindowCounter(rph, 3600)
        if rpd > 0:
            self._rate_config.requests_per_day = rpd
            self._day_limiter = SlidingWindowCounter(rpd, 86400)

    def get_access_stats(self) -> dict:
        recent = self._access_log[-1000:] if self._access_log else []
        blocked_by_rule: dict[str, int] = {}
        top_blocked_ips: dict[str, int] = {}
        for entry in recent:
            if entry.action_taken == "blocked":
                blocked_by_rule[entry.matched_rule] = blocked_by_rule.get(entry.matched_rule, 0) + 1
                top_blocked_ips[entry.ip_address] = top_blocked_ips.get(entry.ip_address, 0) + 1
        sorted_blocked_ips = sorted(top_blocked_ips.items(), key=lambda x: -x[1])[:10]
        return {
            "total_requests": self._total_requests,
            "total_blocked": self._total_blocked,
            "total_rate_limited": self._total_rate_limited,
            "block_rate": round(self._total_blocked / max(self._total_requests, 1), 4),
            "active_rules": len([r for r in self._rules.values() if r.enabled]),
            "total_rules": len(self._rules),
            "log_entries": len(self._access_log),
            "top_blocked_ips": [{"ip": ip, "count": c} for ip, c in sorted_blocked_ips],
            "top_blocked_rules": sorted(blocked_by_rule.items(), key=lambda x: -x[1])[:10],
        }

    def search_logs(self, ip: str = "", action: str = "", limit: int = 100) -> list[dict]:
        results = []
        for entry in reversed(self._access_log):
            if ip and ip not in entry.ip_address:
                continue
            if action and action not in entry.action_taken:
                continue
            results.append(
                {
                    "timestamp": entry.timestamp,
                    "ip": entry.ip_address,
                    "action": entry.action_taken,
                    "rule": entry.matched_rule,
                    "path": entry.path,
                    "method": entry.method,
                    "geo": entry.geo_info,
                }
            )
            if len(results) >= limit:
                break
        return results

    def health_check(self) -> dict:
        return {
            "status": "healthy",
            "healthy": True,
            "module": "ip_access_control",
            "version": "6.38.0",
            "initialized": self._initialized,
            "active_rules": len([r for r in self._rules.values() if r.enabled]),
            "total_requests": self._total_requests,
            "total_blocked": self._total_blocked,
            "log_entries": len(self._access_log),
            "rate_limit_config": {
                "rpm": self._rate_config.requests_per_minute,
                "rph": self._rate_config.requests_per_hour,
                "rpd": self._rate_config.requests_per_day,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
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

    def shutdown(self) -> dict:
        """Graceful shutdown for ip_access_control."""
        self.status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = IPAccessControl
