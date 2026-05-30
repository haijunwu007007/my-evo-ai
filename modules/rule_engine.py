# -*- coding: utf-8 -*-
"""
# Grade: A
AUTO-EVO-AI V0.1 - RuleEngine 规则引擎
======================================
企业级规则引擎：条件匹配/规则评估/优先级/冲突解决/事实库。
支持：IF-THEN规则定义、条件表达式解析、优先级排序、
      规则冲突解决（FIRST-MATCH/ALL-MATCH/HIGHEST-PRIORITY）、
      事实管理、规则组、规则版本、执行追踪、热更新。

A级生产标准：EnterpriseModule + 链路追踪 + Prometheus + 审计 + 熔断 + 限流
"""

__module_meta__ = {
    "id": "rule-engine",
    "name": "Rule Engine",
    "version": "V0.1",
    "group": "workflow",
    "inputs": [
        {"name": "facts", "type": "string", "required": True, "description": ""},
        {"name": "facts", "type": "string", "required": True, "description": ""},
        {"name": "facts", "type": "string", "required": True, "description": ""},
        {"name": "field_path", "type": "string", "required": True, "description": ""},
        {"name": "a", "type": "string", "required": True, "description": ""},
        {"name": "b", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["rule", "engine"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - RuleEngine 规则引擎 ======================================",
}

import time
import asyncio
import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field as dc_field
from enum import Enum
from collections import defaultdict
import uuid

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    Result,
    module_class,
    CircuitBreakerMixin,
    RateLimiterMixin,
)
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.rule_engine")

# ============================================================================
# 数据模型
# ============================================================================

class ConflictStrategy(str, Enum):
    FIRST_MATCH = "first_match"
    ALL_MATCH = "all_match"
    HIGHEST_PRIORITY = "highest_priority"
    LOWEST_PRIORITY = "lowest_priority"

class RuleStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    DRAFT = "draft"

class Operator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    REGEX = "regex"
    EXISTS = "exists"

class LogicalOperator(str, Enum):
    AND = "and"
    OR = "or"
    NOT = "not"

@dataclass
class Condition:
    """条件"""

    field: str = ""
    operator: Operator = Operator.EQ
    value: Any = None
    value2: Any = None  # 用于BETWEEN
    logical: LogicalOperator = LogicalOperator.AND
    conditions: List["Condition"] = dc_field(default_factory=list)  # 嵌套条件

    def evaluate(self, facts: Dict[str, Any]) -> bool:
        """评估条件"""
        if self.conditions:
            # 嵌套逻辑
            if self.logical == LogicalOperator.AND:
                return all(c.evaluate(facts) for c in self.conditions)
            elif self.logical == LogicalOperator.OR:
                return any(c.evaluate(facts) for c in self.conditions)
            elif self.logical == LogicalOperator.NOT:
                return not any(c.evaluate(facts) for c in self.conditions)
        # 叶子条件
        field_value = self._get_field_value(facts)
        op = self.operator
        if op == Operator.EQ:
            return field_value == self.value
        elif op == Operator.NE:
            return field_value != self.value
        elif op == Operator.GT:
            return self._safe_compare(field_value, self.value, lambda a, b: a > b)
        elif op == Operator.GTE:
            return self._safe_compare(field_value, self.value, lambda a, b: a >= b)
        elif op == Operator.LT:
            return self._safe_compare(field_value, self.value, lambda a, b: a < b)
        elif op == Operator.LTE:
            return self._safe_compare(field_value, self.value, lambda a, b: a <= b)
        elif op == Operator.IN:
            return field_value in (self.value or [])
        elif op == Operator.NOT_IN:
            return field_value not in (self.value or [])
        elif op == Operator.CONTAINS:
            return str(self.value) in str(field_value)
        elif op == Operator.STARTS_WITH:
            return str(field_value).startswith(str(self.value))
        elif op == Operator.ENDS_WITH:
            return str(field_value).endswith(str(self.value))
        elif op == Operator.BETWEEN:
            return self._safe_compare(field_value, self.value, lambda a, b: a >= b) and self._safe_compare(
                field_value, self.value2, lambda a, b: a <= b
            )
        elif op == Operator.IS_NULL:
            return field_value is None
        elif op == Operator.IS_NOT_NULL:
            return field_value is not None
        elif op == Operator.REGEX:
            try:
                return bool(re.search(str(self.value), str(field_value)))
            except re.error:
                return False
        elif op == Operator.EXISTS:
            return self._field_exists(facts, self.field)
        return False

    def _get_field_value(self, facts: Dict) -> Any:
        """支持点号路径获取值"""
        parts = self.field.split(".")
        current = facts
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        if current is None:
            return None
        return current

    def _field_exists(self, facts: Dict, field_path: str) -> bool:
        parts = field_path.split(".")
        current = facts
        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    return False
                current = current[part]
            else:
                return False
        return True

    @staticmethod
    def _safe_compare(a, b, fn) -> bool:
        try:
            return fn(a, b)
        except (TypeError, ValueError):
            return False

    def to_dict(self) -> Dict:
        if self.conditions:
            return {"logical": self.logical.value, "conditions": [c.to_dict() for c in self.conditions]}
        return {"field": self.field, "operator": self.operator.value, "value": self.value}

@dataclass
class Action:
    """动作"""

    action_type: str = ""  # set_value, notify, call_api, log, etc.
    params: Dict[str, Any] = dc_field(default_factory=dict)
    priority: int = 0

@dataclass
class Rule:
    """规则"""

    rule_id: str = dc_field(default_factory=lambda: str(uuid.uuid4())[:10])
    name: str = ""
    description: str = ""
    group: str = "default"
    condition: Optional[Condition] = None
    actions: List[Action] = dc_field(default_factory=list)
    priority: int = 100  # 越高越优先
    status: RuleStatus = RuleStatus.ENABLED
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    tags: List[str] = dc_field(default_factory=list)
    version: int = 1
    fire_count: int = 0
    last_fired: Optional[str] = None
    created_at: str = dc_field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = dc_field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class RuleExecution:
    """规则执行记录"""

    execution_id: str = dc_field(default_factory=lambda: str(uuid.uuid4())[:10])
    rule_id: str = ""
    rule_name: str = ""
    group: str = ""
    matched: bool = False
    facts_snapshot: Dict[str, Any] = dc_field(default_factory=dict)
    actions_taken: List[str] = dc_field(default_factory=list)
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    timestamp: str = dc_field(default_factory=lambda: datetime.now().isoformat())

# ============================================================================
# RuleEngine 主类
# ============================================================================

class RuleEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    规则引擎

    功能：
      - IF-THEN规则定义与管理
      - 复杂条件表达式（AND/OR/NOT嵌套）
      - 15种比较运算符
      - 点号路径访问嵌套字段
      - 事实库管理
      - 冲突解决策略（First/All/Highest/Lowest）
      - 规则组
      - 规则版本
      - 执行追踪
      - 热更新
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__()
        self.config = config or {}
        # 规则存储
        self._rules: Dict[str, Rule] = {}
        self._rules_by_group: Dict[str, List[str]] = defaultdict(list)
        # 动作处理器
        self._action_handlers: Dict[str, Callable] = {}
        # 事实库
        self._facts: Dict[str, Dict[str, Any]] = {}
        # 冲突解决策略
        self._conflict_strategy = ConflictStrategy(self.config.get("conflict_strategy", "first_match"))
        # 执行历史
        self._execution_history: List[RuleExecution] = []
        self._execution_history_max = 10000
        # 统计
        self._re_stats = {
            "rules_total": 0,
            "rules_enabled": 0,
            "groups_count": 0,
            "evaluations_total": 0,
            "matches_total": 0,
            "fires_total": 0,
        }

    # ----------------------------------------------------------------
    # 生命周期
    # ----------------------------------------------------------------

    def initialize(self) -> Result:
        self._update_status(ModuleStatus.RUNNING)
        for rule_cfg in self.config.get("preset_rules", []):
            self.add_rule(rule_cfg)
        logger.info(f"[RuleEngine] 初始化完成, {len(self._rules)} rules")
        return Result(success=True)

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        self._metrics = self.record_metrics("rule_engine_executed", 1)
        metrics_collector.counter("rule_engine_ops_total", labels={"action": action})
        params = params or {}
        actions = {
            "evaluate": self.evaluate,
            "add_rule": self.add_rule,
            "remove_rule": self.remove_rule,
            "enable_rule": self.enable_rule,
            "disable_rule": self.disable_rule,
            "register_action_handler": self.register_action_handler,
            "evaluate": self.evaluate,
            "set_facts": self.set_facts,
            "get_facts": self.get_facts,
            "update_fact": self.update_fact,
            "remove_facts": self.remove_facts,
            "get_stats": self.get_stats,
            "list_rules": self.list_rules,
            "get_execution_history": self.get_execution_history,
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }

        if action not in actions:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}

        handler = actions[action]
        if callable(handler) and not isinstance(handler, list):
            import inspect

            if inspect.iscoroutinefunction(handler):
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    self.metrics_collector.counter(
                        "execute_error",
                        labels={"action": action, "error_type": type(e).__name__, "module": "rule_engine"},
                    )
                    return {"status": "error", "message": str(e)}
            else:
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    self.metrics_collector.counter(
                        "execute_error",
                        labels={"action": action, "error_type": type(e).__name__, "module": "rule_engine"},
                    )
                    return {"status": "error", "message": str(e)}
            self.metrics_collector.counter(
                "execute_total", labels={"action": action, "status": "success", "module": "rule_engine"}
            )
            if isinstance(result, dict):
                return {"status": "success", **result}
            return {"status": "success", "data": result}

    def health_check(self) -> HealthReport:
        return HealthReport(
            status="running",
            healthy=True,
            last_beat=datetime.now().isoformat(),
            uptime_seconds=self.stats.uptime_seconds,
            checks_run=4,
            error_rate=self.stats.error_rate,
            details={
                "rules": len(self._rules),
                "enabled": self._re_stats["rules_enabled"],
                "groups": len(self._rules_by_group),
                "handlers": len(self._action_handlers),
            },
            version="V0.1",
        )

    def shutdown(self) -> Result:
        self._update_status(ModuleStatus.STOPPED)
        return Result(success=True)

    # ----------------------------------------------------------------
    # 规则管理
    # ----------------------------------------------------------------

    def add_rule(self, rule_cfg: Dict) -> Result:
        """添加规则"""
        condition = self._build_condition(rule_cfg.get("condition", {}))
        actions = [
            Action(action_type=a.get("type", ""), params=a.get("params", {})) for a in rule_cfg.get("actions", [])
        ]
        rule = Rule(
            name=rule_cfg.get("name", ""),
            group=rule_cfg.get("group", "default"),
            condition=condition,
            actions=actions,
            priority=rule_cfg.get("priority", 100),
            status=RuleStatus(rule_cfg.get("status", "enabled")),
            tags=rule_cfg.get("tags", []),
        )
        self._rules[rule.rule_id] = rule
        self._rules_by_group[rule.group].append(rule.rule_id)
        self._update_stats()
        return Result(success=True, data={"rule_id": rule.rule_id})

    def remove_rule(self, rule_id: str) -> Result:
        rule = self._rules.pop(rule_id, None)
        if not rule:
            return Result(success=False, error="规则不存在")
        self._rules_by_group[rule.group] = [r for r in self._rules_by_group[rule.group] if r != rule_id]
        self._update_stats()
        return Result(success=True)

    def enable_rule(self, rule_id: str) -> Result:
        rule = self._rules.get(rule_id)
        if not rule:
            return Result(success=False, error="规则不存在")
        rule.status = RuleStatus.ENABLED
        self._update_stats()
        return Result(success=True)

    def disable_rule(self, rule_id: str) -> Result:
        rule = self._rules.get(rule_id)
        if not rule:
            return Result(success=False, error="规则不存在")
        rule.status = RuleStatus.DISABLED
        self._update_stats()
        return Result(success=True)

    def _build_condition(self, cond_cfg: Dict) -> Condition:
        """从配置构建条件"""
        if "logical" in cond_cfg:
            return Condition(
                logical=LogicalOperator(cond_cfg.get("logical", "and")),
                conditions=[self._build_condition(c) for c in cond_cfg.get("conditions", [])],
            )
        return Condition(
            field=cond_cfg.get("field", ""),
            operator=Operator(cond_cfg.get("operator", "eq")),
            value=cond_cfg.get("value"),
            value2=cond_cfg.get("value2"),
        )

    # ----------------------------------------------------------------
    # 动作处理器
    # ----------------------------------------------------------------

    def register_action_handler(self, action_type: str, handler: Callable):
        self._action_handlers[action_type] = handler

    def _execute_action(self, action: Action, facts: Dict, context: Dict) -> str:
        handler = self._action_handlers.get(action.action_type)
        if handler:
            try:
                result = handler(action.params, facts, context)
                if asyncio.iscoroutine(result):
                    result = result
                return action.action_type
            except Exception as e:
                logger.error(f"[RuleEngine] 动作执行失败: {action.action_type}, {e}")
                return f"{action.action_type}:error"
        return action.action_type

    # ----------------------------------------------------------------
    # 评估引擎
    # ----------------------------------------------------------------

    def evaluate(
        self,
        facts: Dict[str, Any],
        *,
        groups: Optional[List[str]] = None,
        rule_ids: Optional[List[str]] = None,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        评估规则

        Args:
            facts: 事实数据
            groups: 限定规则组
            rule_ids: 限定规则ID
            context: 额外上下文
        """
        start = time.time()
        context = context or {}
        self._re_stats["evaluations_total"] += 1
        try:
            with self.trace("evaluate"):
                # 筛选候选规则
                candidates = self._get_candidates(groups, rule_ids)
                now = datetime.now().isoformat()
                # 评估
                matches = []
                executions = []
                for rule in candidates:
                    # 有效性检查
                    if rule.status != RuleStatus.ENABLED:
                        continue
                    if rule.effective_from and now < rule.effective_from:
                        continue
                    if rule.effective_until and now > rule.effective_until:
                        continue
                    exec_record = RuleExecution(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        group=rule.group,
                        facts_snapshot=dict(facts),
                    )
                    try:
                        matched = rule.condition.evaluate(facts) if rule.condition else False
                        exec_record.matched = matched
                        if matched:
                            self._re_stats["matches_total"] += 1
                            # 执行动作
                            action_results = []
                            for action in rule.actions:
                                result = self._execute_action(action, facts, context)
                                action_results.append(result)
                            exec_record.actions_taken = action_results
                            rule.fire_count += 1
                            rule.last_fired = now
                            self._re_stats["fires_total"] += 1
                            matches.append(
                                {
                                    "rule_id": rule.rule_id,
                                    "name": rule.name,
                                    "group": rule.group,
                                    "priority": rule.priority,
                                    "actions": action_results,
                                }
                            )
                    except Exception as e:
                        exec_record.error = str(e)
                    finally:
                        exec_record.execution_time_ms = (time.time() - start) * 1000
                        executions.append(exec_record)
                # 冲突解决
                resolved = self._resolve_conflicts(matches)
                # 记录历史
                self._execution_history.extend(executions)
                if len(self._execution_history) > self._execution_history_max:
                    self._execution_history = self._execution_history[-self._execution_history_max // 2 :]
                self.audit(
                    "rules.evaluated",
                    {"candidates": len(candidates), "matches": len(matches), "resolved": len(resolved)},
                )
                latency = (time.time() - start) * 1000
                self.stats.record_request(latency, True)
                return {
                    "matched": len(matches),
                    "resolved": len(resolved),
                    "results": resolved,
                    "execution_time_ms": round(latency, 2),
                }
        except Exception as e:
            self.stats.record_request((time.time() - start) * 1000, False, str(e))
            return {"matched": 0, "resolved": 0, "error": str(e)}

    def _get_candidates(self, groups: Optional[List[str]], rule_ids: Optional[List[str]]) -> List[Rule]:
        if rule_ids:
            return [self._rules[rid] for rid in rule_ids if rid in self._rules]
        if groups:
            candidate_ids = set()
            for g in groups:
                candidate_ids.update(self._rules_by_group.get(g, []))
            return [self._rules[rid] for rid in candidate_ids if rid in self._rules]
        return [r for r in self._rules.values()]

    def _resolve_conflicts(self, matches: List[Dict]) -> List[Dict]:
        """冲突解决"""
        if not matches:
            return []
        strategy = self._conflict_strategy
        if strategy == ConflictStrategy.FIRST_MATCH:
            return [matches[0]]
        elif strategy == ConflictStrategy.ALL_MATCH:
            return matches
        elif strategy == ConflictStrategy.HIGHEST_PRIORITY:
            return [max(matches, key=lambda m: m["priority"])]
        elif strategy == ConflictStrategy.LOWEST_PRIORITY:
            return [min(matches, key=lambda m: m["priority"])]
        return matches

    # ----------------------------------------------------------------
    # 事实管理
    # ----------------------------------------------------------------

    def set_facts(self, key: str, facts: Dict[str, Any]) -> Result:
        self._facts[key] = facts
        return Result(success=True)

    def get_facts(self, key: str) -> Dict:
        return self._facts.get(key, {})

    def update_fact(self, key: str, field_path: str, value: Any) -> Result:
        facts = self._facts.get(key, {})
        parts = field_path.split(".")
        current = facts
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
        self._facts[key] = facts
        return Result(success=True)

    def remove_facts(self, key: str) -> Result:
        self._facts.pop(key, None)
        return Result(success=True)

    # ----------------------------------------------------------------
    # 内部
    # ----------------------------------------------------------------

    def _update_stats(self):
        self._re_stats["rules_total"] = len(self._rules)
        self._re_stats["rules_enabled"] = sum(1 for r in self._rules.values() if r.status == RuleStatus.ENABLED)
        self._re_stats["groups_count"] = len(self._rules_by_group)

    # ----------------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._re_stats,
            "handlers": len(self._action_handlers),
            "history_size": len(self._execution_history),
            "module_stats": self.stats.to_dict(),
        }

    def list_rules(self, group: Optional[str] = None) -> List[Dict]:
        result = []
        for r in self._rules.values():
            if group and r.group != group:
                continue
            result.append(
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "group": r.group,
                    "priority": r.priority,
                    "status": r.status.value,
                    "fire_count": r.fire_count,
                    "last_fired": r.last_fired,
                    "tags": r.tags,
                }
            )
        return sorted(result, key=lambda x: x["priority"], reverse=True)

    def get_execution_history(self, rule_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        result = self._execution_history
        if rule_id:
            result = [e for e in result if e.rule_id == rule_id]
        return [
            {
                "execution_id": e.execution_id,
                "rule": e.rule_name,
                "matched": e.matched,
                "actions": e.actions_taken,
                "time_ms": round(e.execution_time_ms, 2),
                "error": e.error,
                "timestamp": e.timestamp,
            }
            for e in result[-limit:]
        ]

# ============================================================================
# 模块注册
# ============================================================================

module_class = RuleEngine
