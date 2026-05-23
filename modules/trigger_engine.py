"""
Trigger Engine - 企业级事件触发引擎
生产级Cron/Event/Condition/Webhook触发器管理
支持：Cron表达式调度、事件条件匹配、链式触发、死信队列、幂等保证
"""

__module_meta__ = {
    "id": "trigger-engine",
    "name": "事件触发引擎",
    "version": "1.0.0",
    "group": "workflow",
    "inputs": [
        {"name": "trigger_def", "type": "dict", "required": True, "description": "触发器定义"},
        {"name": "event_name", "type": "string", "description": "事件名称"},
        {"name": "cron_expr", "type": "string", "description": "Cron表达式"},
    ],
    "outputs": [{"name": "triggered", "type": "bool", "description": "是否触发"}],
    "triggers": [{"type": "event", "config": {"on": "engine.trigger.register"}}],
    "depends_on": ["event-bus"],
    "tags": ["trigger", "workflow", "scheduler"],
    "grade": "A",
}
import re
import time
import hashlib
import threading
import uuid
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import defaultdict

from modules._base.enterprise_module import EnterpriseModule

class TriggerType(Enum):
    CRON = "cron"
    EVENT = "event"
    CONDITION = "condition"
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"

class TriggerState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"
    FIRED = "fired"

class FireResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    DEDUP = "deduplicated"

# ─── Cron 解析引擎 ───────────────────────────────────────────

class CronExpression:
    """Cron表达式解析与下次执行时间计算（分钟级精度，支持5段标准Cron）"""

    FIELD_NAMES = ["minute", "hour", "day_of_month", "month", "day_of_week"]
    FIELD_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]

    MONTH_ALIASES = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }
    DOW_ALIASES = {"SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6}

    def __init__(self, expression: str):
        self.expression = expression.strip()
        self.fields = self._parse(self.expression)

    def _parse(self, expr: str) -> List[set]:
        parts = expr.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expr}, expected 5 fields")
        fields = []
        for i, part in enumerate(parts):
            field_values = self._parse_field(part, self.FIELD_RANGES[i], i)
            fields.append(field_values)
        return fields

    def _parse_field(self, field: str, value_range: tuple, field_idx: int) -> set:
        field = field.upper()
        # 替换别名
        if field_idx == 3:  # month
            for alias, val in self.MONTH_ALIASES.items():
                field = field.replace(alias, str(val))
        elif field_idx == 4:  # day of week
            for alias, val in self.DOW_ALIASES.items():
                field = field.replace(alias, str(val))

        result = set()
        for segment in field.split(","):
            if segment == "*":
                result.update(range(value_range[0], value_range[1] + 1))
            elif "/" in segment:
                base, step = segment.split("/")
                step = int(step)
                if base == "*":
                    start = value_range[0]
                else:
                    start = int(base)
                result.update(range(start, value_range[1] + 1, step))
            elif "-" in segment:
                start, end = segment.split("-")
                result.update(range(int(start), int(end) + 1))
            else:
                result.add(int(segment))
        return {v for v in result if value_range[0] <= v <= value_range[1]}

    def matches(self, dt: datetime) -> bool:
        return (
            dt.minute in self.fields[0]
            and dt.hour in self.fields[1]
            and dt.day in self.fields[2]
            and dt.month in self.fields[3]
            and dt.weekday() in self._convert_dow(dt.weekday())
        )

    def _convert_dow(self, python_dow: int) -> int:
        # Python: Mon=0, Sun=6; Cron: Sun=0, Sat=6
        return (python_dow + 1) % 7

    def next_fire_time(self, after: Optional[datetime] = None) -> Optional[datetime]:
        if after is None:
            after = datetime.now()
        now = after.replace(second=0, microsecond=0)
        # 最多查找未来2年
        end = now + timedelta(days=730)
        candidate = now + timedelta(minutes=1)
        while candidate <= end:
            if self.matches(candidate):
                return candidate
            candidate += timedelta(minutes=1)
        return None

    def description(self) -> str:
        parts = []
        for i, values in enumerate(self.fields):
            if values == set(range(self.FIELD_RANGES[i][0], self.FIELD_RANGES[i][1] + 1)):
                parts.append("每" + ["分钟", "小时", "日", "月", "周"][i])
            else:
                sorted_vals = sorted(values)
                parts.append(f"{self.FIELD_NAMES[i]}={sorted_vals[:5]}{'...' if len(sorted_vals) > 5 else ''}")
        return " | ".join(parts)

# ─── 条件匹配引擎 ───────────────────────────────────────────

