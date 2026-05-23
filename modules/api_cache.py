"""
AUTO-EVO-AI v7.0 — API缓存
Grade: A (生产级) | Category: API基础设施
职责：API响应缓存、缓存策略管理、TTL过期、缓存穿透/雪崩防护、缓存统计
"""

__module_meta__ = {
    "id": "api-cache",
    "name": "Api Cache",
    "version": "1.0.0",
    "group": "api",
    "inputs": [
        {"name": "task_id", "type": "string", "required": True, "description": ""},
        {"name": "endpoint", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "priority", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "task_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "webhook", "config": {"path": "/hooks/api_cache", "method": "POST"}}],
    "depends_on": [],
    "tags": ["engine", "api", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 — API缓存 Grade: A (生产级) | Category: API基础设施",
}

import os
import asyncio
import time
import time as tmod
import logging
import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger("api_cache")

class EvictionPolicy(Enum):
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"

class CacheLevel(Enum):
    L1 = "l1"  # 内存热缓存
    L2 = "l2"  # 持久缓存

@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: str
    ttl_seconds: float
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    hit_count: int = 0
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    cache_level: str = "l1"  # l1=内存, l2=持久
    source: str = ""  # 来源API端点
    expires_at: float = 0  # 绝对过期时间戳
    version: int = 1  # 数据版本号（CAS乐观锁）
    compression_type: str = ""  # 压缩算法
    compressed_size: int = 0  # 压缩后大小

    @property
    def expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

@dataclass
class CacheRule:
    """缓存规则"""

class CacheWarmingEngine(object):
    """缓存预热引擎 — 预热高频接口、防缓存穿透、批量加载"""

    def __init__(self):
        self._warmup_tasks: Dict[str, Dict] = {}
        self._bloom_filter: set = set()  # 简易布隆过滤防穿透

    def add_warmup_task(
        self, task_id: str, endpoint: str, params: Dict, priority: int = 5, repeat_interval: int = 0
    ) -> Dict:
        """添加预热任务"""
        self._warmup_tasks[task_id] = {
            "endpoint": endpoint,
            "params": params,
            "priority": priority,
            "repeat_interval": repeat_interval,
            "last_run": 0,
            "status": "pending",
        }
        return {"task_id": task_id, "status": "scheduled"}

    def get_warmup_queue(self, limit: int = 10) -> List[Dict]:
        """获取待执行的预热队列（按优先级排序）"""
        pending = [t for t in self._warmup_tasks.values() if t["status"] == "pending"]
        pending.sort(key=lambda t: -t["priority"])
        return pending[:limit]

    def mark_warmed(self, task_id: str) -> None:
        """标记预热完成"""
        task = self._warmup_tasks.get(task_id)
        if task:
            task["status"] = "warmed"
            task["last_run"] = time.time()

    def check_penetration(self, key: str) -> bool:
        """检查是否命中布隆过滤（防缓存穿透）"""
        return key in self._bloom_filter

    def mark_penetration_protected(self, key: str) -> None:
        """标记为穿透保护的key"""
        self._bloom_filter.add(key)

    def get_warming_stats(self) -> Dict:
        pending = sum(1 for t in self._warmup_tasks.values() if t["status"] == "pending")
        warmed = sum(1 for t in self._warmup_tasks.values() if t["status"] == "warmed")
        return {
            "total_tasks": len(self._warmup_tasks),
            "pending": pending,
            "warmed": warmed,
            "bloom_filter_size": len(self._bloom_filter),
        }

    def predict_warmup_candidates(self, access_log: List[Dict]) -> List[Dict]:
        """基于访问日志预测需要预热的key（访问频率突然上升的）"""
        from collections import Counter

        key_counts = Counter(entry.get("key", "") for entry in access_log)
        if not key_counts:
            return []
        avg = sum(key_counts.values()) / len(key_counts)
        hot_candidates = [(k, c) for k, c in key_counts.items() if c > avg * 2]
        hot_candidates.sort(key=lambda x: -x[1])
        return [{"key": k, "access_count": c, "is_above_avg": True} for k, c in hot_candidates[:10]]

    def generate_warmup_plan(self, hot_keys: List[str], concurrency: int = 5) -> Dict:
        """生成并行预热计划"""
        batches = []
        for i in range(0, len(hot_keys), concurrency):
            batches.append(hot_keys[i : i + concurrency])
        return {
            "total_keys": len(hot_keys),
            "batches": len(batches),
            "concurrency": concurrency,
            "estimated_time_seconds": len(batches),
            "batch_plan": [{"batch": j + 1, "keys": batch} for j, batch in enumerate(batches)],
        }

    def validate_cache_consistency(self, cache_snapshot: Dict[str, Dict]) -> Dict:
        """验证缓存一致性 — 对比预热任务与实际缓存"""
        warmed_keys = {t["endpoint"] for t in self._warmup_tasks.values() if t["status"] == "warmed"}
        cached_keys = set(cache_snapshot.keys())
        missing = warmed_keys - cached_keys
        stale = []
        for key in warmed_keys & cached_keys:
            entry = cache_snapshot.get(key, {})
            if entry.get("expires_at", 0) < time.time() + 60:
                stale.append(key)
        return {
            "warmed_tasks": len(warmed_keys),
            "cached": len(cached_keys),
            "missing_in_cache": list(missing),
            "about_to_expire": stale,
            "consistency_score": round(len(warmed_keys & cached_keys) / max(len(warmed_keys), 1), 4),
        }

class CacheRule:
    """缓存规则"""

    rule_id: str
    pattern: str
    ttl_seconds: float
    methods: List[str] = field(default_factory=lambda: ["GET"])
    enabled: bool = True
    priority: int = 0

class ApiCacheManager(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """API缓存管理器"""

    MODULE_ID = "api_cache"
    MODULE_NAME = "API缓存"
    VERSION = "7.0.0"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._cache: Dict[str, CacheEntry] = {}
        self._rules: Dict[str, CacheRule] = {}
        self._eviction_policy = EvictionPolicy.LRU
        self._max_size_mb: float = 100.0
        self._max_entries: int = 10000
        self._warming_engine = CacheWarmingEngine()
        self._stats_hits: int = 0
        self._stats_misses: int = 0
        self._stats_evictions: int = 0
        self._rule_counter: int = 0

    def initialize(self) -> None:
        try:
            pass
            # 默认规则
            defaults = [
                ("status_api", r"/api/status", 10, ["GET"]),
                ("modules_list", r"/api/modules$", 60, ["GET"]),
                ("module_detail", r"/api/modules/\w+", 120, ["GET"]),
                ("health_check", r"/health", 5, ["GET"]),
                ("static_content", r"/static/.*", 3600, ["GET"]),
            ]
            for name, pattern, ttl, methods in defaults:
                self._rule_counter += 1
                rule = CacheRule(
                    rule_id=f"rule_{self._rule_counter}", pattern=pattern, ttl_seconds=ttl, methods=methods
                )
                self._rules[rule.rule_id] = rule
            if self._audit:
                self._audit.log("api_cache_initialized", {"rules": len(self._rules), "max_entries": self._max_entries})
            self.stats.success_count += 1
            logger.info("API缓存初始化完成")
        except Exception as e:
            logger.error(f"API缓存初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("api_cache_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "get":
                key = params.get("key", "")
                if not key:
                    return {"success": False, "error": "Missing: key"}
                result = self._get(key)
                return {"success": True, "result": result}

            elif action == "set":
                key = params.get("key", "")
                value = params.get("value", "")
                ttl = params.get("ttl", 60)
                tags = params.get("tags", [])
                if not key:
                    return {"success": False, "error": "Missing: key"}
                result = self._set(key, value, ttl, tags)
                ok = True
                return {"success": True, "result": result}

            elif action == "delete":
                key = params.get("key", "")
                if not key:
                    return {"success": False, "error": "Missing: key"}
                deleted = self._cache.pop(key, None)
                ok = deleted is not None
                return {"success": ok, "result": {"deleted": deleted is not None}}

            elif action == "invalidate_by_tag":
                tag = params.get("tag", "")
                if not tag:
                    return {"success": False, "error": "Missing: tag"}
                count = 0
                to_delete = [k for k, v in self._cache.items() if tag in v.tags]
                for k in to_delete:
                    del self._cache[k]
                    count += 1
                ok = True
                return {"success": True, "result": {"invalidated": count}}

            elif action == "invalidate_by_pattern":
                pattern = params.get("pattern", "")
                if not pattern:
                    return {"success": False, "error": "Missing: pattern"}
                count = 0
                to_delete = [k for k in self._cache if re.search(pattern, k)]
                for k in to_delete:
                    del self._cache[k]
                    count += 1
                ok = True
                return {"success": True, "result": {"invalidated": count}}

            elif action == "add_rule":
                name = params.get("name", "")
                pattern = params.get("pattern", "")
                ttl = params.get("ttl", 60)
                methods = params.get("methods", ["GET"])
                if not name or not pattern:
                    return {"success": False, "error": "Missing: name, pattern"}
                self._rule_counter += 1
                rule = CacheRule(
                    rule_id=f"rule_{self._rule_counter}", pattern=pattern, ttl_seconds=ttl, methods=methods
                )
                self._rules[rule.rule_id] = rule
                ok = True
                return {"success": True, "result": {"rule_id": rule.rule_id, "name": name, "ttl": ttl}}

            elif action == "cleanup_expired":
                count = self._cleanup_expired()
                ok = True
                return {"success": True, "result": {"cleaned": count}}

            elif action == "get_stats":
                total_size = sum(v.size_bytes for v in self._cache.values())
                hit_rate = self._stats_hits / max(self._stats_hits + self._stats_misses, 1)
                return {
                    "success": True,
                    "result": {
                        "entries": len(self._cache),
                        "max_entries": self._max_entries,
                        "total_bytes": total_size,
                        "hits": self._stats_hits,
                        "misses": self._stats_misses,
                        "hit_rate": round(hit_rate, 4),
                        "evictions": self._stats_evictions,
                        "rules": len(self._rules),
                    },
                }

            elif action == "add_warmup":
                return {
                    "success": True,
                    "result": self._warming_engine.add_warmup_task(
                        params.get("task_id", ""),
                        params.get("endpoint", ""),
                        params.get("params", {}),
                        params.get("priority", 5),
                    ),
                }

            elif action == "warmup_queue":
                return {"success": True, "result": self._warming_engine.get_warmup_queue()}

            elif action == "mark_warmed":
                self._warming_engine.mark_warmed(params.get("task_id", ""))
                return {"success": True}

            elif action == "warming_stats":
                return {"success": True, "result": self._warming_engine.get_warming_stats()}

            elif action == "hotkeys":
                return {"success": True, "result": self._detect_hotkeys(params.get("top_n", 10))}

            elif action == "multi_level_stats":
                return {"success": True, "result": self._multi_level_stats()}

            elif action == "eviction_candidates":
                return {"success": True, "result": self._analyze_eviction_candidates(params.get("count", 10))}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        usage_pct = len(self._cache) / max(self._max_entries, 1)
        return {
            "status": "degraded" if usage_pct > 0.9 else "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "entries": len(self._cache),
            "usage_pct": round(usage_pct, 4),
            "hit_rate": round(self._stats_hits / max(self._stats_hits + self._stats_misses, 1), 4),
        }

    def shutdown(self) -> None:
        self._cache.clear()

    def _get(self, key: str) -> Dict:
        entry = self._cache.get(key)
        if entry is None:
            self._stats_misses += 1
            return {"hit": False, "key": key}
        if entry.expired:
            del self._cache[key]
            self._stats_misses += 1
            return {"hit": False, "key": key, "reason": "expired"}
        entry.hit_count += 1
        entry.last_accessed = time.time()
        self._stats_hits += 1
        return {
            "hit": True,
            "key": key,
            "value": entry.value,
            "age_seconds": round(entry.age_seconds, 1),
            "hit_count": entry.hit_count,
        }

    def _set(self, key: str, value: str, ttl: float, tags: List[str]) -> Dict:
        if len(self._cache) >= self._max_entries:
            self._evict()
        entry = CacheEntry(key=key, value=value, ttl_seconds=ttl, tags=tags, size_bytes=len(value.encode()))
        self._cache[key] = entry
        self.stats.success_count += 1
        return {"key": key, "ttl": ttl, "size_bytes": entry.size_bytes, "total_entries": len(self._cache)}

    def _evict(self):
        """淘汰策略"""
        if self._eviction_policy == EvictionPolicy.LRU:
            oldest = min(self._cache.values(), key=lambda e: e.last_accessed)
        elif self._eviction_policy == EvictionPolicy.LFU:
            oldest = min(self._cache.values(), key=lambda e: e.hit_count)
        else:
            oldest = min(self._cache.values(), key=lambda e: e.created_at)
        self._cache.pop(oldest.key, None)
        self._stats_evictions += 1

    def _cleanup_expired(self) -> int:
        expired_keys = [k for k, v in self._cache.items() if v.expired]
        for k in expired_keys:
            del self._cache[k]
        return len(expired_keys)

    def _detect_hotkeys(self, top_n: int = 10) -> List[Dict]:
        """识别热点Key — 按访问频率排序"""
        access_counts: Dict[str, int] = {}
        for entry in self._cache.values():
            access_counts[entry.key] = entry.hit_count
        sorted_keys = sorted(access_counts.items(), key=lambda x: -x[1])[:top_n]
        return [
            {
                "key": k,
                "hits": h,
                "size_bytes": self._cache[k].size_bytes,
                "ttl_remaining": round(self._cache[k].expires_at - time.time(), 1)
                if self._cache[k].expires_at > 0
                else "infinite",
            }
            for k, h in sorted_keys
        ]

    def _add_ttl_jitter(self, base_ttl: int, jitter_pct: float = 0.1) -> float:
        """TTL抖动 — 防缓存雪崩，随机偏移base_ttl的jitter_pct"""
        import time as tmod

        jitter = base_ttl * jitter_pct * ((int(tmod.time()*1000000)%1000000/1000000) * 2 - 1)
        return max(1, base_ttl + jitter)

    def _analyze_eviction_candidates(self, count: int = 10) -> List[Dict]:
        """分析即将被淘汰的缓存条目"""
        candidates = []
        for key, entry in self._cache.items():
            if entry.expires_at > 0:
                remaining = entry.expires_at - time.time()
                if remaining < 300:  # 5分钟内过期
                    candidates.append(
                        {
                            "key": key,
                            "ttl_remaining": round(remaining, 1),
                            "size_bytes": entry.size_bytes,
                            "hit_count": entry.hit_count,
                        }
                    )
        candidates.sort(key=lambda x: x["ttl_remaining"])
        return candidates[:count]

    def _multi_level_stats(self) -> Dict:
        """多级缓存统计"""
        total_bytes = sum(e.size_bytes for e in self._cache.values())
        avg_ttl = 0
        entries_with_ttl = [e for e in self._cache.values() if e.expires_at > 0]
        if entries_with_ttl:
            avg_ttl = sum(e.expires_at - time.time() for e in entries_with_ttl) / len(entries_with_ttl)
        return {
            "l1_entries": len(self._cache),
            "l1_bytes": total_bytes,
            "l1_avg_ttl": round(avg_ttl, 1),
            "utilization_pct": round(len(self._cache) / max(self._max_entries, 1) * 100, 1),
            "hotkeys": self._detect_hotkeys(5),
            "eviction_candidates": self._analyze_eviction_candidates(5),
        }

    def _diagnose_cache_health(self) -> Dict:
        """缓存健康诊断 — 识别内存压力、TTL分布、碎片化"""
        entries = list(self._cache.values())
        if not entries:
            return {"status": "empty", "issues": []}
        issues = []
        utilization = len(entries) / max(self._max_entries, 1)
        if utilization > 0.9:
            issues.append(
                {
                    "level": "critical",
                    "type": "memory_pressure",
                    "message": f"缓存利用率{utilization * 100:.0f}%，即将触发大量淘汰",
                }
            )
        elif utilization > 0.7:
            issues.append(
                {"level": "warning", "type": "high_utilization", "message": f"缓存利用率{utilization * 100:.0f}%"}
            )
        # TTL分布分析
        expiring_soon = sum(1 for e in entries if e.expires_at > 0 and e.expires_at - time.time() < 60)
        if expiring_soon > len(entries) * 0.5:
            issues.append(
                {
                    "level": "warning",
                    "type": "mass_expiration",
                    "message": f"{expiring_soon}个条目将在60秒内过期，可能导致缓存雪崩",
                }
            )
        # 碎片化 — 很多小条目
        small_entries = sum(1 for e in entries if e.size_bytes < 1024)
        if small_entries > len(entries) * 0.8:
            issues.append(
                {"level": "info", "type": "fragmentation", "message": f"{small_entries}个小条目(<1KB)，考虑合并缓存"}
            )
        total_size = sum(e.size_bytes for e in entries)
        return {
            "status": "healthy" if not issues else "degraded",
            "entries": len(entries),
            "utilization": round(utilization, 4),
            "total_bytes": total_size,
            "issues": issues,
            "issue_count": len(issues),
        }

    def get_cache_utilization_report(self) -> Dict[str, Any]:
        """缓存利用率报告：命中率趋势、内存占用分布、热点Key统计、淘汰统计"""
        stats = self._stats if hasattr(self, "_stats") else {}
        cache = self._cache if hasattr(self, "_cache") else {}
        total_hits = stats.get("hits", 0)
        total_misses = stats.get("misses", 0)
        total = total_hits + total_misses
        hit_rate = total_hits / max(total, 1)
        entries_by_size = {}
        total_memory = 0
        for key, entry in cache.items():
            if isinstance(entry, dict):
                sz = entry.get("size", 0)
            else:
                sz = len(str(entry))
            bucket = f"{(sz // 1024) * 1024}KB-{(sz // 1024 + 1) * 1024}KB" if sz >= 1024 else f"<1KB"
            entries_by_size[bucket] = entries_by_size.get(bucket, 0) + 1
            total_memory += sz
        return {
            "total_entries": len(cache),
            "hit_rate": round(hit_rate, 4),
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_memory_bytes": total_memory,
            "size_distribution": entries_by_size,
        }

    def get_hot_keys(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """获取热点Key列表：按访问频次排序，标记潜在缓存穿透风险"""
        access_counts = self._access_counts if hasattr(self, "_access_counts") else {}
        if not access_counts:
            return []
        sorted_keys = sorted(access_counts.items(), key=lambda x: -x[1])[:top_n]
        total_access = sum(access_counts.values())
        hot_keys = []
        for key, count in sorted_keys:
            access_ratio = count / max(total_access, 1)
            hot_keys.append(
                {
                    "key": key[:50],
                    "access_count": count,
                    "access_ratio": round(access_ratio, 4),
                    "risk": "high" if access_ratio > 0.1 else "medium",
                }
            )
        return hot_keys

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

module_class = ApiCacheManager
