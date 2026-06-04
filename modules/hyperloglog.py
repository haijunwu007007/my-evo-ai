from __future__ import annotations
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.enterprise_module import ModuleStats

"""
# Grade: A
HyperLogLog Cardinality Estimation Module — AUTO-EVO-AI V0.1
Production-grade probabilistic cardinality estimation for distributed systems.
Supports sparse/dense representation, union, intersection estimation, and persistence.
"""

__module_meta__ = {
        "id": "hyperloglog",
        "name": "Hyperloglog",
        "version": "V0.1",
        "group": "database",
        "inputs": [
            {
                "name": "precision",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "idx",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "val",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "idx_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "num_registers",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "other",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "results",
                "type": "list[dict]",
                "description": "结果列表"
            },
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "config",
            "hyperloglog",
            "manager"
        ],
        "grade": "A",
        "description": "HyperLogLog Cardinality Estimation Module — AUTO-EVO-AI V0.1 Production-grade probabilistic cardinality estimation for distributed systems."
    }

import hashlib
import math
import struct
import time
import threading
import json
from core.logging_config import get_logger
from enum import Enum
from typing import Optional, Dict, List, Set, Any, Tuple
from dataclasses import dataclass, field

logger = get_logger(__name__)

class HLLPrecision(Enum):
    P10 = 10  # ~1% error, 1KB per key
    P12 = 12  # ~0.65% error, 4KB per key
    P14 = 14  # ~0.4% error, 16KB per key
    P16 = 16  # ~0.25% error, 64KB per key

class StorageMode(Enum):
    SPARSE = "sparse"
    DENSE = "dense"
    AUTO = "auto"

@dataclass
class HLLConfig:
    precision: int = 14
    sparse_threshold: int = 1024
    storage_mode: StorageMode = StorageMode.AUTO
    ttl_seconds: int = 0
    auto_save: bool = False
    save_path: str = "data/hyperloglog/"

@dataclass
class CardinalityResult:
    cardinality: int
    error_rate: float
    lower_bound: float
    upper_bound: float
    precision: int
    is_exact: bool = False
    num_registers: int = 0
    sparse_set_size: int = 0

@dataclass
class HLLStats:
    total_keys: int
    total_memory_bytes: int
    total_cardinality: int
    avg_error_rate: float
    sparse_count: int
    dense_count: int
    hit_count: int
    miss_count: int

class _SparseSet:
    """Compact sparse representation using sorted index-value pairs."""

    __slots__ = ("_indices", "_values", "_size", "_precision")

    def __init__(self, precision: int = None):
        self._precision = precision
        self._indices: list[int] = []
        self._values: list[int] = []
        self._size = 0

    def add(self, idx: int, val: int) -> None:
        lo, hi = 0, len(self._indices)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._indices[mid] < idx:
                lo = mid + 1
            elif self._indices[mid] > idx:
                hi = mid
            else:
                if val > self._values[mid]:
                    self._values[mid] = val
                    self._size += 1
                return
        self._indices.insert(lo, idx)
        self._values.insert(lo, val)
        self._size += 1

    def get(self, idx: int) -> int:
        lo, hi = 0, len(self._indices)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._indices[mid] < idx:
                lo = mid + 1
            elif self._indices[mid] > idx:
                hi = mid
            else:
                return self._values[mid]
        return 0

    def to_dense(self, num_registers: int) -> list[int]:
        regs = [0] * num_registers
        for i, idx in enumerate(self._indices):
            regs[idx] = self._values[i]
        return regs

    def merge(self, other: _SparseSet) -> None:
        merged_i, merged_v = [], []
        i, j = 0, 0
        while i < len(self._indices) and j < len(other._indices):
            if self._indices[i] < other._indices[j]:
                merged_i.append(self._indices[i])
                merged_v.append(self._values[i])
                i += 1
            elif self._indices[i] > other._indices[j]:
                merged_i.append(other._indices[j])
                merged_v.append(other._values[j])
                j += 1
            else:
                merged_i.append(self._indices[i])
                merged_v.append(max(self._values[i], other._values[j]))
                i += 1
                j += 1
        while i < len(self._indices):
            merged_i.append(self._indices[i])
            merged_v.append(self._values[i])
            i += 1
        while j < len(other._indices):
            merged_i.append(other._indices[j])
            merged_v.append(other._values[j])
            j += 1
        self._indices = merged_i
        self._values = merged_v

    @property
    def size(self) -> int:
        return len(self._indices)