class ConditionEvaluator:
    """事件条件表达式求值引擎
    支持: ==, !=, >, <, >=, <=, in, contains, regex, AND, OR, NOT
    """

    def __init__(self):
        self._compiled_cache: Dict[str, Any] = {}

    def evaluate(self, condition: Dict, context: Dict) -> bool:
        """求值条件表达式，context为事件数据字典"""
        if not condition:
            return True
        logic = condition.get("logic", "AND")
        rules = condition.get("rules", [])
        if not rules:
            return True

        results = []
        for rule in rules:
            results.append(self._eval_rule(rule, context))

        if logic == "AND":
            return all(results)
        elif logic == "OR":
            return any(results)
        elif logic == "NOT":
            return not all(results)
        return all(results)

    def _eval_rule(self, rule: Dict, context: Dict) -> bool:
        field = rule.get("field", "")
        op = rule.get("op", "==")
        value = rule.get("value")
        path_parts = field.split(".")
        actual = context
        try:
            for part in path_parts:
                if isinstance(actual, dict):
                    actual = actual.get(part)
                elif isinstance(actual, (list, tuple)) and part.isdigit():
                    actual = actual[int(part)]
                else:
                    return False
                if actual is None:
                    return False
        except (KeyError, IndexError, TypeError, ValueError):
            return False

        if op == "==":
            return actual == value
        elif op == "!=":
            return actual != value
        elif op == ">":
            return float(actual) > float(value) if isinstance(actual, (int, float)) else False
        elif op == "<":
            return float(actual) < float(value) if isinstance(actual, (int, float)) else False
        elif op == ">=":
            return float(actual) >= float(value) if isinstance(actual, (int, float)) else False
        elif op == "<=":
            return float(actual) <= float(value) if isinstance(actual, (int, float)) else False
        elif op == "in":
            return actual in (value if isinstance(value, list) else [value])
        elif op == "contains":
            return value in str(actual) if actual else False
        elif op == "regex":
            try:
                return bool(re.search(str(value), str(actual)))
            except re.error:
                return False
        elif op == "exists":
            return actual is not None
        elif op == "type":
            return type(actual).__name__ == value
        return False

    def extract_fields(self, condition: Dict) -> List[str]:
        """提取条件中引用的所有字段路径"""
        fields = []
        for rule in condition.get("rules", []):
            f = rule.get("field", "")
            if f and f not in fields:
                fields.append(f)
        return fields

# ─── 触发器调度引擎 ──────────────────────────────────────────

