"""
AUTO-EVO-AI V0.1 — 功能开关
Grade: A (生产级) | Category: 配置管理
职责：开关管理、灰度发布、A/B测试、规则引擎、变体分配
"""

__module_meta__ = {
    "id": "feature-flags",
    "name": "Feature Flags",
    "version": "1.0.0",
    "group": "config",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "flag_id", "type": "string", "required": True, "description": ""},
        {"name": "ctx", "type": "string", "required": True, "description": ""},
        {"name": "f", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["manager", "feature"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 功能开关 Grade: A (生产级) | Category: 配置管理",
}

import os
import asyncio
import time
import logging
import hashlib
from typing import Any, Dict, List, Optional
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

logger = logging.getLogger("feature_flags")

class FlagType(Enum):
    BOOLEAN = "boolean"
    VARIANT = "variant"
    PERCENTAGE = "percentage"

class FlagStatus(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    SCHEDULED = "scheduled"

@dataclass
class FeatureFlag:
    """功能开关"""

    flag_id: str
    name: str
    description: str = ""
    flag_type: FlagType = FlagType.BOOLEAN
    enabled: bool = True
    status: FlagStatus = FlagStatus.ENABLED
    value: Any = True
    variants: Dict[str, float] = field(default_factory=dict)
    percentage: float = 100.0
    rules: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    eval_count: int = 0
    enable_count: int = 0
    disable_count: int = 0

@dataclass
class EvalContext:
    """评估上下文"""

    user_id: str = ""
    user_email: str = ""
    user_group: str = ""
    ip: str = ""
    country: str = ""
    platform: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

class FeatureFlagsManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """功能开关管理器"""

    MODULE_ID = "feature_flags"
    MODULE_NAME = "功能开关"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._flags: Dict[str, FeatureFlag] = {}
        self._counter: int = 0
        self._eval_log: List[Dict] = []

    def initialize(self) -> None:
        try:
            self._flags.clear()
            defaults = [
                ("dark_mode", "深色模式", True, FlagType.BOOLEAN, {"tags": ["ui", "theme"]}),
                (
                    "new_dashboard",
                    "新版仪表盘",
                    True,
                    FlagType.PERCENTAGE,
                    {"percentage": 50, "tags": ["ui", "dashboard"]},
                ),
                ("ai_assistant", "AI助手", False, FlagType.BOOLEAN, {"tags": ["ai", "feature"]}),
                (
                    "payment_v2",
                    "支付V2",
                    True,
                    FlagType.VARIANT,
                    {"variants": {"stripe": 0.5, "paypal": 0.3, "wechat": 0.2}, "tags": ["payment"]},
                ),
            ]
            for fid, name, enabled, ftype, extra in defaults:
                f = FeatureFlag(
                    flag_id=fid,
                    name=name,
                    enabled=enabled,
                    flag_type=ftype,
                    tags=extra.get("tags", []),
                    percentage=extra.get("percentage", 100.0),
                    variants=extra.get("variants", {}),
                )
                f.status = FlagStatus.ENABLED if enabled else FlagStatus.DISABLED
                self._flags[fid] = f
            if self._audit:
                self._audit.log("feature_flags_initialized", {"flags": len(self._flags)})
            self.stats.success_count += 1
            logger.info("功能开关初始化完成")
        except Exception as e:
            logger.error(f"功能开关初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "feature_flags"})
        self.metrics_collector.counter("feature_flags.execute.calls", 1)
        self.audit("execute", {"module": "feature_flags"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "evaluate":
                flag_id = params.get("flag_id", "")
                ctx = params.get("context", {})
                if not flag_id:
                    return {"success": False, "error": "Missing: flag_id"}
                result = self._evaluate(flag_id, EvalContext(**ctx))
                return {"success": True, "result": result}

            elif action == "create_flag":
                fid = params.get("flag_id", "")
                name = params.get("name", "")
                ftype = params.get("flag_type", "boolean")
                enabled = params.get("enabled", True)
                if not fid or not name:
                    return {"success": False, "error": "Missing: flag_id, name"}
                f = FeatureFlag(
                    flag_id=fid,
                    name=name,
                    flag_type=FlagType(ftype),
                    enabled=enabled,
                    status=FlagStatus.ENABLED if enabled else FlagStatus.DISABLED,
                    percentage=params.get("percentage", 100),
                    variants=params.get("variants", {}),
                    tags=params.get("tags", []),
                )
                self._flags[fid] = f
                ok = True
                return {"success": True, "result": {"flag_id": fid, "name": name}}

            elif action == "update_flag":
                fid = params.get("flag_id", "")
                f = self._flags.get(fid)
                if not f:
                    return {"success": False, "error": "Flag not found"}
                if "enabled" in params:
                    f.enabled = params["enabled"]
                    f.status = FlagStatus.ENABLED if params["enabled"] else FlagStatus.DISABLED
                if "percentage" in params:
                    f.percentage = params["percentage"]
                if "variants" in params:
                    f.variants = params["variants"]
                if "rules" in params:
                    f.rules = params["rules"]
                f.updated_at = time.time()
                ok = True
                return {"success": True, "result": {"flag_id": fid, "enabled": f.enabled}}

            elif action == "delete_flag":
                fid = params.get("flag_id", "")
                f = self._flags.pop(fid, None)
                if not f:
                    return {"success": False, "error": "Flag not found"}
                ok = True
                return {"success": True, "result": {"deleted": fid}}

            elif action == "list_flags":
                tag = params.get("tag", "")
                flags = list(self._flags.values())
                if tag:
                    flags = [f for f in flags if tag in f.tags]
                return {
                    "success": True,
                    "result": [
                        {
                            "flag_id": f.flag_id,
                            "name": f.name,
                            "type": f.flag_type.value,
                            "enabled": f.enabled,
                            "status": f.status.value,
                            "percentage": f.percentage,
                            "variants": f.variants,
                            "evaluations": f.eval_count,
                            "tags": f.tags,
                        }
                        for f in flags
                    ],
                }

            elif action == "get_flag":
                fid = params.get("flag_id", "")
                f = self._flags.get(fid)
                if not f:
                    return {"success": False, "error": "Flag not found"}
                return {
                    "success": True,
                    "result": {
                        "flag_id": f.flag_id,
                        "name": f.name,
                        "type": f.flag_type.value,
                        "enabled": f.enabled,
                        "value": f.value,
                        "percentage": f.percentage,
                        "variants": f.variants,
                        "rules": f.rules,
                        "evaluations": f.eval_count,
                        "tags": f.tags,
                    },
                }

            elif action == "get_stats":
                total = len(self._flags)
                enabled = sum(1 for f in self._flags.values() if f.enabled)
                by_type = {}
                for f in self._flags.values():
                    by_type[f.flag_type.value] = by_type.get(f.flag_type.value, 0) + 1
                return {
                    "success": True,
                    "result": {
                        "total": total,
                        "enabled": enabled,
                        "disabled": total - enabled,
                        "by_type": by_type,
                        "total_evaluations": sum(f.eval_count for f in self._flags.values()),
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
            "flags": len(self._flags),
            "enabled": sum(1 for f in self._flags.values() if f.enabled),
        }

    def shutdown(self) -> None:
        self._flags.clear()
        super().shutdown()

    def _evaluate(self, flag_id: str, ctx: EvalContext) -> Dict:
        f = self._flags.get(flag_id)
        if not f:
            return {"flag_id": flag_id, "error": "Flag not found", "enabled": False}

        f.eval_count += 1

        if not f.enabled:
            f.disable_count += 1
            return {"flag_id": flag_id, "enabled": False, "value": None, "reason": "disabled"}

        # 检查规则
        for rule in f.rules:
            match = True
            if "user_group" in rule and ctx.user_group != rule["user_group"]:
                match = False
            if match:
                override = rule.get("enabled")
                if override is not None:
                    if override:
                        f.enable_count += 1
                    else:
                        f.disable_count += 1
                    return {
                        "flag_id": flag_id,
                        "enabled": override,
                        "value": override,
                        "reason": "rule_match",
                        "rule": rule.get("name", ""),
                    }

        if f.flag_type == FlagType.BOOLEAN:
            f.enable_count += 1
            return {"flag_id": flag_id, "enabled": True, "value": True, "reason": "boolean_enabled"}

        elif f.flag_type == FlagType.PERCENTAGE:
            # 基于user_id的稳定哈希
            bucket = 0
            if ctx.user_id:
                bucket = int(hashlib.md5(ctx.user_id.encode()).hexdigest(), 16) % 100
            allowed = bucket < f.percentage
            if allowed:
                f.enable_count += 1
            else:
                f.disable_count += 1
            return {
                "flag_id": flag_id,
                "enabled": allowed,
                "value": allowed,
                "reason": "percentage",
                "bucket": bucket,
                "threshold": f.percentage,
            }

        elif f.flag_type == FlagType.VARIANT:
            variant = self._select_variant(f, ctx)
            f.enable_count += 1
            return {"flag_id": flag_id, "enabled": True, "value": variant, "reason": "variant_selected"}

        return {"flag_id": flag_id, "enabled": True, "value": True}

    def _select_variant(self, f: FeatureFlag, ctx: EvalContext) -> str:
        if not f.variants:
            return "default"
        if ctx.user_id:
            bucket = int(hashlib.md5(ctx.user_id.encode()).hexdigest(), 16) % 100
        else:
            bucket = int(time.time() * 1000) % 100
        cumulative = 0
        for variant, weight in f.variants.items():
            cumulative += weight * 100
            if bucket < cumulative:
                return variant
        return list(f.variants.keys())[-1]

    def create_flag(self, flag_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建Feature Flag。企业场景：产品经理上线新功能前创建灰度开关，
        配置灰度策略（按百分比/用户白名单/AB测试分组）。
        """
        flag_id = hashlib.md5(flag_config.get("name", "").encode()).hexdigest()[:12]
        flag_type_str = flag_config.get("type", "boolean")
        flag_type = FlagType.BOOLEAN
        if flag_type_str == "percentage":
            flag_type = FlagType.PERCENTAGE
        elif flag_type_str == "variant":
            flag_type = FlagType.VARIANT
        flag = FeatureFlag(
            flag_id=flag_id,
            name=flag_config.get("name", ""),
            flag_type=flag_type,
            description=flag_config.get("description", ""),
            enabled=flag_config.get("enabled", False),
            percentage=flag_config.get("percentage", 0),
            variants=flag_config.get("variants", {}),
            created_at=time.time(),
        )
        self._flags[flag_id] = flag
        return {"success": True, "flag_id": flag_id, "name": flag.name}

    def get_flag_evaluation_stats(self, days: int = 7) -> Dict[str, Any]:
        """Flag评估统计。企业场景：灰度发布期间产品团队监控各Flag的
        开启/关闭比例，决定是否全量发布或回滚。
        """
        stats = []
        for fid, flag in self._flags.items():
            total = flag.enable_count + flag.disable_count
            stats.append(
                {
                    "flag_id": fid,
                    "name": flag.name,
                    "type": flag.flag_type.value if hasattr(flag.flag_type, "value") else str(flag.flag_type),
                    "enabled": flag.enabled,
                    "evaluations": total,
                    "enable_count": flag.enable_count,
                    "disable_count": flag.disable_count,
                    "enable_rate": round(flag.enable_count / max(total, 1) * 100, 1),
                }
            )
        stats.sort(key=lambda x: -x["evaluations"])
        return {
            "success": True,
            "period_days": days,
            "total_flags": len(stats),
            "active_flags": sum(1 for s in stats if s["enabled"]),
            "stats": stats,
        }

    def batch_update_flags(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量更新Flag状态。企业场景：版本发布时一次性开关多个Feature Flag。"""
        updated = 0
        not_found = 0
        for u in updates:
            fid = u.get("flag_id", "")
            flag = self._flags.get(fid)
            if not flag:
                not_found += 1
                continue
            if "enabled" in u:
                flag.enabled = u["enabled"]
            if "percentage" in u:
                flag.percentage = u["percentage"]
            if "variants" in u:
                flag.variants = u["variants"]
            updated += 1
        return {"success": True, "updated": updated, "not_found": not_found}

    def get_flag_evaluation_summary(self, days: int = 7) -> Dict[str, Any]:
        """Feature Flag评估汇总。企业场景：产品经理查看各功能开关的
        灰度进度、用户覆盖率、转化效果，决定是否全量发布。
        """
        flags = getattr(self, "_flags", {})
        cutoff = time.time() - days * 86400
        summary = []
        for fid, flag in flags.items():
            evaluations = getattr(flag, "evaluations", [])
            recent = [e for e in evaluations if e.get("ts", 0) > cutoff]
            total_eval = len(recent)
            true_count = sum(1 for e in recent if e.get("result") == True)
            false_count = total_eval - true_count
            true_pct = round(true_count / max(total_eval, 1) * 100, 1)
            summary.append(
                {
                    "flag_id": fid,
                    "name": getattr(flag, "name", fid),
                    "enabled": getattr(flag, "enabled", False),
                    "percentage": getattr(flag, "percentage", 100),
                    "total_evaluations": total_eval,
                    "true_count": true_count,
                    "false_count": false_count,
                    "true_percentage": true_pct,
                    "variants": getattr(flag, "variants", {}),
                }
            )
        summary.sort(key=lambda x: x["total_evaluations"], reverse=True)
        total_flags = len(summary)
        enabled_flags = sum(1 for s in summary if s["enabled"])
        return {
            "success": True,
            "period_days": days,
            "total_flags": total_flags,
            "enabled_flags": enabled_flags,
            "disabled_flags": total_flags - enabled_flags,
            "flags": summary,
        }

    def bulk_toggle(self, enable: bool, pattern: str = "*") -> Dict[str, Any]:
        """批量开关功能。企业场景：紧急故障时一键关闭所有实验性功能，
        或发布完成后批量关闭灰度标记。
        """
        flags = getattr(self, "_flags", {})
        import fnmatch

        toggled = 0
        skipped = 0
        for fid, flag in flags.items():
            if pattern != "*" and not fnmatch.fnmatch(fid, pattern):
                skipped += 1
                continue
            flag.enabled = enable
            toggled += 1
        return {
            "success": True,
            "action": "enable" if enable else "disable",
            "pattern": pattern,
            "toggled": toggled,
            "skipped": skipped,
        }

    def get_flag_usage_stats(self, flag_name: str, days: int = 7) -> Dict[str, Any]:
        """Flag使用统计。企业场景：产品经理评估Feature Flag的使用效果，
        查看曝光量、用户数、A/B分组比例，决定是否全量发布。
        """
        flags = getattr(self, "_flags", {})
        flag = flags.get(flag_name)
        if not flag:
            return {"success": False, "error": f"Flag {flag_name} 不存在"}
        evaluations = getattr(flag, "evaluations", [])
        cutoff = time.time() - days * 86400
        recent = [e for e in evaluations if e.get("timestamp", 0) > cutoff]
        true_count = sum(1 for e in recent if e.get("result", False))
        false_count = len(recent) - true_count
        unique_users = len(set(e.get("user_id", "") for e in recent if e.get("user_id")))
        return {
            "success": True,
            "flag": flag_name,
            "period_days": days,
            "total_evaluations": len(recent),
            "true_evaluations": true_count,
            "false_evaluations": false_count,
            "true_ratio": round(true_count / max(len(recent), 1) * 100, 1),
            "unique_users": unique_users,
        }

    def export_flags_config(self, format_type: str = "json") -> Dict[str, Any]:
        """导出Flag配置。企业场景：从生产导出配置到预发环境，
        保持Feature Flag一致性。
        """
        flags = getattr(self, "_flags", {})
        config = []
        for name, flag in flags.items():
            config.append(
                {
                    "name": name,
                    "enabled": getattr(flag, "enabled", False),
                    "description": getattr(flag, "description", ""),
                    "rules": getattr(flag, "rules", []),
                    "rollout_pct": getattr(flag, "rollout_percentage", 100),
                    "created_by": getattr(flag, "created_by", ""),
                    "tags": getattr(flag, "tags", []),
                }
            )
        return {"success": True, "format": format_type, "total_flags": len(config), "config": config}

    def get_flag_dependencies(self, flag_name: str) -> Dict[str, Any]:
        """查看Flag依赖关系。企业场景：关闭某Flag前检查是否有其他Flag
        依赖它，避免级联影响业务功能。
        """
        flags = getattr(self, "_flags", {})
        flag = flags.get(flag_name)
        if not flag:
            return {"success": False, "error": f"Flag {flag_name} 不存在"}
        depends_on = getattr(flag, "depends_on", [])
        depended_by = []
        for name, f in flags.items():
            deps = getattr(f, "depends_on", [])
            if flag_name in deps:
                depended_by.append(name)
        return {
            "success": True,
            "flag": flag_name,
            "depends_on": depends_on,
            "depended_by": depended_by,
            "safe_to_disable": len(depended_by) == 0,
        }

module_class = FeatureFlagsManager

module_class = FeatureFlagsManager