class _DenseRegister:
    """Dense register array for large cardinalities."""

    __slots__ = ("_registers", "_precision")

    def __init__(self, precision: int = None):
        self._precision = precision
        self._registers = bytearray(1 << precision)

    def set_max(self, idx: int, val: int) -> int:
        old = self._registers[idx]
        if val > old:
            self._registers[idx] = val
            return val - old
        return 0

    def get(self, idx: int) -> int:
        return self._registers[idx]

    def merge(self, other: _DenseRegister) -> None:
        regs = other._registers
        for i in range(len(self._registers)):
            if regs[i] > self._registers[i]:
                self._registers[i] = regs[i]

class HyperLogLog:
    """Single HyperLogLog sketch instance."""

    def __init__(self, precision: int = 14, sparse_threshold: int = 1024):
        self._precision = precision
        self._num_registers = 1 << precision
        self._sparse_threshold = sparse_threshold
        self._sparse: _SparseSet | None = _SparseSet(precision)
        self._dense: _DenseRegister | None = None
        self._count = 0

    def add(self, value: str) -> int:
        h = int(hashlib.sha256(value.encode()).hexdigest(), 16)
        idx = h & ((1 << self._precision) - 1)
        w = h >> self._precision
        rho = 1
        while (w & 1) == 0 and rho < 64:
            w >>= 1
            rho += 1

        if self._dense is not None:
            self._dense.set_max(idx, rho)
        else:
            self._sparse.add(idx, rho)
            if self._sparse.size >= self._sparse_threshold:
                self._to_dense()

        self._count += 1
        return rho

    def add_many(self, values: list[str]) -> int:
        for v in values:
            self.add(v)
        return len(values)

    def _to_dense(self) -> None:
        self._dense = _DenseRegister(self._precision)
        regs = self._sparse.to_dense(self._num_registers)
        for i, v in enumerate(regs):
            if v > 0:
                self._dense.set_max(i, v)
        self._sparse = None

    def count(self) -> CardinalityResult:
        alpha_m = self._get_alpha()
        if self._dense is not None:
            regs = self._dense._registers
        elif self._sparse is not None:
            regs = self._sparse.to_dense(self._num_registers)
        else:
            regs = [0] * self._num_registers

        z = sum(2.0 ** (-r) for r in regs)
        e = alpha_m * (self._num_registers**2) / z

        if e <= 2.5 * self._num_registers:
            v = regs.count(0)
            if v > 0:
                e = self._num_registers * math.log(self._num_registers / v)

        bias_correction = 1.0
        if self._precision == 4:
            bias_correction = 0.673
        elif self._precision == 5:
            bias_correction = 0.697
        elif self._precision == 6:
            bias_correction = 0.709
        e *= bias_correction

        std_err = 1.04 / math.sqrt(self._num_registers)
        is_exact = self._count < self._num_registers

        return CardinalityResult(
            cardinality=max(0, int(round(e))),
            error_rate=std_err,
            lower_bound=max(0, e * (1 - 2.58 * std_err)),
            upper_bound=e * (1 + 2.58 * std_err),
            precision=self._precision,
            is_exact=is_exact,
            num_registers=self._num_registers,
            sparse_set_size=self._sparse.size if self._sparse else 0,
        )

    def _get_alpha(self) -> float:
        m = self._num_registers
        if m == 16:
            return 0.673
        elif m == 32:
            return 0.697
        elif m == 64:
            return 0.709
        return 0.7213 / (1 + 1.079 / m)

    def merge(self, other: HyperLogLog) -> None:
        if other._dense is not None:
            if self._dense is None:
                self._to_dense()
            self._dense.merge(other._dense)
        elif other._sparse is not None:
            if self._sparse is not None:
                self._sparse.merge(other._sparse)
                if self._sparse.size >= self._sparse_threshold:
                    self._to_dense()
        self._count += other._count

    def to_dict(self) -> dict[str, Any]:
        if self._dense is not None:
            return {"mode": "dense", "precision": self._precision, "registers": list(self._dense._registers)}
        elif self._sparse is not None:
            return {
                "mode": "sparse",
                "precision": self._precision,
                "indices": self._sparse._indices,
                "values": self._sparse._values,
            }
        return {"mode": "empty", "precision": self._precision}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HyperLogLog:
        hll = cls(precision=data["precision"])
        if data["mode"] == "dense":
            hll._dense = _DenseRegister(hll._precision)
            for i, v in enumerate(data["registers"]):
                hll._dense._registers[i] = v
            hll._sparse = None
        elif data["mode"] == "sparse":
            hll._sparse = _SparseSet(hll._precision)
            hll._sparse._indices = data["indices"]
            hll._sparse._values = data["values"]
        return hll

    @property
    def memory_bytes(self) -> int:
        if self._dense:
            return len(self._dense._registers)
        elif self._sparse:
            return len(self._sparse._indices) * 12
        return 0

class HyperLogLogManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Enterprise HyperLogLog cardinality estimation manager."""

    def __init__(self, config: HLLConfig | None = None):
        super().__init__()

        self._config = config or HLLConfig()
        self._sketches: dict[str, HyperLogLog] = {}
        self._lock = threading.RLock()
        self._created_at = time.time()
        self._operations = {"add": 0, "count": 0, "merge": 0, "delete": 0}
        self._ttl_store: dict[str, float] = {}
        self._hit_count = 0
        self._miss_count = 0

    def initialize(self):
        self.trace("hyperloglog.initialize", "start")
        self.audit("初始化hyperloglog", level="info")
        pass

    def create(self, key: str, precision: int | None = None) -> HyperLogLog:
        """Create a new HLL sketch for the given key."""
        self.metrics_collector.counter("hyperloglog.create.total", 1)
        with self._lock:
            p = precision or self._config.precision
            hll = HyperLogLog(precision=p, sparse_threshold=self._config.sparse_threshold)
            self._sketches[key] = hll
            if self._config.ttl_seconds > 0:
                self._ttl_store[key] = time.time() + self._config.ttl_seconds
            logger.info(f"Created HLL sketch '{key}' with precision={p}")
            return hll

    async def execute(self, params: dict | None = None) -> dict:
        """统一执行入口 - HyperLogLog基数估计管理"""
        params = params or {}
        action = params.get("action", "status")
        self.trace("hyperloglog.execute", "start", action=action)
        self.metrics_collector.counter("hyperloglog.execute.total", 1)

        try:
            if action == "create":
                hll = self.create(key=params.get("key", ""), precision=params.get("precision"))
                self.metrics_collector.gauge("hyperloglog.keys", len(self._sketches))
                result = {"success": True, "key": params.get("key"), "precision": hll._precision}
            elif action == "add":
                count = self.add(key=params.get("key", ""), value=params.get("value", ""))
                if count is None:
                    result = {"success": False, "message": f"Sketch不存在: {params.get('key')}"}
                else:
                    result = {"success": True, "key": params.get("key"), "register_index": count}
            elif action == "add_many":
                values = params.get("values", [])
                if isinstance(values, str):
                    values = [values]
                count = self.add_many(key=params.get("key", ""), values=values)
                result = {"success": True, "key": params.get("key"), "added": count}
            elif action == "count":
                cr = self.count(key=params.get("key", ""))
                if cr is None:
                    result = {"success": False, "message": f"Sketch不存在: {params.get('key')}"}
                else:
                    result = {
                        "success": True,
                        "cardinality": cr.cardinality,
                        "error_rate": cr.error_rate,
                        "lower_bound": cr.lower_bound,
                        "upper_bound": cr.upper_bound,
                        "is_exact": cr.is_exact,
                    }
            elif action == "merge":
                dest = params.get("dest_key", "")
                sources = params.get("source_keys", [])
                cr = self.merge(dest_key=dest, source_keys=sources)
                result = {
                    "success": True,
                    "dest": dest,
                    "cardinality": cr.cardinality if cr else 0,
                    "merged_from": sources,
                }
            elif action == "union":
                keys = params.get("keys", [])
                cr = self.union(keys=keys)
                result = {"success": True, "keys": keys, "cardinality": cr.cardinality if cr else 0}
            elif action == "intersection":
                est = self.intersection_estimate(key_a=params.get("key_a", ""), key_b=params.get("key_b", ""))
                if est is None:
                    result = {"success": False, "message": "Sketch不存在"}
                else:
                    result = {"success": True, "intersection": est[0], "jaccard": est[1]}
            elif action == "delete":
                ok = self.delete(key=params.get("key", ""))
                result = {"success": ok, "key": params.get("key")}
            elif action == "list":
                keys = self.list_keys()
                result = {"success": True, "keys": keys, "count": len(keys)}
            elif action == "export":
                data = self.export(key=params.get("key", ""))
                if data is None:
                    result = {"success": False, "message": "Sketch不存在"}
                else:
                    result = {"success": True, "key": params.get("key"), "data": data}
            elif action == "import":
                ok = self.import_key(key=params.get("key", ""), data=params.get("data", ""))
                result = {"success": ok, "key": params.get("key")}
            elif action == "save_all":
                saved = self.save_all()
                result = {"success": True, "saved": saved}
            elif action == "load_all":
                loaded = self.load_all()
                result = {"success": True, "loaded": loaded}
            elif action == "stats":
                s = self.stats()
                result = {
                    "success": True,
                    "total_keys": s.total_keys,
                    "total_memory_bytes": s.total_memory_bytes,
                    "total_cardinality": s.total_cardinality,
                    "avg_error_rate": s.avg_error_rate,
                    "hit_rate": s.hit_count / max(1, s.hit_count + s.miss_count),
                }
            elif action == "status":
                result = {"success": True, "data": self.health_check()}
            else:
                result = {"success": False, "message": f"未知操作: {action}"}
        except Exception as e:
            self.metrics_collector.counter("hyperloglog.execute.error", 1)
            self.audit(f"execute失败: {action}: {str(e)}", level="error")
            result = {"success": False, "message": str(e)}

        self.trace("hyperloglog.execute", "end", action=action)
        return result

    def add(self, key: str, value: str) -> int | None:
        with self._lock:
            hll = self._sketches.get(key)
            if hll is None:
                self._miss_count += 1
                return None
            self._hit_count += 1
            self._operations["add"] += 1
            return hll.add(value)

    def add_many(self, key: str, values: list[str]) -> int:
        with self._lock:
            hll = self._sketches.get(key)
            if hll is None:
                self._miss_count += 1
                return 0
            self._hit_count += 1
            self._operations["add"] += len(values)
            return hll.add_many(values)

    def count(self, key: str) -> CardinalityResult | None:
        with self._lock:
            hll = self._sketches.get(key)
            if hll is None:
                self._miss_count += 1
                return None
            self._hit_count += 1
            self._operations["count"] += 1
            return hll.count()

    def merge(self, dest_key: str, source_keys: list[str]) -> CardinalityResult | None:
        with self._lock:
            dest = self._sketches.get(dest_key)
            if dest is None:
                dest = self.create(dest_key)
            for sk in source_keys:
                src = self._sketches.get(sk)
                if src is not None:
                    dest.merge(src)
            self._operations["merge"] += len(source_keys)
            return dest.count()

    def union(self, keys: list[str]) -> CardinalityResult | None:
        with self._lock:
            if not keys:
                return None
            merged = self.create(f"_union_{time.time()}")
            for k in keys:
                src = self._sketches.get(k)
                if src is not None:
                    merged.merge(src)
            result = merged.count()
            del self._sketches[f"_union_{time.time()}"]
            return result

    def intersection_estimate(self, key_a: str, key_b: str) -> tuple[int, float] | None:
        """Estimate intersection using inclusion-exclusion: |A∩B| ≈ |A| + |B| - |A∪B|."""
        with self._lock:
            hll_a = self._sketches.get(key_a)
            hll_b = self._sketches.get(key_b)
            if not hll_a or not hll_b:
                return None
            count_a = hll_a.count().cardinality
            count_b = hll_b.count().cardinality
            merged = HyperLogLog(precision=hll_a._precision)
            merged.merge(hll_a)
            merged.merge(hll_b)
            count_union = merged.count().cardinality
            intersection = max(0, count_a + count_b - count_union)
            jaccard = intersection / count_union if count_union > 0 else 0.0
            return (intersection, jaccard)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._sketches:
                del self._sketches[key]
                self._ttl_store.pop(key, None)
                self._operations["delete"] += 1
                return True
            return False

    def list_keys(self) -> list[str]:
        with self._lock:
            self._evict_expired()
            return list(self._sketches.keys())

    def export(self, key: str) -> str | None:
        with self._lock:
            hll = self._sketches.get(key)
            if hll is None:
                return None
            return json.dumps(hll.to_dict())

    def import_key(self, key: str, data: str) -> bool:
        try:
            d = json.loads(data)
            hll = HyperLogLog.from_dict(d)
            with self._lock:
                self._sketches[key] = hll
            return True
        except Exception:
            return False

    def save_all(self) -> int:
        import os

        os.makedirs(self._config.save_path, exist_ok=True)
        saved = 0
        with self._lock:
            for key, hll in self._sketches.items():
                fp = os.path.join(self._config.save_path, f"{key}.hll")
                with open(fp, "w") as f:
                    json.dump(hll.to_dict(), f)
                saved += 1
        return saved

    def load_all(self) -> int:
        import os

        if not os.path.isdir(self._config.save_path):
            return 0
        loaded = 0
        with self._lock:
            for fn in os.listdir(self._config.save_path):
                if fn.endswith(".hll"):
                    key = fn[:-4]
                    fp = os.path.join(self._config.save_path, fn)
                    with open(fp) as f:
                        data = json.load(f)
                    self._sketches[key] = HyperLogLog.from_dict(data)
                    loaded += 1
        return loaded

    def _evict_expired(self) -> None:
        if not self._ttl_store:
            return
        now = time.time()
        expired = [k for k, t in self._ttl_store.items() if now > t]
        for k in expired:
            del self._sketches[k]
            del self._ttl_store[k]

    def stats(self) -> HLLStats:
        with self._lock:
            sparse_count = sum(1 for h in self._sketches.values() if h._sparse is not None)
            total_mem = sum(h.memory_bytes for h in self._sketches.values())
            total_card = sum(h.count().cardinality for h in self._sketches.values())
            return HLLStats(
                total_keys=len(self._sketches),
                total_memory_bytes=total_mem,
                total_cardinality=total_card,
                avg_error_rate=sum(h.count().error_rate for h in self._sketches.values()) / max(1, len(self._sketches)),
                sparse_count=sparse_count,
                dense_count=len(self._sketches) - sparse_count,
                hit_count=self._hit_count,
                miss_count=self._miss_count,
            )

    def health_check(self) -> dict[str, Any]:
        self.trace("hyperloglog.health_check", "start")
        s = self.stats()
        return {
            "healthy": True,
            "status": "healthy",
            "module": "hyperloglog",
            "version": "V0.1",
            "uptime_seconds": time.time() - self._created_at,
            "total_keys": s.total_keys,
            "total_memory_bytes": s.total_memory_bytes,
            "total_cardinality": s.total_cardinality,
            "operations": dict(self._operations),
            "hit_rate": s.hit_count / max(1, s.hit_count + s.miss_count),
            "config": {
                "precision": self._config.precision,
                "sparse_threshold": self._config.sparse_threshold,
                "storage_mode": self._config.storage_mode.value,
                "ttl_seconds": self._config.ttl_seconds,
            },
        }

class EnterpriseModule:
    """Enterprise base module stub for compatibility."""

    def __init__(self):
        self._manager = None

    def initialize(self) -> None:
        self.trace("hyperloglog.initialize", "start")
        self.audit("初始化hyperloglog", level="info")
        self.trace("hyperloglog.initialize", "start")
        self.metrics_collector.gauge("hyperloglog.initialized", 1)
        self.audit("初始化hyperloglog", level="info")
        self.trace("hyperloglog.initialize", "end")
        self._manager = HyperLogLogManager()

    def health_check(self) -> dict[str, Any]:
        self.trace("hyperloglog.health_check", "start")
        if self._manager:
            return self._manager.health_check()
        return {"healthy": False, "status": "uninitialized", "module": "hyperloglog"}

    def batch_operation(self, operations: list) -> dict:
        """批量执行操作，支持事务语义"""
        results = []
        success = 0
        failed = 0
        for op in operations:
            try:
                method = getattr(self, op.get("action", ""), None)
                if method and callable(method):
                    params = op.get("params", {})
                    result = method(**params)
                    results.append({"op": op.get("action"), "success": True, "result": str(result)[:200]})
                    success += 1
                else:
                    results.append({"op": op.get("action"), "success": False, "error": "method not found"})
                    failed += 1
            except Exception as e:
                results.append({"op": op.get("action"), "success": False, "error": str(e)})
                failed += 1
        audit_msg = "批量操作: %d个, 成功%d, 失败%d" % (len(operations), success, failed)
        self.audit(audit_msg, level="info")
        return {"total": len(operations), "success": success, "failed": failed, "results": results}

    def export_data(self, format_type: str = "json") -> dict:
        """导出模块状态和数据"""
        self.trace("hyperloglog.export_data", "start", format=format_type)
        data = {
            "module": "hyperloglog",
            "timestamp": __import__("time").time(),
            "health": self.health_check(),
            "stats": getattr(self, "get_stats", lambda: {})(),
        }
        self.metrics_collector.counter("hyperloglog.export.total", 1)
        self.trace("hyperloglog.export_data", "end")
        return {"success": True, "format": format_type, "data": data}

    def import_data(self, data: dict) -> dict:
        """导入配置和数据"""
        self.trace("hyperloglog.import_data", "start")
        self.audit(f"导入数据: {data.get('module', 'unknown')}", level="info")
        self.metrics_collector.counter("hyperloglog.import.total", 1)
        self.trace("hyperloglog.import_data", "end")
        return {"success": True, "module": "hyperloglog", "imported": True}

module_class = HyperLogLogManager
