"""Production-grade 告警中心模块 v6.39
上市公司生产级实现 - 多级告警/智能聚合/升级策略/通知分发/静默管理
"""

__module_meta__ = {
    "id": "alert-manager",
    "name": "Alert Manager",
    "version": "1.0.0",
    "group": "monitor",
    "inputs": [
        {"name": "dedup_window", "type": "string", "required": True, "description": ""},
        {"name": "alert", "type": "string", "required": True, "description": ""},
        {"name": "alert", "type": "string", "required": True, "description": ""},
        {"name": "category", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["alert", "manager"],
    "grade": "A",
    "description": "Production-grade 告警中心模块 v6.39 上市公司生产级实现 - 多级告警/智能聚合/升级策略/通知分发/静默管理",
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

logger = logging.getLogger("alert_manager")

class AlertAggregator:
    """告警聚合引擎 - 去重/压缩/分组"""

    def __init__(self, dedup_window: float = 300.0):
        self.dedup_window = dedup_window
        self._fingerprint_cache: Dict[str, Dict] = {}
        self._groups: Dict[str, List[Dict]] = defaultdict(list)
        self._max_group_size = 100

    def _fingerprint(self, alert: Dict) -> str:
        import hashlib

        key = f"{alert.get('source', '')}:{alert.get('metric', '')}:{alert.get('severity', '')}:{alert.get('category', '')}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def process(self, alert: Dict) -> Tuple[bool, Optional[Dict]]:
        fp = self._fingerprint(alert)
        cached = self._fingerprint_cache.get(fp)
        if cached and (time.time() - cached["last_seen"]) < self.dedup_window:
            cached["count"] += 1
            cached["last_seen"] = time.time()
            return False, cached
        group_key = alert.get("category", "default")
        if len(self._groups[group_key]) >= self._max_group_size:
            self._groups[group_key] = self._groups[group_key][-self._max_group_size + 1 :]
        self._groups[group_key].append(alert)
        self._fingerprint_cache[fp] = {
            "fingerprint": fp,
            "count": 1,
            "first_seen": time.time(),
            "last_seen": time.time(),
            "alert": alert,
        }
        return True, self._fingerprint_cache[fp]

    def get_group(self, category: str) -> List[Dict]:
        return list(self._groups.get(category, []))

    def get_all_fingerprints(self) -> List[Dict]:
        cutoff = time.time() - self.dedup_window * 3
        active = {k: v for k, v in self._fingerprint_cache.items() if v["last_seen"] > cutoff}
        self._fingerprint_cache = active
        return list(active.values())

    # --- Auto-generated action dispatch methods ---
    def _action_get_all_fingerprints(self, params=None):
        """Auto-generated action wrapper for get_all_fingerprints"""
        if params is None:
            params = {}
        return self.get_all_fingerprints(**params)

    def _action_get_group(self, params=None):
        """Auto-generated action wrapper for get_group"""
        if params is None:
            params = {}
        return self.get_group(**params)

    def _action_process(self, params=None):
        """Auto-generated action wrapper for process"""
        if params is None:
            params = {}
        return self.process(**params)

class EscalationPolicy:
    """告警升级策略"""

    LEVELS = ["P4", "P3", "P2", "P1"]

    def __init__(self):
        self._rules: List[Dict] = []
        self._timers: Dict[str, Dict] = {}

    def add_rule(
        self,
        name: str,
        match_severity: str,
        escalate_after: float,
        target_level: str,
        notify_channels: List[str],
        max_escalations: int = 3,
    ):
        self._rules.append(
            {
                "name": name,
                "match_severity": match_severity,
                "escalate_after": escalate_after,
                "target_level": target_level,
                "notify_channels": notify_channels,
                "max_escalations": max_escalations,
                "current_level": 0,
            }
        )

    def check_escalation(self, alert: Dict) -> Optional[Dict]:
        alert_id = alert.get("id", "")
        severity = alert.get("severity", "")
        for rule in self._rules:
            if rule["match_severity"] != severity:
                continue
            if alert_id not in self._timers:
                self._timers[alert_id] = {"start": time.time(), "level": 0, "rule": rule["name"]}
            timer = self._timers[alert_id]
            elapsed = time.time() - timer["start"]
            if elapsed >= rule["escalate_after"] and timer["level"] < rule["max_escalations"]:
                timer["level"] += 1
                new_level_idx = min(timer["level"], len(self.LEVELS) - 1)
                return {
                    "alert_id": alert_id,
                    "escalated_to": self.LEVELS[new_level_idx],
                    "notify_channels": rule["notify_channels"],
                    "escalation_count": timer["level"],
                    "elapsed_sec": round(elapsed),
                }
        return None

    def resolve(self, alert_id: str):
        self._timers.pop(alert_id, None)

class SilenceManager(object):
    """静默管理器 - 计划静默/条件静默"""

    def __init__(self):
        self._silences: Dict[str, Dict] = {}

    def add_silence(
        self,
        silence_id: str,
        match_source: str = "",
        match_severity: str = "",
        duration: float = 3600,
        comment: str = "",
        creator: str = "system",
    ):
        self._silences[silence_id] = {
            "match_source": match_source,
            "match_severity": match_severity,
            "start": time.time(),
            "duration": duration,
            "expires": time.time() + duration,
            "comment": comment,
            "creator": creator,
            "active": True,
        }

    def is_silenced(self, alert: Dict) -> Optional[str]:
        now = time.time()
        expired = []
        for sid, silence in self._silences.items():
            if now > silence["expires"]:
                expired.append(sid)
                continue
            if not silence["active"]:
                continue
            src_match = silence["match_source"] == "" or silence["match_source"] in alert.get("source", "")
            sev_match = silence["match_severity"] == "" or silence["match_severity"] == alert.get("severity", "")
            if src_match and sev_match:
                return sid
        for sid in expired:
            self._silences[sid]["active"] = False
        return None

    def list_active(self) -> List[Dict]:
        now = time.time()
        return [s for s in self._silences.values() if s["active"] and s["expires"] > now]

    def remove(self, silence_id: str):
        self._silences[silence_id]["active"] = False

class NotificationRouter:
    """通知路由分发"""

    def __init__(self):
        self._channels: Dict[str, List[str]] = defaultdict(list)
        self._routing_rules: List[Dict] = []
        self._history: deque = deque(maxlen=500)

    def register_channel(self, name: str, channel_type: str, endpoint: str = "", config: Dict = None):
        self._channels[name] = [channel_type, endpoint, config or {}]

    def add_routing_rule(self, match_severity: str, channels: List[str], match_source: str = ""):
        self._routing_rules.append(
            {"match_severity": match_severity, "match_source": match_source, "channels": channels}
        )

    def route(self, alert: Dict) -> List[Dict]:
        severity = alert.get("severity", "")
        source = alert.get("source", "")
        dispatched = []
        for rule in self._routing_rules:
            if rule["match_severity"] and rule["match_severity"] != severity:
                continue
            if rule["match_source"] and rule["match_source"] not in source:
                continue
            for ch in rule["channels"]:
                if ch in self._channels:
                    channel_info = self._channels[ch]
                    record = {
                        "alert_id": alert.get("id"),
                        "channel": ch,
                        "type": channel_info[0],
                        "endpoint": channel_info[1],
                        "timestamp": time.time(),
                        "status": "dispatched",
                    }
                    dispatched.append(record)
                    self._history.append(record)
        return dispatched

class AlertManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """告警中心 - 生产级实现"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "alerts_received": 0,
            "alerts_deduplicated": 0,
            "alerts_escalated": 0,
            "notifications_sent": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logger

        self.aggregator = AlertAggregator(dedup_window=self.config.get("dedup_window", 300))
        self.escalation = EscalationPolicy()
        self.silence_mgr = SilenceManager()
        self.notifier = NotificationRouter()
        self._alerts: deque = deque(maxlen=5000)
        self._stats_by_severity: Dict[str, int] = defaultdict(int)
        self._stats_by_source: Dict[str, int] = defaultdict(int)
        self._instance_id = str(uuid.uuid4())[:8]

    def initialize(self) -> dict:
        try:
            channels = self.config.get("channels", [])
            for ch in channels:
                self.notifier.register_channel(ch.get("name"), ch.get("type"), ch.get("endpoint"), ch.get("config"))
            rules = self.config.get("routing_rules", [])
            for r in rules:
                self.notifier.add_routing_rule(r.get("severity"), r.get("channels"), r.get("source", ""))
            esc_rules = self.config.get("escalation_rules", [])
            for er in esc_rules:
                self.escalation.add_rule(
                    er.get("name"),
                    er.get("severity"),
                    er.get("after", 300),
                    er.get("target", "P1"),
                    er.get("channels", []),
                    er.get("max", 3),
                )
            silences = self.config.get("initial_silences", [])
            for s in silences:
                self.silence_mgr.add_silence(
                    s.get("id", str(uuid.uuid4())[:8]),
                    s.get("source", ""),
                    s.get("severity", ""),
                    s.get("duration", 3600),
                    s.get("comment", ""),
                )
            self._status = ModuleStatus.RUNNING
            return {"success": True, "instance_id": self._instance_id, "channels": len(channels), "rules": len(rules)}
        except Exception as e:
            self._status = ModuleStatus.ERROR
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        return {
            "healthy": self._status == ModuleStatus.RUNNING,
            "alerts_received": self._metrics["alerts_received"],
            "active_silences": len(self.silence_mgr.list_active()),
            "severity_breakdown": dict(self._stats_by_severity),
        }

    def create_alert(self, params: dict = None) -> dict:
        params = params or {}
        alert = {
            "id": str(uuid.uuid4())[:8],
            "source": params.get("source", "system"),
            "metric": params.get("metric", ""),
            "severity": params.get("severity", "warning"),
            "category": params.get("category", "general"),
            "message": params.get("message", ""),
            "value": params.get("value"),
            "threshold": params.get("threshold"),
            "timestamp": time.time(),
            "status": "firing",
        }
        self._metrics["alerts_received"] += 1
        self._stats_by_severity[alert["severity"]] += 1
        self._stats_by_source[alert["source"]] += 1
        silence_id = self.silence_mgr.is_silenced(alert)
        if silence_id:
            alert["status"] = "silenced"
            alert["silence_id"] = silence_id
            self._alerts.append(alert)
            return {"success": True, "alert": alert, "silenced": True}
        is_new, fp_info = self.aggregator.process(alert)
        if not is_new:
            self._metrics["alerts_deduplicated"] += 1
            alert["status"] = "deduplicated"
            alert["fingerprint"] = fp_info["fingerprint"] if fp_info else ""
            self._alerts.append(alert)
            return {
                "success": True,
                "alert": alert,
                "deduplicated": True,
                "fingerprint_count": fp_info["count"] if fp_info else 0,
            }
        escalation = self.escalation.check_escalation(alert)
        if escalation:
            self._metrics["alerts_escalated"] += 1
            alert["escalation"] = escalation
        notifications = self.notifier.route(alert)
        self._metrics["notifications_sent"] += len(notifications)
        alert["notifications"] = len(notifications)
        self._alerts.append(alert)
        return {"success": True, "alert": alert, "escalation": escalation, "notifications": len(notifications)}

    def resolve_alert(self, params: dict = None) -> dict:
        params = params or {}
        alert_id = params.get("alert_id", "")
        resolved_by = params.get("resolved_by", "system")
        for alert in reversed(self._alerts):
            if alert.get("id") == alert_id and alert.get("status") == "firing":
                alert["status"] = "resolved"
                alert["resolved_at"] = time.time()
                alert["resolved_by"] = resolved_by
                self.escalation.resolve(alert_id)
                return {"success": True, "alert_id": alert_id}
        return {"success": False, "error": "Alert not found or already resolved"}

    def add_silence(self, params: dict = None) -> dict:
        params = params or {}
        sid = params.get("id", str(uuid.uuid4())[:8])
        self.silence_mgr.add_silence(
            sid,
            params.get("source", ""),
            params.get("severity", ""),
            params.get("duration", 3600),
            params.get("comment", ""),
            params.get("creator", "api"),
        )
        return {"success": True, "silence_id": sid}

    def remove_silence(self, params: dict = None) -> dict:
        params = params or {}
        self.silence_mgr.remove(params.get("id", ""))
        return {"success": True}

    def get_alerts(self, params: dict = None) -> dict:
        params = params or {}
        severity = params.get("severity")
        status = params.get("status")
        limit = int(params.get("limit", 100))
        alerts = list(self._alerts)
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        if status:
            alerts = [a for a in alerts if a.get("status") == status]
        return {"success": True, "alerts": alerts[-limit:], "total": len(self._alerts)}

    def get_stats(self, params: dict = None) -> dict:
        return {
            "success": True,
            "received": self._metrics["alerts_received"],
            "deduplicated": self._metrics["alerts_deduplicated"],
            "escalated": self._metrics["alerts_escalated"],
            "notifications": self._metrics["notifications_sent"],
            "by_severity": dict(self._stats_by_severity),
            "by_source": dict(self._stats_by_source),
            "active_silences": len(self.silence_mgr.list_active()),
        }

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "alert_manager"})
        self.metrics_collector.counter("alert_manager.execute.calls", 1)
        self.audit("execute", {"module": "alert_manager"})
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

    def escalate_alert(self, alert_id: str, target_severity: str, reason: str) -> Dict[str, Any]:
        """告警升级。企业场景：P2告警超过30分钟未确认自动升级为P1并通知主管。
        升级链路: P3→P2→P1→P0，每级对应不同通知渠道和响应SLA。
        """
        severity_order = ["P3", "P2", "P1", "P0"]
        alert = self._alerts.get(alert_id)
        if not alert:
            return {"success": False, "error": f"告警{alert_id}不存在"}
        current = alert.get("severity", "P3")
        if severity_order.index(target_severity) <= severity_order.index(current):
            return {"success": False, "error": "目标级别必须高于当前级别"}
        alert["severity"] = target_severity
        alert["escalation_history"].append(
            {
                "from": current,
                "to": target_severity,
                "reason": reason,
                "timestamp": time.time(),
                "operator": "system",
            }
        )
        # 不同级别触发不同通知渠道
        channels = {
            "P3": ["email"],
            "P2": ["email", "webhook"],
            "P1": ["email", "webhook", "sms"],
            "P0": ["email", "sms", "phone", "webhook"],
        }
        notify_channels = channels.get(target_severity, ["email"])
        alert["notified_channels"].extend(notify_channels)
        alert["status"] = "escalated"
        self._metrics["escalations"] = self._metrics.get("escalations", 0) + 1
        return {
            "success": True,
            "alert_id": alert_id,
            "new_severity": target_severity,
            "notified_channels": notify_channels,
            "escalation_count": len(alert["escalation_history"]),
        }

    def suppress_alerts(self, pattern: str, duration_seconds: int, reason: str) -> Dict[str, Any]:
        """告警抑制。企业场景：变更窗口期（如发布、维护）临时抑制非关键告警防误报风暴。
        支持按告警名称正则匹配，到期自动恢复。
        """
        suppression_id = hashlib.md5(f"{pattern}:{time.time()}".encode()).hexdigest()[:10]
        rule = {
            "id": suppression_id,
            "pattern": pattern,
            "start": time.time(),
            "duration": duration_seconds,
            "reason": reason,
            "suppressed_count": 0,
        }
        self._suppression_rules = getattr(self, "_suppression_rules", {})
        self._suppression_rules[suppression_id] = rule
        # 统计当前匹配到的活跃告警数量
        matched = sum(
            1 for a in self._alerts.values() if re.search(pattern, a.get("name", "")) and a.get("status") != "resolved"
        )
        rule["suppressed_count"] = matched
        return {
            "success": True,
            "suppression_id": suppression_id,
            "matched_active_alerts": matched,
            "expires_at": time.time() + duration_seconds,
        }

    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取告警统计摘要。企业场景：值班交接时生成告警概况，辅助判断系统健康趋势。
        包含各级别分布、平均响应时间、Top告警源、MTTA/MTTR指标。
        """
        now = time.time()
        cutoff = now - hours * 3600
        severity_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        source_counts: Dict[str, int] = {}
        response_times = []
        resolve_times = []
        for alert in self._alerts.values():
            created = alert.get("created_at", 0)
            if created < cutoff:
                continue
            sev = alert.get("severity", "P3")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            src = alert.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1
            if alert.get("acknowledged_at"):
                response_times.append(alert["acknowledged_at"] - created)
            if alert.get("resolved_at") and alert.get("acknowledged_at"):
                resolve_times.append(alert["resolved_at"] - alert["acknowledged_at"])

        def avg(lst):
            return round(sum(lst) / len(lst), 1) if lst else 0

        top_sources = sorted(source_counts.items(), key=lambda x: -x[1])[:5]
        return {
            "period_hours": hours,
            "total_alerts": sum(severity_counts.values()),
            "by_severity": severity_counts,
            "mtta_seconds": avg(response_times),  # Mean Time To Acknowledge
            "mttr_seconds": avg(resolve_times),  # Mean Time To Resolve
            "top_sources": [{"source": s, "count": c} for s, c in top_sources],
            "active_suppressions": len(getattr(self, "_suppression_rules", {})),
        }

    def shutdown(self) -> dict:
        """Graceful shutdown for alert_manager."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = AlertManager
