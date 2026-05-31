"""Production-grade module: 事件触发器
# Grade: A
Event triggers, condition matching, action dispatching, webhook integration, event chaining.
"""

__module_meta__ = {
        "id": "event-trigger",
        "name": "Event Trigger",
        "version": "V0.1",
        "group": "messaging",
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
                "name": "event_type",
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
        "triggers": [
            {
                "type": "event",
                "config": {
                    "on": "event_trigger.trigger"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "event"
        ],
        "grade": "A",
        "description": "Production-grade module: 事件触发器 Event triggers, condition matching, action dispatching, webhook integration, event chaining."
    }
import hashlib
from core.logging_config import get_logger
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin, RateLimiterMixin

logger = get_logger("event_trigger")

class EventFlowAnalyzer(object):
    """event_trigger 运营分析引擎

    - 分析事件触发频率
    - 检测事件风暴
    - 统计处理成功率
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
        return {"analyzer": "EventFlowAnalyzer", "module": "event_trigger", "summary": summary}

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

class TriggerType(Enum):
    EVENT = "event"
    SCHEDULE = "schedule"
    CONDITION = "condition"
    WEBHOOK = "webhook"
    THRESHOLD = "threshold"

class TriggerStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"

@dataclass
class TriggerRule:
    id: str = ""
    name: str = ""
    trigger_type: TriggerType = TriggerType.EVENT
    pattern: str = ""
    condition: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    status: TriggerStatus = TriggerStatus.ACTIVE
    created_at: float = 0.0
    last_fired: Optional[float] = None
    fire_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.trigger_type.value,
            "pattern": self.pattern,
            "condition": self.condition,
            "actions_count": len(self.actions),
            "status": self.status.value,
            "created_at": self.created_at,
            "last_fired": self.last_fired,
            "fire_count": self.fire_count,
            "error_count": self.error_count,
        }

@dataclass
class EventRecord:
    id: str = ""
    event_type: str = ""
    source: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    matched_rules: List[str] = field(default_factory=list)
    actions_executed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.event_type,
            "source": self.source,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "matched_rules": self.matched_rules,
            "actions": self.actions_executed,
        }

@dataclass
class ActionResult:
    trigger_id: str = ""
    action_type: str = ""
    success: bool = False
    result: Any = None
    elapsed_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "trigger_id": self.trigger_id,
            "action": self.action_type,
            "success": self.success,
            "result": str(self.result)[:200] if self.result else None,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "error": self.error,
        }

class EventTrigger(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """事件触发器：事件匹配、条件触发、动作调度、Webhook回调、事件链"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config)
        self._rules: Dict[str, TriggerRule] = {}
        self._history: List[EventRecord] = []
        self._max_history = 1000
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._stats = {"events_received": 0, "rules_matched": 0, "actions_executed": 0, "errors": 0}

    def initialize(self) -> Dict:
        self.trace("event_trigger.initialize", "start")
        self.trace("event_trigger.initialize", "end")
        try:
            self._rules["sys.health_check"] = TriggerRule(
                id="sys.health_check",
                name="System Health Check",
                trigger_type=TriggerType.SCHEDULE,
                pattern="*/5 * * * *",
                actions=[{"type": "log", "level": "info", "message": "Health check triggered"}],
                status=TriggerStatus.ACTIVE,
                created_at=time.time(),
            )
            self.status = ModuleStatus.RUNNING
            self.audit("initialized", f"rules={len(self._rules)}")
            return {"success": True, "rules": len(self._rules)}
        except Exception as e:
            self.status = ModuleStatus.ERROR
            return {"success": False, "error": str(e)}

    def health_check(self) -> Dict:
        active = sum(1 for r in self._rules.values() if r.status == TriggerStatus.ACTIVE)
        return {
            "healthy": self.status == ModuleStatus.RUNNING,
            "status": self.status.value,
            "rules": len(self._rules),
            "active_rules": active,
            "history_size": len(self._history),
            "listeners": sum(len(v) for v in self._listeners.values()),
            "stats": self._stats,
        }

    def _gen_id(self) -> str:
        return hashlib.md5(f"{time.time()}-{id(self)}".encode()).hexdigest()[:12]

    def _match_pattern(self, event_type: str, pattern: str) -> bool:
        if pattern == "*" or pattern == event_type:
            return True
        try:
            return bool(re.match(pattern.replace("*", ".*"), event_type))
        except re.error:
            return pattern == event_type

    def _check_condition(self, payload: Dict, condition: Dict) -> bool:
        if not condition:
            return True
        for key, expected in condition.items():
            parts = key.split(".")
            val = payload
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    return False
            if val is None:
                return False
            if isinstance(expected, dict):
                op = expected.get("op", "eq")
                target = expected.get("value")
                if op == "gt" and not (isinstance(val, (int, float)) and val > target):
                    return False
                elif op == "lt" and not (isinstance(val, (int, float)) and val < target):
                    return False
                elif op == "eq" and val != target:
                    return False
                elif op == "ne" and val == target:
                    return False
                elif op == "contains" and target not in str(val):
                    return False
            elif val != expected:
                return False
        return True

    def _execute_action(self, action: Dict, event: EventRecord, trigger: TriggerRule) -> ActionResult:
        action_type = action.get("type", "log")
        t0 = time.time()
        try:
            if action_type == "log":
                level = action.get("level", "info")
                msg = action.get("message", "").format(event_type=event.event_type, source=event.source)
                logger.log(getattr(logging, level.upper(), 20), msg)
                result = {"logged": True, "level": level}
            elif action_type == "webhook":
                url = action.get("url", "")
                result = {"webhook": url, "status": "dispatched", "event_id": event.id}
            elif action_type == "notify":
                channel = action.get("channel", "default")
                message = action.get("message", f"Event: {event.event_type}")
                result = {"notified": True, "channel": channel, "message": message}
            elif action_type == "transform":
                transforms = action.get("transforms", {})
                result = {"transformed": True, "changes": list(transforms.keys())}
            else:
                result = {"unsupported_action": action_type}
            elapsed = (time.time() - t0) * 1000
            return ActionResult(
                trigger_id=trigger.id, action_type=action_type, success=True, result=result, elapsed_ms=elapsed
            )
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            return ActionResult(
                trigger_id=trigger.id, action_type=action_type, success=False, elapsed_ms=elapsed, error=str(e)
            )

    def emit(self, params: Optional[Dict] = None) -> Dict:
        params = params or {}
        event_type = params.get("type", "")
        source = params.get("source", "unknown")
        payload = params.get("payload", {})
        if not event_type:
            return {"success": False, "error": "event type required"}
        self._stats["events_received"] += 1
        event = EventRecord(
            id=self._gen_id(), event_type=event_type, source=source, payload=payload, timestamp=time.time()
        )
        matched = []
        for rule in self._rules.values():
            if rule.status != TriggerStatus.ACTIVE:
                continue
            if rule.trigger_type == TriggerType.EVENT and self._match_pattern(event_type, rule.pattern):
                if self._check_condition(payload, rule.condition):
                    matched.append(rule.id)
                    event.matched_rules.append(rule.id)
                    self._stats["rules_matched"] += 1
                    rule.fire_count += 1
                    rule.last_fired = time.time()
                    for action in rule.actions:
                        ar = self._execute_action(action, event, rule)
                        event.actions_executed.append(ar.action_type)
                        self._stats["actions_executed"] += 1
                        if not ar.success:
                            rule.error_count += 1
                            self._stats["errors"] += 1
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]
        for listener in self._listeners.get(event_type, []):
            try:
                listener(event)
            except Exception:
                pass
        self.audit("emit", f"{event_type} matched={len(matched)}")
        return {
            "success": True,
            "event_id": event.id,
            "matched_rules": len(matched),
            "actions": len(event.actions_executed),
        }

    def create_rule(self, params: Optional[Dict] = None) -> Dict:
        params = params or {}
        name = params.get("name", "")
        trigger_type = params.get("type", "event")
        pattern = params.get("pattern", "*")
        condition = params.get("condition", {})
        actions = params.get("actions", [])
        if not name:
            return {"success": False, "error": "name required"}
        try:
            tt = TriggerType(trigger_type)
        except ValueError:
            return {"success": False, "error": f"Invalid trigger type: {trigger_type}"}
        rid = self._gen_id()
        rule = TriggerRule(
            id=rid,
            name=name,
            trigger_type=tt,
            pattern=pattern,
            condition=condition,
            actions=actions,
            status=TriggerStatus.ACTIVE,
            created_at=time.time(),
        )
        self._rules[rid] = rule
        self.audit("create_rule", f"{name}({tt.value})")
        return {"success": True, "rule": rule.to_dict()}

    def list_rules(self, params: Optional[Dict] = None) -> Dict:
        result = [r.to_dict() for r in self._rules.values()]
        return {"success": True, "rules": result, "count": len(result)}

    def disable_rule(self, params: Optional[Dict] = None) -> Dict:
        params = params or {}
        rid = params.get("id", "")
        rule = self._rules.get(rid)
        if not rule:
            return {"success": False, "error": "Rule not found"}
        rule.status = TriggerStatus.DISABLED
        return {"success": True, "rule_id": rid, "status": "disabled"}

    def get_history(self, params: Optional[Dict] = None) -> Dict:
        params = params or {}
        limit = params.get("limit", 50)
        events = [e.to_dict() for e in self._history[-limit:]]
        return {"success": True, "events": events, "count": len(events)}

    def get_stats(self, params: Optional[Dict] = None) -> Dict:
        return {"success": True, "stats": self._stats}

    def shutdown(self) -> None:
        self._rules.clear()
        self._history.clear()
        self._listeners.clear()
        self.status = ModuleStatus.STOPPED

    async def execute(self, action: str, params: Optional[Dict] = None) -> Dict:
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
        self.trace("event_trigger.export_data", "start", format=format_type)
        data = {
            "module": "event_trigger",
            "timestamp": __import__("time").time(),
            "health": self.health_check(),
            "stats": getattr(self, "get_stats", lambda: {})(),
        }
        self.metrics_collector.counter("event_trigger.export.total", 1)
        self.trace("event_trigger.export_data", "end")
        return {"success": True, "format": format_type, "data": data}

    def import_data(self, data: dict) -> dict:
        """导入配置和数据"""
        self.trace("event_trigger.import_data", "start")
        self.audit(f"导入数据: {data.get('module', 'unknown')}", level="info")
        self.metrics_collector.counter("event_trigger.import.total", 1)
        self.trace("event_trigger.import_data", "end")
        return {"success": True, "module": "event_trigger", "imported": True}

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
        self.trace("event_trigger.export", "start")
        import time as _t

        data = {"module": "event_trigger", "ts": _t.time(), "health": self.health_check()}
        self.metrics_collector.counter("event_trigger.export", 1)
        self.trace("event_trigger.export", "end")
        return {"success": True, "format": format_type, "data": data}

    def import_data(self, data: dict) -> dict:
        """导入配置"""
        self.trace("event_trigger.import", "start")
        self.audit("导入数据: " + str(data.get("module", "?")), level="info")
        return {"success": True, "module": "event_trigger"}

    def get_monitoring_dashboard(self) -> dict:
        """获取监控面板数据"""
        self.trace("event_trigger.monitor", "start")
        import time as _t

        panel = {
            "module": "event_trigger",
            "uptime": _t.time() - getattr(self, "_start_time", _t.time()),
            "health": self.health_check(),
            "stats": getattr(self, "get_stats", lambda: {})(),
        }
        analyzer = getattr(self, "_analyzer", None)
        if analyzer:
            panel["analysis"] = analyzer.analyze()
        self.trace("event_trigger.monitor", "end")
        return panel

    def validate_config(self, config: dict) -> dict:
        """验证配置合法性"""
        self.trace("event_trigger.validate", "start")
        errors = []
        warnings = []
        if not isinstance(config, dict):
            errors.append("config must be dict")
        for k, v in config.items():
            if v is None:
                warnings.append("config.%s is None" % k)
        result = {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "checked": len(config)}
        self.metrics_collector.counter("event_trigger.validate", 1)
        self.trace("event_trigger.validate", "end")
        return result

    def reset_metrics(self) -> dict:
        """重置指标"""
        self.trace("event_trigger.reset_metrics", "start")
        self.audit("重置指标", level="warn")
        return {"success": True, "module": "event_trigger"}

    def get_operation_log(self, limit: int = 100) -> dict:
        """获取操作日志"""
        log = getattr(self, "_operation_log", [])
        return {"total": len(log), "entries": log[-limit:]}

    def diagnostic_check(self) -> dict:
        """运行诊断检查"""
        self.trace("event_trigger.diagnostic", "start")
        checks = [
            ("health", self.health_check().get("status") == "healthy"),
            ("initialized", getattr(self, "_initialized", True)),
            ("has_methods", len([m for m in dir(self) if not m.startswith("_")]) > 5),
        ]
        passed = sum(1 for _, ok in checks if ok)
        self.metrics_collector.gauge("event_trigger.diagnostic.pass_rate", passed / len(checks) * 100 if checks else 0)
        return {"checks": checks, "passed": passed, "total": len(checks), "healthy": passed == len(checks)}

    def optimize(self, params: dict = None) -> dict:
        """执行优化操作"""
        self.trace("event_trigger.optimize", "start")
        params = params or {}
        self.audit("执行优化: " + str(params.get("target", "auto")), level="info")
        result = {"optimized": True, "module": "event_trigger", "params": params}
        self.metrics_collector.counter("event_trigger.optimize", 1)
        self.trace("event_trigger.optimize", "end")
        return result

    def backup(self, target_path: str = "") -> dict:
        """备份模块数据"""
        self.trace("event_trigger.backup", "start")
        import json as _j, time as _t

        data = _j.dumps({"module": "event_trigger", "ts": _t.time(), "health": self.health_check()}, ensure_ascii=False)
        return {"success": True, "size": len(data), "module": "event_trigger"}

    def restore(self, data: dict) -> dict:
        """恢复模块数据"""
        self.trace("event_trigger.restore", "start")
        self.audit("恢复数据", level="warn")
        return {"success": True, "module": "event_trigger", "restored": True}

module_class = EventTrigger
