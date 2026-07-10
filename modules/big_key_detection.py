"""
AUTO-EVO-AI V0.1 — 大Key检测模块
Grade: A (生产级) | Category: 性能监控
职责：检测缓存/数据库中的大Key，分析内存占用，提供优化建议
"""

__module_meta__ = {
        "id": "big-key-detection",
        "name": "Big Key Detection",
        "version": "V0.1",
        "group": "database",
        "inputs": [
            {
                "name": "key",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "data_type",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "size",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "access_freq",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "history",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "days",
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
        "triggers": [],
        "depends_on": [],
        "tags": [
            "config",
            "big",
            "manager"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — 大Key检测模块 Grade: A (生产级) | Category: 性能监控"
    }

import os
import asyncio
import time
import logging
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.tracing import trace_operation
from modules._base.metrics import MetricsCollector, metrics_collector

logger = logging.getLogger("big_key_detection")

class KeyType(Enum):
    STRING = "string"
    HASH = "hash"
    LIST = "list"
    SET = "set"
    ZSET = "zset"
    STREAM = "stream"
    UNKNOWN = "unknown"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class KeyInfo:
    """Key详细信息"""

    key: str
    key_type: KeyType
    size_bytes: int
    element_count: int
    encoding: str
    ttl: int = -1
    last_access: float = 0.0
    created_at: str = ""

@dataclass
class BigKeyRecord:
    """大Key记录"""

    key: str
    key_type: KeyType
    size_bytes: int
    element_count: int
    risk_level: RiskLevel
    detected_at: str
    suggestions: list[str] = field(default_factory=list)

@dataclass
class ThresholdConfig:
    """阈值配置"""

    key_type: KeyType
    size_threshold_bytes: int
    element_threshold: int
    risk_if_exceed: RiskLevel

class BigKeyRiskAssessor:
    """大键风险评估器 — 评估大键风险等级、预测增长趋势、生成优化建议"""

    def __init__(self):
        self._risk_thresholds = {
            "hash": {"warn": 5000, "critical": 50000},
            "list": {"warn": 10000, "critical": 100000},
            "set": {"warn": 50000, "critical": 500000},
            "zset": {"warn": 50000, "critical": 500000},
            "string": {"warn": 10240, "critical": 102400},
        }

    def assess_risk(self, key: str, data_type: str, size: int, access_freq: int = 0) -> dict[str, Any]:
        """评估单个大键的风险等级"""
        thresholds = self._risk_thresholds.get(data_type, {"warn": 10000, "critical": 100000})
        if size >= thresholds["critical"]:
            level = "critical"
        elif size >= thresholds["warn"]:
            level = "warning"
        else:
            level = "normal"

        impact_score = 0.0
        if level == "critical":
            impact_score = 0.9
        elif level == "warning":
            impact_score = 0.5

        if access_freq > 100:
            impact_score *= 1.5
        elif access_freq > 10:
            impact_score *= 1.2

        return {
            "key": key,
            "type": data_type,
            "size": size,
            "risk_level": level,
            "impact_score": round(min(impact_score, 1.0), 2),
            "access_frequency": access_freq,
            "recommended_action": self._get_recommendation(data_type, size, level),
        }

    def predict_growth(self, history: list[dict[str, Any]], days: int = 30) -> dict[str, Any]:
        """根据历史数据预测大键增长趋势"""
        if len(history) < 2:
            return {"trend": "insufficient_data"}
        sizes = [h.get("size", 0) for h in history]
        growth_rates = []
        for i in range(1, len(sizes)):
            if sizes[i - 1] > 0:
                growth_rates.append((sizes[i] - sizes[i - 1]) / sizes[i - 1])

        avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0
        current = sizes[-1]
        projected = current * ((1 + avg_growth) ** days)

        return {
            "current_size": current,
            "avg_growth_rate": round(avg_growth * 100, 2),
            "projected_size": round(projected, 0),
            "projected_days": days,
            "trend": "growing" if avg_growth > 0.01 else "stable" if avg_growth > -0.01 else "shrinking",
            "days_to_critical": self._days_to_threshold(current, avg_growth, "critical") if avg_growth > 0 else None,
        }

    def batch_assess(self, keys: list[dict[str, Any]]) -> dict[str, Any]:
        """批量评估多个大键"""
        results = []
        critical_count = 0
        warning_count = 0
        for k in keys:
            assessment = self.assess_risk(
                k.get("key", ""), k.get("type", "string"), k.get("size", 0), k.get("access_freq", 0)
            )
            results.append(assessment)
            if assessment["risk_level"] == "critical":
                critical_count += 1
            elif assessment["risk_level"] == "warning":
                warning_count += 1

        results.sort(key=lambda x: x["impact_score"], reverse=True)
        return {
            "total": len(keys),
            "critical": critical_count,
            "warning": warning_count,
            "normal": len(keys) - critical_count - warning_count,
            "top_risks": results[:10],
            "health_score": round((1 - critical_count / max(len(keys), 1)) * 100, 1),
        }

    def generate_report(self, assessments: list[dict[str, Any]]) -> dict[str, Any]:
        """生成大键风险报告"""
        by_type = {}
        for a in assessments:
            t = a.get("type", "unknown")
            by_type.setdefault(t, {"count": 0, "total_size": 0, "critical": 0})
            by_type[t]["count"] += 1
            by_type[t]["total_size"] += a.get("size", 0)
            if a.get("risk_level") == "critical":
                by_type[t]["critical"] += 1

        top_actions = {}
        for a in assessments:
            rec = a.get("recommended_action", "")
            top_actions[rec] = top_actions.get(rec, 0) + 1

        return {
            "summary": {
                "total_keys": len(assessments),
                "critical": sum(1 for a in assessments if a.get("risk_level") == "critical"),
            },
            "by_type": by_type,
            "recommended_actions": top_actions,
        }

    def _get_recommendation(self, data_type: str, size: int, level: str) -> str:
        if level == "critical":
            return "split_immediately"
        if data_type == "hash" and size > 10000:
            return "consider_hash_splitting"
        if data_type == "list" and size > 5000:
            return "use_pagination_or_ltrim"
        if data_type == "string" and size > 10000:
            return "compress_or_move_to_external_storage"
        return "monitor"

    def _days_to_threshold(self, current: int, growth_rate: float, level: str) -> int:
        if growth_rate <= 0:
            return -1
        return 30

class BigKeyDetectionManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """大Key检测管理器 - 生产级实现"""

    MODULE_ID = "big_key_detection"
    MODULE_NAME = "大Key检测"
    VERSION = "V0.1"

    def __init__(self, config: dict[str, Any] | None = None):

        super().__init__(config)
        self._keys: dict[str, KeyInfo] = {}
        self._big_keys: list[BigKeyRecord] = []
        self._scan_count = 0
        self._counter = 0
        self._thresholds: dict[KeyType, ThresholdConfig] = {}
        self._load_default_thresholds()

    def _next_id(self) -> str:
        self._counter += 1
        raw = f"bk_{self._counter}_{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:10]

    def _load_default_thresholds(self):
        """加载默认检测阈值（每种类型保留最大阈值）"""
        all_thresholds = [
            (KeyType.STRING, 10 * 1024, 1, RiskLevel.LOW),
            (KeyType.STRING, 100 * 1024, 1, RiskLevel.HIGH),
            (KeyType.STRING, 1024 * 1024, 1, RiskLevel.CRITICAL),
            (KeyType.HASH, 5000, 5000, RiskLevel.LOW),
            (KeyType.HASH, 50000, 50000, RiskLevel.HIGH),
            (KeyType.HASH, 500000, 500000, RiskLevel.CRITICAL),
            (KeyType.LIST, 5000, 5000, RiskLevel.LOW),
            (KeyType.LIST, 50000, 50000, RiskLevel.HIGH),
            (KeyType.SET, 5000, 5000, RiskLevel.LOW),
            (KeyType.ZSET, 5000, 5000, RiskLevel.LOW),
            (KeyType.STREAM, 5000, 5000, RiskLevel.LOW),
        ]
        # 按风险等级数值比较
        _risk_rank = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
        for kt, size, elements, risk in all_thresholds:
            existing = self._thresholds.get(kt)
            if existing is None or _risk_rank.get(risk, 0) > _risk_rank.get(existing.risk_if_exceed, 0):
                self._thresholds[kt] = ThresholdConfig(
                    key_type=kt, size_threshold_bytes=size, element_threshold=elements, risk_if_exceed=risk
                )

    def initialize(self) -> bool:
        try:
            self._load_sample_keys()
            logger.info("大Key检测初始化完成")
            return True
        except Exception as e:
            logger.error(f"大Key检测初始化失败: {e}")
            return False

    def _load_sample_keys(self):
        """加载示例Key数据（实际生产环境从Redis/DB采样）"""
        samples = [
            ("user:profile:1001", KeyType.HASH, 2048, 45, "hashtable", -1),
            ("cache:product_list", KeyType.LIST, 256000, 8000, "quicklist", 3600),
            ("session:abc123def456", KeyType.STRING, 4096, 1, "raw", 1800),
            ("analytics:daily:2026-05-05", KeyType.HASH, 102400, 15000, "hashtable", 86400),
            ("queue:email:pending", KeyType.LIST, 512000, 25000, "quicklist", -1),
            ("config:feature_flags", KeyType.HASH, 512, 20, "ziplist", -1),
            ("rate_limit:ip:192.168.1.1", KeyType.STRING, 64, 1, "embstr", 60),
            ("social:followers:1001", KeyType.SET, 1048576, 100000, "hashtable", -1),
            ("ranking:scoreboard", KeyType.ZSET, 204800, 10000, "skiplist", -1),
        ]
        now = time.time()
        for key, kt, size, count, enc, ttl in samples:
            self._keys[key] = KeyInfo(
                key=key,
                key_type=kt,
                size_bytes=size,
                element_count=count,
                encoding=enc,
                ttl=ttl,
                last_access=now,
                created_at=datetime.now().isoformat(),
            )

    def _assess_risk(self, kt: KeyType, size_bytes: int, element_count: int) -> tuple:
        """评估风险等级和生成建议"""
        # 找到最接近的阈值
        thresholds = sorted(
            [t for t in self._thresholds.values() if t.key_type == kt], key=lambda t: t.size_threshold_bytes
        )
        risk = RiskLevel.LOW
        suggestions = []
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024

        _risk_rank = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
        for t in thresholds:
            if size_bytes >= t.size_threshold_bytes or element_count >= t.element_threshold:
                if _risk_rank.get(t.risk_if_exceed, 0) > _risk_rank.get(risk, 0):
                    risk = t.risk_if_exceed

        if risk.value in ("high", "critical"):
            if kt == KeyType.STRING:
                suggestions.append(f"String大小{size_mb:.1f}MB，考虑压缩或拆分")
                suggestions.append("使用客户端压缩(zstd/gzip)减少存储")
            elif kt == KeyType.HASH:
                suggestions.append(f"Hash含{element_count}个字段，考虑按业务拆分")
                suggestions.append("可按范围分片: user:profile:1001:base, user:profile:1001:ext")
            elif kt == KeyType.LIST:
                suggestions.append(f"List含{element_count}个元素，考虑使用Stream或分页")
                suggestions.append("使用LRANGE分页访问，避免LRANGE 0 -1")
            elif kt == KeyType.SET:
                suggestions.append(f"Set含{element_count}个成员，考虑使用BloomFilter或拆分")
            elif kt == KeyType.ZSET:
                suggestions.append(f"ZSet含{element_count}个成员，考虑按分数范围分片")
            if size_mb > 1:
                suggestions.append(f"Key占用{size_mb:.1f}MB内存，可能阻塞Redis主线程")
                suggestions.append("建议使用UNLINK异步删除，避免DEL阻塞")

        return risk, suggestions

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("big_key_detection_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        actions = {
            "register_key": self._exec_register_key,
            "scan": self._exec_scan,
            "get_big_keys": self._exec_get_big_keys,
            "analyze_key": self._exec_analyze_key,
            "remove_key": self._exec_remove_key,
            "set_threshold": self._exec_set_threshold,
            "get_thresholds": self._exec_get_thresholds,
            "get_stats": self._exec_get_stats,
            "top_keys": self._exec_top_keys,
        }
        handler = actions.get(action)
        if not handler:
            return {"success": False, "error": f"未知操作: {action}"}
        return handler(params)
        return {"status": "healthy", "module": "big_key_detection"}

    def _exec_register_key(self, p: dict) -> dict:
        """注册/更新Key信息"""
        key = p["key"]
        kt = KeyType(p.get("type", "string"))
        self._keys[key] = KeyInfo(
            key=key,
            key_type=kt,
            size_bytes=p.get("size_bytes", 0),
            element_count=p.get("element_count", 0),
            encoding=p.get("encoding", "unknown"),
            ttl=p.get("ttl", -1),
            last_access=time.time(),
            created_at=datetime.now().isoformat(),
        )
        return {"success": True, "result": {"key": key, "registered": True}}

    def _exec_scan(self, p: dict) -> dict:
        """执行大Key扫描"""
        pattern = p.get("pattern", "*")
        min_size = p.get("min_size_bytes", 0)
        self._big_keys.clear()
        scanned = 0
        found = 0
        for key, info in self._keys.items():
            if not self._match_pattern(key, pattern):
                continue
            scanned += 1
            if info.size_bytes >= min_size:
                risk, suggestions = self._assess_risk(info.key_type, info.size_bytes, info.element_count)
                if risk.value in (RiskLevel.MEDIUM.value, RiskLevel.HIGH.value, RiskLevel.CRITICAL.value):
                    record = BigKeyRecord(
                        key=key,
                        key_type=info.key_type,
                        size_bytes=info.size_bytes,
                        element_count=info.element_count,
                        risk_level=risk,
                        detected_at=datetime.now().isoformat(),
                        suggestions=suggestions,
                    )
                    self._big_keys.append(record)
                    found += 1
        self._scan_count += 1
        self.record_metric("bigkey_scan_total", 1)
        self.record_metric("bigkey_found_total", found)
        self._big_keys.sort(key=lambda r: r.size_bytes, reverse=True)
        return {
            "success": True,
            "result": {
                "scan_id": self._scan_count,
                "scanned_keys": scanned,
                "big_keys_found": found,
                "top_key_size_mb": round(self._big_keys[0].size_bytes / 1024 / 1024, 2) if self._big_keys else 0,
            },
        }

    def _exec_get_big_keys(self, p: dict) -> dict:
        """获取大Key列表"""
        risk_filter = p.get("risk_level", "")
        limit = p.get("limit", 20)
        keys = self._big_keys
        if risk_filter:
            keys = [k for k in keys if k.risk_level.value == risk_filter]
        return {
            "success": True,
            "result": {
                "total": len(keys),
                "keys": [
                    {
                        "key": k.key,
                        "type": k.key_type.value,
                        "size_kb": round(k.size_bytes / 1024, 1),
                        "elements": k.element_count,
                        "risk": k.risk_level.value,
                        "suggestions": k.suggestions,
                    }
                    for k in keys[:limit]
                ],
            },
        }

    def _exec_analyze_key(self, p: dict) -> dict:
        """分析单个Key"""
        key = p["key"]
        if key not in self._keys:
            return {"success": False, "error": f"Key不存在: {key}"}
        info = self._keys[key]
        risk, suggestions = self._assess_risk(info.key_type, info.size_bytes, info.element_count)
        return {
            "success": True,
            "result": {
                "key": info.key,
                "type": info.key_type.value,
                "size_bytes": info.size_bytes,
                "size_kb": round(info.size_bytes / 1024, 2),
                "size_mb": round(info.size_bytes / 1024 / 1024, 4),
                "element_count": info.element_count,
                "encoding": info.encoding,
                "ttl": info.ttl,
                "risk_level": risk.value,
                "suggestions": suggestions,
            },
        }

    def _exec_remove_key(self, p: dict) -> dict:
        """移除Key（异步删除建议）"""
        key = p.get("key", "")
        if key and key in self._keys:
            size = self._keys[key].size_bytes
            del self._keys[key]
            return {"success": True, "result": {"key": key, "freed_bytes": size}}
        return {"success": False, "error": "Key不存在"}

    def _exec_set_threshold(self, p: dict) -> dict:
        """设置阈值"""
        kt = KeyType(p.get("key_type", "string"))
        self._thresholds[kt] = ThresholdConfig(
            key_type=kt,
            size_threshold_bytes=p.get("size_bytes", 10240),
            element_threshold=p.get("elements", 5000),
            risk_if_exceed=RiskLevel(p.get("risk", "low")),
        )
        return {"success": True, "result": {"key_type": kt.value, "threshold_set": True}}

    def _exec_get_thresholds(self, p: dict) -> dict:
        return {
            "success": True,
            "result": {
                t.key_type.value: {
                    "size_bytes": t.size_threshold_bytes,
                    "elements": t.element_threshold,
                    "risk": t.risk_if_exceed.value,
                }
                for t in self._thresholds.values()
            },
        }

    def _exec_get_stats(self, p: dict) -> dict:
        total_size = sum(k.size_bytes for k in self._keys.values())
        return {
            "success": True,
            "result": {
                "total_keys": len(self._keys),
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "big_keys_count": len(self._big_keys),
                "scan_count": self._scan_count,
                "by_type": dict(defaultdict(int, {k.key_type.value: 1 for k in self._keys.values()})),
            },
        }

    def _exec_top_keys(self, p: dict) -> dict:
        """获取最大的N个Key"""
        n = min(p.get("limit", 10), 50)
        sorted_keys = sorted(self._keys.values(), key=lambda k: k.size_bytes, reverse=True)[:n]
        return {
            "success": True,
            "result": [
                {
                    "key": k.key,
                    "type": k.key_type.value,
                    "size_kb": round(k.size_bytes / 1024, 1),
                    "elements": k.element_count,
                }
                for k in sorted_keys
            ],
        }

    def _match_pattern(self, key: str, pattern: str) -> bool:
        """简单通配符匹配"""
        import fnmatch

        return fnmatch.fnmatch(key, pattern)

    def health_check(self) -> dict[str, Any]:
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy",
                "module_id": self.MODULE_ID,
                "total_keys": len(self._keys),
                "big_keys": len(self._big_keys),
                "scans": self._scan_count,
                "last_check": datetime.now().isoformat(),
            }
        )
        return result

    def shutdown(self) -> bool:
        logger.info("大Key检测关闭")
        return True

    def _audit_detection(self, event: str, detail: dict) -> None:
        """记录审计日志 - 检测到big key或执行清理操作时调用"""
        if hasattr(self, "_audit") and self._audit:
            self._audit.log(event, detail)

    def audit_scan_result(self, found_count: int, scan_duration: float, risk_high: int = 0) -> None:
        """审计扫描结果"""
        self._audit_detection(
            "big_key_scan",
            {
                "found_count": found_count,
                "duration_ms": round(scan_duration * 1000, 2),
                "high_risk": risk_high,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def audit_key_removal(self, key_name: str, key_type: str, size_bytes: int) -> None:
        """审计键删除操作"""
        self._audit_detection(
            "big_key_removed",
            {"key": key_name, "type": key_type, "size_bytes": size_bytes, "timestamp": datetime.now().isoformat()},
        )

    def audit_threshold_change(self, key_type: str, old_val: int, new_val: int) -> None:
        """审计阈值变更"""
        self._audit_detection(
            "threshold_changed",
            {
                "key_type": key_type,
                "old_threshold": old_val,
                "new_threshold": new_val,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def get_memory_footprint(self) -> dict[str, Any]:
        """获取所有监控键的内存占用汇总"""
        import sys

        total = 0
        by_type: dict[str, int] = {}
        for key_info in self._keys.values():
            sz = key_info.get("size_bytes", 0)
            total += sz
            kt = key_info.get("key_type", "unknown")
            by_type[kt] = by_type.get(kt, 0) + sz
        return {"total_bytes": total, "total_mb": round(total / 1024 / 1024, 2), "by_type": by_type}

    def export_report(self, include_details: bool = False) -> dict:
        """导出大键检测报告"""
        big_sorted = sorted(self._big_keys.values(), key=lambda x: x.get("size_bytes", 0), reverse=True)
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_monitored": len(self._keys),
            "big_keys_count": len(self._big_keys),
            logger.info(y_footprint": self.get_memory_footprint(),)
            "top_big_keys": big_sorted[:20]
            if include_details
            else [
                {"key": k.get("key_name"), "size": k.get("size_bytes"), "type": k.get("key_type")}
                for k in big_sorted[:20]
            ],
            "scan_count": self._scan_count,
        }
        return report

    def track_key_growth(self, key_name: str, current_size: int) -> dict:
        """追踪键增长趋势"""
        history_key = f"growth:{key_name}"
        if not hasattr(self, "_growth_history"):
            self._growth_history: dict[str, list] = {}
        history = self._growth_history.setdefault(history_key, [])
        history.append({"size": current_size, "ts": datetime.now().isoformat()})
        if len(history) > 100:
            history[:] = history[-100:]
        if len(history) >= 2:
            growth_rate = (current_size - history[-2]["size"]) / max(history[-2]["size"], 1)
            return {
                "key": key_name,
                "current_size": current_size,
                "growth_rate": round(growth_rate, 4),
                "history_len": len(history),
            }
        return {"key": key_name, "current_size": current_size, "growth_rate": 0.0, "history_len": len(history)}

    def recommend_action(self, key_name: str, key_type: str, size_bytes: int, element_count: int) -> dict:
        """根据键特征给出优化建议"""
        recommendations = []
        if key_type == "string" and size_bytes > 10 * 1024 * 1024:
            recommendations.append("考虑压缩存储或拆分为多个小键")
        elif key_type == "hash" and element_count > 10000:
            recommendations.append("考虑按业务维度拆分为多个小hash")
        elif key_type == "list" and element_count > 50000:
            recommendations.append("考虑使用stream或分页加载")
        elif key_type == "set" and element_count > 50000:
            recommendations.append("考虑使用bitmap或bloom filter替代")
        elif key_type == "zset" and element_count > 50000:
            recommendations.append("考虑按分数范围拆分")
        if size_bytes > 100 * 1024 * 1024:
            recommendations.append("严重警告: 键超过100MB，可能导致Redis阻塞")
        risk_level = (
            "critical" if size_bytes > 100 * 1024 * 1024 else "high" if size_bytes > 10 * 1024 * 1024 else "medium"
        )
        return {
            "key": key_name,
            "risk_level": risk_level,
            "recommendations": recommendations,
            "size_mb": round(size_bytes / 1024 / 1024, 2),
        }

    def batch_analyze(self, keys: list[dict]) -> list[dict]:
        """批量分析多个键的风险和建议"""
        results = []
        for k in keys:
            rec = self.recommend_action(
                k.get("key_name", ""), k.get("key_type", ""), k.get("size_bytes", 0), k.get("element_count", 0)
            )
            results.append(rec)
        return results

module_class = BigKeyDetectionManager
