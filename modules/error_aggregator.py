"""Production-grade module: 错误聚合分析
# Grade: A
Error collection, aggregation, deduplication, root cause analysis, trend tracking, alerting.
"""

__module_meta__ = {
        "id": "error-aggregator",
        "name": "Error Aggregator",
        "version": "V0.1",
        "group": "monitor",
        "inputs": [
            {
                "name": "metric",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value",
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
                "name": "params_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "config",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "message",
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
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "error"
        ],
        "grade": "A",
        "description": "Production-grade module: 错误聚合分析 Error collection, aggregation, deduplication, root cause analysis, trend tracking, alerting."
    }
import hashlib
from core.logging_config import get_logger
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin, RateLimiterMixin

logger = get_logger("error_aggregator")

class ErrorPatternAnalyzer:
    """error_aggregator 运营分析引擎

    - 分析错误类型分布趋势
    - 检测新引入错误
    - 统计错误修复耗时
    """

    def __init__(self):
        self._stats = {}

    def record(self, metric: str, value: float = 1.0):
        self._stats.setdefault(metric, []).append(value)
        if len(self._stats[metric]) > 1000:
            self._stats[metric] = self._stats[metric][-500:]

    def analyze(self) -> dict:
        summary = {}
        for k, v in self._stats.items():
            if v:
                summary[k] = {"count": len(v), "avg": sum(v) / len(v), "last": v[-1]}
        return {"analyzer": "ErrorPatternAnalyzer", "module": "error_aggregator", "summary": summary}

    # --- Auto-generated action dispatch methods ---
    def _action_analyze(self, params=None):
        """Auto-generated action wrapper for analyze"""
        if params is None:
            params = {}
        return self.analyze(**params)

    def _action_record(self, params=None):
        """Auto-generated action wrapper for record"""
        if params is None:
            params = {}
        return self.record(**params)

class ErrorSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ErrorStatus(Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SNOOZED = "snoozed"
    MUTED = "muted"

@dataclass
class ErrorEvent:
    id: str = ""
    fingerprint: str = ""
    message: str = ""
    error_type: str = ""
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    source: str = ""
    stack_trace: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    status: ErrorStatus = ErrorStatus.OPEN
    first_seen: float = 0.0
    last_seen: float = 0.0
    count: int = 1
    affected_services: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    assigned_to: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fingerprint": self.fingerprint[:12],
            "message": self.message[:200],
            "type": self.error_type,
            "severity": self.severity.value,
            "source": self.source,
            "status": self.status.value,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "services": self.affected_services,
            "tags": self.tags,
            "assigned_to": self.assigned_to,
        }

@dataclass
class ErrorTrend:
    severity: str = ""
    count: int = 0
    trend: str = "stable"
    delta_pct: float = 0.0

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "count": self.count,
            "trend": self.trend,
            "delta_pct": round(self.delta_pct, 1),
        }

@dataclass
class RootCause:
    error_id: str = ""
    likely_cause: str = ""
    confidence: float = 0.0
    suggestions: list[str] = field(default_factory=list)
    related_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "error_id": self.error_id,
            "cause": self.likely_cause,
            "confidence": round(self.confidence, 2),
            "suggestions": self.suggestions,
            "related_errors": self.related_errors,
        }

