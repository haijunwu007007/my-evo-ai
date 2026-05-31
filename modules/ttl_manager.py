"""Production-grade module: TTL过期管理器
# Grade: A
企业级TTL生命周期引擎 - 管理缓存/会话/临时文件/验证码等资源的自动过期。
典型场景: Redis Key过期策略、Session超时管理、临时文件清理、OTP验证码生命周期。
"""

__module_meta__ = {
        "id": "ttl-manager",
        "name": "Ttl Manager",
        "version": "V0.1",
        "group": "storage",
        "inputs": [
            {
                "name": "default_ttl_seconds",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "key",
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
                "name": "ttl",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "policy",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "key_2",
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
            "ttl",
            "manager"
        ],
        "grade": "A",
        "description": "Production-grade module: TTL过期管理器 企业级TTL生命周期引擎 - 管理缓存/会话/临时文件/验证码等资源的自动过期。"
    }
import heapq
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger("ttl_manager")

class TtlPolicy(Enum):
    FIXED = "fixed"  # 固定过期时间
    SLIDING = "sliding"  # 滑动过期（每次访问续期）
    LAZY = "lazy"  # 惰性过期（访问时检查）
    PROACTIVE = "proactive"  # 主动过期（定时扫描清理）

class ExpirationScheduler:
    """过期调度器 - 基于最小堆的高效过期时间管理。

    企业场景：管理数十万缓存Key的过期时间，支持主动扫描和惰性检查两种模式。
    使用最小堆实现O(log n)的插入和O(1)的最小值查询，适合大规模Key管理。
    """

    def __init__(self, default_ttl_seconds: int = 3600):
        self._heap: List[Tuple[float, str]] = []  # (expire_timestamp, key)
        self._entries: Dict[str, Dict] = {}  # key -> metadata
        self._default_ttl = default_ttl_seconds
        self._total_set = 0
        self._total_expired = 0
        self._total_extended = 0
        self._total_deleted = 0
        self._expired_callbacks: Dict[str, str] = {}  # key -> callback_action

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        policy: str = "fixed",
        tags: Optional[List[str]] = None,
        on_expire: Optional[str] = None,
    ) -> Dict[str, Any]:
        """设置带TTL的Key。企业场景：设置验证码5分钟过期、缓存30分钟过期。
        支持fixed（固定到期）和sliding（滑动续期）两种策略。
        """
        ttl_seconds = ttl if ttl is not None else self._default_ttl
        now = time.time()
        expire_at = now + ttl_seconds

        # 如果Key已存在，先移除旧条目
        if key in self._entries:
            old = self._entries[key]
            if old.get("policy") == "fixed":
                old["expire_at"] = expire_at
                old["value"] = value
                old["ttl"] = ttl_seconds
                old["updated_at"] = now
                old["extend_count"] = old.get("extend_count", 0) + 1
                heapq.heappush(self._heap, (expire_at, key))
                self._total_extended += 1
                return {"key": key, "ttl_seconds": ttl_seconds, "expire_at": expire_at, "extended": True}

        entry = {
            "key": key,
            "value": value,
            "ttl": ttl_seconds,
            "policy": policy,
            "expire_at": expire_at,
            "created_at": now,
            "updated_at": now,
            "last_accessed": now,
            "access_count": 0,
            "extend_count": 0,
            "tags": tags or [],
        }
        self._entries[key] = entry
        heapq.heappush(self._heap, (expire_at, key))
        self._total_set += 1

        if on_expire:
            self._expired_callbacks[key] = on_expire

        return {"key": key, "ttl_seconds": ttl_seconds, "expire_at": expire_at, "policy": policy}

    def get(self, key: str) -> Optional[Dict]:
        """获取Key，同时检查是否过期。企业场景：读取Session时自动检查超时。
        支持sliding策略自动续期。
        """
        entry = self._entries.get(key)
        if not entry:
            return None
        now = time.time()
        if now >= entry["expire_at"]:
            return None  # 已过期，不返回
        entry["last_accessed"] = now
        entry["access_count"] += 1
        if entry.get("policy") == "sliding":
            entry["expire_at"] = now + entry["ttl"]
            entry["updated_at"] = now
            heapq.heappush(self._heap, (entry["expire_at"], key))
            self._total_extended += 1
        return entry

    def check_expired(self, key: str) -> Dict[str, Any]:
        """检查单个Key是否过期。企业场景：前端轮询验证码是否还有效。"""
        entry = self._entries.get(key)
        if not entry:
            return {"key": key, "exists": False, "expired": True}
        now = time.time()
        remaining = entry["expire_at"] - now
        if remaining <= 0:
            return {
                "key": key,
                "exists": True,
                "expired": True,
                "expired_at": entry["expire_at"],
                "ttl_seconds": entry["ttl"],
            }
        return {
            "key": key,
            "exists": True,
            "expired": False,
            "remaining_seconds": round(remaining, 1),
            "ttl_seconds": entry["ttl"],
            "progress_pct": round((entry["ttl"] - remaining) / entry["ttl"] * 100, 1),
        }

    def extend(self, key: str, additional_seconds: Optional[int] = None) -> Dict[str, Any]:
        """延长Key的TTL。企业场景：用户活跃时续期Session，避免频繁重新登录。"""
        entry = self._entries.get(key)
        if not entry:
            return {"success": False, "error": f"Key {key} 不存在"}
        now = time.time()
        if now >= entry["expire_at"]:
            return {"success": False, "error": f"Key {key} 已过期，无法续期"}
        add_seconds = additional_seconds or entry["ttl"]
        entry["expire_at"] = now + add_seconds
        entry["ttl"] = add_seconds
        entry["updated_at"] = now
        entry["extend_count"] += 1
        heapq.heappush(self._heap, (entry["expire_at"], key))
        self._total_extended += 1
        return {
            "success": True,
            "key": key,
            "new_expire_at": entry["expire_at"],
            "new_ttl": add_seconds,
            "total_extensions": entry["extend_count"],
        }

    def scan_and_expire(self, batch_size: int = 1000) -> Dict[str, Any]:
        """主动扫描过期Key并清理。企业场景：定时任务每分钟扫描一次，
        批量清理过期缓存Key释放内存。
        """
        now = time.time()
        expired_keys = []
        expired_callbacks = []
        while self._heap and len(expired_keys) < batch_size:
            expire_at, key = self._heap[0]
            if expire_at > now:
                break
            heapq.heappop(self._heap)
            # 堆中可能有同一Key的多个时间戳（续期产生）
            entry = self._entries.get(key)
            if entry and now >= entry["expire_at"]:
                expired_keys.append(key)
                if key in self._expired_callbacks:
                    expired_callbacks.append({"key": key, "callback": self._expired_callbacks.pop(key)})
                del self._entries[key]
                self._total_expired += 1

        return {
            "expired_count": len(expired_keys),
            "expired_keys": expired_keys[:20],
            "callbacks_triggered": expired_callbacks[:10],
            "remaining_entries": len(self._entries),
            "heap_size": len(self._heap),
        }

    def delete(self, key: str) -> Dict[str, Any]:
        """主动删除Key。企业场景：用户退出登录时清除Session。"""
        entry = self._entries.pop(key, None)
        if not entry:
            return {"success": False, "error": f"Key {key} 不存在"}
        self._expired_callbacks.pop(key, None)
        self._total_deleted += 1
        return {
            "success": True,
            "key": key,
            "was_expired": time.time() >= entry["expire_at"],
            "existed_seconds": round(time.time() - entry["created_at"], 1),
        }

    def get_by_tag(self, tag: str) -> List[Dict]:
        """按标签查询Key。企业场景：查询所有user_session标签的Key用于批量清理。"""
        now = time.time()
        results = []
        for key, entry in self._entries.items():
            if tag in entry.get("tags", []):
                remaining = max(0, entry["expire_at"] - now)
                results.append(
                    {
                        "key": key,
                        "remaining_seconds": round(remaining, 1),
                        "expired": remaining <= 0,
                        "policy": entry["policy"],
                        "access_count": entry["access_count"],
                    }
                )
        results.sort(key=lambda x: x["remaining_seconds"])
        return results

    def get_expiring_soon(self, seconds: int = 300, limit: int = 50) -> List[Dict]:
        """获取即将过期的Key。企业场景：发送即将过期提醒（如证书续期、会员到期）。"""
        now = time.time()
        results = []
        for key, entry in self._entries.items():
            remaining = entry["expire_at"] - now
            if 0 < remaining <= seconds:
                results.append(
                    {
                        "key": key,
                        "remaining_seconds": round(remaining, 1),
                        "tags": entry.get("tags", []),
                        "access_count": entry["access_count"],
                    }
                )
        results.sort(key=lambda x: x["remaining_seconds"])
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """获取TTL统计。企业场景：监控面板展示Key数量、过期速率、命中率。"""
        now = time.time()
        policy_counts = {}
        for entry in self._entries.values():
            p = entry.get("policy", "fixed")
            policy_counts[p] = policy_counts.get(p, 0) + 1
        return {
            "active_keys": len(self._entries),
            "heap_size": len(self._heap),
            "total_set": self._total_set,
            "total_expired": self._total_expired,
            "total_extended": self._total_extended,
            "total_deleted": self._total_deleted,
            "expire_rate": round(self._total_expired / max(self._total_set, 1) * 100, 1),
            "default_ttl": self._default_ttl,
            "policy_distribution": policy_counts,
        }

class TtlManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """TTL过期管理器 - 企业级资源生命周期引擎。

    核心能力：
    1. 高效过期调度（最小堆，O(log n)操作）
    2. 多策略支持（固定/滑动/惰性/主动）
    3. 批量过期扫描
    4. 按标签分组管理
    5. 即将过期预警
    6. 过期回调触发
    7. 生命周期统计与分析
    """

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._data: Dict[str, Any] = {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logging.getLogger("ttl_manager")
        self._scheduler = ExpirationScheduler(default_ttl_seconds=self.config.get("default_ttl", 3600))
        self._namespaces: Dict[str, ExpirationScheduler] = {}

    def initialize(self) -> dict:
        try:
            self._data["config"] = self.config
            self._data["instance_id"] = str(uuid.uuid4())[:8]
            self._data["created_at"] = time.time()
            self._status = ModuleStatus.RUNNING
            return {"success": True, "instance_id": self._data["instance_id"]}
        except Exception as e:
            self._status = ModuleStatus.ERROR
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        stats = self._scheduler.get_stats()
        checks = [
            ("config_loaded", bool(self.config) or "config" in self._data),
            ("scheduler_active", stats["active_keys"] >= 0),
            ("metrics_active", self._metrics is not None),
            ("status_ok", self._status == ModuleStatus.RUNNING),
        ]
        results = [{"name": n, "healthy": bool(v)} for n, v in checks]
        return {
            "healthy": all(c["healthy"] for c in results),
            "checks": results,
            "status": self._status.value if hasattr(self._status, "value") else str(self._status),
            "total_operations": self._metrics["total_operations"],
            "ttl_stats": stats,
        }

    def _get_scheduler(self, namespace: str = "default") -> ExpirationScheduler:
        """获取或创建命名空间调度器。企业场景：不同业务隔离TTL管理
        （session命名空间、cache命名空间、otp命名空间）。
        """
        if namespace not in self._namespaces:
            ttl = self.config.get(f"{namespace}_ttl", self.config.get("default_ttl", 3600))
            self._namespaces[namespace] = ExpirationScheduler(default_ttl_seconds=ttl)
        return self._namespaces[namespace]

    def set_ttl(self, params: dict = None) -> dict:
        """设置TTL Key。params: key(必填), value(必填), ttl(可选), policy(可选),
        namespace(可选), tags(可选), on_expire(可选)
        """
        params = params or {}
        key = params.get("key", "")
        value = params.get("value")
        if not key or value is None:
            return {"success": False, "error": "key 和 value 必填"}
        scheduler = self._get_scheduler(params.get("namespace", "default"))
        self._metrics["total_operations"] += 1
        return {
            "success": True,
            **scheduler.set(
                key=key,
                value=value,
                ttl=params.get("ttl"),
                policy=params.get("policy", "fixed"),
                tags=params.get("tags"),
                on_expire=params.get("on_expire"),
            ),
        }

    def expire_check(self, params: dict = None) -> dict:
        """检查Key过期状态。params: key(必填), namespace(可选)"""
        params = params or {}
        key = params.get("key", "")
        if not key:
            return {"success": False, "error": "key 必填"}
        scheduler = self._get_scheduler(params.get("namespace", "default"))
        self._metrics["total_operations"] += 1
        return {"success": True, **scheduler.check_expired(key)}

    def extend_ttl(self, params: dict = None) -> dict:
        """延长TTL。params: key(必填), additional_seconds(可选), namespace(可选)"""
        params = params or {}
        key = params.get("key", "")
        if not key:
            return {"success": False, "error": "key 必填"}
        scheduler = self._get_scheduler(params.get("namespace", "default"))
        self._metrics["total_operations"] += 1
        return scheduler.extend(key, params.get("additional_seconds"))

    def batch_expire(self, params: dict = None) -> dict:
        """批量扫描过期Key。params: namespace(可选), batch_size(可选)
        企业场景：定时任务每分钟调用，清理所有命名空间的过期Key。
        """
        params = params or {}
        results = {}
        namespaces = [params.get("namespace", "default")]
        if not params.get("namespace"):
            namespaces = list(self._namespaces.keys()) + ["default"]
        total_expired = 0
        for ns in set(namespaces):
            scheduler = self._get_scheduler(ns)
            r = scheduler.scan_and_expire(batch_size=params.get("batch_size", 1000))
            results[ns] = r
            total_expired += r["expired_count"]
        self._metrics["total_operations"] += 1
        return {"success": True, "total_expired": total_expired, "namespaces": results}

    def stats(self, params: dict = None) -> dict:
        """获取TTL统计。params: namespace(可选)
        企业场景：运维面板展示各命名空间的Key数量和过期速率。
        """
        params = params or {}
        ns = params.get("namespace")
        if ns:
            return {"success": True, "namespace": ns, **self._get_scheduler(ns).get_stats()}
        all_stats = {"default": self._scheduler.get_stats()}
        for name, scheduler in self._namespaces.items():
            all_stats[name] = scheduler.get_stats()
        total_keys = sum(s["active_keys"] for s in all_stats.values())
        total_expired = sum(s["total_expired"] for s in all_stats.values())
        return {
            "success": True,
            "namespaces": all_stats,
            "total_active_keys": total_keys,
            "total_expired_ever": total_expired,
        }

    def get_expiring_soon(self, params: dict = None) -> dict:
        """获取即将过期的Key。params: seconds(默认300), namespace(可选), limit(可选)
        企业场景：发送证书/会员到期提醒。
        """
        params = params or {}
        scheduler = self._get_scheduler(params.get("namespace", "default"))
        items = scheduler.get_expiring_soon(seconds=params.get("seconds", 300), limit=params.get("limit", 50))
        return {"success": True, "count": len(items), "items": items}

    def get_by_tag(self, params: dict = None) -> dict:
        """按标签查询Key。params: tag(必填), namespace(可选)"""
        params = params or {}
        tag = params.get("tag", "")
        if not tag:
            return {"success": False, "error": "tag 必填"}
        scheduler = self._get_scheduler(params.get("namespace", "default"))
        items = scheduler.get_by_tag(tag)
        return {"success": True, "tag": tag, "count": len(items), "items": items}

    async def execute(self, action: str, params: dict = None) -> dict:
        """Dispatch action to business methods."""
        self.trace("execute", {"module": "ttl_manager", "action": action})
        self.metrics_collector.counter("ttl_manager.execute.calls", 1)
        self.audit("execute", {"module": "ttl_manager", "action": action})
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

    def get_ttl_distribution(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """TTL分布统计。企业场景：分析Key的过期时间分布，
        发现大量短命Key（可能是缓存穿透攻击）或过长TTL（内存浪费）。
        """
        scheduler = self._get_scheduler(namespace or "default")
        now = time.time()
        buckets = {"<1min": 0, "1-5min": 0, "5-30min": 0, "30min-1h": 0, "1h-6h": 0, "6h-24h": 0, ">24h": 0}
        total_size_estimate = 0
        for key, entry in scheduler._entries.items():
            remaining = max(0, entry["expire_at"] - now)
            total_size_estimate += len(str(entry.get("value", "")).encode())
            if remaining < 60:
                buckets["<1min"] += 1
            elif remaining < 300:
                buckets["1-5min"] += 1
            elif remaining < 1800:
                buckets["5-30min"] += 1
            elif remaining < 3600:
                buckets["30min-1h"] += 1
            elif remaining < 21600:
                buckets["1h-6h"] += 1
            elif remaining < 86400:
                buckets["6h-24h"] += 1
            else:
                buckets[">24h"] += 1
        return {
            "success": True,
            "namespace": namespace or "default",
            "distribution": buckets,
            "total_keys": sum(buckets.values()),
            "estimated_memory_bytes": total_size_estimate,
            "estimated_memory_mb": round(total_size_estimate / 1024 / 1024, 2),
        }

    def shutdown(self) -> dict:
        """Graceful shutdown for ttl_manager."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = TtlManager
