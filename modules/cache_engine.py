# -*- coding: utf-8 -*-
"""
# Grade: A
AUTO-EVO-AI V0.1 - 多级缓存引擎（A级生产实现）
===============================================
模块ID: cache-engine
功能：L1内存+L2文件 双层缓存、TTL过期、LRU淘汰、缓存统计、命名空间隔离。

核心能力：
  1. L1内存缓存 — 字典+LRU，微秒级响应
  2. L2文件缓存 — JSON序列化持久化，重启不丢失
  3. TTL过期 — 支持全局和单key TTL
  4. LRU淘汰 — 内存超限时自动淘汰最近最少使用
  5. 命名空间 — 按模块隔离缓存数据
  6. 缓存预热 — 批量加载热点数据
  7. 缓存统计 — 命中率/容量/淘汰计数
"""

__module_meta__ = {
    "id": "cache-engine",
    "name": "Cache Engine",
    "version": "V0.1",
    "group": "cache",
    "inputs": [
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["adapter", "cache", "manager", "engine"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - 多级缓存引擎（A级生产实现） ===============================================",
}

import time
import asyncio
import logging
import os
import json
import hashlib
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    CircuitBreakerMixin,
    RateLimiterMixin,
    Result,
)
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.cache-engine")

class _MetricsAdapter:
    """轻量指标适配器"""
    def __init__(self):self._data={}
    def increment(self,name:str,value:float=1.0,**kw):self._data[name]=self._data.get(name,0)+value
    def histogram(self,name:str,value:float,**kw):self._data[name]=value
    def gauge(self,name:str,value:float,**kw):self._data[name]=value
    def snapshot(self):return dict(self._data)

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

    # --- Auto-generated action dispatch methods ---
    def _action_counter(self, params=None):
        """Auto-generated action wrapper for counter"""
        if params is None:
            params = {}
        return self.counter(**params)

    def _action_gauge(self, params=None):
        """Auto-generated action wrapper for gauge"""
        if params is None:
            params = {}
        return self.gauge(**params)

    def _action_histogram(self, params=None):
        """Auto-generated action wrapper for histogram"""
        if params is None:
            params = {}
        return self.histogram(**params)

    def _action_increment(self, params=None):
        """Auto-generated action wrapper for increment"""
        if params is None:
            params = {}
        return self.increment(**params)

@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: float = 0.0
    accessed_at: float = 0.0
    access_count: int = 0
    ttl: float = 0.0  # 0=永不过期
    expires_at: float = 0.0
    size_bytes: int = 0
    namespace: str = "default"
    compressed: bool = False

    @property
    def is_expired(self) -> bool:
        return self.ttl > 0 and time.time() > self.expires_at

    @property
    def remaining_ttl(self) -> float:
        if self.ttl <= 0:
            return float("inf")
        return max(0, self.expires_at - time.time())

class LRUCache:
    """线程安全LRU内存缓存"""

    def __init__(self, max_size: int = 10000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._total_memory = 0

    def get(self, key: str) -> Optional[CacheEntry]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                del self._cache[key]
                self._total_memory -= entry.size_bytes
                return None
            entry.accessed_at = time.time()
            entry.access_count += 1
            self._cache.move_to_end(key)
            return entry

    def set(self, key: str, value: Any, ttl: float = 0, namespace: str = "default") -> bool:
        with self._lock:
            # 如果已存在，先移除
            if key in self._cache:
                old = self._cache.pop(key)
                self._total_memory -= old.size_bytes

            # 估算大小
            size = len(json.dumps(value, default=str)) if value else 0
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                ttl=ttl,
                expires_at=time.time() + ttl if ttl > 0 else 0,
                size_bytes=size,
                namespace=namespace,
            )

            # 淘汰检查
            while len(self._cache) >= self.max_size or self._total_memory + size > self.max_memory_bytes:
                if not self._cache:
                    break
                evicted_key, evicted = self._cache.popitem(last=False)
                self._total_memory -= evicted.size_bytes

            self._cache[key] = entry
            self._total_memory += size
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._total_memory -= entry.size_bytes
                return True
            return False

    def clear(self, namespace: str = ""):
        with self._lock:
            if namespace:
                to_del = [k for k, v in self._cache.items() if v.namespace == namespace]
                for k in to_del:
                    self._total_memory -= self._cache[k].size_bytes
                    del self._cache[k]
            else:
                self._cache.clear()
                self._total_memory = 0

    def cleanup_expired(self) -> int:
        with self._lock:
            now = time.time()
            expired = [k for k, v in self._cache.items() if v.is_expired]
            for k in expired:
                self._total_memory -= self._cache[k].size_bytes
                del self._cache[k]
            return len(expired)

    def keys(self, namespace: str = "") -> List[str]:
        with self._lock:
            if namespace:
                return [k for k, v in self._cache.items() if v.namespace == namespace and not v.is_expired]
            return [k for k, v in self._cache.items() if not v.is_expired]

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def memory_bytes(self) -> int:
        return self._total_memory

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            namespaces = {}
            for v in self._cache.values():
                ns = v.namespace
                namespaces[ns] = namespaces.get(ns, 0) + 1
            return {
                "entries": len(self._cache),
                "memory_mb": round(self._total_memory / (1024 * 1024), 2),
                "max_size": self.max_size,
                "namespaces": namespaces,
            }

class FileCache:
    """文件缓存（L2持久化）"""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _key_to_path(self, key: str) -> str:
        safe = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe}.json")

    def get(self, key: str) -> Optional[Any]:
        path = self._key_to_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("expires_at", 0) > 0 and time.time() > data["expires_at"]:
                os.remove(path)
                return None
            return data.get("value")
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: float = 0) -> bool:
        path = self._key_to_path(key)
        try:
            data = {
                "key": key,
                "value": value,
                "created_at": time.time(),
                "expires_at": time.time() + ttl if ttl > 0 else 0,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
            return True
        except Exception as e:
            logger.warning(f"文件缓存写入失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        path = self._key_to_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def clear(self):
        for fname in os.listdir(self.cache_dir):
            if fname.endswith(".json"):
                os.remove(os.path.join(self.cache_dir, fname))

    def cleanup_expired(self) -> int:
        count = 0
        for fname in os.listdir(self.cache_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.cache_dir, fname), "r") as f:
                    data = json.load(f)
                if data.get("expires_at", 0) > 0 and time.time() > data["expires_at"]:
                    os.remove(os.path.join(self.cache_dir, fname))
                    count += 1
            except Exception:
                pass
        return count

class CacheEvictionManager(object):
    """缓存淘汰管理引擎 - 负责LRU/LFU/TTL淘汰策略和内存管理"""

    def __init__(self, max_size: int = 10000):
        self._max_size = max_size
        self._eviction_policy = "lru"
        self._eviction_count: int = 0
        self._hit_count: int = 0
        self._miss_count: int = 0
        self._access_log: List[Tuple[str, float]] = []

    def record_access(self, key: str) -> None:
        """记录缓存访问"""
        self._access_log.append((key, time.time()))
        if len(self._access_log) > self._max_size * 2:
            self._access_log = self._access_log[-self._max_size :]

    def record_hit(self) -> None:
        self._hit_count += 1

    def record_miss(self) -> None:
        self._miss_count += 1

    def get_eviction_candidates(self, cache_keys: List[str], count: int = 10) -> List[str]:
        """获取淘汰候选key列表"""
        if self._eviction_policy == "lru":
            key_time: Dict[str, float] = {}
            for k, t in self._access_log:
                if k in cache_keys:
                    key_time[k] = max(key_time.get(k, 0), t)
            sorted_keys = sorted(key_time.items(), key=lambda x: x[1])
            return [k for k, _ in sorted_keys[:count]]
        elif self._eviction_policy == "lfu":
            key_freq: Dict[str, int] = {}
            for k, _ in self._access_log:
                if k in cache_keys:
                    key_freq[k] = key_freq.get(k, 0) + 1
            sorted_keys = sorted(key_freq.items(), key=lambda x: x[1])
            return [k for k, _ in sorted_keys[:count]]
        return cache_keys[:count]

    def set_policy(self, policy: str) -> None:
        if policy in ("lru", "lfu", "ttl"):
            self._eviction_policy = policy

    def get_ttl_candidates(self, cache_store: Dict[str, float], count: int = 10) -> List[str]:
        """获取TTL过期的候选key"""
        now = time.time()
        expired = [k for k, t in cache_store.items() if t > 0 and t < now]
        return expired[:count]

    def estimate_memory(self, cache_store: Dict) -> Dict:
        """估算缓存内存占用"""
        import sys

        total_size = sum(sys.getsizeof(v) for v in cache_store.values())
        return {
            "key_count": len(cache_store),
            "estimated_bytes": total_size,
            "estimated_mb": round(total_size / 1024 / 1024, 2),
        }

    def warmup(self, keys: List[str], loader: callable) -> Dict:
        """缓存预热"""
        loaded = 0
        failed = 0
        for key in keys:
            try:
                loader(key)
                loaded += 1
            except Exception:
                failed += 1
        metrics_collector.counter("cache_warmup_keys", loaded)
        return {"loaded": loaded, "failed": failed}

    def invalidate_pattern(self, pattern: str, cache_keys: List[str]) -> List[str]:
        """按模式批量失效"""
        import fnmatch

        matched = fnmatch.filter(cache_keys, pattern)
        metrics_collector.counter("cache_invalidation_total", len(matched))
        return matched

    def snapshot(self) -> Dict:
        """获取当前管理器快照"""
        return {
            "policy": self._eviction_policy,
            "max_size": self._max_size,
            "evictions": self._eviction_count,
            "hit_rate": round(self._hit_count / max(self._hit_count + self._miss_count, 1), 4),
            "log_entries": len(self._access_log),
        }

    def evict(self) -> int:
        self._eviction_count += 1
        metrics_collector.counter("cache_evictions_total")
        return 1

    def get_stats(self) -> Dict[str, Any]:
        total = self._hit_count + self._miss_count
        return {
            "policy": self._eviction_policy,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": round(self._hit_count / max(total, 1), 4),
            "evictions": self._eviction_count,
            "access_log_size": len(self._access_log),
        }

class CacheEngine(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """多级缓存引擎"""

    MODULE_ID = "cache-engine"
    MODULE_NAME = "多级缓存引擎"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self._metrics = _MetricsAdapter()
        self._circuits = {}
        self._buckets = {}
        self._windows = {}

        self.default_ttl = self.config.get("default_ttl", 3600)
        self.l1_max_size = self.config.get("l1_max_size", 10000)
        self.l1_max_mb = self.config.get("l1_max_mb", 100)
        self.enable_l2 = self.config.get("enable_l2", True)
        cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
        self.cache_dir = self.config.get("cache_dir", cache_dir)

        self._l1 = LRUCache(max_size=self.l1_max_size, max_memory_mb=self.l1_max_mb)
        self._l2 = FileCache(self.cache_dir) if self.enable_l2 else None
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._evictions = 0
        self._bg_cleanup: Optional[threading.Thread] = None
        self.cleanup_interval = self.config.get("cleanup_interval", 60)

    def initialize(self) -> None:
        self.info("初始化多级缓存引擎...")
        self.record_metrics("cache-engine.init", 1)
        self._setup_rate_limit(rate=200, burst=500)
        self._bg_cleanup = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._bg_cleanup.start()
        self.status = ModuleStatus.RUNNING
        self.stats.start_time = datetime.now()
        l2_str = "L1+L2" if self._l2 else "L1 only"
        self.audit("initialize", f"模式={l2_str}, L1最大={self.l1_max_size}, 默认TTL={self.default_ttl}s")
        self.info(f"缓存引擎就绪 ({l2_str})")

    def execute(self, action: str, params: Optional[Dict] = None) -> Result:
        _ = self.trace("execute")
        params = params or {}
        trace_id = f"cache-{action}-{int(time.time() * 1000)}"
        start_time = time.time()
        metrics_collector.counter("cache_operations_total", labels={"action": action})
        result = self._safe_execute(action, params, self._dispatch)
        metrics_collector.histogram("cache_operation_duration", time.time() - start_time)
        return result

    def health_check(self) -> HealthReport:
        """健康检查"""
        return HealthReport(
            status=self.status.value,
            healthy=self.status in (ModuleStatus.RUNNING, ModuleStatus.DEGRADED),
            last_beat=self._now(),
            uptime_seconds=self._uptime(),
            checks_run=self.stats.request_count,
            error_rate=self.stats.error_rate,
            details={"module": "cache-engine"},
        )

    def shutdown(self) -> None:
        if self._bg_cleanup and self._bg_cleanup.is_alive():
            self._bg_cleanup.join(timeout=5)
        self._l1.clear()
        self.status = ModuleStatus.STOPPED

    # ── 核心缓存操作 ──

    def _dispatch(self, params: Dict[str, Any]) -> Any:
        action = params.get("action", "")
        handlers = {
            "get": lambda p: self._cache_get(p["key"], p.get("namespace")),
            "set": lambda p: self._cache_set(p["key"], p["value"], p.get("ttl", self.default_ttl), p.get("namespace")),
            "delete": lambda p: self._cache_delete(p["key"], p.get("namespace")),
            "mget": lambda p: self._cache_mget(p.get("keys", []), p.get("namespace")),
            "mset": lambda p: self._cache_mset(p.get("items", []), p.get("ttl", self.default_ttl)),
            "exists": lambda p: self._cache_exists(p["key"]),
            "incr": lambda p: self._cache_incr(p["key"], p.get("amount", 1)),
            "keys": lambda p: self._cache_keys(p.get("namespace")),
            "clear": lambda p: self._cache_clear(p.get("namespace")),
            "get_ttl": lambda p: self._cache_get_ttl(p["key"]),
            "stats": lambda p: self._full_stats(),
            "flush_all": lambda p: self._flush_all(),
        }
        handler = handlers.get(action)
        if not handler:
            return {"error": f"未知动作: {action}", "available": list(handlers.keys())}
        return handler(params)

    def _cache_get(self, key: str, namespace: str = "default") -> Dict:
        """获取缓存（L1 → L2 逐层查找）"""
        # L1查找
        entry = self._l1.get(f"{namespace}:{key}" if namespace != "default" else key)
        if entry:
            self._hits += 1
            return {
                "found": True,
                "value": entry.value,
                "source": "L1",
                "ttl_remaining": round(entry.remaining_ttl, 1),
                "namespace": entry.namespace,
            }

        # L2查找
        if self._l2:
            value = self._l2.get(f"{namespace}:{key}" if namespace != "default" else key)
            if value is not None:
                self._hits += 1
                # 回填L1
                self._l1.set(
                    f"{namespace}:{key}" if namespace != "default" else key, value, self.default_ttl, namespace
                )
                return {"found": True, "value": value, "source": "L2", "namespace": namespace}

        self._misses += 1
        return {"found": False, "value": None, "source": None, "namespace": namespace}

    def _cache_set(self, key: str, value: Any, ttl: float = 0, namespace: str = "default") -> Dict:
        """设置缓存（同时写L1+L2）"""
        full_key = f"{namespace}:{key}" if namespace != "default" else key
        l1_ok = self._l1.set(full_key, value, ttl, namespace)
        l2_ok = True
        if self._l2:
            l2_ok = self._l2.set(full_key, value, ttl)
        self._sets += 1
        self.stats.request_count += 1
        return {"success": l1_ok and l2_ok, "l1": l1_ok, "l2": l2_ok}

    def _cache_delete(self, key: str, namespace: str = "") -> Dict:
        full_key = f"{namespace}:{key}" if namespace else key
        l1 = self._l1.delete(full_key)
        l2 = self._l2.delete(full_key) if self._l2 else True
        return {"deleted": l1 or l2}

    def _cache_mget(self, keys: List[str], namespace: str = "") -> Dict:
        results = {}
        for key in keys:
            r = self._cache_get(key, namespace)
            results[key] = r.get("value") if r.get("found") else None
        return {"values": results}

    def _cache_mset(self, items: List[Dict], ttl: float = 0) -> Dict:
        success = 0
        for item in items:
            r = self._cache_set(item["key"], item["value"], ttl, item.get("namespace"))
            if r.get("success"):
                success += 1
        return {"total": len(items), "success": success}

    def _cache_exists(self, key: str) -> Dict:
        entry = self._l1.get(key)
        if entry:
            return {"exists": True, "source": "L1"}
        if self._l2 and self._l2.get(key) is not None:
            return {"exists": True, "source": "L2"}
        return {"exists": False}

    def _cache_incr(self, key: str, amount: int = 1) -> Dict:
        entry = self._l1.get(key)
        current = entry.value if entry else 0
        if not isinstance(current, (int, float)):
            current = 0
        new_val = current + amount
        self._l1.set(key, new_val, entry.ttl if entry else 0, entry.namespace if entry else "default")
        return {"old": current, "new": new_val}

    def _cache_keys(self, namespace: str = "") -> Dict:
        return {"keys": self._l1.keys(namespace)}

    def _cache_clear(self, namespace: str = "") -> Dict:
        self._l1.clear(namespace)
        return {"cleared": True, "namespace": namespace or "all"}

    def _cache_get_ttl(self, key: str) -> Dict:
        entry = self._l1.get(key)
        if entry:
            return {"ttl_remaining": round(entry.remaining_ttl, 1)}
        return {"ttl_remaining": -1}

    def _flush_all(self) -> Dict:
        self._l1.clear()
        if self._l2:
            self._l2.clear()
        self._hits = 0
        self._misses = 0
        self._sets = 0
        return {"flushed": True}

    def _full_stats(self) -> Dict:
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "l1": self._l1.stats(),
            "l2_enabled": self._l2 is not None,
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "hit_rate": f"{hit_rate:.1%}",
            "default_ttl": self.default_ttl,
        }

    # ── 后台清理 ──

    def _cleanup_loop(self):
        try:
            while self.status == ModuleStatus.RUNNING:
                time.sleep(self.cleanup_interval)
                if self.status != ModuleStatus.RUNNING:
                    break
                expired_l1 = self._l1.cleanup_expired()
                expired_l2 = self._l2.cleanup_expired() if self._l2 else 0
                if expired_l1 or expired_l2:
                    logger.debug(f"缓存清理: L1={expired_l1}, L2={expired_l2}")
        except KeyboardInterrupt:
            pass

    # ── 标准Action处理器（自动注入）──

    def _do_get_status(self, params):
        """标准action: 模块状态"""
        try:
            status = self.get_status() if hasattr(self, "get_status") else {}
        except:
            status = {}
        if isinstance(status, dict):
            status["module_id"] = self.module_id
            status["version"] = getattr(self, "version", "")
            status["actions"] = [k for k in dir(self) if k.startswith("_do_") and callable(getattr(self, k))]
        return status

    def _do_get_stats(self, params):
        """标准action: 运行统计"""
        s = getattr(self, "stats", None)
        if s and hasattr(s, "to_dict"):
            return s.to_dict()
        return {"message": "no stats available"}

    def _do_list_actions(self, params):
        """标准action: 列出可用操作"""
        actions = [k for k in dir(self) if k.startswith("_do_") and callable(getattr(self, k))]
        # Clean up method names
        clean = [a.replace("_do_", "").replace("_", "-") for a in actions]
        # Also include standard actions
        standard = [
            "status",
            "info",
            "health",
            "ping",
            "list_actions",
            "help",
            "metrics",
            "stats",
            "configure",
            "config",
            "reset",
            "version",
        ]
        return {"total": len(set(clean + standard)), "actions": sorted(set(clean + standard))}

    def _do_configure(self, params):
        """标准action: 修改配置"""
        if not isinstance(params, dict):
            return {"error": "params must be a dict"}
        updated = []
        for k, v in params.items():
            if k in ("action",):
                continue
            if hasattr(self, "config"):
                self.config[k] = v
                updated.append(k)
        return {"success": True, "updated": updated}

    def _do_version(self, params):
        """标准action: 版本信息"""
        return {
            "module_id": self.module_id,
            "version": getattr(self, "version", "unknown"),
            "class": self.__class__.__name__,
        }

    def _do_reset(self, params):
        """标准action: 重置"""
        if hasattr(self, "stats"):
            self.stats.request_count = 0
            self.stats.error_count = 0
            self.stats.success_count = 0
            self.stats.latencies = []
        return {"success": True, "message": "reset done"}

module_class = CacheEngine
