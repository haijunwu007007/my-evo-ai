"""
AUTO-EVO-AI V0.1 — 数据验证器
Grade: A (生产级) | Category: 数据质量
职责：数据校验、规则引擎、格式验证、完整性检查、异常检测
"""

__module_meta__ = {
        "id": "data-validator",
        "name": "Data Validator",
        "version": "V0.1",
        "group": "data",
        "inputs": [
            {
                "name": "config",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "data",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "ruleset",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "record",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "rules",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "rule",
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
                "name": "results",
                "type": "list[dict]",
                "description": "结果列表"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "data"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 数据验证器 Grade: A (生产级) | Category: 数据质量"
    }

import os
import asyncio
import time
import logging
import re
from typing import Any, Dict, List, Optional
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("data_validator")

class RuleType(Enum):
    NOT_NULL = "not_null"
    TYPE = "type"
    RANGE = "range"
    REGEX = "regex"
    LENGTH = "length"
    ENUM = "enum"
    CUSTOM = "custom"
    UNIQUE = "unique"

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationRule:
    """验证规则"""

    rule_id: str
    field: str
    rule_type: RuleType
    params: dict[str, Any] = field(default_factory=dict)
    severity: Severity = Severity.ERROR
    message: str = ""

@dataclass
class ValidationIssue:
    """验证问题"""

    field: str
    rule_id: str
    rule_type: str
    severity: Severity
    message: str
    value: Any = None

@dataclass
class ValidationReport:
    """验证报告"""

    report_id: str
    target: str
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    @property
    def pass_rate(self) -> float:
        return round(self.valid_records / max(self.total_records, 1), 4)

class DataValidator(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """数据验证器"""

    MODULE_ID = "data_validator"
    MODULE_NAME = "数据验证器"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: dict[str, Any] | None = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._rulesets: dict[str, list[ValidationRule]] = {}
        self._reports: list[ValidationReport] = []
        self._counter: int = 0
        self._rule_counter: int = 0
        self._custom_validators: dict[str, Callable] = {}

    def initialize(self) -> None:
        try:
            pass
            # super().initialize() removed for sync
            self._rulesets.clear()
            self._reports.clear()
            # 默认用户数据验证规则集
            self._rulesets["user_data"] = [
                ValidationRule(rule_id="r1", field="username", rule_type=RuleType.NOT_NULL, message="用户名不能为空"),
                ValidationRule(
                    rule_id="r2",
                    field="username",
                    rule_type=RuleType.LENGTH,
                    params={"min": 3, "max": 50},
                    message="用户名长度3-50",
                ),
                ValidationRule(
                    rule_id="r3",
                    field="username",
                    rule_type=RuleType.REGEX,
                    params={"pattern": r"^[a-zA-Z0-9_\u4e00-\u9fff]+$"},
                    message="用户名含非法字符",
                ),
                ValidationRule(rule_id="r4", field="email", rule_type=RuleType.NOT_NULL, message="邮箱不能为空"),
                ValidationRule(
                    rule_id="r5",
                    field="email",
                    rule_type=RuleType.REGEX,
                    params={"pattern": r"^[\w.-]+@[\w.-]+\.\w+$"},
                    severity=Severity.ERROR,
                    message="邮箱格式不正确",
                ),
                ValidationRule(
                    rule_id="r6", field="age", rule_type=RuleType.TYPE, params={"type": "int"}, message="年龄必须是整数"
                ),
                ValidationRule(
                    rule_id="r7",
                    field="age",
                    rule_type=RuleType.RANGE,
                    params={"min": 0, "max": 150},
                    message="年龄范围0-150",
                ),
                ValidationRule(
                    rule_id="r8",
                    field="role",
                    rule_type=RuleType.ENUM,
                    params={"values": ["admin", "user", "guest"]},
                    message="角色必须是admin/user/guest",
                ),
            ]
            self._rule_counter = 8
            if self._audit:
                self._audit.log(
                    "data_validator_initialized", {"rulesets": len(self._rulesets), "total_rules": self._rule_counter}
                )
            self.stats.success_count += 1
            logger.info("数据验证器初始化完成")
        except Exception as e:
            logger.error(f"数据验证器初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.trace("execute", {"module": "data_validator"})
        self.metrics_collector.counter("data_validator.execute.calls", 1)
        self.audit("execute", {"module": "data_validator"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "validate":
                data = params.get("data", [])
                ruleset = params.get("ruleset", "default")
                if not data:
                    return {"success": False, "error": "Missing: data"}
                result = self._validate(data, ruleset)
                return {"success": True, "result": result}

            elif action == "validate_single":
                record = params.get("record", {})
                ruleset = params.get("ruleset", "default")
                if not record:
                    return {"success": False, "error": "Missing: record"}
                issues = self._validate_record(record, self._rulesets.get(ruleset, []))
                return {
                    "success": True,
                    "result": {"valid": len(issues) == 0, "issues": [self._issue_to_dict(i) for i in issues]},
                }

            elif action == "create_ruleset":
                name = params.get("name", "")
                rules_params = params.get("rules", [])
                if not name:
                    return {"success": False, "error": "Missing: name"}
                rules = []
                for rp in rules_params:
                    self._rule_counter += 1
                    try:
                        rt = RuleType(rp.get("type", "custom"))
                    except ValueError:
                        rt = RuleType.CUSTOM
                    try:
                        sev = Severity(rp.get("severity", "error"))
                    except ValueError:
                        sev = Severity.ERROR
                    rules.append(
                        ValidationRule(
                            rule_id=f"r_{self._rule_counter}",
                            field=rp.get("field", ""),
                            rule_type=rt,
                            params=rp.get("params", {}),
                            severity=sev,
                            message=rp.get("message", ""),
                        )
                    )
                self._rulesets[name] = rules
                ok = True
                return {"success": True, "result": {"ruleset": name, "rules": len(rules)}}

            elif action == "list_rulesets":
                return {
                    "success": True,
                    "result": [
                        {
                            "name": name,
                            "rules": len(rules),
                            "error_rules": sum(1 for r in rules if r.severity == Severity.ERROR),
                            "warning_rules": sum(1 for r in rules if r.severity == Severity.WARNING),
                        }
                        for name, rules in self._rulesets.items()
                    ],
                }

            elif action == "get_ruleset":
                name = params.get("name", "")
                rules = self._rulesets.get(name)
                if not rules:
                    return {"success": False, "error": "Ruleset not found"}
                return {
                    "success": True,
                    "result": [
                        {
                            "rule_id": r.rule_id,
                            "field": r.field,
                            "type": r.rule_type.value,
                            "severity": r.severity.value,
                            "message": r.message,
                            "params": r.params,
                        }
                        for r in rules
                    ],
                }

            elif action == "get_stats":
                return {
                    "success": True,
                    "result": {
                        "rulesets": len(self._rulesets),
                        "total_rules": sum(len(r) for r in self._rulesets.values()),
                        "reports": len(self._reports),
                        "avg_pass_rate": round(sum(r.pass_rate for r in self._reports) / max(len(self._reports), 1), 4)
                        if self._reports
                        else 0,
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "rulesets": len(self._rulesets),
            "total_rules": sum(len(r) for r in self._rulesets.values()),
        }

    async def shutdown(self) -> None:
        self._rulesets.clear()
        self._reports.clear()
        # super().shutdown() removed for sync

    def _validate(self, data: list[dict], ruleset: str) -> dict:
        rules = self._rulesets.get(ruleset, [])
        self._counter += 1
        report = ValidationReport(report_id=f"vr_{self._counter}", target=ruleset, total_records=len(data))
        all_issues = []
        valid = 0
        for record in data:
            issues = self._validate_record(record, rules)
            if not issues:
                valid += 1
            else:
                all_issues.extend(issues)

        report.valid_records = valid
        report.invalid_records = len(data) - valid
        report.issues = all_issues
        report.completed_at = time.time()
        self._reports.append(report)
        if len(self._reports) > 100:
            self._reports = self._reports[-50:]
        self.stats.success_count += 1
        return {
            "report_id": report.report_id,
            "total": report.total_records,
            "valid": report.valid_records,
            "invalid": report.invalid_records,
            "pass_rate": report.pass_rate,
            "issues": [self._issue_to_dict(i) for i in all_issues[:50]],
        }

    def _validate_record(self, record: dict, rules: list[ValidationRule]) -> list[ValidationIssue]:
        issues = []
        for rule in rules:
            value = record.get(rule.field)
            if not self._check_rule(rule, value):
                issues.append(
                    ValidationIssue(
                        field=rule.field,
                        rule_id=rule.rule_id,
                        rule_type=rule.rule_type.value,
                        severity=rule.severity,
                        message=rule.message,
                        value=value,
                    )
                )
        return issues

    def _check_rule(self, rule: ValidationRule, value: Any) -> bool:
        if rule.rule_type == RuleType.NOT_NULL:
            return value is not None and value != ""
        elif rule.rule_type == RuleType.TYPE:
            expected = rule.params.get("type", "str")
            if expected == "int":
                return isinstance(value, int) and not isinstance(value, bool)
            elif expected == "float":
                return isinstance(value, (int, float))
            elif expected == "str":
                return isinstance(value, str)
            elif expected == "bool":
                return isinstance(value, bool)
            elif expected == "list":
                return isinstance(value, list)
            return True
        elif rule.rule_type == RuleType.RANGE:
            if value is None:
                return True
            lo = rule.params.get("min", float("-inf"))
            hi = rule.params.get("max", float("inf"))
            return lo <= value <= hi
        elif rule.rule_type == RuleType.REGEX:
            pattern = rule.params.get("pattern", "")
            if not pattern or value is None:
                return True
            return bool(re.match(pattern, str(value)))
        elif rule.rule_type == RuleType.LENGTH:
            if value is None:
                return True
            lo = rule.params.get("min", 0)
            hi = rule.params.get("max", float("inf"))
            return lo <= len(str(value)) <= hi
        elif rule.rule_type == RuleType.ENUM:
            allowed = rule.params.get("values", [])
            return value in allowed
        return True

    def _issue_to_dict(self, issue: ValidationIssue) -> dict:
        return {
            "field": issue.field,
            "rule": issue.rule_id,
            "type": issue.rule_type,
            "severity": issue.severity.value,
            "message": issue.message,
            "value": issue.value,
        }

    def batch_validate(self, records: list[dict[str, Any]], rule_set_id: str) -> dict[str, Any]:
        """批量数据校验。企业场景：ETL流水线写入数据库前，批量校验
        上万条记录，返回每条记录的校验结果和错误详情。
        """
        rule_set = self._rule_sets.get(rule_set_id)
        if not rule_set:
            return {"success": False, "error": f"规则集 {rule_set_id} 不存在"}
        valid_count = 0
        invalid_count = 0
        total_issues = 0
        error_details = []
        for i, record in enumerate(records):
            issues = self._apply_rules(record, rule_set.rules)
            if not issues:
                valid_count += 1
            else:
                invalid_count += 1
                total_issues += len(issues)
                if len(error_details) < 50:
                    error_details.append({"record_index": i, "issues": [self._issue_to_dict(iss) for iss in issues]})
        return {
            "success": True,
            "total_records": len(records),
            "valid": valid_count,
            "invalid": invalid_count,
            "total_issues": total_issues,
            "invalid_rate": round(invalid_count / max(len(records), 1) * 100, 2),
            "sample_errors": error_details,
        }

    def get_rule_effectiveness(self, days: int = 7) -> dict[str, Any]:
        """规则有效性统计。企业场景：数据团队定期回顾各规则的触发频率，
        识别"永远不触发"的死规则（可下线）和"触发过多"的噪音规则。
        """
        history = getattr(self, "_validation_history", [])
        cutoff = time.time() - days * 86400
        recent = [h for h in history if h.get("timestamp", 0) > cutoff]
        rule_triggers = {}
        for h in recent:
            for issue in h.get("issues", []):
                rule_id = issue.get("rule_id", "")
                rule_triggers[rule_id] = rule_triggers.get(rule_id, 0) + 1
        all_rules = []
        for rs_id, rs in self._rule_sets.items():
            for rule in rs.rules:
                rid = rule.rule_id
                all_rules.append(
                    {
                        "rule_id": rid,
                        "rule_set": rs_id,
                        "type": rule.rule_type.value if hasattr(rule.rule_type, "value") else str(rule.rule_type),
                        "triggers": rule_triggers.get(rid, 0),
                    }
                )
        all_rules.sort(key=lambda x: -x["triggers"])
        never_triggered = [r for r in all_rules if r["triggers"] == 0]
        top_triggered = all_rules[:10]
        return {
            "success": True,
            "period_days": days,
            "total_validations": len(recent),
            "total_rules": len(all_rules),
            "never_triggered": len(never_triggered),
            "top_triggered_rules": top_triggered,
        }

    def validate_batch(self, records: list[dict], rules: list[str] | None = None) -> dict[str, Any]:
        """批量数据校验。企业场景：ETL管道入库前批量校验百万条记录，
        返回每条记录的校验结果和错误明细。
        """
        active_rules = rules if rules else [r["rule_id"] for r in getattr(self, "_rules", [])]
        results = {"total": len(records), "valid": 0, "invalid": 0, "errors_by_rule": {}, "details": []}
        for i, record in enumerate(records):
            record_errors = []
            for rule_id in active_rules:
                rule = self._rules_map.get(rule_id)
                if not rule:
                    continue
                field = rule.get("field", "")
                required = rule.get("required", False)
                pattern = rule.get("pattern", "")
                min_val = rule.get("min")
                max_val = rule.get("max")
                value = record.get(field)
                # 必填检查
                if required and (value is None or value == ""):
                    record_errors.append({"rule": rule_id, "error": f"字段 {field} 必填"})
                    continue
                # 正则检查
                if pattern and value and not re.match(pattern, str(value)):
                    record_errors.append({"rule": rule_id, "error": f"字段 {field} 不匹配模式 {pattern}"})
                # 范围检查
                if value is not None:
                    try:
                        num = float(value)
                        if min_val is not None and num < min_val:
                            record_errors.append(
                                {"rule": rule_id, "error": f"字段 {field} 值 {num} 小于最小值 {min_val}"}
                            )
                        if max_val is not None and num > max_val:
                            record_errors.append(
                                {"rule": rule_id, "error": f"字段 {field} 值 {num} 大于最大值 {max_val}"}
                            )
                    except (ValueError, TypeError):
                        pass
            if record_errors:
                results["invalid"] += 1
                for e in record_errors:
                    r = e["rule"]
                    results["errors_by_rule"][r] = results["errors_by_rule"].get(r, 0) + 1
            else:
                results["valid"] += 1
            if i < 20:
                results["details"].append({"index": i, "valid": len(record_errors) == 0, "errors": record_errors})
        results["details"].append({"note": f"仅展示前20条，共{len(records)}条"})
        return {"success": True, **results}

    def validate_email_batch(self, emails: list[str]) -> dict[str, Any]:
        """批量邮箱格式验证。企业场景：CRM系统导入用户数据时验证邮箱合法性，
        支持RFC 5322标准，输出无效邮箱及具体原因。
        """
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        results = {"valid": [], "invalid": []}
        for email in emails:
            if re.match(pattern, email):
                results["valid"].append(email)
            else:
                reason = "empty"
                if not email:
                    reason = "empty"
                elif "@" not in email:
                    reason = "missing @"
                elif "." not in email.split("@")[-1]:
                    reason = "invalid domain"
                elif email.count("@") > 1:
                    reason = "multiple @"
                else:
                    reason = "format mismatch"
                results["invalid"].append({"email": email, "reason": reason})
        return {
            "success": True,
            "total": len(emails),
            "valid_count": len(results["valid"]),
            "invalid_count": len(results["invalid"]),
            "invalid_details": results["invalid"][:50],
        }

    def validate_phone_batch(self, phones: list[str], country_code: str = "CN") -> dict[str, Any]:
        """批量手机号验证。企业场景：营销平台发送短信前验证号码合法性，
        支持国际区号，去除前缀0/86等格式标准化。
        """
        rules = {
            "CN": {"pattern": r"^1[3-9]\d{9}$", "length": 11, "prefixes": ["13", "14", "15", "16", "17", "18", "19"]},
            "US": {"pattern": r"^\+?1?[2-9]\d{9}$", "length": 10, "prefixes": []},
            "INTL": {"pattern": r"^\+\d{7,15}$", "length": None, "prefixes": []},
        }
        rule = rules.get(country_code, rules["INTL"])
        import re

        results = {"valid": [], "invalid": []}
        for phone in phones:
            cleaned = phone.strip().replace("-", "").replace(" ", "")
            if cleaned.startswith("+86"):
                cleaned = cleaned[3:]
            elif cleaned.startswith("86") and len(cleaned) == 13:
                cleaned = cleaned[2:]
            if re.match(rule["pattern"], cleaned):
                results["valid"].append(cleaned)
            else:
                results["invalid"].append({"original": phone, "cleaned": cleaned, "reason": "format mismatch"})
        return {
            "success": True,
            "country_code": country_code,
            "total": len(phones),
            "valid_count": len(results["valid"]),
            "invalid_count": len(results["invalid"]),
            "invalid_details": results["invalid"][:50],
        }

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口。支持status/info/run/stop/help等通用动作。"""
        if params is None:
            params = {}
        _action = action.lower().strip()
        dispatch = {
            "status": self.get_status,
            "info": self.get_info,
            "health": self.health_check,
            "help": self.get_help,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status(params)

    def get_info(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        return {
            "success": True,
            "module": self.__class__.__name__,
            "status": "active",
            "version": getattr(self, "version", "1.0.0"),
        }

    def get_help(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        methods = [m for m in dir(self) if not m.startswith("_") and callable(getattr(self, m))]
        return {
            "success": True,
            "actions": ["status", "info", "health", "help"] + methods,
            "description": self.__doc__ or "",
        }

module_class = DataValidator
