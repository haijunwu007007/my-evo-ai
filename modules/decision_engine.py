"""Production-grade 决策引擎模块 V0.1
上市公司生产级实现 - 规则引擎/决策树/评分模型/A/B测试/决策审计
"""

__module_meta__ = {
    "id": "decision-engine",
    "name": "Decision Engine",
    "version": "1.0.0",
    "group": "workflow",
    "inputs": [
        {"name": "rule", "type": "string", "required": True, "description": ""},
        {"name": "rule_id", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "conditions", "type": "string", "required": True, "description": ""},
        {"name": "actions", "type": "string", "required": True, "description": ""},
        {"name": "conditions", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["engine", "decision"],
    "grade": "A",
    "description": "Production-grade 决策引擎模块 V0.1 上市公司生产级实现 - 规则引擎/决策树/评分模型/A/B测试/决策审计",
}
import hashlib
import logging
import math

import time
import uuid
from collections import defaultdict, deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("decision_engine")

class RuleEngine(object):
    """规则引擎 - 条件匹配与优先级执行"""

    def __init__(self):
        self._rules: Dict[str, Dict] = {}
        self._rule_groups: Dict[str, List[str]] = defaultdict(list)

    def add_rule(
        self,
        rule_id: str,
        name: str,
        conditions: List[Dict],
        actions: List[Dict],
        priority: int = 100,
        group: str = "default",
        enabled: bool = True,
    ):
        self._rules[rule_id] = {
            "name": name,
            "conditions": conditions,
            "actions": actions,
            "priority": priority,
            "group": group,
            "enabled": enabled,
            "hit_count": 0,
            "created_at": time.time(),
        }
        self._rule_groups[group].append(rule_id)

    def evaluate_conditions(self, conditions: List[Dict], context: Dict) -> bool:
        for cond in conditions:
            field = cond.get("field", "")
            operator = cond.get("operator", "eq")
            value = cond.get("value")
            logic = cond.get("logic", "and")
            actual = self._get_nested_value(context, field)
            result = self._compare(actual, operator, value)
            if logic == "or" and result:
                return True
            if logic == "and" and not result:
                return False
        return True

    async def execute(self, context: Dict, group: str = None) -> Dict:
        _ = self.trace("execute")
        metrics_collector.counter("decision_engine_eval_total", labels={"group": group or "default"})
        self.audit(
            "execute",
            f"group={group}, rules={len(self._rule_groups.get(group, self._rules) if group else self._rules)}",
        )
        rule_ids = self._rule_groups.get(group, list(self._rules.keys())) if group else list(self._rules.keys())
        sorted_rules = sorted(
            [self._rules[rid] for rid in rule_ids if rid in self._rules and self._rules[rid]["enabled"]],
            key=lambda r: r["priority"],
        )
        matched = []
        executed_actions = []
        for rule in sorted_rules:
            if self.evaluate_conditions(rule["conditions"], context):
                rule["hit_count"] += 1
                matched.append({"id": rule_id_for(rule), "name": rule["name"], "priority": rule["priority"]})
                for action in rule["actions"]:
                    executed_actions.append(self._execute_action(action, context))
                if rule.get("stop_on_match", False):
                    break
        return {
            "matched_rules": matched,
            "actions_executed": executed_actions,
            "total_evaluated": len(sorted_rules),
            "match_count": len(matched),
        }

    def _execute_action(self, action: Dict, context: Dict) -> Dict:
        action_type = action.get("type", "set_value")
        if action_type == "set_value":
            target = action.get("target", "")
            value = action.get("value", action.get("computed"))
            return {"type": "set_value", "target": target, "value": value}
        elif action_type == "assign_score":
            return {"type": "assign_score", "score": action.get("score", 0)}
        elif action_type == "tag":
            return {"type": "tag", "tags": action.get("tags", [])}
        elif action_type == "route":
            return {"type": "route", "destination": action.get("destination", "")}
        return {"type": action_type, "params": action}

    @staticmethod
    def _get_nested_value(obj: Dict, path: str) -> Any:
        parts = path.split(".")
        current = obj
        for p in parts:
            if isinstance(current, dict):
                current = current.get(p)
            else:
                return None
            if current is None:
                return None
        return current

    @staticmethod
    def _compare(actual: Any, operator: str, expected: Any) -> bool:
        if actual is None:
            return operator in ("is_null", "not_exists")
        if operator == "eq":
            return str(actual) == str(expected)
        elif operator == "neq":
            return str(actual) != str(expected)
        elif operator == "gt":
            try:
                return float(actual) > float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "gte":
            try:
                return float(actual) >= float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "lt":
            try:
                return float(actual) < float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "lte":
            try:
                return float(actual) <= float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "in":
            return actual in expected if isinstance(expected, list) else str(actual) in str(expected)
        elif operator == "contains":
            return str(expected) in str(actual)
        elif operator == "regex":
            import re

            return bool(re.search(str(expected), str(actual)))
        elif operator == "between":
            try:
                return float(expected[0]) <= float(actual) <= float(expected[1])
            except (ValueError, TypeError, IndexError):
                return False
        return False

def rule_id_for(rule: Dict) -> str:
    return str(id(rule))[:8]

class ScoringModel:
    """评分模型引擎"""

    def __init__(self):
        self._models: Dict[str, Dict] = {}

    def create_model(self, name: str, features: List[Dict], weights: Dict[str, float], thresholds: Dict = None):
        total_weight = sum(abs(w) for w in weights.values())
        normalized = {k: v / total_weight for k, v in weights.items()}
        self._models[name] = {
            "features": features,
            "weights": normalized,
            "thresholds": thresholds or {"high": 80, "medium": 50, "low": 0},
            "score_count": 0,
        }

    def score(self, model_name: str, context: Dict) -> Dict:
        model = self._models.get(model_name)
        if not model:
            return {"error": "model_not_found"}
        total_score = 0
        feature_scores = {}
        for feat in model["features"]:
            fname = feat["name"]
            weight = model["weights"].get(fname, 0)
            value = context.get(fname, feat.get("default", 0))
            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 0
            feat_min = float(feat.get("min", 0))
            feat_max = float(feat.get("max", 100))
            if feat_max > feat_min:
                normalized = (value - feat_min) / (feat_max - feat_min) * 100
            else:
                normalized = 50
            normalized = max(0, min(100, normalized))
            contribution = normalized * weight * 100
            feature_scores[fname] = {
                "raw": value,
                "normalized": round(normalized, 1),
                "weight": round(weight, 3),
                "contribution": round(contribution, 1),
            }
            total_score += contribution
        total_score = max(0, min(100, total_score))
        thresholds = model["thresholds"]
        if total_score >= thresholds.get("high", 80):
            grade = "A"
        elif total_score >= thresholds.get("medium", 50):
            grade = "B"
        else:
            grade = "C"
        model["score_count"] += 1
        return {"score": round(total_score, 1), "grade": grade, "feature_scores": feature_scores}

    def batch_score(self, model_name: str, contexts: List[Dict]) -> List[Dict]:
        """批量评分"""
        return [self.score(model_name, ctx) for ctx in contexts]

    def get_feature_importance(self, model_name: str) -> Dict[str, float]:
        """获取特征重要性排名"""
        model = self._models.get(model_name)
        if not model:
            return {}
        return dict(sorted(model["weights"].items(), key=lambda x: -abs(x[1])))

    def calibrate_thresholds(self, model_name: str, scores: List[float]) -> Dict:
        """基于历史分数校准阈值"""
        if not scores:
            return {"error": "no_scores"}
        sorted_scores = sorted(scores)
        p75 = sorted_scores[int(len(sorted_scores) * 0.75)]
        p50 = sorted_scores[int(len(sorted_scores) * 0.50)]
        model = self._models.get(model_name)
        if model:
            model["thresholds"] = {"high": p75, "medium": p50, "low": 0}
        return {"high": p75, "medium": p50, "calibrated_from": len(scores)}

class ABTestEngine(object):
    """A/B测试引擎"""

    def __init__(self):
        self._experiments: Dict[str, Dict] = {}
        self._assignments: Dict[str, str] = {}

    def create_experiment(
        self, name: str, variants: List[Dict], traffic_pct: float = 100.0, allocation: Dict[str, float] = None
    ):
        if not allocation:
            n = len(variants)
            allocation = {v["name"]: round(100 / n, 1) for v in variants}
        self._experiments[name] = {
            "variants": {v["name"]: v.get("config", {}) for v in variants},
            "allocation": allocation,
            "traffic_pct": traffic_pct,
            "metrics": defaultdict(lambda: {"impressions": 0, "conversions": 0}),
            "created_at": time.time(),
            "active": True,
        }

    def assign(self, experiment: str, user_id: str) -> Dict:
        exp = self._experiments.get(experiment)
        if not exp or not exp["active"]:
            return {"variant": "control", "reason": "no_experiment"}
        key = f"{experiment}:{user_id}"
        if key in self._assignments:
            variant = self._assignments[key]
        else:
            import hashlib

            hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16) % 100
            cumulative = 0
            variant = list(exp["variants"].keys())[0]
            for v, pct in exp["allocation"].items():
                cumulative += pct
                if hash_val < cumulative:
                    variant = v
                    break
            self._assignments[key] = variant
        exp["metrics"][variant]["impressions"] += 1
        return {"experiment": experiment, "variant": variant, "config": exp["variants"].get(variant, {})}

    def track_conversion(self, experiment: str, variant: str) -> Dict:
        exp = self._experiments.get(experiment)
        if exp and variant in exp["metrics"]:
            exp["metrics"][variant]["conversions"] += 1
            metrics = exp["metrics"][variant]
            cvr = metrics["conversions"] / metrics["impressions"] * 100 if metrics["impressions"] > 0 else 0
            return {"variant": variant, "conversions": metrics["conversions"], "cvr": round(cvr, 2)}
        return {"error": "not_found"}

    def get_experiment_results(self, experiment: str) -> Dict:
        exp = self._experiments.get(experiment, {})
        results = {}
        for variant, metrics in exp.get("metrics", {}).items():
            cvr = metrics["conversions"] / metrics["impressions"] * 100 if metrics["impressions"] > 0 else 0
            results[variant] = {
                "impressions": metrics["impressions"],
                "conversions": metrics["conversions"],
                "cvr": round(cvr, 2),
            }
        return {"experiment": experiment, "active": exp.get("active", False), "results": results}

    def get_statistical_significance(self, experiment: str, min_samples: int = 100) -> Dict:
        """统计显著性检验（简化版z-test）"""
        import math

        exp = self._experiments.get(experiment, {})
        variants_data = exp.get("metrics", {})
        if len(variants_data) < 2:
            return {"error": "need_at_least_2_variants"}
        results = {}
        for v, m in variants_data.items():
            if m["impressions"] >= min_samples:
                p = m["conversions"] / m["impressions"]
                se = math.sqrt(p * (1 - p) / m["impressions"]) if m["impressions"] > 0 else 1
                results[v] = {
                    "conversion_rate": round(p, 4),
                    "std_error": round(se, 4),
                    "ci_95": (round(max(0, p - 1.96 * se), 4), round(min(1, p + 1.96 * se), 4)),
                    "samples": m["impressions"],
                }
        return {"experiment": experiment, "variants": results}

    def stop_experiment(self, experiment: str, winner: str = None) -> Dict:
        """停止实验"""
        exp = self._experiments.get(experiment)
        if exp:
            exp["active"] = False
            exp["winner"] = winner
            return {"experiment": experiment, "stopped": True, "winner": winner}
        return {"error": "not_found"}

    def get_experiment_impact_summary(self) -> Dict[str, Any]:
        """汇总所有实验的业务影响：总曝光、提升幅度、最佳实验"""
        experiments = self._experiments if hasattr(self, "_experiments") else {}
        total_impressions = 0
        total_conversions = 0
        best_lift = {"name": None, "lift": 0}
        for name, exp in experiments.items():
            metrics = exp.get("metrics", {})
            for variant, m in metrics.items():
                total_impressions += m.get("impressions", 0)
                total_conversions += m.get("conversions", 0)
            if exp.get("winner"):
                variants = list(metrics.keys())
                if len(variants) >= 2:
                    control = metrics.get(variants[0], {})
                    treatment = metrics.get(exp["winner"], {})
                    c_cvr = control["conversions"] / max(control["impressions"], 1)
                    t_cvr = treatment["conversions"] / max(treatment["impressions"], 1)
                    lift = (t_cvr - c_cvr) / max(c_cvr, 0.001)
                    if lift > best_lift["lift"]:
                        best_lift = {"name": name, "winner": exp["winner"], "lift": round(lift, 4)}
        global_cvr = total_conversions / max(total_impressions, 1)
        return {
            "total_experiments": len(experiments),
            "total_impressions": total_impressions,
            "total_conversions": total_conversions,
            "global_cvr": round(global_cvr, 4),
            "best_lift_experiment": best_lift,
        }

class DecisionAuditLog:
    """决策审计日志"""

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self._log: deque = deque(maxlen=max_entries)
        self._stats: Dict[str, int] = defaultdict(int)

    def record(self, decision_type: str, context: Dict, result: Dict, source: str = "rule_engine"):
        entry = {
            "id": str(uuid.uuid4())[:8],
            "type": decision_type,
            "source": source,
            "context_keys": list(context.keys()),
            "result_summary": {k: v for k, v in result.items() if isinstance(v, (str, int, float, bool))},
            "timestamp": time.time(),
        }
        self._log.append(entry)
        self._stats[decision_type] += 1

    def query(self, decision_type: str = None, limit: int = 100) -> List[Dict]:
        entries = list(self._log)
        if decision_type:
            entries = [e for e in entries if e["type"] == decision_type]
        return entries[-limit:]

    def get_stats(self) -> Dict:
        return {"total_decisions": len(self._log), "by_type": dict(self._stats)}

    def get_anomaly_report(self) -> Dict:
        """异常决策分析 - 识别频率异常的决策类型"""
        avg = sum(self._stats.values()) / max(len(self._stats), 1)
        anomalies = {k: v for k, v in self._stats.items() if v > avg * 3}
        return {
            "avg_decisions_per_type": round(avg, 2),
            "total_types": len(self._stats),
            "anomalies": anomalies,
            "recommendation": "检查高频异常决策类型" if anomalies else "正常",
        }

    def export_summary(self, hours: int = 24) -> Dict:
        """导出审计摘要（按小时统计）"""
        cutoff = time.time() - hours * 3600
        recent = [e for e in self._log if e["timestamp"] > cutoff]
        hourly = defaultdict(int)
        for e in recent:
            hour = int(e["timestamp"] // 3600)
            hourly[hour] += 1
        return {
            "period_hours": hours,
            "total_records": len(recent),
            "hourly_distribution": dict(sorted(hourly.items())),
        }

    def search_by_source(self, source: str, limit: int = 50) -> List[Dict]:
        """按来源搜索审计记录"""
        return [e for e in self._log if e.get("source") == source][-limit:]

class DecisionEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """决策引擎 - 生产级实现"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__()
        self.config = config or {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "decisions_made": 0,
            "rules_evaluated": 0,
            "scores_computed": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logger

        self.rule_engine = RuleEngine()
        self.scoring = ScoringModel()
        self.ab_test = ABTestEngine()
        self.audit = DecisionAuditLog()

    def initialize(self) -> dict:
        rules = self.config.get("rules", [])
        for r in rules:
            self.rule_engine.add_rule(
                r.get("id", str(uuid.uuid4())[:8]),
                r.get("name", ""),
                r.get("conditions", []),
                r.get("actions", []),
                r.get("priority", 100),
                r.get("group", "default"),
            )
        models = self.config.get("scoring_models", [])
        for m in models:
            self.scoring.create_model(
                m.get("name", ""), m.get("features", []), m.get("weights", {}), m.get("thresholds")
            )
        self._status = ModuleStatus.RUNNING
        return {"success": True, "rules": len(rules), "models": len(models)}

    def health_check(self) -> dict:
        return {
            "healthy": self._status == ModuleStatus.RUNNING,
            "decisions_made": self._metrics["decisions_made"],
            **self.audit.get_stats(),
        }

    def evaluate_rules(self, params: dict = None) -> dict:
        params = params or {}
        context = params.get("context", {})
        group = params.get("group")
        self._metrics["rules_evaluated"] += 1
        result = self.rule_engine.execute(context, group)
        self._metrics["decisions_made"] += len(result["matched_rules"])
        self.audit.record("rule_evaluation", context, result)
        return {"success": True, **result}

    def add_rule(self, params: dict = None) -> dict:
        params = params or {}
        rule_id = params.get("id", str(uuid.uuid4())[:8])
        self.rule_engine.add_rule(
            rule_id,
            params.get("name", ""),
            params.get("conditions", []),
            params.get("actions", []),
            params.get("priority", 100),
            params.get("group", "default"),
            params.get("enabled", True),
        )
        return {"success": True, "rule_id": rule_id}

    def compute_score(self, params: dict = None) -> dict:
        params = params or {}
        model = params.get("model", "")
        context = params.get("context", {})
        self._metrics["scores_computed"] += 1
        result = self.scoring.score(model, context)
        self._metrics["decisions_made"] += 1
        self.audit.record("scoring", context, result, "scoring_model")
        return {"success": True, **result}

    def create_scoring_model(self, params: dict = None) -> dict:
        params = params or {}
        self.scoring.create_model(
            params.get("name", ""), params.get("features", []), params.get("weights", {}), params.get("thresholds")
        )
        return {"success": True}

    def ab_assign(self, params: dict = None) -> dict:
        params = params or {}
        result = self.ab_test.assign(params.get("experiment", ""), params.get("user_id", ""))
        return {"success": True, **result}

    def ab_track(self, params: dict = None) -> dict:
        params = params or {}
        result = self.ab_test.track_conversion(params.get("experiment", ""), params.get("variant", ""))
        return {"success": True, **result}

    def get_audit_log(self, params: dict = None) -> dict:
        params = params or {}
        return {"success": True, "entries": self.audit.query(params.get("type"), int(params.get("limit", 100)))}

    def execute(self, action: str, params: dict = None) -> dict:
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

    def shutdown(self) -> dict:
        """Graceful shutdown for decision_engine."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

    # --- Auto-generated action dispatch methods ---
    def _action_ab_assign(self, params=None):
        """Auto-generated action wrapper for ab_assign"""
        if params is None:
            params = {}
        return self.ab_assign(**params)

    def _action_ab_track(self, params=None):
        """Auto-generated action wrapper for ab_track"""
        if params is None:
            params = {}
        return self.ab_track(**params)

    def _action_add_rule(self, params=None):
        """Auto-generated action wrapper for add_rule"""
        if params is None:
            params = {}
        return self.add_rule(**params)

    def _action_compute_score(self, params=None):
        """Auto-generated action wrapper for compute_score"""
        if params is None:
            params = {}
        return self.compute_score(**params)

    def _action_create_scoring_model(self, params=None):
        """Auto-generated action wrapper for create_scoring_model"""
        if params is None:
            params = {}
        return self.create_scoring_model(**params)

    def _action_evaluate_rules(self, params=None):
        """Auto-generated action wrapper for evaluate_rules"""
        if params is None:
            params = {}
        return self.evaluate_rules(**params)

    def _action_get_audit_log(self, params=None):
        """Auto-generated action wrapper for get_audit_log"""
        if params is None:
            params = {}
        return self.get_audit_log(**params)

    def _action_initialize(self, params=None):
        """Auto-generated action wrapper for initialize"""
        if params is None:
            params = {}
        return self.initialize(**params)

    def _action_shutdown(self, params=None):
        """Auto-generated action wrapper for shutdown"""
        if params is None:
            params = {}
        return self.shutdown(**params)

module_class = DecisionEngine
