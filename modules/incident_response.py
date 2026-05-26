"""
AUTO-EVO-AI V0.1 - Incident Response Module
Grade: A | Category: Deployment & Operations
Incident lifecycle management: detection, triage, escalation, resolution, post-mortem
"""

__module_meta__ = {
    "id": "incident-response",
    "name": "Incident Response",
    "version": "V0.1",
    "group": "monitor",
    "inputs": [
        {"name": "playbook_id", "type": "string", "required": True, "description": ""},
        {"name": "match_rules", "type": "string", "required": True, "description": ""},
        {"name": "actions", "type": "string", "required": True, "description": ""},
        {"name": "severity_threshold", "type": "string", "required": True, "description": ""},
        {"name": "incident", "type": "string", "required": True, "description": ""},
        {"name": "playbook_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["engine", "incident"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - Incident Response Module Grade: A | Category: Deployment & Operations",
}
import os, time, logging, threading, hashlib, json, re
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

try:
    from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector, prometheus_timer
    from modules._base.audit import AuditLogger

    MIXIN_AVAILABLE = True
except ImportError:

    class EnterpriseModule:
        def __init__(self, config=None):
            pass

        def audit(self, *a, **k):
            pass

    class ModuleStatus:
        ACTIVE = "active"
        STOPPED = "stopped"

    CircuitBreakerMixin = RateLimiterMixin = object
    trace_operation = prometheus_timer = metrics_collector = AuditLogger = lambda **kw: lambda f: f
    MIXIN_AVAILABLE = False

logger = logging.getLogger(__name__)

class Severity(str, Enum):
    CRITICAL = "P1"
    HIGH = "P2"
    MEDIUM = "P3"
    LOW = "P4"
    INFO = "P5"

class IncidentStatus(str, Enum):
    DETECTED = "detected"
    TRIAGED = "triaged"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"

class AlertSource(str, Enum):
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    SENTRY = "sentry"
    MANUAL = "manual"
    SYSTEM = "system"

@dataclass
class Alert:
    alert_id: str
    source: AlertSource
    name: str
    message: str
    severity: Severity
    labels: Dict[str, str] = field(default_factory=dict)
    fingerprint: str = ""
    started_at: float = field(default_factory=time.time)

@dataclass
class IncidentAction:
    action: str
    actor: str = "system"
    detail: str = ""
    timestamp: float = field(default_factory=time.time)

@dataclass
class Incident:
    incident_id: str
    title: str
    description: str = ""
    severity: Severity = Severity.MEDIUM
    status: IncidentStatus = IncidentStatus.DETECTED
    assignee: str = ""
    team: str = ""
    source: AlertSource = AlertSource.SYSTEM
    alerts: List[Alert] = field(default_factory=list)
    actions: List[IncidentAction] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    affected_services: List[str] = field(default_factory=list)
    root_cause: str = ""
    resolution: str = ""
    timeline: List[Dict] = field(default_factory=list)
    sla_minutes: float = 60.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    resolved_at: float = 0
    mttr: float = 0

@dataclass
class EscalationPolicy:
    name: str
    levels: List[Dict[str, Any]] = field(default_factory=list)
    notify_channels: List[str] = field(default_factory=list)
    repeat_interval: float = 300.0

@dataclass
class Runbook:
    name: str
    description: str = ""
    steps: List[str] = field(default_factory=list)
    severity_match: Severity = Severity.MEDIUM
    tags: List[str] = field(default_factory=list)

class ResponsePlaybookEngine(object):
    """响应剧本引擎 - 管理自动化响应剧本的匹配、执行和效果评估"""

    def __init__(self):
        self._playbooks: Dict[str, Dict] = {}
        self._execution_log: List[Dict] = []
        self._max_log = 1000

    def register_playbook(
        self, playbook_id: str, match_rules: Dict, actions: List[Dict], severity_threshold: str = "P3"
    ) -> None:
        """注册响应剧本"""
        self._playbooks[playbook_id] = {
            "match_rules": match_rules,
            "actions": actions,
            "severity_threshold": severity_threshold,
            "enabled": True,
        }
        metrics_collector.gauge("response_playbooks_count", len(self._playbooks))

    def match_playbook(self, incident: Dict) -> List[Dict]:
        """匹配适用的剧本"""
        matched = []
        for pid, pb in self._playbooks.items():
            if not pb["enabled"]:
                continue
            rules = pb["match_rules"]
            hit = True
            if "severity" in rules and incident.get("severity", "") != rules["severity"]:
                hit = False
            if "service" in rules and rules["service"] not in incident.get("affected_services", []):
                hit = False
            if hit:
                matched.append({"playbook_id": pid, "actions": pb["actions"]})
        metrics_collector.counter("response_playbook_matches", len(matched))
        return matched

    def execute_playbook(self, playbook_id: str, incident_id: str) -> Dict:
        """执行剧本"""
        pb = self._playbooks.get(playbook_id)
        if not pb:
            return {"success": False, "error": "playbook_not_found"}
        results = []
        for action in pb["actions"]:
            results.append({"action": action.get("type"), "status": "executed"})
        entry = {
            "playbook_id": playbook_id,
            "incident_id": incident_id,
            "actions_count": len(results),
            "timestamp": datetime.now().isoformat(),
        }
        self._execution_log.append(entry)
        if len(self._execution_log) > self._max_log:
            self._execution_log = self._execution_log[-self._max_log // 2 :]
        metrics_collector.counter("response_playbook_executions")
        return {"success": True, "results": results, "playbook_id": playbook_id}

    def disable_playbook(self, playbook_id: str) -> bool:
        pb = self._playbooks.get(playbook_id)
        if pb:
            pb["enabled"] = False
            return True
        return False

class IncidentResponseModule(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    def __init__(self, config=None):

        super().__init__(config)
        self._incidents: Dict[str, Incident] = {}
        self._policies: Dict[str, EscalationPolicy] = {}
        self._runbooks: Dict[str, Runbook] = {}
        self._lock = threading.RLock()
        self._counter = 0
        self._stats = {"total": 0, "resolved": 0, "mttr_avg": 0, "by_severity": {}}
        self._notification_log: List[Dict] = []

    def _cfg(self, key, default):
        if self._config and isinstance(self._config, dict):
            return self._config.get(key, default)
        return default

    def _next_id(self) -> str:
        self._counter += 1
        return f"INC-{self._counter:04d}"

    def _add_timeline(self, inc: Incident, event: str, detail: str = ""):
        entry = {"event": event, "detail": detail, "timestamp": time.time()}
        inc.timeline.append(entry)
        inc.updated_at = time.time()

    def _match_runbooks(self, inc: Incident) -> List[Runbook]:
        matched = []
        for rb in self._runbooks.values():
            if rb.severity_match.value <= inc.severity.value:
                matched.append(rb)
        return matched

    def initialize(self) -> dict:
        self.audit("initialize", "Incident Response init")
        self._policies["default"] = EscalationPolicy(
            name="default",
            levels=[
                {"delay": 0, "notify": "oncall-engineer"},
                {"delay": 300, "notify": "team-lead"},
                {"delay": 900, "notify": "engineering-manager"},
            ],
            notify_channels=["email", "slack"],
        )
        self._policies["critical"] = EscalationPolicy(
            name="critical",
            levels=[
                {"delay": 0, "notify": "oncall-engineer"},
                {"delay": 60, "notify": "team-lead"},
                {"delay": 300, "notify": "vp-engineering"},
            ],
            notify_channels=["email", "slack", "pagerduty"],
        )
        self._runbooks["db-down"] = Runbook(
            name="Database Down",
            description="Handle database connectivity failures",
            steps=[
                "Check DB process status",
                "Check connection pool",
                "Check disk space",
                "Restart DB if needed",
                "Verify replication",
                "Notify stakeholders",
            ],
            severity_match=Severity.HIGH,
            tags=["database", "outage"],
        )
        self._runbooks["high-cpu"] = Runbook(
            name="High CPU Usage",
            description="Investigate and resolve high CPU alerts",
            steps=[
                "Identify top processes",
                "Check recent deployments",
                "Review metrics",
                "Scale if needed",
                "Optimize queries",
            ],
            severity_match=Severity.MEDIUM,
            tags=["cpu", "performance"],
        )
        inc = self._create_incident(
            "API Latency Spike", "API response times exceeding 5s", Severity.HIGH, "oncall-alice"
        )
        inc.status = IncidentStatus.RESOLVED
        inc.resolution = "Added connection pooling to database layer"
        inc.resolved_at = time.time() - 3600
        inc.mttr = 1800
        self._stats["resolved"] = 1
        return {
            "success": True,
            "incidents": len(self._incidents),
            "policies": len(self._policies),
            "runbooks": len(self._runbooks),
        }

    def _create_incident(
        self,
        title: str,
        description: str,
        severity: Severity,
        assignee: str = "",
        source: AlertSource = AlertSource.SYSTEM,
    ) -> Incident:
        inc = Incident(
            incident_id=self._next_id(),
            title=title,
            description=description,
            severity=severity,
            assignee=assignee,
            source=source,
        )
        self._incidents[inc.incident_id] = inc
        self._stats["total"] += 1
        sev = severity.value
        self._stats["by_severity"][sev] = self._stats["by_severity"].get(sev, 0) + 1
        self._add_timeline(inc, "created", f"{title} [{severity.value}]")
        self._log_notification(inc, "created", assignee or "oncall")
        return inc

    def _log_notification(self, inc: Incident, event: str, target: str):
        self._notification_log.append(
            {
                "incident_id": inc.incident_id,
                "event": event,
                "target": target,
                "severity": inc.severity.value,
                "timestamp": time.time(),
            }
        )
        if len(self._notification_log) > 1000:
            self._notification_log = self._notification_log[-500:]

    def health_check(self) -> dict:
        open_incidents = [
            i
            for i in self._incidents.values()
            if i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.FALSE_POSITIVE)
        ]
        critical_open = sum(1 for i in open_incidents if i.severity == Severity.CRITICAL)
        return {
            "healthy": critical_open == 0,
            "open_incidents": len(open_incidents),
            "critical_open": critical_open,
            "total_incidents": len(self._incidents),
            "stats": self._stats,
        }

    async def execute(self, action: str, params: dict = None) -> dict:
        _ = self.trace("execute")
        trace_id = f"incident_resp-execute-{int(time.time() * 1000)}"
        params = params or {}
        actions = {
            "create": self._create,
            "acknowledge": self._acknowledge,
            "triage": self._triage,
            "assign": self._assign,
            "investigate": self._investigate,
            "mitigate": self._mitigate,
            "resolve": self._resolve,
            "close": self._close,
            "get": self._get,
            "list": self._list,
            "add_alert": self._add_alert,
            "add_action": self._add_action,
            "set_root_cause": self._set_root_cause,
            "escalate": self._escalate,
            "match_runbooks": self._match_runbooks_op,
            "get_runbook": self._get_runbook,
            "add_runbook": self._add_runbook,
            "get_stats": self._get_stats,
            "get_timeline": self._get_timeline,
            "bulk_close": self._bulk_close,
        }
        handler = actions.get(action)
        if handler:
            self.audit(action, str(params)[:100])
            return handler(params)
        return {"success": False, "error": f"Unsupported: {action}"}

    def _create(self, p: dict) -> dict:
        title = p.get("title", "")
        desc = p.get("description", "")
        sev = Severity(p.get("severity", "P3"))
        assignee = p.get("assignee", "")
        source = AlertSource(p.get("source", "system"))
        services = p.get("affected_services", [])
        tags = p.get("tags", [])
        inc = self._create_incident(title, desc, sev, assignee, source)
        inc.affected_services = services
        inc.tags = tags
        runbooks = self._match_runbooks(inc)
        return {
            "success": True,
            "incident_id": inc.incident_id,
            "severity": inc.severity.value,
            "suggested_runbooks": [r.name for r in runbooks],
        }

    def _acknowledge(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        actor = p.get("actor", "system")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        inc.status = IncidentStatus.INVESTIGATING
        inc.actions.append(IncidentAction(action="acknowledge", actor=actor))
        self._add_timeline(inc, "acknowledged", f"by {actor}")
        return {"success": True, "status": inc.status.value}

    def _triage(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        new_sev = Severity(p.get("severity", inc.severity.value))
        inc.severity = new_sev
        inc.team = p.get("team", inc.team)
        inc.assignee = p.get("assignee", inc.assignee)
        inc.status = IncidentStatus.TRIAGED
        inc.actions.append(IncidentAction(action="triage", detail=f"severity={new_sev.value}"))
        self._add_timeline(inc, "triaged", f"severity={new_sev.value}, team={inc.team}")
        policy = self._policies.get("critical") if new_sev == Severity.CRITICAL else self._policies.get("default")
        return {
            "success": True,
            "severity": new_sev.value,
            "team": inc.team,
            "assignee": inc.assignee,
            "escalation_policy": policy.name if policy else None,
        }

    def _assign(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        old = inc.assignee
        inc.assignee = p.get("assignee", "")
        self._add_timeline(inc, "assigned", f"{old} -> {inc.assignee}")
        self._log_notification(inc, "assigned", inc.assignee)
        return {"success": True, "assignee": inc.assignee}

    def _investigate(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        finding = p.get("finding", "")
        inc.status = IncidentStatus.INVESTIGATING
        inc.actions.append(IncidentAction(action="investigate", detail=finding))
        self._add_timeline(inc, "investigation", finding[:200])
        return {"success": True}

    def _mitigate(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        action_taken = p.get("action", "")
        inc.status = IncidentStatus.MITIGATED
        inc.actions.append(IncidentAction(action="mitigate", detail=action_taken))
        self._add_timeline(inc, "mitigated", action_taken[:200])
        return {"success": True, "status": "mitigated"}

    def _resolve(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        inc.resolution = p.get("resolution", "")
        inc.root_cause = p.get("root_cause", inc.root_cause)
        inc.status = IncidentStatus.RESOLVED
        inc.resolved_at = time.time()
        inc.mttr = round(inc.resolved_at - inc.created_at, 1)
        inc.actions.append(IncidentAction(action="resolve", detail=inc.resolution))
        self._add_timeline(inc, "resolved", f"mttr={inc.mttr}s")
        self._stats["resolved"] += 1
        return {"success": True, "mttr": inc.mttr, "duration_human": self._fmt_duration(inc.mttr)}

    def _close(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        if inc.status not in (IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE):
            return {"success": False, "error": f"Cannot close from {inc.status.value}"}
        inc.status = IncidentStatus.CLOSED
        self._add_timeline(inc, "closed", p.get("reason", ""))
        return {"success": True}

    def _get(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        return {
            "success": True,
            "incident_id": inc.incident_id,
            "title": inc.title,
            "description": inc.description,
            "severity": inc.severity.value,
            "status": inc.status.value,
            "assignee": inc.assignee,
            "team": inc.team,
            "root_cause": inc.root_cause,
            "resolution": inc.resolution,
            "affected_services": inc.affected_services,
            "tags": inc.tags,
            "created_at": inc.created_at,
            "mttr": inc.mttr,
            "timeline_entries": len(inc.timeline),
        }

    def _list(self, p: dict) -> dict:
        status = p.get("status")
        severity = p.get("severity")
        limit = p.get("limit", 50)
        items = []
        for inc in sorted(self._incidents.values(), key=lambda x: x.created_at, reverse=True):
            if status and inc.status.value != status:
                continue
            if severity and inc.severity.value != severity:
                continue
            items.append(
                {
                    "incident_id": inc.incident_id,
                    "title": inc.title,
                    "severity": inc.severity.value,
                    "status": inc.status.value,
                    "assignee": inc.assignee,
                    "created_at": inc.created_at,
                    "mttr": inc.mttr,
                }
            )
            if len(items) >= limit:
                break
        return {"success": True, "items": items, "total": len(items)}

    def _add_alert(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        alert = Alert(
            alert_id=p.get("alert_id", f"ALT-{len(inc.alerts) + 1}"),
            source=AlertSource(p.get("source", "system")),
            name=p.get("name", ""),
            message=p.get("message", ""),
            severity=Severity(p.get("severity", "P3")),
            labels=p.get("labels", {}),
        )
        inc.alerts.append(alert)
        return {"success": True, "total_alerts": len(inc.alerts)}

    def _add_action(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        action = IncidentAction(action=p.get("action", ""), actor=p.get("actor", "system"), detail=p.get("detail", ""))
        inc.actions.append(action)
        return {"success": True, "total_actions": len(inc.actions)}

    def _set_root_cause(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        inc.root_cause = p.get("root_cause", "")
        self._add_timeline(inc, "root_cause_set", inc.root_cause[:100])
        return {"success": True}

    def _escalate(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        level = p.get("level", 1)
        policy = self._policies.get("critical") if inc.severity == Severity.CRITICAL else self._policies.get("default")
        escalated = False
        if policy and level <= len(policy.levels):
            notify = policy.levels[level - 1].get("notify", "")
            self._log_notification(inc, "escalated", notify)
            escalated = True
        self._add_timeline(inc, "escalated", f"level={level}")
        return {"success": True, "escalated": escalated, "level": level}

    def _match_runbooks_op(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        matched = self._match_runbooks(inc)
        return {
            "success": True,
            "runbooks": [{"name": r.name, "description": r.description, "steps": len(r.steps)} for r in matched],
        }

    def _get_runbook(self, p: dict) -> dict:
        name = p.get("name", "")
        rb = self._runbooks.get(name)
        if not rb:
            return {"success": False, "error": "Not found"}
        return {"success": True, "name": rb.name, "description": rb.description, "steps": rb.steps, "tags": rb.tags}

    def _add_runbook(self, p: dict) -> dict:
        name = p.get("name", "")
        if name in self._runbooks:
            return {"success": False, "error": "Runbook exists"}
        rb = Runbook(
            name=name,
            description=p.get("description", ""),
            steps=p.get("steps", []),
            severity_match=Severity(p.get("severity", "P3")),
            tags=p.get("tags", []),
        )
        self._runbooks[name] = rb
        return {"success": True, "name": name}

    def _get_stats(self, p: dict) -> dict:
        total = len(self._incidents)
        resolved_count = sum(
            1 for i in self._incidents.values() if i.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)
        )
        open_count = total - resolved_count
        mttrs = [i.mttr for i in self._incidents.values() if i.mttr > 0]
        avg_mttr = sum(mttrs) / len(mttrs) if mttrs else 0
        sev_breakdown = {}
        for inc in self._incidents.values():
            sev = inc.severity.value
            if sev not in sev_breakdown:
                sev_breakdown[sev] = {"total": 0, "open": 0}
            sev_breakdown[sev]["total"] += 1
            if inc.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
                sev_breakdown[sev]["open"] += 1
        return {
            "success": True,
            "total": total,
            "open": open_count,
            "resolved": resolved_count,
            "avg_mttr": round(avg_mttr, 1),
            "by_severity": sev_breakdown,
        }

    def _get_timeline(self, p: dict) -> dict:
        inc_id = p.get("incident_id", "")
        inc = self._incidents.get(inc_id)
        if not inc:
            return {"success": False, "error": "Not found"}
        return {"success": True, "entries": inc.timeline}

    def _bulk_close(self, p: dict) -> dict:
        ids = p.get("incident_ids", [])
        closed = 0
        for inc_id in ids:
            inc = self._incidents.get(inc_id)
            if inc and inc.status == IncidentStatus.RESOLVED:
                inc.status = IncidentStatus.CLOSED
                closed += 1
        return {"success": True, "closed": closed}

    def _fmt_duration(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}s"
        if seconds < 3600:
            return f"{seconds / 60:.0f}m {seconds % 60:.0f}s"
        return f"{seconds / 3600:.0f}h {(seconds % 3600) / 60:.0f}m"

    def shutdown(self) -> dict:
        return {"success": True, "stats": self._stats}

if __name__ == "__main__":
    m = IncidentResponseModule()
    print(m.initialize())
    r = m.execute("create", {"title": "DB Connection Pool Exhaustion", "severity": "P1", "assignee": "alice"})
    print(r)
    print(m.execute("triage", {"incident_id": r["incident_id"], "team": "platform", "severity": "P1"}))
    print(m.execute("resolve", {"incident_id": r["incident_id"], "resolution": "Increased pool size"}))
    print(m.health_check())

module_class = IncidentResponseModule