class TriggerScheduler:
    """触发器调度引擎：管理触发器生命周期、执行触发、死信处理"""

    def __init__(self):
        self._triggers: Dict[str, Dict] = {}
        self._fire_history: List[Dict] = []
        self._dead_letters: List[Dict] = []
        self._dedup_cache: Dict[str, float] = {}
        self._dedup_ttl = 60.0  # 去重窗口秒数
        self._max_history = 10000
        self._lock = threading.Lock()
        self._condition_engine = ConditionEvaluator()

    def register(self, trigger_id: str, trigger_type: str, config: Dict) -> Dict:
        with self._lock:
            trigger = {
                "id": trigger_id,
                "type": trigger_type,
                "config": config,
                "state": "active",
                "created_at": time.time(),
                "last_fired": None,
                "fire_count": 0,
                "fail_count": 0,
                "tags": config.get("tags", []),
            }
            # 预编译Cron
            if trigger_type == "cron" and "expression" in config:
                try:
                    trigger["_cron"] = CronExpression(config["expression"])
                except ValueError as e:
                    trigger["state"] = "error"
                    trigger["error"] = str(e)
            self._triggers[trigger_id] = trigger
            return trigger

    def unregister(self, trigger_id: str) -> bool:
        with self._lock:
            return self._triggers.pop(trigger_id, None) is not None

    def fire(self, trigger_id: str, payload: Dict = None, dedup: bool = True) -> Dict:
        with self._lock:
            trigger = self._triggers.get(trigger_id)
            if not trigger:
                return {"success": False, "error": f"Trigger {trigger_id} not found"}
            if trigger["state"] not in ("active",):
                return {"success": False, "error": f"Trigger state is {trigger['state']}"}

            # 幂等去重
            if dedup:
                dedup_key = hashlib.md5(
                    f"{trigger_id}:{json.dumps(payload or {}, sort_keys=True)}".encode()
                ).hexdigest()
                now = time.time()
                if dedup_key in self._dedup_cache:
                    if now - self._dedup_cache[dedup_key] < self._dedup_ttl:
                        return {"success": True, "result": "deduplicated", "trigger_id": trigger_id}
                self._dedup_cache[dedup_key] = now
                # 清理过期缓存
                expired = [k for k, v in self._dedup_cache.items() if now - v > self._dedup_ttl]
                for k in expired:
                    del self._dedup_cache[k]

            fire_record = {
                "id": str(uuid.uuid4())[:8],
                "trigger_id": trigger_id,
                "trigger_type": trigger["type"],
                "payload": payload or {},
                "fired_at": time.time(),
                "result": "success",
            }

            # 条件检查
            if trigger["type"] == "condition":
                condition = trigger["config"].get("condition", {})
                if not self._condition_engine.evaluate(condition, payload or {}):
                    fire_record["result"] = "skipped"
                    self._add_history(fire_record)
                    return {"success": True, "result": "skipped", "reason": "condition_not_met"}

            trigger["last_fired"] = fire_record["fired_at"]
            trigger["fire_count"] += 1
            self._add_history(fire_record)

            # 执行回调
            callback = trigger["config"].get("callback")
            if callback:
                try:
                    if callable(callback):
                        callback(trigger_id, payload or {})
                except Exception as e:
                    trigger["fail_count"] += 1
                    fire_record["result"] = "failed"
                    fire_record["error"] = str(e)
                    # 死信队列
                    self._dead_letters.append(
                        {
                            "trigger_id": trigger_id,
                            "payload": payload,
                            "error": str(e),
                            "timestamp": time.time(),
                            "retries": 0,
                        }
                    )
                    return {"success": False, "error": str(e)}

            # 链式触发
            chain = trigger["config"].get("chain", [])
            if chain:
                for next_id in chain:
                    self.fire(next_id, payload, dedup=False)

            return {"success": True, "result": fire_record["result"], "fire_id": fire_record["id"]}

    def check_cron_triggers(self, now: Optional[datetime] = None) -> List[Dict]:
        """检查哪些Cron触发器应该在当前时间触发"""
        if now is None:
            now = datetime.now()
        results = []
        with self._lock:
            for tid, t in self._triggers.items():
                if t["type"] == "cron" and t["state"] == "active":
                    cron = t.get("_cron")
                    if cron and cron.matches(now):
                        results.append({"trigger_id": tid, "fired": self.fire(tid)})
        return results

    def match_event(self, event_type: str, payload: Dict) -> List[Dict]:
        """匹配事件触发器"""
        results = []
        with self._lock:
            for tid, t in self._triggers.items():
                if t["type"] != "event" or t["state"] != "active":
                    continue
                config = t["config"]
                # 事件类型匹配
                subscribed = config.get("event_types", ["*"])
                if subscribed != ["*"] and event_type not in subscribed:
                    continue
                # 条件过滤
                condition = config.get("condition", {})
                if condition and not self._condition_engine.evaluate(condition, payload):
                    continue
                results.append({"trigger_id": tid, "fired": self.fire(tid, {"event_type": event_type, **payload})})
        return results

    def _add_history(self, record: Dict):
        self._fire_history.append(record)
        if len(self._fire_history) > self._max_history:
            self._fire_history = self._fire_history[-self._max_history :]

    def get_trigger(self, trigger_id: str) -> Optional[Dict]:
        return self._triggers.get(trigger_id)

    def list_triggers(self, state_filter: str = None, tag: str = None) -> List[Dict]:
        results = []
        with self._lock:
            for t in self._triggers.values():
                if state_filter and t["state"] != state_filter:
                    continue
                if tag and tag not in t["tags"]:
                    continue
                result = {k: v for k, v in t.items() if not k.startswith("_")}
                if "_cron" in t:
                    result["cron_description"] = t["_cron"].description()
                    result["next_fire"] = str(t["_cron"].next_fire_time()) if t["_cron"].next_fire_time() else None
                results.append(result)
        return results

    def get_history(self, trigger_id: str = None, limit: int = 50) -> List[Dict]:
        records = self._fire_history
        if trigger_id:
            records = [r for r in records if r["trigger_id"] == trigger_id]
        return records[-limit:]

    def get_dead_letters(self, limit: int = 50) -> List[Dict]:
        return self._dead_letters[-limit:]

    def retry_dead_letter(self, index: int) -> Optional[Dict]:
        with self._lock:
            if 0 <= index < len(self._dead_letters):
                dl = self._dead_letters.pop(index)
                return self.fire(dl["trigger_id"], dl["payload"])
        return None

    def pause(self, trigger_id: str) -> bool:
        t = self._triggers.get(trigger_id)
        if t and t["state"] == "active":
            t["state"] = "paused"
            return True
        return False

    def resume(self, trigger_id: str) -> bool:
        t = self._triggers.get(trigger_id)
        if t and t["state"] == "paused":
            t["state"] = "active"
            return True
        return False

    def stats(self) -> Dict:
        triggers = list(self._triggers.values())
        return {
            "total_triggers": len(triggers),
            "active": sum(1 for t in triggers if t["state"] == "active"),
            "paused": sum(1 for t in triggers if t["state"] == "paused"),
            "error": sum(1 for t in triggers if t["state"] == "error"),
            "by_type": dict(
                defaultdict(int, {t["type"]: sum(1 for x in triggers if x["type"] == t["type"]) for t in triggers})
            ),
            "total_fires": sum(t["fire_count"] for t in triggers),
            "total_fails": sum(t["fail_count"] for t in triggers),
            "history_size": len(self._fire_history),
            "dead_letter_size": len(self._dead_letters),
        }

