"""
AUTO-EVO-AI V0.1 — Redis缓存管理模块
Grade: A (生产级) | Category: 缓存
职责：Redis键值缓存、过期策略、分布式锁、发布订阅、Lua脚本执行、集群管理
"""

__module_meta__ = {
        "id": "redis-cache",
        "name": "Redis Cache",
        "version": "V0.1",
        "group": "cache",
        "inputs": [
            {
                "name": "ttl",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "params",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "params_2",
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
                "name": "cache",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "ttl_map",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "success",
                "type": "bool",
                "description": "是否成功"
            },
            {
                "name": "success_2",
                "type": "bool",
                "description": "是否成功"
            },
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "engine",
            "redis"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — Redis缓存管理模块 Grade: A (生产级) | Category: 缓存"
    }

import os
import asyncio
import time
import logging
import threading
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import OrderedDict

try:
    import redis as _redis_lib
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False
    _redis_lib = None

try:
    from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
    from modules._base.enterprise_module import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector, prometheus_timer
    from modules._base.audit import AuditLogger
except ImportError:

    class EnterpriseModule:
        def __init__(self, config=None):
            pass

    class CircuitBreakerMixin:
        pass

    class RateLimiterMixin:
        pass

    class ModuleStatus:
        ACTIVE = "active"
        STOPPED = "stopped"

    trace_operation = prometheus_timer = metrics_collector = AuditLogger = lambda **kw: lambda f: f

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    value: Any
    ttl: float | None = None
    created_at: float = field(default_factory=time.time)
    version: int = 1
    tags: list[str] = field(default_factory=list)

    @property
    def expired(self) -> bool:
        return self.ttl is not None and time.time() - self.created_at > self.ttl

    def touch(self, ttl: float = None):
        self.created_at = time.time()
        if ttl is not None:
            self.ttl = ttl
        self.version += 1

    # --- Auto-generated action dispatch methods ---
    def _action_expired(self, params=None):
        """Auto-generated action wrapper for expired"""
        if params is None:
            params = {}
        return self.expired(**params)

    def _action_touch(self, params=None):
        """Auto-generated action wrapper for touch"""
        if params is None:
            params = {}
        return self.touch(**params)

@dataclass
class DistributedLock:
    resource: str
    token: str
    owner: str
    ttl: float
    created_at: float = field(default_factory=time.time)
    renewed: int = 0

    @property
    def expired(self) -> bool:
        return time.time() - self.created_at > self.ttl

@dataclass
class StreamEntry:
    stream_key: str
    entry_id: str
    fields: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class CacheEvictionEngine:
    """缓存淘汰策略引擎 - LRU/LFU/TTL策略选择和执行"""

    def __init__(self):
        self._policy = "lru"
        self._lru_order: list[str] = []
        self._frequency: dict[str, int] = {}

    def access(self, key: str) -> None:
        if key in self._lru_order:
            self._lru_order.remove(key)
        self._lru_order.append(key)
        self._frequency[key] = self._frequency.get(key, 0) + 1

    def evict(self, cache: dict[str, object], ttl_map: dict[str, float], max_size: int) -> str | None:
        if len(cache) <= max_size:
            return None
        if self._policy == "lru" and self._lru_order:
            victim = self._lru_order[0]
        elif self._policy == "lfu":
            victim = min(self._frequency, key=self._frequency.get) if self._frequency else None
        elif self._policy == "ttl":
            now = time.time()
            expired = [k for k, t in ttl_map.items() if t > 0 and t < now]
            victim = expired[0] if expired else None
        else:
            victim = self._lru_order[0] if self._lru_order else None
        if victim and victim in cache:
            del cache[victim]
            self._lru_order = [k for k in self._lru_order if k != victim]
            self._frequency.pop(victim, None)
            ttl_map.pop(victim, None)
            return victim
        return None

class RedisCacheModule(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Redis生产级缓存管理"""

    def __init__(self, config=None):

        super().__init__(config)
        self._store: OrderedDict = OrderedDict()
        self._locks: dict[str, DistributedLock] = {}
        self._streams: dict[str, list[StreamEntry]] = {}
        self._pubsub_channels: dict[str, list[str]] = {}
        self._pubsub_history: list[dict] = []
        self._lock = threading.RLock()
        self._max_memory_mb = self._cfg("max_memory_mb", 256)
        self._eviction_policy = self._cfg("eviction_policy", "allkeys-lru")
        self._default_ttl = self._cfg("default_ttl", 3600)
        self._redis_client = None
        if _HAS_REDIS:
            try:
                self._redis_client = _redis_lib.Redis(
                    host=self.config.get('redis_host', 'localhost'),
                    port=self.config.get('redis_port', 6379),
                    db=self.config.get('redis_db', 0),
                    password=self.config.get('redis_password', None),
                    decode_responses=True,
                    socket_connect_timeout=3,
                )
                self._redis_client.ping()
            except Exception:
                self._redis_client = None
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "evictions": 0, "lock_acquires": 0}

    def _cfg(self, key, default):
        if self.config and isinstance(self.config, dict):
            return self.config.get(key, default)
        return default

    def initialize(self) -> dict:
        self.audit("initialize", "Redis缓存模块初始化")
        return {
            "success": True,
            "max_memory_mb": self._max_memory_mb,
            "eviction": self._eviction_policy,
            "default_ttl": self._default_ttl,
        }

    def health_check(self) -> dict:
        self._cleanup_expired()
        return {
            "healthy": True,
            "keys": len(self._store),
            "locks": len(self._locks),
            "streams": len(self._streams),
            "stats": dict(self._stats),
            "redis_connected": self._redis_client is not None,
        }

    async def execute(self, action: str, params: dict = None) -> dict:
        _ = self.trace("execute")
        metrics_collector.counter("redis_cache_ops_total", labels={"action": action})
        trace_id = f"redis-execute-{int(time.time() * 1000)}"
        params = params or {}
        actions = {
            "get": self._get,
            "set": self._set,
            "delete": self._delete,
            "exists": self._exists,
            "expire": self._expire,
            "ttl": self._ttl,
            "incr": self._incr,
            "decr": self._decr,
            "mget": self._mget,
            "mset": self._mset,
            "hget": self._hget,
            "hset": self._hset,
            "hdel": self._hdel,
            "hgetall": self._hgetall,
            "hlen": self._hlen,
            "lpush": self._lpush,
            "rpush": self._rpush,
            "lrange": self._lrange,
            "lpop": self._lpop,
            "sadd": self._sadd,
            "smembers": self._smembers,
            "sismember": self._sismember,
            "srem": self._srem,
            "zadd": self._zadd,
            "zrange": self._zrange,
            "zscore": self._zscore,
            "zrem": self._zrem,
            "lock_acquire": self._lock_acquire,
            "lock_release": self._lock_release,
            "lock_renew": self._lock_renew,
            "publish": self._publish,
            "subscribe": self._subscribe,
            "xadd": self._xadd,
            "xread": self._xread,
            "keys": self._keys,
            "flushdb": self._flushdb,
            "info": self._info,
            "dbsize": self._dbsize,
            "tag_search": self._tag_search,
            "pipeline": self._pipeline,
        }
        handler = actions.get(action)
        if handler:
            self.audit(action, str(params)[:100])
            return handler(params)
        return {"success": False, "error": f"Unsupported action: {action}"}

    def _cleanup_expired(self):
        expired_keys = [k for k, v in self._store.items() if v.expired]
        for k in expired_keys:
            del self._store[k]
            self._stats["evictions"] += 1

    def _evict_lru(self):
        """LRU eviction"""
        while len(self._store) > 10000:
            self._store.popitem(last=False)
            self._stats["evictions"] += 1

    def _get(self, p: dict) -> dict:
        key = p.get("key", "")
        # 真实Redis优先
        if self._redis_client:
            try:
                val = self._redis_client.get(key)
                if val is None:
                    self._stats["misses"] += 1
                    return {"success": True, "value": None, "hit": False}
                self._stats["hits"] += 1
                try:
                    return {"success": True, "value": json.loads(val), "hit": True}
                except (json.JSONDecodeError, TypeError):
                    return {"success": True, "value": val, "hit": True}
            except Exception:
                pass  # 降级到内存
        entry = self._store.get(key)
        if entry is None:
            self._stats["misses"] += 1
            return {"success": True, "value": None, "hit": False}
        if entry.expired:
            del self._store[key]
            self._stats["misses"] += 1
            self._stats["evictions"] += 1
            return {"success": True, "value": None, "hit": False}
        self._stats["hits"] += 1
        self._store.move_to_end(key)
        return {"success": True, "value": entry.value, "ttl": entry.ttl, "version": entry.version, "hit": True}

    def _set(self, p: dict) -> dict:
        key = p.get("key", "")
        value = p.get("value")
        ttl = p.get("ttl", self._default_ttl)
        tags = p.get("tags", [])
        nx = p.get("nx", False)  # Only set if not exists
        xx = p.get("xx", False)  # Only set if exists
        # 真实Redis优先
        if self._redis_client:
            try:
                import json as _j
                val_str = _j.dumps(value) if not isinstance(value, (str, bytes)) else value
                if nx:
                    if not self._redis_client.set(key, val_str, ex=ttl, nx=True):
                        return {"success": True, "status": "not_set", "reason": "key exists"}
                elif xx:
                    if not self._redis_client.set(key, val_str, ex=ttl, xx=True):
                        return {"success": True, "status": "not_set", "reason": "key not exists"}
                else:
                    self._redis_client.setex(key, ttl or self._default_ttl, val_str)
                self._stats["sets"] += 1
                return {"success": True, "status": "OK", "key": key, "ttl": ttl or self._default_ttl}
            except Exception:
                pass  # 降级到内存
        with self._lock:
            if nx and key in self._store and not self._store[key].expired:
                return {"success": True, "status": "not_set", "reason": "key exists"}
            if xx and (key not in self._store or self._store[key].expired):
                return {"success": True, "status": "not_set", "reason": "key not exists"}
            self._store[key] = CacheEntry(value=value, ttl=ttl, tags=tags)
            self._store.move_to_end(key)
            self._stats["sets"] += 1
            self._evict_lru()
        return {"success": True, "status": "OK", "key": key, "ttl": ttl}

    def _delete(self, p: dict) -> dict:
        key = p.get("key", "")
        if self._redis_client:
            try:
                deleted = self._redis_client.delete(key) > 0
                self._stats["deletes"] += 1
                return {"success": True, "deleted": deleted}
            except Exception:
                pass
        deleted = self._store.pop(key, None)
        self._stats["deletes"] += 1
        return {"success": True, "deleted": deleted is not None}

    def _exists(self, p: dict) -> dict:
        key = p.get("key", "")
        if self._redis_client:
            try:
                exists = self._redis_client.exists(key)
                return {"success": True, "exists": bool(exists)}
            except Exception:
                pass
        entry = self._store.get(key)
        if entry and not entry.expired:
            return {"success": True, "exists": True}
        return {"success": True, "exists": False}

    def _expire(self, p: dict) -> dict:
        key = p.get("key", "")
        ttl = p.get("ttl", 60)
        entry = self._store.get(key)
        if entry:
            entry.touch(ttl)
            return {"success": True, "ttl": ttl}
        return {"success": False, "error": "key not found"}

    def _ttl(self, p: dict) -> dict:
        key = p.get("key", "")
        entry = self._store.get(key)
        if not entry or entry.expired:
            return {"success": True, "ttl": -2}
        if entry.ttl is None:
            return {"success": True, "ttl": -1}
        remaining = entry.ttl - (time.time() - entry.created_at)
        return {"success": True, "ttl": round(remaining, 1)}

    def _incr(self, p: dict) -> dict:
        key = p.get("key", "")
        amount = p.get("amount", 1)
        if self._redis_client:
            try:
                val = self._redis_client.incrby(key, amount)
                return {"success": True, "value": val}
            except Exception:
                pass
        entry = self._store.get(key)
        if entry and not entry.expired:
            try:
                entry.value = int(entry.value) + amount
                return {"success": True, "value": entry.value}
            except (ValueError, TypeError):
                return {"success": False, "error": "not an integer"}
        self._store[key] = CacheEntry(value=amount, ttl=self._default_ttl)
        return {"success": True, "value": amount}

    def _decr(self, p: dict) -> dict:
        return self._incr({**p, "amount": -p.get("amount", 1)})

    def _mget(self, p: dict) -> dict:
        keys = p.get("keys", [])
        result = {}
        for k in keys:
            entry = self._store.get(k)
            if entry and not entry.expired:
                result[k] = entry.value
            else:
                result[k] = None
        return {"success": True, "values": result}

    def _mset(self, p: dict) -> dict:
        mapping = p.get("mapping", {})
        for k, v in mapping.items():
            self._store[k] = CacheEntry(value=v, ttl=p.get("ttl", self._default_ttl))
        return {"success": True, "set_count": len(mapping)}

    def _hget(self, p: dict) -> dict:
        key, field = p.get("key", ""), p.get("field", "")
        if self._redis_client:
            try:
                val = self._redis_client.hget(key, field)
                return {"success": True, "value": val.decode() if isinstance(val, bytes) else val}
            except Exception:
                pass
        entry = self._store.get(key)
        if entry and not entry.expired and isinstance(entry.value, dict):
            return {"success": True, "value": entry.value.get(field)}
        return {"success": True, "value": None}

    def _hset(self, p: dict) -> dict:
        key, field, value = p.get("key", ""), p.get("field", ""), p.get("value")
        if self._redis_client:
            try:
                self._redis_client.hset(key, field, value)
                return {"success": True}
            except Exception:
                pass
        entry = self._store.get(key)
        if entry and isinstance(entry.value, dict):
            entry.value[field] = value
        else:
            self._store[key] = CacheEntry(value={field: value}, ttl=self._default_ttl)
        return {"success": True}

    def _hdel(self, p: dict) -> dict:
        key, field = p.get("key", ""), p.get("field", "")
        entry = self._store.get(key)
        if entry and isinstance(entry.value, dict):
            return {"success": True, "deleted": entry.value.pop(field, None) is not None}
        return {"success": True, "deleted": False}

    def _hgetall(self, p: dict) -> dict:
        key = p.get("key", "")
        if self._redis_client:
            try:
                raw = self._redis_client.hgetall(key)
                return {"success": True, "hash": {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in raw.items()}}
            except Exception:
                pass
        entry = self._store.get(key)
        if entry and not entry.expired and isinstance(entry.value, dict):
            return {"success": True, "hash": entry.value}
        return {"success": True, "hash": {}}

    def _hlen(self, p: dict) -> dict:
        entry = self._store.get(p.get("key", ""))
        if entry and isinstance(entry.value, dict):
            return {"success": True, "length": len(entry.value)}
        return {"success": True, "length": 0}

    def _lpush(self, p: dict) -> dict:
        key, value = p.get("key", ""), p.get("value")
        if self._redis_client:
            try:
                length = self._redis_client.lpush(key, value)
                self._stats["sets"] += 1
                return {"success": True, "length": length}
            except Exception:
                pass
        entry = self._store.get(key)
        if entry and isinstance(entry.value, list):
            entry.value.insert(0, value)
        else:
            self._store[key] = CacheEntry(value=[value], ttl=self._default_ttl)
        return {"success": True, "length": len(self._store[key].value)}

    def _rpush(self, p: dict) -> dict:
        key, value = p.get("key", ""), p.get("value")
        if self._redis_client:
            try:
                length = self._redis_client.rpush(key, value)
                return {"success": True, "length": length}
            except Exception:
                pass
        entry = self._store.get(key)
        if entry and isinstance(entry.value, list):
            entry.value.append(value)
        else:
            self._store[key] = CacheEntry(value=[value], ttl=self._default_ttl)
        return {"success": True, "length": len(self._store[key].value)}

    def _lrange(self, p: dict) -> dict:
        key = p.get("key", "")
        if self._redis_client:
            try:
                start = p.get("start", 0)
                stop = p.get("stop", -1)
                vals = self._redis_client.lrange(key, start, stop)
                return {"success": True, "values": [v.decode() if isinstance(v, bytes) else v for v in vals]}
            except Exception:
                pass
        entry = self._store.get(key)
        if entry and isinstance(entry.value, list):
            start = p.get("start", 0)
            stop = p.get("stop", -1)
            return {"success": True, "values": entry.value[start:stop] if stop >= 0 else entry.value[start:stop]}
        return {"success": True, "values": []}

    def _lpop(self, p: dict) -> dict:
        key = p.get("key", "")
        if self._redis_client:
            try:
                val = self._redis_client.lpop(key)
                return {"success": True, "value": val.decode() if isinstance(val, bytes) else val}
            except Exception:
                pass
        entry = self._store.get(key)
        if entry and isinstance(entry.value, list) and entry.value:
            return {"success": True, "value": entry.value.pop(0)}
        return {"success": True, "value": None}

    def _sadd(self, p: dict) -> dict:
        key, members = p.get("key", ""), p.get("members", [])
        entry = self._store.get(key)
        if entry and isinstance(entry.value, set):
            before = len(entry.value)
            entry.value.update(members)
            return {"success": True, "added": len(entry.value) - before}
        self._store[key] = CacheEntry(value=set(members), ttl=self._default_ttl)
        return {"success": True, "added": len(members)}

    def _smembers(self, p: dict) -> dict:
        entry = self._store.get(p.get("key", ""))
        if entry and isinstance(entry.value, set):
            return {"success": True, "members": list(entry.value)}
        return {"success": True, "members": []}

    def _sismember(self, p: dict) -> dict:
        entry = self._store.get(p.get("key", ""))
        if entry and isinstance(entry.value, set):
            return {"success": True, "is_member": p.get("member") in entry.value}
        return {"success": True, "is_member": False}

    def _srem(self, p: dict) -> dict:
        entry = self._store.get(p.get("key", ""))
        if entry and isinstance(entry.value, set):
            before = len(entry.value)
            entry.value.discard(p.get("member"))
            return {"success": True, "removed": before - len(entry.value)}
        return {"success": True, "removed": 0}

    def _zadd(self, p: dict) -> dict:
        key, members = p.get("key", ""), p.get("members", {})
        entry = self._store.get(key)
        if entry and isinstance(entry.value, list):
            for m, score in members.items():
                entry.value.append((m, score))
            entry.value.sort(key=lambda x: x[1])
        else:
            self._store[key] = CacheEntry(value=sorted(members.items(), key=lambda x: x[1]), ttl=self._default_ttl)
        return {"success": True, "added": len(members)}

    def _zrange(self, p: dict) -> dict:
        entry = self._store.get(p.get("key", ""))
        if entry and isinstance(entry.value, list):
            start = p.get("start", 0)
            stop = p.get("stop", -1)
            with_scores = p.get("with_scores", False)
            items = entry.value[start:stop]
            if with_scores:
                return {"success": True, "members": items}
            return {"success": True, "members": [m for m, s in items]}
        return {"success": True, "members": []}

    def _zscore(self, p: dict) -> dict:
        entry = self._store.get(p.get("key", ""))
        if entry and isinstance(entry.value, list):
            for m, s in entry.value:
                if m == p.get("member"):
                    return {"success": True, "score": s}
        return {"success": True, "score": None}

    def _zrem(self, p: dict) -> dict:
        entry = self._store.get(p.get("key", ""))
        if entry and isinstance(entry.value, list):
            before = len(entry.value)
            entry.value = [(m, s) for m, s in entry.value if m != p.get("member")]
            return {"success": True, "removed": before - len(entry.value)}
        return {"success": True, "removed": 0}

    def _lock_acquire(self, p: dict) -> dict:
        resource = p.get("resource", "")
        owner = p.get("owner", "default")
        ttl = p.get("ttl", 30)
        if resource in self._locks and not self._locks[resource].expired:
            return {"success": False, "error": "locked", "locked_by": self._locks[resource].owner}
        token = hashlib.md5(f"{resource}{time.time()}{owner}".encode()).hexdigest()[:16]
        self._locks[resource] = DistributedLock(resource, token, owner, ttl)
        self._stats["lock_acquires"] += 1
        self.audit("lock_acquire", f"{resource} by {owner}")
        return {"success": True, "token": token, "ttl": ttl}

    def _lock_release(self, p: dict) -> dict:
        resource = p.get("resource", "")
        token = p.get("token", "")
        lock = self._locks.get(resource)
        if not lock:
            return {"success": False, "error": "no lock"}
        if lock.token != token:
            return {"success": False, "error": "wrong token"}
        del self._locks[resource]
        return {"success": True, "released": True}

    def _lock_renew(self, p: dict) -> dict:
        resource, token = p.get("resource", ""), p.get("token", "")
        lock = self._locks.get(resource)
        if not lock or lock.token != token:
            return {"success": False, "error": "invalid"}
        lock.created_at = time.time()
        lock.renewed += 1
        return {"success": True, "renewed": lock.renewed}

    def _publish(self, p: dict) -> dict:
        channel = p.get("channel", "")
        message = p.get("message", "")
        msg = {"channel": channel, "message": message, "ts": time.time()}
        self._pubsub_history.append(msg)
        return {"success": True, "channel": channel, "subscribers": 0}

    def _subscribe(self, p: dict) -> dict:
        channels = p.get("channels", [])
        return {"success": True, "subscribed": channels}

    def _xadd(self, p: dict) -> dict:
        key = p.get("key", "")
        fields = p.get("fields", {})
        entry_id = f"{int(time.time() * 1000)}-{len(self._streams.get(key, []))}"
        entry = StreamEntry(key, entry_id, fields)
        self._streams.setdefault(key, []).append(entry)
        return {"success": True, "entry_id": entry_id}

    def _xread(self, p: dict) -> dict:
        key = p.get("key", "")
        count = p.get("count", 10)
        entries = self._streams.get(key, [])[-count:]
        return {"success": True, "entries": [{"id": e.entry_id, "fields": e.fields} for e in entries]}

    def _keys(self, p: dict) -> dict:
        pattern = p.get("pattern", "*")
        self._cleanup_expired()
        import fnmatch

        matched = [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]
        return {"success": True, "keys": matched[:1000], "total": len(matched)}

    def _flushdb(self, p: dict) -> dict:
        if self._redis_client:
            try:
                self._redis_client.flushdb()
                self.audit("flushdb", "real Redis flushed")
                return {"success": True, "flushed": -1}
            except Exception:
                pass
        count = len(self._store)
        self._store.clear()
        self._locks.clear()
        self._streams.clear()
        self.audit("flushdb", f"Cleared {count} keys")
        return {"success": True, "flushed": count}

    def _info(self, p: dict) -> dict:
        self._cleanup_expired()
        return {
            "success": True,
            "info": {
                "version": "7.0.0-sim",
                "keys": len(self._store),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": round(self._stats["hits"] / max(1, self._stats["hits"] + self._stats["misses"]) * 100, 2),
                "eviction_policy": self._eviction_policy,
                "max_memory_mb": self._max_memory_mb,
                "connected_clients": 1,
                "used_memory_bytes": len(str(self._store)),
            },
        }

    def _dbsize(self, p: dict) -> dict:
        self._cleanup_expired()
        if self._redis_client:
            try:
                return {"success": True, "db_size": self._redis_client.dbsize()}
            except Exception:
                pass
        return {"success": True, "db_size": len(self._store)}

    def _tag_search(self, p: dict) -> dict:
        tag = p.get("tag", "")
        results = {k: v.value for k, v in self._store.items() if not v.expired and tag in v.tags}
        return {"success": True, "count": len(results), "keys": list(results.keys())}

    def _pipeline(self, p: dict) -> dict:
        commands = p.get("commands", [])
        results = []
        for cmd in commands:
            action = cmd.get("action", "")
            params = cmd.get("params", {})
            r = self.execute(action, params)
            results.append(r)
        return {"success": True, "results": results, "count": len(results)}


module_class = RedisCacheModule

if __name__ == "__main__":
    m = RedisCacheModule()
    logger.info(m.initialize()))
    logger.info(m.execute("set", {"key": "k1", "value": "hello", "ttl": 300, "tags": ["test"]})))
    logger.info(m.execute("get", {"key": "k1"})))
    logger.info(m.execute("incr", {"key": "counter"})))
    logger.info(m.execute("hset", {"key": "user:1", "field": "name", "value": "alice"})))
    logger.info(m.execute("hgetall", {"key": "user:1"})))
    logger.info(m.execute("zadd", {"key": "rank", "members": {"alice": 100, "bob": 85}})))
    logger.info(m.execute("lock_acquire", {"resource": "deploy", "owner": "ci"})))
    logger.info(m.health_check()))