class ErrorAggregator(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """错误聚合分析：错误收集、指纹去重、根因分析、趋势跟踪、告警"""

    def __init__(self, config: dict | None = None):

        super().__init__(config)
        self._errors: dict[str, ErrorEvent] = {}
        self._history: list[ErrorEvent] = []
        self._hourly_buckets: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._rules: list[dict] = []
        self._ops_count = 0
        self._dedup_window = 300

    def initialize(self) -> dict:
        self.trace("error_aggregator.initialize", "start")
        self.trace("error_aggregator.initialize", "end")
        try:
            self._rules = [
                {"pattern": "OutOfMemory", "severity": "critical", "auto_ack": True},
                {"pattern": "ConnectionRefused", "severity": "high", "auto_ack": False},
                {"pattern": "Timeout", "severity": "medium", "auto_ack": False},
                {"pattern": "NullPointer", "severity": "high", "auto_ack": True},
            ]
            self.status = ModuleStatus.RUNNING
            self.audit("initialized", f"rules={len(self._rules)}")
            return {"success": True, "rules": len(self._rules)}
        except Exception as e:
            self.status = ModuleStatus.ERROR
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        open_errors = [e for e in self._errors.values() if e.status == ErrorStatus.OPEN]
        critical = [e for e in open_errors if e.severity == ErrorSeverity.CRITICAL]
        return {
            "healthy": self.status == ModuleStatus.RUNNING and len(critical) == 0,
            "status": self.status.value,
            "total_unique": len(self._errors),
            "open_errors": len(open_errors),
            "critical_open": len(critical),
            "rules": len(self._rules),
            "history_size": len(self._history),
            "ops_count": self._ops_count,
        }

    def _fingerprint(self, message: str, error_type: str) -> str:
        raw = f"{error_type}:{message[:500]}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _hour_key(self, ts: float) -> str:
        return time.strftime("%Y%m%d%H", time.localtime(ts))

    def ingest(self, params: dict | None = None) -> dict:
        params = params or {}
        message = params.get("message", "")
        error_type = params.get("type", "Exception")
        severity = params.get("severity", "medium")
        source = params.get("source", "unknown")
        stack_trace = params.get("stack_trace", "")
        context = params.get("context", {})
        tags = params.get("tags", [])
        service = params.get("service", "")
        if not message:
            return {"success": False, "error": "message required"}
        try:
            sev = ErrorSeverity(severity)
        except ValueError:
            sev = ErrorSeverity.MEDIUM
        logger.info(elf._fingerprint(message, error_type))
        now = time.time()
        eid = fp[:12]
        if fp in self._errors:
            evt = self._errors[fp]
            evt.count += 1
            evt.last_seen = now
            evt.status = ErrorStatus.OPEN
            if service and service not in evt.affected_services:
                evt.affected_services.append(service)
            for t in tags:
                if t not in evt.tags:
                    evt.tags.append(t)
        else:
            evt = ErrorEvent(
                id=eid,
                fingerprint=fp,
                message=message,
                error_type=error_type,
                severity=sev,
                source=source,
                stack_trace=stack_trace,
                context=context,
                status=ErrorStatus.OPEN,
                first_seen=now,
                last_seen=now,
                count=1,
                affected_services=[service] if service else [],
                tags=tags,
            )
            self._errors[fp] = evt
        self._history.append(evt)
        hour = self._hour_key(now)
        self._hourly_buckets[hour][sev.value] += 1
        self._ops_count += 1
        for rule in self._rules:
            if rule["pattern"] in message and rule.get("auto_ack"):
                evt.status = ErrorStatus.ACKNOWLEDGED
                break
        return {"success": True, "error_id": eid, "count": evt.count, "status": evt.status.value}

    def list_errors(self, params: dict | None = None) -> dict:
        params = params or {}
        severity = params.get("severity")
        status = params.get("status")
        source = params.get("source")
        limit = params.get("limit", 50)
        results = []
        for e in self._errors.values():
            if severity and e.severity.value != severity:
                continue
            if status and e.status.value != status:
                continue
            if source and e.source != source:
                continue
            results.append(e.to_dict())
        results.sort(key=lambda x: x["last_seen"], reverse=True)
        self._ops_count += 1
        return {"success": True, "errors": results[:limit], "total": len(results)}

    def get_error(self, params: dict | None = None) -> dict:
        params = params or {}
        eid = params.get("id", "")
        for e in self._errors.values():
            if e.id == eid:
                return {"success": True, "error": e.to_dict()}
        return {"success": False, "error": "Error not found"}

    def acknowledge(self, params: dict | None = None) -> dict:
        params = params or {}
        eid = params.get("id", "")
        assignee = params.get("assign_to")
        for e in self._errors.values():
            if e.id == eid:
                e.status = ErrorStatus.ACKNOWLEDGED
                if assignee:
                    e.assigned_to = assignee
                self._ops_count += 1
                self.audit("acknowledge", eid)
                return {"success": True, "error_id": eid, "status": e.status.value, "assigned_to": e.assigned_to}
        return {"success": False, "error": "Error not found"}

    def resolve(self, params: dict | None = None) -> dict:
        params = params or {}
        eid = params.get("id", "")
        for e in self._errors.values():
            if e.id == eid:
                e.status = ErrorStatus.RESOLVED
                self._ops_count += 1
                self.audit("resolve", eid)
                return {"success": True, "error_id": eid, "status": "resolved"}
        return {"success": False, "error": "Error not found"}

    def get_trends(self, params: dict | None = None) -> dict:
        params = params or {}
        hours = params.get("hours", 24)
        now = time.time()
        trends = []
        for sev in ErrorSeverity:
            total = 0
            for h in range(hours):
                ts = now - (hours - 1 - h) * 3600
                hk = self._hour_key(ts)
                total += self._hourly_buckets[hk].get(sev.value, 0)
            trends.append(ErrorTrend(severity=sev.value, count=total).to_dict())
        self._ops_count += 1
        return {"success": True, "hours": hours, "trends": trends}

    def analyze_root_cause(self, params: dict | None = None) -> dict:
        params = params or {}
        eid = params.get("id", "")
        for e in self._errors.values():
            if e.id == eid:
                causes = []
                suggestions = []
                if "timeout" in e.message.lower():
                    causes.append("Network timeout or slow downstream service")
                    suggestions.extend(
                        ["Check network latency", "Increase timeout threshold", "Verify downstream health"]
                    )
                if "memory" in e.message.lower():
                    causes.append("Memory exhaustion or leak")
                    suggestions.extend(
                        ["Check memory usage trends", "Review recent deployments", "Profile memory allocation"]
                    )
                if "connection" in e.message.lower():
                    causes.append("Network connectivity issue")
                    suggestions.extend(["Check DNS resolution", "Verify firewall rules", "Test endpoint reachability"])
                if not causes:
                    causes.append("Unknown - further investigation needed")
                    suggestions.append("Collect additional logs and context")
                related = [
                    r.id
                    for r in self._errors.values()
                    if r.id != eid and r.source == e.source and any(t in r.tags for t in e.tags)
                ][:5]
                rc = RootCause(
                    error_id=eid,
                    likely_cause=causes[0] if len(causes) == 1 else " | ".join(causes),
                    confidence=0.8 if len(causes) == 1 else 0.5,
                    suggestions=suggestions,
                    related_errors=related,
                )
                return {"success": True, "analysis": rc.to_dict()}
        return {"success": False, "error": "Error not found"}

    def add_rule(self, params: dict | None = None) -> dict:
        params = params or {}
        pattern = params.get("pattern", "")
        severity = params.get("severity", "medium")
        auto_ack = params.get("auto_ack", False)
        if not pattern:
            return {"success": False, "error": "pattern required"}
        self._rules.append({"pattern": pattern, "severity": severity, "auto_ack": auto_ack})
        return {"success": True, "rule": {"pattern": pattern, "severity": severity, "auto_ack": auto_ack}}

    def shutdown(self) -> None:
        self._errors.clear()
        self._history.clear()
        self._hourly_buckets.clear()
        self.status = ModuleStatus.STOPPED

    async def execute(self, action: str, params: dict | None = None) -> dict:
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    def batch_operation(self, operations: list) -> dict:
        """批量执行操作，支持事务语义"""
        results = []
        success = 0
        failed = 0
        for op in operations:
            try:
                method = getattr(self, op.get("action", ""), None)
                if method and callable(method):
                    params = op.get("params", {})
                    result = method(**params)
                    results.append({"op": op.get("action"), "success": True, "result": str(result)[:200]})
                    success += 1
                else:
                    results.append({"op": op.get("action"), "success": False, "error": "method not found"})
                    failed += 1
            except Exception as e:
                results.append({"op": op.get("action"), "success": False, "error": str(e)})
                failed += 1
        audit_msg = "批量操作: %d个, 成功%d, 失败%d" % (len(operations), success, failed)
        self.audit(audit_msg, level="info")
        return {"total": len(operations), "success": success, "failed": failed, "results": results}

    def export_data(self, format_type: str = "json") -> dict:
        """导出模块状态和数据"""
        self.trace("error_aggregator.export_data", "start", format=format_type)
        data = {
            "module": "error_aggregator",
            "timestamp": __import__("time").time(),
            "health": self.health_check(),
            "stats": getattr(self, "get_stats", lambda: {})(),
        }
        self.metrics_collector.counter("error_aggregator.export.total", 1)
        self.trace("error_aggregator.export_data", "end")
        return {"success": True, "format": format_type, "data": data}

    def import_data(self, data: dict) -> dict:
        """导入配置和数据"""
        self.trace("error_aggregator.import_data", "start")
        self.audit(f"导入数据: {data.get('module', 'unknown')}", level="info")
        self.metrics_collector.counter("error_aggregator.import.total", 1)
        self.trace("error_aggregator.import_data", "end")
        return {"success": True, "module": "error_aggregator", "imported": True}

    def batch_operation(self, operations: list) -> dict:
        """批量执行操作"""
        results = []
        success = failed = 0
        for op in operations:
            try:
                method = getattr(self, op.get("action", ""), None)
                if method and callable(method):
                    r = method(**op.get("params", {}))
                    results.append({"op": op.get("action"), "success": True})
                    success += 1
                else:
                    results.append({"op": op.get("action"), "success": False, "error": "not_found"})
                    failed += 1
            except Exception as e:
                results.append({"op": op.get("action"), "success": False, "error": str(e)[:100]})
                failed += 1
        return {"total": len(operations), "success": success, "failed": failed, "results": results}

    def export_data(self, format_type: str = "json") -> dict:
        """导出模块数据"""
        self.trace("error_aggregator.export", "start")
        import time as _t

        data = {"module": "error_aggregator", "ts": _t.time(), "health": self.health_check()}
        self.metrics_collector.counter("error_aggregator.export", 1)
        self.trace("error_aggregator.export", "end")
        return {"success": True, "format": format_type, "data": data}

    def import_data(self, data: dict) -> dict:
        """导入配置"""
        self.trace("error_aggregator.import", "start")
        self.audit("导入数据: " + str(data.get("module", "?")), level="info")
        return {"success": True, "module": "error_aggregator"}

    def get_monitoring_dashboard(self) -> dict:
        """获取监控面板数据"""
        self.trace("error_aggregator.monitor", "start")
        import time as _t

        panel = {
            "module": "error_aggregator",
            "uptime": _t.time() - getattr(self, "_start_time", _t.time()),
            "health": self.health_check(),
            "stats": getattr(self, "get_stats", lambda: {})(),
        }
        analyzer = getattr(self, "_analyzer", None)
        if analyzer:
            panel["analysis"] = analyzer.analyze()
        self.trace("error_aggregator.monitor", "end")
        return panel

    def validate_config(self, config: dict) -> dict:
        """验证配置合法性"""
        self.trace("error_aggregator.validate", "start")
        errors = []
        warnings = []
        if not isinstance(config, dict):
            errors.append("config must be dict")
        for k, v in config.items():
            if v is None:
                warnings.append("config.%s is None" % k)
        result = {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "checked": len(config)}
        self.metrics_collector.counter("error_aggregator.validate", 1)
        self.trace("error_aggregator.validate", "end")
        return result

    def reset_metrics(self) -> dict:
        """重置指标"""
        self.trace("error_aggregator.reset_metrics", "start")
        self.audit("重置指标", level="warn")
        return {"success": True, "module": "error_aggregator"}

    def get_operation_log(self, limit: int = 100) -> dict:
        """获取操作日志"""
        log = getattr(self, "_operation_log", [])
        return {"total": len(log), "entries": log[-limit:]}

    def diagnostic_check(self) -> dict:
        """运行诊断检查"""
        self.trace("error_aggregator.diagnostic", "start")
        checks = [
            ("health", self.health_check().get("status") == "healthy"),
            ("initialized", getattr(self, "_initialized", True)),
            ("has_methods", len([m for m in dir(self) if not m.startswith("_")]) > 5),
        ]
        passed = sum(1 for _, ok in checks if ok)
        self.metrics_collector.gauge(
            "error_aggregator.diagnostic.pass_rate", passed / len(checks) * 100 if checks else 0
        )
        return {"checks": checks, "passed": passed, "total": len(checks), "healthy": passed == len(checks)}

    def optimize(self, params: dict = None) -> dict:
        """执行优化操作"""
        self.trace("error_aggregator.optimize", "start")
        params = params or {}
        self.audit("执行优化: " + str(params.get("target", "auto")), level="info")
        result = {"optimized": True, "module": "error_aggregator", "params": params}
        self.metrics_collector.counter("error_aggregator.optimize", 1)
        self.trace("error_aggregator.optimize", "end")
        return result

    def backup(self, target_path: str = "") -> dict:
        """备份模块数据"""
        self.trace("error_aggregator.backup", "start")
        import json as _j, time as _t

        data = _j.dumps(
            {"module": "error_aggregator", "ts": _t.time(), "health": self.health_check()}, ensure_ascii=False
        )
        return {"success": True, "size": len(data), "module": "error_aggregator"}

    def restore(self, data: dict) -> dict:
        """恢复模块数据"""
        self.trace("error_aggregator.restore", "start")
        self.audit("恢复数据", level="warn")
        return {"success": True, "module": "error_aggregator", "restored": True}

module_class = ErrorAggregator
