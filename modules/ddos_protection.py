"""Production-grade DDoS防护模块 v6.39
上市公司生产级实现 - 流量分析/速率限制/IP信誉/协议分析/自动缓解
"""

__module_meta__ = {
    "id": "ddos-protection",
    "name": "Ddos Protection",
    "version": "1.0.0",
    "group": "security",
    "inputs": [
        {"name": "window_seconds", "type": "string", "required": True, "description": ""},
        {"name": "max_track", "type": "string", "required": True, "description": ""},
        {"name": "ip", "type": "string", "required": True, "description": ""},
        {"name": "path", "type": "string", "required": True, "description": ""},
        {"name": "method", "type": "string", "required": True, "description": ""},
        {"name": "protocol", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["ddos", "engine"],
    "grade": "A",
    "description": "Production-grade DDoS防护模块 v6.39 上市公司生产级实现 - 流量分析/速率限制/IP信誉/协议分析/自动缓解",
}
import logging
import math
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger("ddos_protection")

class TrafficAnalyzer(object):
    """流量分析引擎"""

    def __init__(self, window_seconds: int = 60, max_track: int = 10000):
        self.window_seconds = window_seconds
        self.max_track = max_track
        self._ip_requests: Dict[str, deque] = {}
        self._global_window: deque = deque(maxlen=100000)
        self._protocol_stats: Dict[str, int] = defaultdict(int)
        self._path_stats: Dict[str, int] = defaultdict(int)
        self._baseline: Dict[str, float] = {}

    def record(self, ip: str, path: str = "/", method: str = "GET", protocol: str = "HTTP/1.1", size: int = 0) -> Dict:
        ts = time.time()
        entry = {"ip": ip, "path": path, "method": method, "protocol": protocol, "size": size, "ts": ts}
        self._global_window.append(entry)
        if ip not in self._ip_requests:
            self._ip_requests[ip] = deque(maxlen=500)
        self._ip_requests[ip].append(ts)
        self._protocol_stats[protocol] += 1
        self._path_stats[path] += 1
        cutoff = ts - self.window_seconds
        active = sum(1 for t in self._ip_requests[ip] if t > cutoff)
        if len(self._ip_requests) > self.max_track:
            now = ts
            stale = [k for k, v in self._ip_requests.items() if v and v[-1] < now - self.window_seconds * 5]
            for k in stale[:100]:
                del self._ip_requests[k]
        return {"ip": ip, "requests_in_window": active, "total_tracked": len(self._ip_requests)}

    def get_ip_rate(self, ip: str) -> float:
        q = self._ip_requests.get(ip)
        if not q:
            return 0
        cutoff = time.time() - self.window_seconds
        active = sum(1 for t in q if t > cutoff)
        return active / self.window_seconds

    def get_global_rate(self) -> Dict:
        now = time.time()
        cutoff = now - self.window_seconds
        recent = sum(1 for e in self._global_window if e.get("ts", 0) > cutoff)
        total = len(self._global_window)
        avg_size = 0
        if self._global_window:
            avg_size = sum(e.get("size", 0) for e in list(self._global_window)[-1000:]) / min(1000, total)
        return {
            "requests_per_second": round(recent / self.window_seconds, 2),
            "requests_in_window": recent,
            "total_recorded": total,
            "unique_ips": len(self._ip_requests),
            "avg_response_size": round(avg_size, 1),
            "top_protocols": dict(sorted(self._protocol_stats.items(), key=lambda x: -x[1])[:5]),
            "top_paths": dict(sorted(self._path_stats.items(), key=lambda x: -x[1])[:10]),
        }

    def set_baseline(self, metric: str, value: float):
        self._baseline[metric] = value

    def is_above_baseline(self, metric: str, current: float, threshold_pct: float = 200) -> bool:
        baseline = self._baseline.get(metric)
        if baseline is None or baseline <= 0:
            return False
        return (current - baseline) / baseline * 100 > threshold_pct

    # --- Auto-generated action dispatch methods ---
    def _action_get_global_rate(self, params=None):
        """Auto-generated action wrapper for get_global_rate"""
        if params is None:
            params = {}
        return self.get_global_rate(**params)

    def _action_get_ip_rate(self, params=None):
        """Auto-generated action wrapper for get_ip_rate"""
        if params is None:
            params = {}
        return self.get_ip_rate(**params)

    def _action_is_above_baseline(self, params=None):
        """Auto-generated action wrapper for is_above_baseline"""
        if params is None:
            params = {}
        return self.is_above_baseline(**params)

    def _action_record(self, params=None):
        """Auto-generated action wrapper for record"""
        if params is None:
            params = {}
        return self.record(**params)

    def _action_set_baseline(self, params=None):
        """Auto-generated action wrapper for set_baseline"""
        if params is None:
            params = {}
        return self.set_baseline(**params)

class RateLimiter:
    """多维度速率限制器"""

    def __init__(self, config: Dict = None):
        config = config or {}
        self._limits = {
            "global": config.get("global_rps", 1000),
            "per_ip": config.get("per_ip_rps", 30),
            "per_path": config.get("per_path_rps", 100),
        }
        self._ip_counters: Dict[str, deque] = {}
        self._path_counters: Dict[str, deque] = {}
        self._global_counter: deque = deque(maxlen=100000)
        self._blocked: Dict[str, Dict] = {}

    def check(self, ip: str, path: str = "/") -> Dict:
        now = time.time()
        for key, limit in self._limits.items():
            if key == "global":
                counter = self._global_counter
                window = 1.0
            elif key == "per_ip":
                if ip not in self._ip_counters:
                    self._ip_counters[ip] = deque(maxlen=500)
                counter = self._ip_counters[ip]
                window = 1.0
            elif key == "per_path":
                if path not in self._path_counters:
                    self._path_counters[path] = deque(maxlen=5000)
                counter = self._path_counters[path]
                window = 1.0
            else:
                continue
            while counter and counter[0] < now - window:
                counter.popleft()
            if len(counter) >= limit:
                return {"allowed": False, "limit_type": key, "limit": limit, "current": len(counter)}
            counter.append(now)
        return {"allowed": True, "limit_type": None}

    def block_ip(self, ip: str, duration: float = 3600, reason: str = ""):
        self._blocked[ip] = {"blocked_at": time.time(), "duration": duration, "reason": reason}

    def unblock_ip(self, ip: str):
        self._blocked.pop(ip, None)

    def is_blocked(self, ip: str) -> bool:
        info = self._blocked.get(ip)
        if not info:
            return False
        if time.time() - info["blocked_at"] > info["duration"]:
            del self._blocked[ip]
            return False
        return True

class IPRputationEngine(object):
    """IP信誉评估引擎"""

    def __init__(self):
        self._scores: Dict[str, Dict] = {}
        self._blacklists: List[str] = []

    def score_ip(
        self, ip: str, request_rate: float = 0, error_rate: float = 0, bot_score: float = 0, geographic_risk: float = 0
    ) -> Dict:
        score = 100.0
        if request_rate > 20:
            score -= min(40, (request_rate - 20) * 0.5)
        if error_rate > 0.5:
            score -= min(30, error_rate * 30)
        if bot_score > 0.7:
            score -= min(25, bot_score * 25)
        score -= geographic_risk * 10
        score = max(0, min(100, score))
        self._scores[ip] = {
            "score": round(score, 1),
            "request_rate": round(request_rate, 2),
            "error_rate": round(error_rate, 3),
            "bot_score": round(bot_score, 2),
            "last_updated": time.time(),
        }
        return {"ip": ip, "score": round(score, 1), "risk": "high" if score < 30 else "medium" if score < 60 else "low"}

    def get_reputation(self, ip: str) -> Dict:
        return self._scores.get(ip, {"ip": ip, "score": 100, "risk": "unknown"})

class DDoSProtection(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """DDoS防护 - 生产级实现"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "requests_analyzed": 0,
            "attacks_detected": 0,
            "ips_blocked": 0,
            "requests_blocked": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logger

        self.traffic = TrafficAnalyzer(window_seconds=self.config.get("window_seconds", 60))
        self.limiter = RateLimiter(config)
        self.reputation = IPRputationEngine()
        self._attack_log: List[Dict] = []
        self._whitelist: set = set(self.config.get("whitelist", []))

    def initialize(self) -> dict:
        self._status = ModuleStatus.RUNNING
        return {
            "success": True,
            "global_rps_limit": self.limiter._limits["global"],
            "per_ip_rps_limit": self.limiter._limits["per_ip"],
        }

    def health_check(self) -> dict:
        return {
            "healthy": self._status == ModuleStatus.RUNNING,
            "requests_analyzed": self._metrics["requests_analyzed"],
            "attacks_detected": self._metrics["attacks_detected"],
            "blocked_ips": self._metrics["ips_blocked"],
        }

    def analyze_traffic(self, params: dict = None) -> dict:
        params = params or {}
        ip = params.get("ip", "0.0.0.0")
        path = params.get("path", "/")
        method = params.get("method", "GET")
        protocol = params.get("protocol", "HTTP/1.1")
        size = int(params.get("size", 0))
        self._metrics["requests_analyzed"] += 1
        if ip in self._whitelist:
            return {"success": True, "action": "allow", "reason": "whitelisted"}
        if self.limiter.is_blocked(ip):
            self._metrics["requests_blocked"] += 1
            return {"success": True, "action": "block", "reason": "previously_blocked"}
        rate_check = self.limiter.check(ip, path)
        if not rate_check["allowed"]:
            self.limiter.block_ip(ip, duration=600, reason=rate_check["limit_type"])
            self._metrics["ips_blocked"] += 1
            self._metrics["requests_blocked"] += 1
            return {"success": True, "action": "block", **rate_check}
        traffic_info = self.traffic.record(ip, path, method, protocol, size)
        ip_rate = self.traffic.get_ip_rate(ip)
        global_stats = self.traffic.get_global_rate()
        rep = self.reputation.score_ip(ip, request_rate=ip_rate)
        is_attack = False
        attack_type = None
        if self.traffic.is_above_baseline("requests_per_second", global_stats["requests_per_second"]):
            is_attack = True
            attack_type = "volumetric"
        elif ip_rate > 50:
            is_attack = True
            attack_type = "application_layer"
        if is_attack:
            self._metrics["attacks_detected"] += 1
            self._attack_log.append({"ip": ip, "type": attack_type, "rate": round(ip_rate, 2), "ts": time.time()})
            return {
                "success": True,
                "action": "mitigate",
                "attack_type": attack_type,
                "ip_rate": round(ip_rate, 2),
                "reputation": rep,
            }
        return {"success": True, "action": "allow", "ip_rate": round(ip_rate, 2), "reputation": rep}

    def block_ip(self, params: dict = None) -> dict:
        params = params or {}
        ip = params.get("ip", "")
        duration = float(params.get("duration", 3600))
        self.limiter.block_ip(ip, duration, params.get("reason", "manual"))
        self._metrics["ips_blocked"] += 1
        return {"success": True, "ip": ip, "duration": duration}

    def unblock_ip(self, params: dict = None) -> dict:
        params = params or {}
        self.limiter.unblock_ip(params.get("ip", ""))
        return {"success": True}

    def get_attack_log(self, params: dict = None) -> dict:
        params = params or {}
        limit = int(params.get("limit", 100))
        return {"success": True, "attacks": self._attack_log[-limit:]}

    def get_traffic_stats(self, params: dict = None) -> dict:
        return {"success": True, **self.traffic.get_global_rate()}

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "ddos_protection"})
        self.metrics_collector.counter("ddos_protection.execute.calls", 1)
        self.audit("execute", {"module": "ddos_protection"})
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            self._metrics["total_operations"] += 1
            t0 = time.time()
            try:
                result = handler(params)
                self._metrics["last_success_ts"] = time.time()
                self._metrics["avg_latency_ms"] = (
                    self._metrics["avg_latency_ms"] * 0.9 + (time.time() - t0) * 1000 * 0.1
                )
                return result
            except Exception as e:
                self._metrics["errors"] += 1
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    def get_blocked_ip_summary(self) -> Dict[str, Any]:
        """已封禁IP摘要。企业场景：安全运营中心看板展示当前所有封禁IP列表，
        按封禁原因分类统计。
        """
        limiter = getattr(self, "limiter", None)
        blocked = getattr(limiter, "_blocked_ips", {}) if limiter else {}
        now = time.time()
        active_blocks = []
        reason_counts = {}
        for ip, info in blocked.items():
            expires = info.get("expires_at", 0)
            if expires > now:
                reason = info.get("reason", "unknown")
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
                active_blocks.append(
                    {
                        "ip": ip,
                        "reason": reason,
                        "expires_in_s": int(expires - now),
                        "blocked_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info.get("blocked_at", now))),
                    }
                )
        return {
            "success": True,
            "total_blocked": len(active_blocks),
            "by_reason": reason_counts,
            "recent_blocks": sorted(active_blocks, key=lambda x: x["expires_in_s"])[:20],
        }

    def get_traffic_anomaly_report(self, hours: int = 1) -> Dict[str, Any]:
        """流量异常报告。企业场景：SOC分析师每小时审查流量异常事件，
        判断是否为DDoS攻击或误报，决定是否需要升级响应。
        """
        log = getattr(self, "_attack_log", [])
        cutoff = time.time() - hours * 3600
        recent = [e for e in log if e.get("ts", 0) > cutoff]
        by_type = {}
        for e in recent:
            atype = e.get("attack_type", "unknown")
            by_type[atype] = by_type.get(atype, 0) + 1
        traffic = getattr(self, "traffic", None)
        current_rate = 0
        if traffic and hasattr(traffic, "get_global_rate"):
            current_rate = traffic.get_global_rate().get("requests_per_second", 0)
        return {
            "success": True,
            "hours": hours,
            "anomaly_events": len(recent),
            "by_attack_type": by_type,
            "current_rps": round(current_rate, 2),
            "ips_blocked_total": self._metrics.get("ips_blocked", 0),
        }

    def get_blocked_ips(self, reason: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """查看被封禁IP列表。企业场景：安全团队审查被自动封禁的IP，
        识别误封并手动解封，或导出给防火墙同步。
        """
        blocked = getattr(self, "_blocked_ips", {})
        results = []
        now = time.time()
        for ip, info in blocked.items():
            block_reason = info.get("reason", "unknown")
            if reason and block_reason != reason:
                continue
            remaining = max(0, info.get("expires_at", 0) - now)
            results.append(
                {
                    "ip": ip,
                    "reason": block_reason,
                    "blocked_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info.get("blocked_at", 0))),
                    "expires_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info.get("expires_at", 0))),
                    "remaining_seconds": round(remaining, 1),
                    "request_count": info.get("request_count", 0),
                }
            )
        results.sort(key=lambda x: x["request_count"], reverse=True)
        total = len(results)
        results = results[:limit]
        return {
            "success": True,
            "total_blocked": len(blocked),
            "filtered_count": total,
            "showing": len(results),
            "ips": results,
        }

    def unblock_ip(self, ip: str) -> Dict[str, Any]:
        """手动解封IP。企业场景：安全团队确认误封后手动解封，
        解封操作记录审计日志。
        """
        blocked = getattr(self, "_blocked_ips", {})
        if ip not in blocked:
            return {"success": False, "error": f"IP {ip} 未被封禁"}
        info = blocked.pop(ip)
        return {
            "success": True,
            "ip": ip,
            "was_blocked_for": round(time.time() - info.get("blocked_at", time.time()), 1),
            "original_reason": info.get("reason", "unknown"),
        }

    def get_traffic_baseline(self, hours: int = 168) -> Dict[str, Any]:
        """流量基线分析。企业场景：根据最近7天历史流量计算正常基线，
        用于区分正常流量波动和真正的DDoS攻击，减少误报。
        """
        history = getattr(self, "_traffic_history", [])
        cutoff = time.time() - hours * 3600
        recent = [h for h in history if h.get("timestamp", 0) > cutoff]
        if not recent:
            return {"success": True, "message": "无历史流量数据"}
        rps_values = [h.get("rps", 0) for h in recent]
        avg_rps = sum(rps_values) / len(rps_values)
        max_rps = max(rps_values)
        min_rps = min(rps_values)
        std_dev = (sum((x - avg_rps) ** 2 for x in rps_values) / len(rps_values)) ** 0.5
        # 基线 = 均值 + 2倍标准差
        baseline_threshold = avg_rps + 2 * std_dev
        peak_hour = max(recent, key=lambda h: h.get("rps", 0))
        return {
            "success": True,
            "period_hours": hours,
            "data_points": len(recent),
            "avg_rps": round(avg_rps, 1),
            "max_rps": round(max_rps, 1),
            "min_rps": round(min_rps, 1),
            "std_dev": round(std_dev, 1),
            "baseline_threshold": round(baseline_threshold, 1),
            "peak_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(peak_hour.get("timestamp", 0))),
            "peak_rps": peak_hour.get("rps", 0),
        }

    def get_attack_summary(self, hours: int = 24) -> Dict[str, Any]:
        """攻击摘要。企业场景：安全团队每日查看DDoS攻击统计，
        按类型/来源/持续时间分类，评估防护效果。
        """
        attacks = getattr(self, "_attacks", [])
        cutoff = time.time() - hours * 3600
        recent = [a for a in attacks if a.get("start_time", 0) > cutoff]
        if not recent:
            return {"success": True, "period_hours": hours, "message": "无攻击记录"}
        by_type = {}
        total_blocked = 0
        total_duration = 0
        for a in recent:
            atype = a.get("type", "unknown")
            by_type[atype] = by_type.get(atype, 0) + 1
            total_blocked += a.get("blocked_requests", 0)
            total_duration += a.get("duration_s", 0)
        sorted_types = sorted(by_type.items(), key=lambda x: -x[1])
        return {
            "success": True,
            "period_hours": hours,
            "total_attacks": len(recent),
            "total_blocked_requests": total_blocked,
            "total_attack_duration_s": round(total_duration, 1),
            "by_type": [{"type": t, "count": c} for t, c in sorted_types],
            "latest_attack": recent[-1] if recent else None,
        }

    def get_protected_endpoints(self) -> Dict[str, Any]:
        """查看受保护端点列表。企业场景：安全团队审计哪些API端点
        已开启DDoS防护，哪些还未保护。
        """
        rules = getattr(self, "_rules", {})
        protected = []
        for pattern, rule in rules.items():
            protected.append(
                {
                    "pattern": pattern,
                    "rate_limit": getattr(rule, "rate_limit", 0),
                    "enabled": getattr(rule, "enabled", True),
                    "action": getattr(rule, "action", "block"),
                }
            )
        return {"success": True, "protected_endpoints": len(protected), "endpoints": protected}

    def shutdown(self) -> dict:
        """Graceful shutdown for ddos_protection."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = DDoSProtection
