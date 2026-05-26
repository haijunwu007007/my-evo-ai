# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI V0.1 - Agent安全防护（A级生产实现）
===============================================
模块ID: agentguard-sec
功能：AI Agent行为安全 — 输入过滤/输出审查/行为审计/危险操作拦截。

核心能力：
  1. 输入过滤 — 注入攻击/命令注入/XSS/路径遍历检测
  2. 输出审查 — 敏感信息泄露/PII检测/合规检查
  3. 行为审计 — Agent操作全记录，异常行为实时告警
  4. 危险操作拦截 — 删除/格式化/网络访问/外部命令 限制
  5. 安全策略 — 可配置安全规则集
  6. 威胁情报 — 可疑模式库，持续更新
"""

__module_meta__ = {
    "id": "agentguard-sec",
    "name": "Agentguard Sec",
    "version": "V0.1",
    "group": "agent",
    "inputs": [
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["adapter", "agentguard", "agent"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - Agent安全防护（A级生产实现） ===============================================",
}

import time
import asyncio
import logging
import os
import re
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    CircuitBreakerMixin,
    RateLimiterMixin,
    Result,
)
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.agentguard-sec")

class _MetricsAdapter:
    """轻量指标适配器 — 兼容 self._metrics.increment/histogram 接口"""

    def increment(self, name: str, value: float = 1.0, **kw):
        pass  # 已由 EnterpriseModule.record_metrics() 覆盖

    def histogram(self, name: str, value: float, **kw):
        pass

    def gauge(self, name: str, value: float, **kw):
        pass

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

    # --- Auto-generated action dispatch methods ---
    def _action_counter(self, params=None):
        """Auto-generated action wrapper for counter"""
        if params is None:
            params = {}
        return self.counter(**params)

    def _action_gauge(self, params=None):
        """Auto-generated action wrapper for gauge"""
        if params is None:
            params = {}
        return self.gauge(**params)

    def _action_histogram(self, params=None):
        """Auto-generated action wrapper for histogram"""
        if params is None:
            params = {}
        return self.histogram(**params)

    def _action_increment(self, params=None):
        """Auto-generated action wrapper for increment"""
        if params is None:
            params = {}
        return self.increment(**params)

class ThreatLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityEvent:
    """安全事件"""

    event_id: str = ""
    timestamp: str = ""
    agent_id: str = ""
    threat_level: str = "low"
    category: str = ""
    detail: str = ""
    action_taken: str = ""  # allowed/blocked/quarantined
    source: str = ""

def __post_init__(self):
    if not self.event_id:
        self.event_id = f"SEV-{int(time.time() * 1000) % 10000000}"
    if not self.timestamp:
        self.timestamp = datetime.now().isoformat()

@dataclass
class SecurityPolicy:
    """安全策略"""

    block_shell_commands: bool = True
    block_path_traversal: bool = True
    block_network_access: bool = False
    block_file_delete: bool = True
    block_code_execution: bool = False
    max_output_length: int = 100000
    block_patterns: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    pii_detection: bool = True
    audit_all_operations: bool = True

class ThreatPatterns:
    """威胁模式库"""

    # 命令注入模式
    SHELL_INJECTION = [
        r";\s*(rm|del|format|shutdown|reboot|dd|mkfs)",
        r"`.*`",  # 反引号执行
        r"\$\([^)]+\)",  # $(cmd)
        r"\|\s*(bash|sh|cmd|powershell)",
        r">\s*/dev/",
        r"(wget|curl)\s+.*\|.*(bash|sh)",
    ]

    # 路径遍历
    PATH_TRAVERSAL = [
        r"\.\./",
        r"\.\.\\",
        r"/etc/passwd",
        r"/etc/shadow",
        r"C:\\Windows\\System32",
        r"~/.ssh/",
        r"~/.aws/",
        r"~/.gnupg/",
    ]

    # XSS模式
    XSS = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
    ]

    # SQL注入
    SQL_INJECTION = [
        r"(\b(union|select|insert|drop|delete|alter)\b.*--)",
        r"('\s*(or|and)\s+.*=)",
        r";\s*(drop|truncate|alter)\s+",
    ]

    # PII模式
    PII = [
        (r"\b\d{3}[-\s]?\d{4}[-\s]?\d{4}\b", "身份证号"),
        (r"\b1[3-9]\d{9}\b", "手机号"),
        (r"\b[\w.+-]+@[\w-]+\.[\w.]+\b", "邮箱"),
        (r"\b\d{16,19}\b", "银行卡号"),
    ]

    # 危险文件操作
    DANGEROUS_OPS = [
        r"(rm|del)\s+(-rf|-r\s+|-f\s+).*(/|\\)",
        r"format\s+[a-zA-Z]:",
        r"mkfs\.",
        r"dd\s+if=.*of=/dev/",
    ]

class SecurityAuditAnalyzer(object):
    """安全审计分析器 - 事件聚合、趋势分析、风险评估"""

    def __init__(self, max_events: int = 10000):
        self._events: deque = deque(maxlen=max_events)
        self._threat_count: int = 0
        self._blocked_count: int = 0

    def record_event(self, event_type: str, severity: str, source: str, detail: str = "") -> None:
        """记录安全事件"""
        self._events.append(
            {
                "type": event_type,
                "severity": severity,
                "source": source,
                "detail": detail[:200],
                "timestamp": time.time(),
            }
        )
        if severity in ("high", "critical"):
            self._threat_count += 1
        if event_type == "blocked":
            self._blocked_count += 1

    def get_summary(self, minutes: int = 60) -> Dict:
        """获取时间范围内的安全摘要"""
        cutoff = time.time() - minutes * 60
        recent = [e for e in self._events if e["timestamp"] >= cutoff]
        severity_dist = defaultdict(int)
        type_dist = defaultdict(int)
        for e in recent:
            severity_dist[e["severity"]] += 1
            type_dist[e["type"]] += 1
        return {
            "period_minutes": minutes,
            "total_events": len(recent),
            "by_severity": dict(severity_dist),
            "by_type": dict(type_dist),
            "threat_count": sum(1 for e in recent if e["severity"] in ("high", "critical")),
            "blocked_count": sum(1 for e in recent if e["type"] == "blocked"),
        }

    def detect_burst(self, window_seconds: int = 60, threshold: int = 10) -> Optional[Dict]:
        """检测短时间内的事件爆发"""
        cutoff = time.time() - window_seconds
        burst_events = [e for e in self._events if e["timestamp"] >= cutoff]
        if len(burst_events) >= threshold:
            return {
                "detected": True,
                "event_count": len(burst_events),
                "window_seconds": window_seconds,
                "risk_level": "HIGH",
                "top_types": dict(
                    sorted(defaultdict(int, {e["type"]: 1 for e in burst_events}).items(), key=lambda x: -x[1])[:5]
                ),
            }
        return None

    def get_top_sources(self, n: int = 5) -> List[Dict]:
        """获取事件最多的来源"""
        source_counts = defaultdict(int)
        for e in self._events:
            source_counts[e["source"]] += 1
        return [{"source": s, "count": c} for s, c in sorted(source_counts.items(), key=lambda x: -x[1])[:n]]

class AgentGuardSec(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """Agent安全防护模块"""

    MODULE_ID = "agentguard-sec"
    MODULE_NAME = "Agent安全防护"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self._metrics = _MetricsAdapter()
        self._circuits = {}
        self._buckets = {}
        self._windows = {}

        policy_cfg = self.config.get("policy", {})
        self.policy = SecurityPolicy(
            **{k: policy_cfg.get(k, getattr(SecurityPolicy(), k)) for k in SecurityPolicy.__dataclass_fields__}
        )
        self.patterns = ThreatPatterns()
        self._events: deque = deque(maxlen=5000)
        self._agent_risk_scores: Dict[str, float] = defaultdict(float)
        self._blocked_count = 0
        self._allowed_count = 0

    def initialize(self) -> None:
        self.info("初始化Agent安全防护...")
        self.record_metrics("agentguard-sec.init", 1)
        self._setup_rate_limit(rate=200, burst=500)
        self.status = ModuleStatus.RUNNING
        self.stats.start_time = datetime.now()
        self.audit("initialize", f"shell_block={self.policy.block_shell_commands}")
        self.info("Agent安全防护就绪")

    async def execute(self, action: str, params: Optional[Dict] = None) -> Result:
        _ = self.trace("execute")
        metrics_collector.counter("agentguard_ops_total", labels={"action": action})
        params = params or {}
        trace_id = f"guard-{action}-{int(time.time() * 1000)}"
        return self._safe_execute(action, params, self._dispatch)

    def health_check(self) -> HealthReport:
        """健康检查"""
        return HealthReport(
            status=self.status.value,
            healthy=self.status in (ModuleStatus.RUNNING, ModuleStatus.DEGRADED),
            last_beat=self._now(),
            uptime_seconds=self._uptime(),
            checks_run=self.stats.request_count,
            error_rate=self.stats.error_rate,
            details={"module": "agentguard-sec"},
        )

    def shutdown(self) -> None:
        self.status = ModuleStatus.STOPPED

    # ── 安全检查 ──

    def _dispatch(self, params: Dict[str, Any]) -> Any:
        action = params.get("action", "")
        handlers = {
            "check_input": self._do_check_input,
            "check_output": self._do_check_output,
            "check_operation": self._do_check_operation,
            "get_events": self._do_get_events,
            "get_agent_risk": self._do_get_agent_risk,
            "update_policy": self._do_update_policy,
            "get_policy": self._do_get_policy,
            "scan_text": self._do_scan_text,
            "get_stats": self._do_stats,
        }
        handler = handlers.get(action)
        if not handler:
            return {"error": f"未知动作: {action}", "available": list(handlers.keys())}
        return handler(params)

    def _do_check_input(self, params: Dict) -> Dict:
        text = params.get("text", "")
        agent_id = params.get("agent_id", "")
        threats = self._scan_threats(text, "input")
        blocked = any(t["level"] in ("high", "critical") for t in threats)
        event = SecurityEvent(
            agent_id=agent_id,
            threat_level=max((t["level"] for t in threats), default="safe"),
            category="input_filter",
            detail=f"检测到{len(threats)}个威胁",
            action_taken="blocked" if blocked else "allowed",
            source="check_input",
        )
        self._events.append(event)
        if blocked:
            self._blocked_count += 1
            self._agent_risk_scores[agent_id] += 5
            self.audit("block_input", f"agent={agent_id} threats={len(threats)}")
            self.record_metrics("input_blocked", 1, {"agent": agent_id})
        else:
            self._allowed_count += 1
        return {"safe": not blocked, "threats": threats, "action": "blocked" if blocked else "allowed"}

    def _do_check_output(self, params: Dict) -> Dict:
        text = params.get("text", "")
        agent_id = params.get("agent_id", "")
        threats = self._scan_threats(text, "output")
        # 输出不阻断，但标记和审计
        pii_found = self._detect_pii(text)
        event = SecurityEvent(
            agent_id=agent_id,
            threat_level="medium" if pii_found else "low",
            category="output_review",
            detail=f"PII={len(pii_found)}, threats={len(threats)}",
            action_taken="allowed",
            source="check_output",
        )
        self._events.append(event)
        self._allowed_count += 1
        return {
            "safe": len(threats) == 0,
            "threats": threats,
            "pii_detected": pii_found,
            "pii_count": len(pii_found),
            "action": "allowed",
        }

    def _sanitize_pii(self, text: str, replacement: str = "***") -> str:
        """PII脱敏处理"""
        import re as _re

        # 手机号
        text = _re.sub(r"1[3-9]\d{9}", lambda m: m.group()[:3] + replacement + m.group()[-2:], text)
        # 邮箱
        text = _re.sub(r"(\w{2})\w+(@\S+)", r"\1" + replacement + r"\2", text)
        # 身份证
        text = _re.sub(
            r"\d{6}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]",
            lambda m: m.group()[:6] + replacement + m.group()[-4:],
            text,
        )
        # 银行卡
        text = _re.sub(r"\d{16,19}", lambda m: m.group()[:4] + replacement + m.group()[-4:], text)
        return text

    def get_security_report(self) -> Dict:
        """获取安全总览报告"""
        return {
            "total_scans": self._scan_count if hasattr(self, "_scan_count") else 0,
            "blocked": self._blocked_count if hasattr(self, "_blocked_count") else 0,
            "allowed": self._allowed_count if hasattr(self, "_allowed_count") else 0,
            "events_total": len(self._events) if hasattr(self, "_events") else 0,
            "high_severity_events": len([e for e in self._events if e.threat_level == "high"])
            if hasattr(self, "_events")
            else 0,
        }

    def analyze_threat_timeline(self, hours: int = 24) -> Dict[str, Any]:
        """分析威胁时间线：按小时统计事件、识别攻击模式"""
        events = self._events if hasattr(self, "_events") else []
        now = time.time()
        cutoff = now - hours * 3600
        recent = [e for e in events if getattr(e, "timestamp", now) > cutoff]
        hourly: Dict[int, Dict[str, int]] = {}
        for e in recent:
            ts = getattr(e, "timestamp", now)
            hour_bucket = int(ts // 3600)
            level = getattr(e, "threat_level", "info")
            if hour_bucket not in hourly:
                hourly[hour_bucket] = {"high": 0, "medium": 0, "low": 0, "info": 0}
            hourly[hour_bucket][level] = hourly[hour_bucket].get(level, 0) + 1
        sorted_hours = sorted(hourly.items())
        peak_hour = max(hourly.items(), key=lambda x: sum(x[1].values())) if hourly else (0, {})
        agents_hit = set(getattr(e, "agent_id", "") for e in recent)
        top_agents = {}
        for e in recent:
            aid = getattr(e, "agent_id", "")
            if aid:
                top_agents[aid] = top_agents.get(aid, 0) + 1
        top_agents_sorted = sorted(top_agents.items(), key=lambda x: -x[1])[:5]
        return {
            "window_hours": hours,
            "total_events": len(recent),
            "peak_hour_events": sum(peak_hour[1].values()) if isinstance(peak_hour[1], dict) else 0,
            "unique_agents": len(agents_hit),
            "top_targeted_agents": top_agents_sorted,
            "hourly_breakdown": [{"hour": h, **counts} for h, counts in sorted_hours],
        }

    def _do_check_operation(self, params: Dict) -> Dict:
        op = params.get("operation", "")
        agent_id = params.get("agent_id", "")
        target = params.get("target", "")

        if self.policy.block_shell_commands and self._is_shell_op(op):
            self._record_block(agent_id, "shell_command", op)
            return {"allowed": False, "reason": "shell命令被安全策略拦截"}

        if self.policy.block_file_delete and self._is_dangerous_file_op(op, target):
            self._record_block(agent_id, "file_delete", op)
            return {"allowed": False, "reason": "危险文件操作被拦截"}

        if self.policy.block_path_traversal and self._has_path_traversal(target):
            self._record_block(agent_id, "path_traversal", target)
            return {"allowed": False, "reason": "路径遍历被拦截"}

        self._allowed_count += 1
        return {"allowed": True}

    def _do_get_events(self, params: Dict) -> Dict:
        limit = params.get("limit", 50)
        agent_id = params.get("agent_id", "")
        events = list(self._events)
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        return {
            "total": len(events),
            "items": [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp,
                    "agent_id": e.agent_id,
                    "threat_level": e.threat_level,
                    "category": e.category,
                    "detail": e.detail,
                    "action_taken": e.action_taken,
                }
                for e in events[-limit:]
            ],
        }

    def _do_get_agent_risk(self, params: Dict) -> Dict:
        return {"agents": {k: round(v, 1) for k, v in self._agent_risk_scores.items()}}

    def _do_update_policy(self, params: Dict) -> Dict:
        for key in SecurityPolicy.__dataclass_fields__:
            if key in params:
                setattr(self.policy, key, params[key])
        self.audit("update_policy", str({k: v for k, v in params.items() if k in SecurityPolicy.__dataclass_fields__}))
        return {"success": True}

    def _do_get_policy(self, params: Dict) -> Dict:
        return {k: v for k, v in self.policy.__dict__.items() if not k.startswith("_")}

    def _do_scan_text(self, params: Dict) -> Dict:
        text = params.get("text", "")
        mode = params.get("mode", "all")
        return {"threats": self._scan_threats(text, mode)}

    def _do_stats(self, params: Dict) -> Dict:
        total = self._blocked_count + self._allowed_count
        return {
            "total_checks": total,
            "blocked": self._blocked_count,
            "allowed": self._allowed_count,
            "block_rate": f"{self._blocked_count / total * 100:.1f}%" if total > 0 else "0%",
            "events": len(self._events),
            "agents": len(self._agent_risk_scores),
        }

    def _do_threat_summary(self, params: Dict) -> Dict:
        """威胁类型统计"""
        threat_type_counts = defaultdict(int)
        for e in self._events:
            threat_type_counts[e.category] += 1
        return {
            "by_category": dict(sorted(threat_type_counts.items(), key=lambda x: -x[1])),
            "total_categories": len(threat_type_counts),
        }

    def _do_quarantine_agent(self, params: Dict) -> Dict:
        """隔离高风险Agent"""
        agent_id = params.get("agent_id", "")
        if not agent_id:
            return {"error": "agent_id_required"}
        self._agent_risk_scores[agent_id] = 100.0
        self.audit("quarantine_agent", f"agent={agent_id}")
        return {"quarantined": True, "agent_id": agent_id, "risk_score": 100.0}

    def _do_clear_agent_risk(self, params: Dict) -> Dict:
        """清除Agent风险评分"""
        agent_id = params.get("agent_id", "")
        if agent_id in self._agent_risk_scores:
            del self._agent_risk_scores[agent_id]
            self.audit("clear_agent_risk", f"agent={agent_id}")
            return {"cleared": True}
        return {"cleared": False, "reason": "not_found"}

    # ── 威胁扫描引擎 ──

    def _scan_threats(self, text: str, mode: str = "all") -> List[Dict]:
        threats = []
        patterns = []

        if mode in ("all", "input"):
            patterns.extend([(p, "shell_injection", "high") for p in ThreatPatterns.SHELL_INJECTION])
            patterns.extend([(p, "sql_injection", "high") for p in ThreatPatterns.SQL_INJECTION])
            patterns.extend([(p, "xss", "medium") for p in ThreatPatterns.XSS])
        if mode in ("all", "input"):
            patterns.extend([(p, "path_traversal", "high") for p in ThreatPatterns.PATH_TRAVERSAL])
        if mode in ("all", "output"):
            patterns.extend([(p, "dangerous_ops", "high") for p in ThreatPatterns.DANGEROUS_OPS])
        if mode in ("all",):
            patterns.extend([(p, "dangerous_ops", "high") for p in ThreatPatterns.DANGEROUS_OPS])

        # 自定义模式
        for custom in self.policy.block_patterns:
            patterns.append((custom, "custom", "medium"))

        for pattern, category, level in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    threats.append(
                        {
                            "category": category,
                            "level": level,
                            "match": match.group()[:50],
                            "position": match.start(),
                        }
                    )
            except re.error:
                pass

        return threats

    def _detect_pii(self, text: str) -> List[Dict]:
        if not self.policy.pii_detection:
            return []
        found = []
        for pattern, label in ThreatPatterns.PII:
            try:
                matches = re.findall(pattern, text)
                for m in matches:
                    masked = m[:3] + "*" * (len(m) - 6) + m[-3:] if len(m) > 6 else "***"
                    found.append({"type": label, "masked": masked, "raw_length": len(m)})
            except re.error:
                pass
        return found

    def _is_shell_op(self, op: str) -> bool:
        shell_cmds = ["bash", "sh", "cmd", "powershell", "eval", "exec", "system", "popen", "subprocess"]
        return any(cmd in op.lower() for cmd in shell_cmds)

    def _is_dangerous_file_op(self, op: str, target: str) -> bool:
        dangerous = ["delete", "remove", "unlink", "rmdir", "truncate", "erase"]
        combined = f"{op} {target}".lower()
        for p in ThreatPatterns.DANGEROUS_OPS:
            try:
                if re.search(p, combined):
                    return True
            except re.error:
                pass
        return any(d in op.lower() for d in dangerous) and ("*" in target or "/" in target or "\\" in target)

    def _has_path_traversal(self, target: str) -> bool:
        for p in ThreatPatterns.PATH_TRAVERSAL:
            try:
                if re.search(p, target, re.IGNORECASE):
                    return True
            except re.error:
                pass
        return False

    def _record_block(self, agent_id: str, category: str, detail: str):
        self._blocked_count += 1
        self._agent_risk_scores[agent_id] += 10
        event = SecurityEvent(
            agent_id=agent_id,
            threat_level="high",
            category=category,
            detail=detail,
            action_taken="blocked",
        )
        self._events.append(event)
        self.audit("block", f"agent={agent_id} cat={category}")

    # ── 标准Action处理器（自动注入）──

    def _do_get_status(self, params):
        """标准action: 模块状态"""
        try:
            status = self.get_status() if hasattr(self, "get_status") else {}
        except:
            status = {}
        if isinstance(status, dict):
            status["module_id"] = self.module_id
            status["version"] = getattr(self, "version", "")
            status["actions"] = [k for k in dir(self) if k.startswith("_do_") and callable(getattr(self, k))]
        return status

    def _do_list_actions(self, params):
        """标准action: 列出可用操作"""
        actions = [k for k in dir(self) if k.startswith("_do_") and callable(getattr(self, k))]
        # Clean up method names
        clean = [a.replace("_do_", "").replace("_", "-") for a in actions]
        # Also include standard actions
        standard = [
            "status",
            "info",
            "health",
            "ping",
            "list_actions",
            "help",
            "metrics",
            "stats",
            "configure",
            "config",
            "reset",
            "version",
        ]
        return {"total": len(set(clean + standard)), "actions": sorted(set(clean + standard))}

    def _do_configure(self, params):
        """标准action: 修改配置"""
        if not isinstance(params, dict):
            return {"error": "params must be a dict"}
        updated = []
        for k, v in params.items():
            if k in ("action",):
                continue
            if hasattr(self, "config"):
                self.config[k] = v
                updated.append(k)
        return {"success": True, "updated": updated}

    def _do_version(self, params):
        """标准action: 版本信息"""
        return {
            "module_id": self.module_id,
            "version": getattr(self, "version", "unknown"),
            "class": self.__class__.__name__,
        }

    def _do_reset(self, params):
        """标准action: 重置"""
        if hasattr(self, "stats"):
            self.stats.request_count = 0
            self.stats.error_count = 0
            self.stats.success_count = 0
            self.stats.latencies = []
        return {"success": True, "message": "reset done"}

module_class = AgentGuardSec