# ─── 主模块 ──────────────────────────────────────────────────

class TriggerEngine(EnterpriseModule):
    """企业级事件触发引擎
    核心能力：Cron调度、事件匹配、条件触发、链式编排、幂等去重、死信队列
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._scheduler = TriggerScheduler()
        self._condition_engine = ConditionEvaluator()
        self._event_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def _dispatch(self, action: str, params: Dict) -> Dict:
        handler = {
            "status": self._action_status,
            "stats": self._action_stats,
            "health": self._action_health,
            "configure": self._action_configure,
            "register_cron": self._action_register_cron,
            "register_event": self._action_register_event,
            "register_condition": self._action_register_condition,
            "list_triggers": self._action_list_triggers,
            "get_trigger": self._action_get_trigger,
            "remove_trigger": self._action_remove_trigger,
            "pause_trigger": self._action_pause,
            "resume_trigger": self._action_resume,
            "fire": self._action_fire,
            "emit_event": self._action_emit_event,
            "check_cron": self._action_check_cron,
            "evaluate_condition": self._action_eval_condition,
            "history": self._action_history,
            "dead_letters": self._action_dead_letters,
            "retry_dead_letter": self._action_retry_dl,
            "reset": self._action_reset,
        }.get(action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                self.trace("dispatch_error", {"action": action, "error": str(e)})
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    async def execute(self, action: str = "status", params: Dict = None) -> Dict:
        params = params or {}
        self.trace("execute", {"action": action})
        self.metrics_collector.counter("trigger_execute_total", labels={"action": action}).inc()
        return self._dispatch(action, params)

    # ── 基础Action ──

    def _action_status(self, params: Dict) -> Dict:
        return {
            "success": True,
            "data": {
                "module": "TriggerEngine",
                "state": "active",
                "triggers": self._scheduler.stats()["total_triggers"],
            },
        }

    def _action_stats(self, params: Dict) -> Dict:
        s = self._scheduler.stats()
        s["event_counts"] = dict(self._event_counts)
        return {"success": True, "data": s}

    def _action_health(self, params: Dict) -> Dict:
        s = self._scheduler.stats()
        issues = []
        if s["error"] > 0:
            issues.append(f"{s['error']} triggers in error state")
        if s["dead_letter_size"] > 10:
            issues.append(f"{s['dead_letter_size']} dead letters pending")
        return {
            "success": True,
            "data": {"status": "healthy" if not issues else "degraded", "issues": issues, "stats": s},
        }

    def _action_configure(self, params: Dict) -> Dict:
        dedup_ttl = params.get("dedup_ttl")
        if dedup_ttl is not None:
            self._scheduler._dedup_ttl = float(dedup_ttl)
        max_history = params.get("max_history")
        if max_history is not None:
            self._scheduler._max_history = int(max_history)
        return {
            "success": True,
            "data": {"dedup_ttl": self._scheduler._dedup_ttl, "max_history": self._scheduler._max_history},
        }

    # ── 注册 ──

    def _action_register_cron(self, params: Dict) -> Dict:
        tid = params.get("trigger_id", str(uuid.uuid4())[:8])
        expression = params.get("expression", "0 * * * *")
        config = {
            "expression": expression,
            "callback": params.get("callback"),
            "chain": params.get("chain", []),
            "tags": params.get("tags", []),
            "description": params.get("description", ""),
        }
        result = self._scheduler.register(tid, "cron", config)
        if result.get("state") == "error":
            return {"success": False, "error": result.get("error", "Invalid cron expression")}
        return {"success": True, "data": {"trigger_id": tid, "type": "cron", "expression": expression}}

    def _action_register_event(self, params: Dict) -> Dict:
        tid = params.get("trigger_id", str(uuid.uuid4())[:8])
        config = {
            "event_types": params.get("event_types", ["*"]),
            "condition": params.get("condition", {}),
            "callback": params.get("callback"),
            "chain": params.get("chain", []),
            "tags": params.get("tags", []),
            "description": params.get("description", ""),
        }
        self._scheduler.register(tid, "event", config)
        return {"success": True, "data": {"trigger_id": tid, "type": "event", "event_types": config["event_types"]}}

    def _action_register_condition(self, params: Dict) -> Dict:
        tid = params.get("trigger_id", str(uuid.uuid4())[:8])
        config = {
            "condition": params.get("condition", {}),
            "callback": params.get("callback"),
            "chain": params.get("chain", []),
            "tags": params.get("tags", []),
            "description": params.get("description", ""),
        }
        self._scheduler.register(tid, "condition", config)
        return {"success": True, "data": {"trigger_id": tid, "type": "condition"}}

    # ── 查询 ──

    def _action_list_triggers(self, params: Dict) -> Dict:
        triggers = self._scheduler.list_triggers(
            state_filter=params.get("state"),
            tag=params.get("tag"),
        )
        return {"success": True, "data": {"triggers": triggers, "total": len(triggers)}}

    def _action_get_trigger(self, params: Dict) -> Dict:
        t = self._scheduler.get_trigger(params.get("trigger_id", ""))
        if not t:
            return {"success": False, "error": "Trigger not found"}
        return {"success": True, "data": {k: v for k, v in t.items() if not k.startswith("_")}}

    def _action_remove_trigger(self, params: Dict) -> Dict:
        ok = self._scheduler.unregister(params.get("trigger_id", ""))
        return {"success": ok, "data": {"removed": ok}}

    def _action_pause(self, params: Dict) -> Dict:
        ok = self._scheduler.pause(params.get("trigger_id", ""))
        return {"success": ok}

    def _action_resume(self, params: Dict) -> Dict:
        ok = self._scheduler.resume(params.get("trigger_id", ""))
        return {"success": ok}

    # ── 执行 ──

    def _action_fire(self, params: Dict) -> Dict:
        return self._scheduler.fire(
            params.get("trigger_id", ""),
            payload=params.get("payload"),
            dedup=params.get("dedup", True),
        )

    def _action_emit_event(self, params: Dict) -> Dict:
        event_type = params.get("event_type", "custom")
        payload = params.get("payload", {})
        with self._lock:
            self._event_counts[event_type] += 1
        matched = self._scheduler.match_event(event_type, payload)
        return {
            "success": True,
            "data": {"event_type": event_type, "matched_triggers": len(matched), "details": matched},
        }

    def _action_check_cron(self, params: Dict) -> Dict:
        fired = self._scheduler.check_cron_triggers()
        return {
            "success": True,
            "data": {"checked_at": datetime.now().isoformat(), "fired_count": len(fired), "details": fired},
        }

    def _action_eval_condition(self, params: Dict) -> Dict:
        condition = params.get("condition", {})
        context = params.get("context", {})
        result = self._condition_engine.evaluate(condition, context)
        fields = self._condition_engine.extract_fields(condition)
        return {"success": True, "data": {"result": result, "fields_referenced": fields}}

    # ── 历史/死信 ──

    def _action_history(self, params: Dict) -> Dict:
        history = self._scheduler.get_history(
            trigger_id=params.get("trigger_id"),
            limit=params.get("limit", 50),
        )
        return {"success": True, "data": {"history": history, "total": len(history)}}

    def _action_dead_letters(self, params: Dict) -> Dict:
        dls = self._scheduler.get_dead_letters(params.get("limit", 50))
        return {"success": True, "data": {"dead_letters": dls, "total": len(dls)}}

    def _action_retry_dl(self, params: Dict) -> Dict:
        result = self._scheduler.retry_dead_letter(params.get("index", 0))
        return {"success": result is not None, "data": {"result": result}}

    def _action_reset(self, params: Dict) -> Dict:
        self._scheduler._fire_history.clear()
        self._scheduler._dead_letters.clear()
        self._scheduler._dedup_cache.clear()
        self._event_counts.clear()
        return {"success": True, "data": {"message": "History, dead letters, and dedup cache cleared"}}

module_class = TriggerEngine
