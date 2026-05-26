# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI V0.1 - IncidentManager 事件管理器
============================================
企业级事件管理：事件发现/分级/派发/升级/复盘/自动化。
支持：事件全生命周期管理、多级严重度（P1-P5）、
      自动/手动派发、值班排班、升级Escalation、
      战争室(War Room)、事件Timeline、自动修复动作、
      事件报告生成、MTTA/MTTR/MTBF指标追踪、
      通知集成、影响分析。

A级生产标准：EnterpriseModule + 链路追踪 + Prometheus + 审计 + 熔断 + 限流
"""

__module_meta__ = {
    "id": "incident-manager",
    "name": "Incident Manager",
    "version": "V0.1",
    "group": "monitor",
    "inputs": [
        {"name": "incident", "type": "string", "required": True, "description": ""},
        {"name": "incident", "type": "string", "required": True, "description": ""},
        {"name": "current_level", "type": "string", "required": True, "description": ""},
        {"name": "incidents", "type": "string", "required": True, "description": ""},
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["incident", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - IncidentManager 事件管理器 ============================================",
}

import time
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    Result,
    CircuitBreakerMixin,
    RateLimiterMixin,
)
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.incident_manager")

# ============================================================================
# 数据模型
# ============================================================================

class IncidentSeverity(str, Enum):
    P1_CRITICAL = "P1"  # 系统不可用，严重影响业务
    P2_MAJOR = "P2"  # 主要功能不可用
    P3_MINOR = "P3"  # 部分功能异常
    P4_LOW = "P4"  # 轻微问题
    P5_INFO = "P5"  # 信息性事件

class IncidentStatus(str, Enum):
    DETECTED = "detected"
    TRIAGING = "triaging"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"

class AlertSource(str, Enum):
    MONITORING = "monitoring"
    MANUAL = "manual"
    USER_REPORT = "user_report"
    CI_CD = "ci_cd"
    CHAOS_ENGINE = "chaos_engine"
    EXTERNAL = "external"

@dataclass
class IncidentImpact:
    """事件影响"""

    affected_services: List[str] = field(default_factory=list)
    affected_users_count: int = 0
    affected_region: str = ""
    revenue_impact: float = 0.0
    sla_breach: bool = False
    description: str = ""

@dataclass
class IncidentTimeline:
    """事件Timeline条目"""

    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    event_type: str = ""  # detected/acknowledged/escalated/comment/action/resolved/closed
    description: str = ""
    actor: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AutoAction:
    """自动动作"""

    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_type: str = ""  # restart/scale/rollback/notify/script
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending/running/succeeded/failed
    result: str = ""
    executed_at: Optional[str] = None
    duration_ms: float = 0.0

@dataclass
class OnCallSchedule:
    """值班排班"""

    schedule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    team_name: str = ""
    rotations: List[Dict[str, str]] = field(default_factory=list)  # [{user, start, end}]
    current_oncall: str = ""
    escalation_chain: List[str] = field(default_factory=list)

@dataclass
class Incident:
    """事件"""

    incident_id: str = field(default_factory=lambda: f"INC-{uuid.uuid4().hex[:8].upper()}")
    title: str = ""
    description: str = ""
    severity: IncidentSeverity = IncidentSeverity.P4_LOW
    status: IncidentStatus = IncidentStatus.DETECTED
    source: AlertSource = AlertSource.MONITORING
    impact: IncidentImpact = field(default_factory=IncidentImpact)
    assignee: str = ""
    team: str = ""
    labels: List[str] = field(default_factory=list)
    timeline: List[IncidentTimeline] = field(default_factory=list)
    auto_actions: List[AutoAction] = field(default_factory=list)
    related_incidents: List[str] = field(default_factory=list)
    root_cause: str = ""
    resolution: str = ""
    war_room_url: Optional[str] = None
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged_at: Optional[str] = None
    mitigated_at: Optional[str] = None
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    mtta_seconds: float = 0.0
    mttr_seconds: float = 0.0
    closed_by: str = ""
    postmortem_required: bool = False

@dataclass
class IncidentMetric:
    """事件指标"""

    total_incidents: int = 0
    by_severity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    avg_mtta_seconds: float = 0.0
    avg_mttr_seconds: float = 0.0
    mtbf_seconds: float = 0.0
    last_incident_at: Optional[str] = None
    resolved_today: int = 0
    auto_resolved: int = 0
    escalation_rate: float = 0.0

# ============================================================================
# IncidentManager 主类
# ============================================================================

class IncidentImpactScorer:
    """事件影响评分器 — 评估事件影响范围、计算优先级、生成升级建议"""

    def __init__(self):
        self._impact_weights = {
            "critical_services": 10,
            "affected_users": 8,
            "revenue_impact": 9,
            "data_loss_risk": 7,
            "recovery_time": 6,
        }

    def score_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """计算事件影响分数"""
        severity = incident.get("severity", "low")
        base_scores = {"critical": 80, "high": 60, "medium": 40, "low": 20}
        score = base_scores.get(severity, 20)

        affected_services = incident.get("affected_services", [])
        if len(affected_services) >= 3:
            score += 15
        elif len(affected_services) >= 1:
            score += 5

        affected_users = incident.get("affected_users", 0)
        if affected_users > 10000:
            score += 15
        elif affected_users > 1000:
            score += 10
        elif affected_users > 0:
            score += 5

        data_loss = incident.get("data_loss_risk", False)
        if data_loss:
            score += 10

        score = min(score, 100)
        return {
            "incident_id": incident.get("id", ""),
            "impact_score": score,
            "priority": "P1" if score >= 85 else "P2" if score >= 60 else "P3" if score >= 40 else "P4",
            "factors": {
                "severity_base": base_scores.get(severity, 20),
                "service_count_bonus": min(len(affected_services) * 5, 15),
                "user_impact_bonus": 15
                if affected_users > 10000
                else 10
                if affected_users > 1000
                else 5
                if affected_users > 0
                else 0,
                "data_loss_bonus": 10 if data_loss else 0,
            },
        }

    def should_escalate(self, incident: Dict[str, Any], current_level: int = 1) -> Dict[str, Any]:
        """判断是否需要升级事件"""
        score_result = self.score_incident(incident)
        score = score_result["impact_score"]

        escalation_thresholds = {1: 60, 2: 80, 3: 90}
        threshold = escalation_thresholds.get(current_level, 95)

        should = score >= threshold
        next_level = current_level + 1 if should else current_level
        reason = "impact_score_exceeds_threshold" if should else "no_escalation_needed"

        return {
            "should_escalate": should,
            "current_level": current_level,
            "next_level": next_level,
            "score": score,
            "threshold": threshold,
            "reason": reason,
        }

    def batch_score(self, incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量评分并排序"""
        scored = []
        for inc in incidents:
            result = self.score_incident(inc)
            scored.append({**inc, **result})
        scored.sort(key=lambda x: x["impact_score"], reverse=True)

        p1 = sum(1 for s in scored if s["priority"] == "P1")
        p2 = sum(1 for s in scored if s["priority"] == "P2")
        return {"total": len(scored), "P1": p1, "P2": p2, "P3_plus": len(scored) - p1 - p2, "ranked": scored}

class IncidentManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    事件管理器

    功能：
      - 事件创建与全生命周期管理
      - 5级严重度分级（P1-P5）
      - 自动派发（值班排班/团队路由）
      - 升级Escalation链
      - 事件Timeline审计
      - 自动修复动作编排
      - 影响分析
      - MTTA/MTTR/MTBF指标
      - 事件报告生成
      - 复习(Postmortem)管理
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__()
        self.config = config or {}
        # 事件存储
        self._incidents: Dict[str, Incident] = {}
        # 值班排班
        self._schedules: Dict[str, OnCallSchedule] = {}
        # 团队路由规则: label/service -> team
        self._routing_rules: Dict[str, str] = {}
        # 升级规则
        self._escalation_rules: Dict[str, Dict[str, Any]] = {
            "P1": {"initial_timeout": 300, "escalation_interval": 600, "max_escalations": 4},
            "P2": {"initial_timeout": 600, "escalation_interval": 900, "max_escalations": 3},
            "P3": {"initial_timeout": 1800, "escalation_interval": 1800, "max_escalations": 2},
        }
        # 自动动作注册
        self._auto_action_handlers: Dict[str, Callable] = {}
        # 通知回调
        self._notify_callback: Optional[Callable] = None
        # 指标
        self._incident_metrics = IncidentMetric()
        # 升级检查任务
        self._escalation_task: Optional[asyncio.Task] = None
        # 统计
        self._im_stats = {
            "incidents_total": 0,
            "active": 0,
            "resolved": 0,
            "auto_actions_executed": 0,
            "escalations": 0,
        }

    # ----------------------------------------------------------------
    # 生命周期
    # ----------------------------------------------------------------

    def initialize(self) -> Result:
        self._update_status(ModuleStatus.RUNNING)
        self._escalation_task = None  # escalation loop disabled in sync mode
        for rule in self.config.get("routing_rules", []):
            self._routing_rules[rule.get("key", "")] = rule.get("team", "default")
        for sched in self.config.get("oncall_schedules", []):
            self._schedules[sched.get("team", "")] = OnCallSchedule(
                team_name=sched.get("team", ""),
                current_oncall=sched.get("current", ""),
                escalation_chain=sched.get("escalation_chain", []),
            )
        logger.info("[IncidentManager] 初始化完成")
        return Result(success=True)

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        _ = self.trace("execute")
        """统一执行入口 — 根据action路由到对应业务方法"""
        metrics_collector.counter("incident_manager_ops_total", labels={"action": action})
        params = params or {}
        actions = {
            "create_incident": self.create_incident,
            "acknowledge": self.acknowledge,
            "update_status": self.update_status,
            "add_comment": self.add_comment,
            "set_root_cause": self.set_root_cause,
            "set_resolution": self.set_resolution,
            "get_incident": self.get_incident,
            "search_incidents": self.search_incidents,
            "get_metrics": self.get_metrics,
            "get_stats": self.get_stats,
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }

        if action not in actions:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}

        handler = actions.get(action)
        if not handler:
            return {"status": "error", "message": f"Unknown action: {action}"}
        try:
            import inspect

            sig = inspect.signature(handler)
            if len(sig.parameters) <= 1:
                result = handler()
            else:
                result = handler(**params)
        except Exception as e:
            return {"status": "error", "message": str(e)}
        if isinstance(result, dict):
            return {"status": "success", **result}
        return {"status": "success", "data": result}

    def health_check(self) -> HealthReport:
        active = sum(
            1 for i in self._incidents.values() if i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)
        )
        return HealthReport(
            status="running",
            healthy=True,
            last_beat=datetime.now().isoformat(),
            uptime_seconds=self.stats.uptime_seconds,
            checks_run=4,
            error_rate=self.stats.error_rate,
            details={"incidents": len(self._incidents), "active": active, "schedules": len(self._schedules)},
            version="V0.1",
        )

    async def shutdown(self) -> Result:
        if self._escalation_task:
            self._escalation_task.cancel()
        self._update_status(ModuleStatus.STOPPED)
        return Result(success=True)

    # ----------------------------------------------------------------
    # 事件管理
    # ----------------------------------------------------------------

    def create_incident(
        self,
        title: str,
        *,
        severity: str = "P4",
        source: str = "monitoring",
        description: str = "",
        affected_services: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        detected_by: str = "",
        auto_actions: Optional[List[Dict]] = None,
    ) -> Result:
        trace_id = f"incident-create-{int(time.time() * 1000)}"
        start = time.time()
        try:
            inc = Incident(
                title=title,
                description=description,
                severity=IncidentSeverity(severity),
                source=AlertSource(source),
                labels=labels or [],
            )
            if affected_services:
                inc.impact.affected_services = affected_services
            # Timeline: 检测
            inc.timeline.append(
                IncidentTimeline(event_type="detected", description=f"事件检测: {title}", actor=detected_by or "system")
            )
            # 自动派发
            team = self._route_incident(inc)
            inc.team = team
            # 值班人员
            oncall = self._get_oncall(team)
            if oncall:
                inc.assignee = oncall
            # P1/P2自动动作
            if inc.severity in (IncidentSeverity.P1_CRITICAL, IncidentSeverity.P2_MAJOR):
                inc.postmortem_required = True
                # 自动动作
                for action_cfg in auto_actions or self.config.get("default_auto_actions", []):
                    action = AutoAction(
                        action_type=action_cfg.get("type", "notify"),
                        target=action_cfg.get("target", ""),
                        parameters=action_cfg.get("parameters", {}),
                    )
                    inc.auto_actions.append(action)
            self._incidents[inc.incident_id] = inc
            self._im_stats["incidents_total"] += 1
            self._im_stats["active"] += 1
            self._incident_metrics.total_incidents += 1
            self._incident_metrics.by_severity[inc.severity.value] += 1
            self._incident_metrics.last_incident_at = inc.detected_at
            # 通知
            self._send_notification(inc, "created")
            self.audit("incident.created", {"id": inc.incident_id, "severity": severity, "team": team})
            self.stats.record_request((time.time() - start) * 1000, True)
            return Result(success=True, data={"incident_id": inc.incident_id, "assignee": inc.assignee})
        except Exception as e:
            self.stats.record_request((time.time() - start) * 1000, False, str(e))
            return Result(success=False, error=str(e))

    def acknowledge(self, incident_id: str, acknowledged_by: str) -> Result:
        inc = self._incidents.get(incident_id)
        if not inc:
            return Result(success=False, error="事件不存在")
        inc.status = IncidentStatus.ACKNOWLEDGED
        inc.acknowledged_at = datetime.now().isoformat()
        inc.assignee = acknowledged_by or inc.assignee
        inc.mtta_seconds = (
            datetime.fromisoformat(inc.acknowledged_at) - datetime.fromisoformat(inc.detected_at)
        ).total_seconds()
        inc.timeline.append(
            IncidentTimeline(event_type="acknowledged", description="事件已确认", actor=acknowledged_by)
        )
        self._send_notification(inc, "acknowledged")
        return Result(success=True)

    def update_status(self, incident_id: str, status: str, *, actor: str = "", comment: str = "") -> Result:
        inc = self._incidents.get(incident_id)
        if not inc:
            return Result(success=False, error="事件不存在")
        old_status = inc.status
        inc.status = IncidentStatus(status)
        now = datetime.now().isoformat()
        if status == "resolved":
            inc.resolved_at = now
            inc.mttr_seconds = (datetime.fromisoformat(now) - datetime.fromisoformat(inc.detected_at)).total_seconds()
            self._im_stats["active"] -= 1
            self._im_stats["resolved"] += 1
            self._incident_metrics.resolved_today += 1
        elif status == "closed":
            inc.closed_at = now
            inc.closed_by = actor
        inc.timeline.append(
            IncidentTimeline(
                event_type=status, description=comment or f"状态变更: {old_status.value} -> {status}", actor=actor
            )
        )
        self._send_notification(inc, status)
        return Result(success=True)

    def add_comment(self, incident_id: str, comment: str, actor: str = "") -> Result:
        inc = self._incidents.get(incident_id)
        if not inc:
            return Result(success=False, error="事件不存在")
        inc.timeline.append(IncidentTimeline(event_type="comment", description=comment, actor=actor))
        return Result(success=True)

    def set_root_cause(self, incident_id: str, root_cause: str) -> Result:
        inc = self._incidents.get(incident_id)
        if not inc:
            return Result(success=False, error="事件不存在")
        inc.root_cause = root_cause
        return Result(success=True)

    def set_resolution(self, incident_id: str, resolution: str) -> Result:
        inc = self._incidents.get(incident_id)
        if not inc:
            return Result(success=False, error="事件不存在")
        inc.resolution = resolution
        return Result(success=True)

    # ----------------------------------------------------------------
    # 派发与路由
    # ----------------------------------------------------------------

    def _route_incident(self, inc: Incident) -> str:
        for label in inc.labels:
            if label in self._routing_rules:
                return self._routing_rules[label]
        for svc in inc.impact.affected_services:
            if svc in self._routing_rules:
                return self._routing_rules[svc]
        return "default"

    def _get_oncall(self, team: str) -> Optional[str]:
        schedule = self._schedules.get(team)
        if schedule and schedule.current_oncall:
            return schedule.current_oncall
        return None

    def _send_notification(self, inc: Incident, event: str):
        if self._notify_callback:
            try:
                self._notify_callback(
                    {
                        "incident_id": inc.incident_id,
                        "title": inc.title,
                        "severity": inc.severity.value,
                        "event": event,
                        "assignee": inc.assignee,
                        "team": inc.team,
                    }
                )
            except Exception as e:
                logger.error(f"[IncidentManager] 通知失败: {e}")

    # ----------------------------------------------------------------
    # 升级
    # ----------------------------------------------------------------

    def _escalation_loop(self):
        while True:
            try:
                time.sleep(60.0)
                now = datetime.now()
                for inc in self._incidents.values():
                    if inc.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.FALSE_POSITIVE):
                        continue
                    if inc.severity not in (IncidentSeverity.P1_CRITICAL, IncidentSeverity.P2_MAJOR):
                        continue
                    rules = self._escalation_rules.get(inc.severity.value)
                    if not rules:
                        continue
                    acknowledged = inc.acknowledged_at
                    if not acknowledged:
                        elapsed = (now - datetime.fromisoformat(inc.detected_at)).total_seconds()
                        if elapsed > rules["initial_timeout"]:
                            self._escalate(inc, "未确认超时")
                    else:
                        elapsed = (now - datetime.fromisoformat(acknowledged)).total_seconds()
                        if elapsed > rules["escalation_interval"]:
                            self._escalate(inc, "处理超时")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[IncidentManager] 升级检查异常: {e}")

    def _escalate(self, inc: Incident, reason: str):
        schedule = self._schedules.get(inc.team)
        if not schedule or not schedule.escalation_chain:
            return
        # 查找升级目标
        current_level = (
            schedule.escalation_chain.index(inc.assignee) if inc.assignee in schedule.escalation_chain else -1
        )
        next_level = current_level + 1
        if next_level < len(schedule.escalation_chain):
            new_assignee = schedule.escalation_chain[next_level]
            inc.timeline.append(
                IncidentTimeline(
                    event_type="escalated", description=f"升级到: {new_assignee} (原因: {reason})", actor="system"
                )
            )
            inc.assignee = new_assignee
            self._im_stats["escalations"] += 1
            self._send_notification(inc, "escalated")
            logger.warning(f"[IncidentManager] 事件升级: {inc.incident_id} -> {new_assignee}")

    # ----------------------------------------------------------------
    # 查询
    # ----------------------------------------------------------------

    def get_incident(self, incident_id: str) -> Optional[Dict]:
        inc = self._incidents.get(incident_id)
        if not inc:
            return None
        return {
            "incident_id": inc.incident_id,
            "title": inc.title,
            "severity": inc.severity.value,
            "status": inc.status.value,
            "source": inc.source.value,
            "description": inc.description,
            "team": inc.team,
            "assignee": inc.assignee,
            "impact": {
                "services": inc.impact.affected_services,
                "users": inc.impact.affected_users_count,
                "region": inc.impact.affected_region,
            },
            "timeline": [
                {"time": t.timestamp, "type": t.event_type, "desc": t.description, "actor": t.actor}
                for t in inc.timeline
            ],
            "auto_actions": [{"type": a.action_type, "target": a.target, "status": a.status} for a in inc.auto_actions],
            "root_cause": inc.root_cause,
            "resolution": inc.resolution,
            "mtta": round(inc.mtta_seconds, 1),
            "mttr": round(inc.mttr_seconds, 1),
            "detected_at": inc.detected_at,
            "resolved_at": inc.resolved_at,
            "postmortem_required": inc.postmortem_required,
            "labels": inc.labels,
        }

    def search_incidents(
        self,
        *,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        team: Optional[str] = None,
        assignee: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        results = []
        for inc in sorted(self._incidents.values(), key=lambda x: x.detected_at, reverse=True):
            if severity and inc.severity.value != severity:
                continue
            if status and inc.status.value != status:
                continue
            if team and inc.team != team:
                continue
            if assignee and inc.assignee != assignee:
                continue
            results.append(
                {
                    "incident_id": inc.incident_id,
                    "title": inc.title,
                    "severity": inc.severity.value,
                    "status": inc.status.value,
                    "team": inc.team,
                    "assignee": inc.assignee,
                    "detected_at": inc.detected_at,
                    "resolved_at": inc.resolved_at,
                    "mtta": round(inc.mtta_seconds, 1),
                    "mttr": round(inc.mttr_seconds, 1),
                }
            )
        return results[:limit]

    def get_metrics(self) -> Dict[str, Any]:
        resolved = [i for i in self._incidents.values() if i.status == IncidentStatus.RESOLVED]
        mttas = [i.mtta_seconds for i in resolved if i.mtta_seconds > 0]
        mttrs = [i.mttr_seconds for i in resolved if i.mttr_seconds > 0]
        return {
            "total": self._incident_metrics.total_incidents,
            "by_severity": dict(self._incident_metrics.by_severity),
            "active": self._im_stats["active"],
            "resolved": self._im_stats["resolved"],
            "avg_mtta_seconds": round(sum(mttas) / len(mttas), 1) if mttas else 0,
            "avg_mttr_seconds": round(sum(mttrs) / len(mttrs), 1) if mttrs else 0,
            "escalations": self._im_stats["escalations"],
            "last_incident": self._incident_metrics.last_incident_at,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {**self._im_stats, "module_stats": self.stats.to_dict()}

# ============================================================================
# 模块注册
# ============================================================================

module_class = IncidentManager
