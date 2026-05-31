"""
AUTO-EVO-AI V0.1 — Minerva AI智能体
Grade: A (生产级) | Category: AI智能体
职责：智能决策、规则引擎、策略评估、AB测试、推荐引擎
"""

__module_meta__ = {
        "id": "agent-minerva",
        "name": "Agent Minerva",
        "version": "V0.1",
        "group": "agent",
        "inputs": [
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "fn",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "context",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "strategy",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "evidence",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "decision_id",
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
                    "on": "agent_minerva.task.request"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "engine",
            "manager",
            "multi-agent",
            "agent"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — Minerva AI智能体 Grade: A (生产级) | Category: AI智能体"
    }

import os
import asyncio
import time
import logging
import hashlib

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from modules._base.enterprise_module import CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("agent_minerva")

class DecisionType(Enum):
    RULE = "rule"
    ML = "ml"
    HYBRID = "hybrid"
    MANUAL = "manual"

class DecisionOutcome(Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    DEFERRED = "deferred"

@dataclass
class DecisionRule:
    """决策规则"""

    rule_id: str
    name: str
    condition: str
    action: str
    priority: int = 0
    enabled: bool = True
    hit_count: int = 0

@dataclass
class Decision:
    """决策记录"""

    decision_id: str
    context: Dict[str, Any]
    rules_matched: List[str]
    outcome: DecisionOutcome
    confidence: float
    reason: str = ""
    decided_at: float = field(default_factory=time.time)

class ReasoningEngine(object):
    """Minerva推理引擎 - 多策略决策推理、置信度评估、决策回溯"""

    def __init__(self):
        self._strategies: Dict[str, callable] = {}
        self._reasoning_log: List[Dict] = []

    def register_strategy(self, name: str, fn: callable) -> None:
        self._strategies[name] = fn

    def reason(self, context: Dict, strategy: str = "default") -> Dict:
        """执行推理"""
        fn = self._strategies.get(strategy)
        result = fn(context) if fn else {"conclusion": "no_strategy", "confidence": 0.0}
        self._reasoning_log.append(
            {"strategy": strategy, "context_keys": list(context.keys()), "confidence": result.get("confidence", 0)}
        )
        return result

    def evaluate_confidence(self, evidence: List[Dict]) -> float:
        """基于证据评估决策置信度"""
        if not evidence:
            return 0.0
        weights = [e.get("weight", 0.5) for e in evidence]
        scores = [e.get("score", 0) for e in evidence]
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0
        return round(sum(w * s for w, s in zip(weights, scores)) / total_weight, 3)

    def backtrack(self, decision_id: str, max_depth: int = 10) -> List[Dict]:
        """决策回溯"""
        related = [entry for entry in self._reasoning_log if entry.get("decision_id") == decision_id]
        return related[-max_depth:]

    def get_stats(self) -> Dict:
        return {
            "strategies": len(self._strategies),
            "reasoning_count": len(self._reasoning_log),
            "avg_confidence": round(
                sum(e.get("confidence", 0) for e in self._reasoning_log) / max(len(self._reasoning_log), 1), 3
            ),
        }

class AgentMinervaManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Minerva智能体 - 智能决策引擎"""

    MODULE_ID = "agent_minerva"
    MODULE_NAME = "Minerva智能体"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._rules: Dict[str, DecisionRule] = {}
        self._decisions: List[Decision] = []
        self._rule_counter: int = 0
        self._dec_counter: int = 0

    def initialize(self) -> None:
        try:
            pass
            # super().initialize() removed for sync compatibility
            # 默认规则
            defaults = [
                ("高负载告警", "cpu_usage>90", "escalate", 10),
                ("内存压力", "memory_usage>85", "alert", 8),
                ("请求异常", "error_rate>5", "reject", 9),
                ("正常通过", "cpu_usage<70 AND error_rate<1", "approve", 1),
            ]
            for name, cond, action, priority in defaults:
                self._rule_counter += 1
                rule = DecisionRule(
                    rule_id=f"rule_{self._rule_counter}", name=name, condition=cond, action=action, priority=priority
                )
                self._rules[rule.rule_id] = rule
            if self._audit:
                self._audit.log("minerva_initialized", {"rules": len(self._rules)})
            self.stats.success_count += 1
            logger.info("Minerva智能体初始化完成")
        except Exception as e:
            logger.error(f"Minerva初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("agent_minerva_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "decide":
                context = params.get("context", {})
                if not context:
                    return {"success": False, "error": "Missing: context"}
                result = self._decide(context)
                ok = True
                return {"success": True, "result": result}

            elif action == "add_rule":
                name = params.get("name", "")
                condition = params.get("condition", "")
                action_val = params.get("action", "alert")
                priority = params.get("priority", 5)
                if not name or not condition:
                    return {"success": False, "error": "Missing: name, condition"}
                self._rule_counter += 1
                rule = DecisionRule(
                    rule_id=f"rule_{self._rule_counter}",
                    name=name,
                    condition=condition,
                    action=action_val,
                    priority=priority,
                )
                self._rules[rule.rule_id] = rule
                ok = True
                return {"success": True, "result": {"rule_id": rule.rule_id, "name": name}}

            elif action == "toggle_rule":
                rule_id = params.get("rule_id", "")
                enabled = params.get("enabled", True)
                rule = self._rules.get(rule_id)
                if not rule:
                    return {"success": False, "error": "Rule not found"}
                rule.enabled = enabled
                return {"success": True, "result": {"rule_id": rule_id, "enabled": enabled}}

            elif action == "list_rules":
                return {
                    "success": True,
                    "result": [
                        {
                            "rule_id": r.rule_id,
                            "name": r.name,
                            "condition": r.condition,
                            "action": r.action,
                            "priority": r.priority,
                            "enabled": r.enabled,
                            "hit_count": r.hit_count,
                        }
                        for r in sorted(self._rules.values(), key=lambda x: -x.priority)
                    ],
                }

            elif action == "evaluate_strategy":
                metric = params.get("metric", "accuracy")
                decisions_n = params.get("decisions", 100)
                # 模拟策略评估
                approved = sum(1 for d in self._decisions[-decisions_n:] if d.outcome == DecisionOutcome.APPROVED)
                total = min(len(self._decisions), decisions_n)
                accuracy = approved / max(total, 1)
                ok = True
                return {
                    "success": True,
                    "result": {
                        "metric": metric,
                        "sample_size": total,
                        "value": round(accuracy, 3),
                        "approved": approved,
                    },
                }

            elif action == "get_stats":
                outcome_counts = {}
                for d in self._decisions:
                    o = d.outcome.value
                    outcome_counts[o] = outcome_counts.get(o, 0) + 1
                return {
                    "success": True,
                    "result": {
                        "total_decisions": len(self._decisions),
                        "rules": len(self._rules),
                        "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
                        "outcomes": outcome_counts,
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "rules": len(self._rules),
            "decisions": len(self._decisions),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
        }

    def shutdown(self) -> None:
        pass  # super().shutdown() removed for sync compatibility

    def _decide(self, context: Dict[str, Any]) -> Dict:
        """执行决策"""
        matched_rules = []
        action = "approve"
        confidence = 0.5
        reason = ""

        for rule in sorted(self._rules.values(), key=lambda x: -x.priority):
            if not rule.enabled:
                continue
            if self._evaluate_condition(rule.condition, context):
                matched_rules.append(rule.rule_id)
                rule.hit_count += 1
                action = rule.action
                confidence = min(0.95, confidence + rule.priority * 0.05)
                reason = f"Rule '{rule.name}' matched: {rule.condition}"

        outcome_map = {
            "approve": DecisionOutcome.APPROVED,
            "reject": DecisionOutcome.REJECTED,
            "escalate": DecisionOutcome.ESCALATED,
            "alert": DecisionOutcome.ESCALATED,
        }
        outcome = outcome_map.get(action, DecisionOutcome.DEFERRED)

        self._dec_counter += 1
        decision = Decision(
            decision_id=f"dec_{self._dec_counter}",
            context=context,
            rules_matched=matched_rules,
            outcome=outcome,
            confidence=round(confidence, 3),
            reason=reason,
        )
        self._decisions.append(decision)
        if len(self._decisions) > 5000:
            self._decisions = self._decisions[-3000:]

        if self._audit:
            self._audit.log(
                "decision_made",
                {"decision_id": decision.decision_id, "outcome": outcome.value, "rules_matched": len(matched_rules)},
            )
        self.stats.success_count += 1
        return {
            "decision_id": decision.decision_id,
            "outcome": outcome.value,
            "confidence": confidence,
            "rules_matched": matched_rules,
            "reason": reason,
        }

    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """评估规则条件（简化实现）"""
        parts = condition.split(" AND ")
        for part in parts:
            part = part.strip()
            if ">" in part:
                field_name, threshold = part.split(">", 1)
                field_name = field_name.strip()
                try:
                    threshold = float(threshold.strip())
                except ValueError:
                    continue
                value = context.get(field_name)
                if value is None:
                    return False
                try:
                    if float(value) <= threshold:
                        return False
                except (ValueError, TypeError):
                    return False
            elif "<" in part:
                field_name, threshold = part.split("<", 1)
                field_name = field_name.strip()
                try:
                    threshold = float(threshold.strip())
                except ValueError:
                    continue
                value = context.get(field_name)
                if value is None:
                    return False
                try:
                    if float(value) >= threshold:
                        return False
                except (ValueError, TypeError):
                    return False
        return True

    def _batch_evaluate(self, decisions: List[Dict]) -> List[Dict]:
        """批量评估决策"""
        results = []
        for d in decisions:
            r = self._evaluate_rule(d.get("context", {}), d.get("rules", []))
            results.append({"decision_id": d.get("id", ""), "result": r})
        return results

    def _get_rule_stats(self) -> Dict:
        """规则使用统计"""
        stats = {}
        for rule in self._rules:
            stats[rule.rule_id] = {"name": rule.name, "priority": rule.priority, "enabled": rule.enabled}
        return {"total_rules": len(self._rules), "enabled": sum(1 for r in self._rules if r.enabled), "rules": stats}

    def _export_rules(self, format: str = "json") -> Dict:
        """导出规则"""
        exported = [
            {
                "id": r.rule_id,
                "name": r.name,
                "priority": r.priority,
                "condition": r.condition,
                "action": r.action,
                "enabled": r.enabled,
            }
            for r in self._rules
        ]
        return {"format": format, "count": len(exported), "rules": exported}

    def _import_rules(self, rules_data: List[Dict]) -> Dict:
        """导入规则"""
        imported, skipped = 0, 0
        for rd in rules_data:
            rule_id = rd.get("id", f"imported_{imported}")
            if any(r.rule_id == rule_id for r in self._rules):
                skipped += 1
                continue
            rule = DecisionRule(
                rule_id=rule_id,
                name=rd.get("name", ""),
                priority=rd.get("priority", 5),
                condition=rd.get("condition", ""),
                action=rd.get("action", ""),
                enabled=rd.get("enabled", True),
            )
            self._rules.append(rule)
            imported += 1
        if self._audit:
            self._audit.log("rules_imported", {"imported": imported, "skipped": skipped})
        return {"imported": imported, "skipped": skipped}

    def _find_conflicting_rules(self) -> List[Dict]:
        """找出冲突规则（同优先级+同条件）"""
        conflicts = []
        seen = {}
        for r in self._rules:
            key = (r.priority, r.condition)
            if key in seen:
                conflicts.append({"rule_a": seen[key], "rule_b": r.rule_id, "priority": r.priority})
            else:
                seen[key] = r.rule_id
        return conflicts

    def _get_decision_history(self, limit: int = 20) -> List[Dict]:
        """获取决策历史"""
        return self._decisions[-limit:] if hasattr(self, "_decisions") else []

    def _simulate_scenario(self, context: Dict, rules: List[Dict]) -> Dict:
        """模拟场景：给定上下文和规则，预测决策结果"""
        would_fire = []
        for rd in rules:
            cond = rd.get("condition", "")
            if cond and cond in str(context):
                would_fire.append(
                    {"rule_id": rd.get("id", ""), "action": rd.get("action", ""), "priority": rd.get("priority", 0)}
                )
        would_fire.sort(key=lambda x: x["priority"])
        return {
            "context_keys": list(context.keys()),
            "rules_evaluated": len(rules),
            "would_fire": would_fire,
            "predicted_action": would_fire[0]["action"] if would_fire else "no_match",
        }

    def _enable_rule(self, rule_id: str) -> Dict:
        """启用规则"""
        for r in self._rules:
            if r.rule_id == rule_id:
                r.enabled = True
                return {"enabled": True, "rule_id": rule_id}
        return {"error": "rule_not_found"}

    def _disable_rule(self, rule_id: str) -> Dict:
        """禁用规则"""
        for r in self._rules:
            if r.rule_id == rule_id:
                r.enabled = False
                return {"disabled": True, "rule_id": rule_id}
        return {"error": "rule_not_found"}

    def _delete_rule(self, rule_id: str) -> Dict:
        """删除规则"""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.rule_id != rule_id]
        removed = before - len(self._rules)
        if self._audit and removed:
            self._audit.log("rule_deleted", {"rule_id": rule_id})
        return {"deleted": removed > 0, "rule_id": rule_id}

    def _validate_rules_integrity(self) -> Dict:
        """验证规则完整性"""
        issues = []
        for r in self._rules:
            if not r.condition:
                issues.append({"rule_id": r.rule_id, "issue": "empty_condition"})
            if not r.action:
                issues.append({"rule_id": r.rule_id, "issue": "empty_action"})
            if r.priority < 1 or r.priority > 10:
                issues.append({"rule_id": r.rule_id, "issue": "invalid_priority", "value": r.priority})
        return {"valid": len(issues) == 0, "total_rules": len(self._rules), "issues": issues}

    def _get_rule_dependencies(self) -> Dict[str, List[str]]:
        """分析规则间依赖关系（通过action引用）"""
        deps: Dict[str, List[str]] = {}
        action_map = {r.action: r.rule_id for r in self._rules if r.action}
        for r in self._rules:
            referenced = []
            for action, rule_id in action_map.items():
                if action in r.condition and rule_id != r.rule_id:
                    referenced.append(rule_id)
            if referenced:
                deps[r.rule_id] = referenced
        return deps

    def _optimize_rule_order(self) -> List[str]:
        """优化规则执行顺序（拓扑排序）"""
        deps = self._get_rule_dependencies()
        in_degree: Dict[str, int] = {r.rule_id: 0 for r in self._rules}
        for targets in deps.values():
            for t in targets:
                if t in in_degree:
                    in_degree[t] += 1
        queue = [rid for rid, d in in_degree.items() if d == 0]
        order = []
        while queue:
            rid = queue.pop(0)
            order.append(rid)
            for targets in deps.values():
                if rid in targets:
                    for t in targets:
                        if t in in_degree:
                            in_degree[t] -= 1
                            if in_degree[t] == 0:
                                queue.append(t)
        return (
            order
            if len(order) == len(self._rules)
            else [r.rule_id for r in sorted(self._rules, key=lambda x: -x.priority)]
        )

    def _get_rules_by_priority(self, min_p: int = 1, max_p: int = 10) -> List[Dict]:
        """按优先级范围筛选规则"""
        return [
            {"id": r.rule_id, "name": r.name, "priority": r.priority, "enabled": r.enabled}
            for r in self._rules
            if min_p <= r.priority <= max_p
        ]

    def _bulk_toggle(self, rule_ids: List[str], enabled: bool) -> Dict:
        """批量启用/禁用规则"""
        toggled = 0
        for rid in rule_ids:
            for r in self._rules:
                if r.rule_id == rid:
                    r.enabled = enabled
                    toggled += 1
                    break
        if self._audit:
            self._audit.log("bulk_toggle", {"enabled": enabled, "toggled": toggled})
        return {"toggled": toggled, "target": len(rule_ids)}

    def _clone_rule(self, source_id: str, new_id: str) -> Dict:
        """克隆规则"""
        for r in self._rules:
            if r.rule_id == source_id:
                clone = DecisionRule(
                    rule_id=new_id,
                    name=f"{r.name}_clone",
                    priority=r.priority,
                    condition=r.condition,
                    action=r.action,
                    enabled=r.enabled,
                )
                self._rules.append(clone)
                return {"cloned": True, "new_id": new_id}
        return {"error": "source_not_found"}

    def generate_knowledge_insights(self, limit: int = 10) -> Dict[str, Any]:
        """生成知识洞察：按领域统计知识覆盖度、识别知识盲区"""
        knowledge = self._knowledge if hasattr(self, "_knowledge") else {}
        if not knowledge:
            return {"total_entries": 0}
        domain_stats: Dict[str, int] = {}
        source_stats: Dict[str, int] = {}
        freshness_days: List[float] = []
        for kid, entry in knowledge.items():
            domain = entry.get("domain", "general")
            source = entry.get("source", "unknown")
            domain_stats[domain] = domain_stats.get(domain, 0) + 1
            source_stats[source] = source_stats.get(source, 0) + 1
            created = entry.get("created_at", time.time())
            freshness_days.append((time.time() - created) / 86400)
        top_domains = sorted(domain_stats.items(), key=lambda x: -x[1])[:limit]
        avg_freshness = sum(freshness_days) / max(len(freshness_days), 1)
        stale_count = sum(1 for d in freshness_days if d > 30)
        return {
            "total_entries": len(knowledge),
            "unique_domains": len(domain_stats),
            "top_domains": top_domains,
            "unique_sources": len(source_stats),
            "avg_age_days": round(avg_freshness, 1),
            "stale_entries": stale_count,
            "stale_rate": round(stale_count / max(len(knowledge), 1), 3),
        }

module_class = AgentMinervaManager
