# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 — 数据脱敏引擎（上市公司级）

支持电话/邮箱/身份证/银行卡/姓名/地址/自定义正则脱敏，
批量处理、JSON 字段递归、审计日志、可配置脱敏规则集。
"""
__module_meta__ = {
    "id": "data-masking",
    "name": "Data Masking Engine",
    "version": "3.0.0",
    "group": "security",
    "grade": "A",
    "tags": ["security", "masking", "pii", "compliance"],
    "description": "企业级数据脱敏引擎 — 电话/邮箱/身份证/银行卡/姓名/地址/自定义",
}
import time, uuid, logging, re, json, hashlib
from typing import Any, Dict, List, Optional, Callable, Union
from modules._base.enterprise_module import (
    EnterpriseModule, ModuleStatus, HealthReport,
    CircuitBreakerMixin, RateLimiterMixin,
)

logger = logging.getLogger("evo.data-masking")

# ─── 内置脱敏规则 ─────────────────────────────────────
MASK_RULES: Dict[str, Dict] = {
    "phone": {
        "pattern": r"(1[3-9]\d)\d{4}(\d{4})",
        "replacement": r"\1****\2",
        "description": "手机号：保留前3后4",
    },
    "email": {
        "pattern": r"(\w)[^@]*(@\w+\.\w+)",
        "replacement": r"\1***\2",
        "description": "邮箱：保留首字符和域名",
    },
    "idcard": {
        "pattern": r"(\d{6})\d{8,10}(\d{4}|[0-9Xx])",
        "replacement": r"\1********\2",
        "description": "身份证：保留前6后4",
    },
    "bankcard": {
        "pattern": r"(\d{4})\d{8,10}(\d{4})",
        "replacement": r"\1********\2",
        "description": "银行卡：保留前4后4",
    },
    "name": {
        "pattern": r"^(\S)\S+$",
        "replacement": r"\1**",
        "description": "姓名：保留姓氏",
    },
    "address": {
        "pattern": r"(\S{2,4})\S+(\S{2})",
        "replacement": r"\1****\2",
        "description": "地址：保留前后部分",
    },
    "ip": {
        "pattern": r"(\d{1,3}\.\d{1,3})\.\d{1,3}\.\d{1,3}",
        "replacement": r"\1.*.*",
        "description": "IP 地址：保留前两段",
    },
}


class DataMaskingEngine(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """企业级数据脱敏引擎"""

    MODULE_ID = "data-masking"
    MODULE_NAME = "数据脱敏引擎"
    VERSION = "v3.0"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._rules: Dict[str, Dict] = dict(MASK_RULES)
        self._custom_rules: Dict[str, Dict] = {}
        self._stats = {
            "total_masks": 0,
            "total_batches": 0,
            "by_type": {},
            "started_at": time.time(),
        }
        self._audit_log: List[Dict] = []

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING
        logger.info("[DataMasking] 引擎就绪, %d 内置规则", len(self._rules))

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value,
            healthy=True,
            module_id=self.MODULE_ID,
            checks={
                "builtin_rules": len(self._rules),
                "custom_rules": len(self._custom_rules),
                "total_masks": self._stats["total_masks"],
                "engine": "regex",
            },
        )

    async def execute(self, action=None, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)

    # ─── 脱敏核心 ──────────────────────────────────────
    def _apply_rule(self, value: str, rule: Dict) -> str:
        """对单值应用单条脱敏规则"""
        try:
            return re.sub(rule["pattern"], rule["replacement"], str(value))
        except re.error as e:
            logger.warning("[DataMasking] 正则错误: %s", e)
            return str(value)

    def mask_value(self, value: str, mask_type: str = "phone") -> str:
        """对单值脱敏"""
        rule = self._custom_rules.get(mask_type) or self._rules.get(mask_type)
        if not rule:
            return str(value)
        result = self._apply_rule(str(value), rule)
        self._stats["total_masks"] += 1
        self._stats["by_type"][mask_type] = self._stats["by_type"].get(mask_type, 0) + 1
        return result

    def mask_dict(self, data: Dict, fields: Optional[List[str]] = None,
                  field_types: Optional[Dict[str, str]] = None) -> Dict:
        """对字典指定字段脱敏

        Args:
            data: 输入字典
            fields: 要脱敏的字段列表（自动推断类型）
            field_types: 字段到脱敏类型的映射，如 {"phone_field": "phone"}
        """
        result = dict(data)
        ft = field_types or {}

        for key in (fields or list(data.keys())):
            if key not in result:
                continue
            val = result[key]
            if val is None:
                continue

            # 递归处理嵌套字典
            if isinstance(val, dict):
                result[key] = self.mask_dict(val, fields, field_types)
                continue
            # 递归处理列表
            if isinstance(val, list):
                result[key] = [
                    self.mask_dict(item, fields, field_types) if isinstance(item, dict)
                    else self.mask_value(str(item), ft.get(key, "phone"))
                    for item in val
                ]
                continue

            mask_type = ft.get(key, self._detect_type(str(val)))
            result[key] = self.mask_value(str(val), mask_type)
        return result

    def mask_batch(self, records: List[Dict], fields: Optional[List[str]] = None,
                   field_types: Optional[Dict[str, str]] = None) -> List[Dict]:
        """批量脱敏

        Args:
            records: 字典列表
            fields: 要脱敏的字段
            field_types: 字段→类型映射
        Returns:
            脱敏后的记录列表
        """
        self._stats["total_batches"] += 1
        return [self.mask_dict(r, fields, field_types) for r in records]

    def _detect_type(self, value: str) -> str:
        """自动检测敏感数据类型"""
        v = value.strip()
        # 手机号
        if re.match(r"^1[3-9]\d{9}$", v):
            return "phone"
        # 邮箱
        if re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", v):
            return "email"
        # 身份证 (15/18位)
        if re.match(r"^\d{15}$|^\d{17}[\dXx]$", v):
            return "idcard"
        # 银行卡 (16-19位数字)
        if re.match(r"^\d{16,19}$", v):
            return "bankcard"
        # IP
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", v):
            return "ip"
        return "phone"

    def _audit(self, action: str, detail: str, level: str = "info"):
        """记录审计日志"""
        self._audit_log.append({
            "id": uuid.uuid4().hex[:12],
            "time": time.time(),
            "action": action,
            "detail": detail,
            "level": level,
        })
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]

    # ─── 规则管理 ──────────────────────────────────────
    def add_custom_rule(self, name: str, pattern: str, replacement: str,
                        description: str = "") -> Dict:
        """添加自定义脱敏规则"""
        if not pattern or not replacement:
            return {"success": False, "error": "pattern和replacement必填"}
        try:
            re.compile(pattern)
        except re.error as e:
            return {"success": False, "error": f"正则无效: {e}"}
        self._custom_rules[name] = {
            "pattern": pattern,
            "replacement": replacement,
            "description": description or f"自定义规则: {name}",
        }
        self._audit("add_rule", f"添加自定义规则: {name}")
        return {"success": True, "rule": name}

    def remove_rule(self, name: str) -> Dict:
        """删除自定义规则（内置规则不可删除）"""
        if name in MASK_RULES:
            return {"success": False, "error": f"内置规则不可删除: {name}"}
        if name in self._custom_rules:
            del self._custom_rules[name]
            self._audit("remove_rule", f"删除自定义规则: {name}")
            return {"success": True, "removed": name}
        return {"success": False, "error": f"规则不存在: {name}"}

    # ─── 分发器 ────────────────────────────────────────
    def _dispatch(self, p: Dict) -> Dict:
        a = p.get("action", "status")

        try:
            # ─── 脱敏操作 ───
            if a == "mask":
                value = p.get("value", "")
                mask_type = p.get("type", "phone")
                return {"success": True, "orig_len": len(str(value)),
                        "masked": self.mask_value(value, mask_type)}

            if a == "mask_dict":
                data = p.get("data", {})
                fields = p.get("fields")
                field_types = p.get("field_types")
                return {"success": True, "masked": self.mask_dict(data, fields, field_types)}

            if a == "mask_batch":
                records = p.get("records", [])
                fields = p.get("fields")
                field_types = p.get("field_types")
                return {"success": True, "count": len(records),
                        "masked": self.mask_batch(records, fields, field_types)}

            if a == "detect":
                value = p.get("value", "")
                types_found = []
                v = str(value).strip()
                if re.match(r"^1[3-9]\d{9}$", v):
                    types_found.append("phone")
                if re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", v):
                    types_found.append("email")
                if re.match(r"^\d{15}$|^\d{17}[\dXx]$", v):
                    types_found.append("idcard")
                if re.match(r"^\d{16,19}$", v):
                    types_found.append("bankcard")
                return {"success": True, "types": types_found, "value_preview": v[:20]}

            # ─── 规则管理 ───
            if a == "rules":
                return {
                    "success": True,
                    "builtin": {k: v["description"] for k, v in self._rules.items()},
                    "custom": {k: v["description"] for k, v in self._custom_rules.items()},
                }

            if a == "add_rule":
                return self.add_custom_rule(
                    p.get("name", ""), p.get("pattern", ""),
                    p.get("replacement", ""), p.get("description", ""),
                )

            if a == "remove_rule":
                return self.remove_rule(p.get("name", ""))

            # ─── 审计/统计 ───
            if a == "stats":
                uptime = round(time.time() - self._stats["started_at"], 1)
                return {
                    "success": True,
                    "stats": {
                        "total_masks": self._stats["total_masks"],
                        "total_batches": self._stats["total_batches"],
                        "by_type": self._stats["by_type"],
                        "uptime_seconds": uptime,
                    },
                }

            if a == "audit_log":
                limit = int(p.get("limit", 100))
                level_filter = p.get("level", "")
                entries = self._audit_log
                if level_filter:
                    entries = [e for e in entries if e["level"] == level_filter]
                return {"success": True, "entries": entries[-limit:], "total": len(self._audit_log)}

            if a == "export_rules":
                return {
                    "success": True,
                    "format": "json",
                    "rules": {
                        "builtin": {k: {"description": v["description"]} for k, v in self._rules.items()},
                        "custom": self._custom_rules,
                    },
                }

            # ─── JSON 文本脱敏（对 JSON 字符串中的值递归脱敏）───
            if a == "mask_json":
                raw = p.get("json", "")
                keys = p.get("keys", [])
                try:
                    parsed = json.loads(raw)
                    masked = self._mask_json_recursive(parsed, keys or [])
                    return {"success": True, "masked_json": json.dumps(masked, ensure_ascii=False)}
                except json.JSONDecodeError as e:
                    return {"success": False, "error": f"JSON解析失败: {e}"}

            if a == "status":
                return {
                    "success": True,
                    "rules": len(self._rules) + len(self._custom_rules),
                    "total_masks": self._stats["total_masks"],
                    "uptime": round(time.time() - self._stats["started_at"], 1),
                }

            return {"success": False, "error": f"unknown_action: {a}"}

        except Exception as e:
            logger.error("[DataMasking] %s 失败: %s", a, e, exc_info=True)
            return {"success": False, "error": str(e)}

    def _mask_json_recursive(self, obj: Any, keys: List[str]) -> Any:
        """递归脱敏 JSON 对象中的指定字段"""
        if isinstance(obj, dict):
            return {
                k: self._mask_json_recursive(v, keys)
                if isinstance(v, (dict, list))
                else self.mask_value(str(v), "phone") if k in keys else v
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [self._mask_json_recursive(item, keys) for item in obj]
        return obj

    async def shutdown(self) -> None:
        self._audit("shutdown", "数据脱敏引擎关闭")
        self.status = ModuleStatus.STOPPED


module_class = DataMaskingEngine
