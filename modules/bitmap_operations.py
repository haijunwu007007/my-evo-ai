from __future__ import annotations
"""
AUTO-EVO-AI V0.1 — 位图操作模块
Grade: A (生产级) | Category: 数据结构
职责：高效位图数据结构操作，支持位运算、统计、压缩、布隆过滤器集成
"""

__module_meta__ = {
        "id": "bitmap-operations",
        "name": "Bitmap Operations",
        "version": "V0.1",
        "group": "database",
        "inputs": [
            {
                "name": "size",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "index",
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
                "name": "index_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "index_3",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "start",
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
                "name": "success_3",
                "type": "bool",
                "description": "是否成功"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "bitmap",
            "manager"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 位图操作模块 Grade: A (生产级) | Category: 数据结构"
    }

import os
import asyncio
import time
import logging
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
logger = logging.getLogger("bitmap_operations")

metrics_collector = None

class Bitmap:
    """高效位图实现"""

    def __init__(self, size: int = 1024):
        self._size = max(size, 1)
        self._words = bytearray((self._size + 7) // 8)

    @property
    def size(self) -> int:
        return self._size

    def set(self, index: int, value: bool = True) -> bool:
        if index < 0 or index >= self._size:
            return False
        word_idx = index >> 3
        bit_idx = index & 7
        if value:
            self._words[word_idx] |= 1 << bit_idx
        else:
            self._words[word_idx] &= ~(1 << bit_idx)
        return True

    def get(self, index: int) -> bool:
        if index < 0 or index >= self._size:
            return False
        return bool(self._words[index >> 3] & (1 << (index & 7)))

    def flip(self, index: int) -> bool:
        if index < 0 or index >= self._size:
            return False
        self._words[index >> 3] ^= 1 << (index & 7)
        return True

    def count(self) -> int:
        """统计置位数（popcount）"""
        total = 0
        # Brian Kernighan算法
        for word in self._words:
            c = word
            while c:
                c &= c - 1
                total += 1
        return total

    def count_range(self, start: int, end: int) -> int:
        total = 0
        for i in range(max(0, start), min(self._size, end)):
            if self.get(i):
                total += 1
        return total

    def and_op(self, other: Bitmap) -> Bitmap:
        size = max(self._size, other._size)
        result = Bitmap(size)
        for i in range(min(len(self._words), len(other._words))):
            result._words[i] = self._words[i] & other._words[i]
        return result

    def or_op(self, other: Bitmap) -> Bitmap:
        size = max(self._size, other._size)
        result = Bitmap(size)
        for i in range(min(len(self._words), len(result._words))):
            result._words[i] |= self._words[i]
        for i in range(min(len(other._words), len(result._words))):
            result._words[i] |= other._words[i]
        return result

    def xor_op(self, other: Bitmap) -> Bitmap:
        size = max(self._size, other._size)
        result = Bitmap(size)
        for i in range(min(len(self._words), len(result._words))):
            result._words[i] ^= self._words[i]
        for i in range(min(len(other._words), len(result._words))):
            result._words[i] ^= other._words[i]
        return result

    def not_op(self) -> Bitmap:
        result = Bitmap(self._size)
        for i in range(len(self._words)):
            result._words[i] = ~self._words[i] & 0xFF
        return result

    def find_first_set(self, start: int = 0) -> int:
        for i in range(start, self._size):
            if self.get(i):
                return i
        return -1

    def find_first_clear(self, start: int = 0) -> int:
        for i in range(start, self._size):
            if not self.get(i):
                return i
        return -1

    def fill_rate(self) -> float:
        return self.count() / self._size if self._size > 0 else 0.0

    def to_bytes(self) -> bytes:
        return bytes(self._words)

    def to_hex(self) -> str:
        return self.to_bytes().hex()

    @classmethod
    def from_hex(cls, hex_str: str, size: int) -> Bitmap:
        bmp = cls(size)
        raw = bytes.fromhex(hex_str)
        for i in range(min(len(raw), len(bmp._words))):
            bmp._words[i] = raw[i]
        return bmp

    def __repr__(self) -> str:
        return f"Bitmap(size={self._size}, set_bits={self.count()})"

    # --- Auto-generated action dispatch methods ---
    def _action_and_op(self, params=None):
        """Auto-generated action wrapper for and_op"""
        if params is None:
            params = {}
        return self.and_op(**params)

    def _action_count(self, params=None):
        """Auto-generated action wrapper for count"""
        if params is None:
            params = {}
        return self.count(**params)

    def _action_count_range(self, params=None):
        """Auto-generated action wrapper for count_range"""
        if params is None:
            params = {}
        return self.count_range(**params)

    def _action_fill_rate(self, params=None):
        """Auto-generated action wrapper for fill_rate"""
        if params is None:
            params = {}
        return self.fill_rate(**params)

    def _action_find_first_clear(self, params=None):
        """Auto-generated action wrapper for find_first_clear"""
        if params is None:
            params = {}
        return self.find_first_clear(**params)

    def _action_find_first_set(self, params=None):
        """Auto-generated action wrapper for find_first_set"""
        if params is None:
            params = {}
        return self.find_first_set(**params)

    def _action_flip(self, params=None):
        """Auto-generated action wrapper for flip"""
        if params is None:
            params = {}
        return self.flip(**params)

    def _action_from_hex(self, params=None):
        """Auto-generated action wrapper for from_hex"""
        if params is None:
            params = {}
        return self.from_hex(**params)

    def _action_get(self, params=None):
        """Auto-generated action wrapper for get"""
        if params is None:
            params = {}
        return self.get(**params)

    def _action_not_op(self, params=None):
        """Auto-generated action wrapper for not_op"""
        if params is None:
            params = {}
        return self.not_op(**params)

    def _action_or_op(self, params=None):
        """Auto-generated action wrapper for or_op"""
        if params is None:
            params = {}
        return self.or_op(**params)

    def _action_set(self, params=None):
        """Auto-generated action wrapper for set"""
        if params is None:
            params = {}
        return self.set(**params)

    def _action_size(self, params=None):
        """Auto-generated action wrapper for size"""
        if params is None:
            params = {}
        return self.size(**params)

    def _action_to_bytes(self, params=None):
        """Auto-generated action wrapper for to_bytes"""
        if params is None:
            params = {}
        return self.to_bytes(**params)

    def _action_to_hex(self, params=None):
        """Auto-generated action wrapper for to_hex"""
        if params is None:
            params = {}
        return self.to_hex(**params)

    def _action_xor_op(self, params=None):
        """Auto-generated action wrapper for xor_op"""
        if params is None:
            params = {}
        return self.xor_op(**params)

@dataclass
class BitmapOperation:
    """位图操作记录"""

    op_id: str
    bitmap_id: str
    operation: str
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)

class BitmapOperationsManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """位图操作管理器 - 生产级实现"""

    MODULE_ID = "bitmap_operations"
    MODULE_NAME = "位图操作"
    VERSION = "V0.1"

    def __init__(self, config: dict[str, Any] | None = None):

        super().__init__(config)
        self._bitmaps: dict[str, Bitmap] = {}
        self._operations: list[BitmapOperation] = []
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return hashlib.md5(f"bm_{self._counter}_{time.time()}".encode()).hexdigest()[:10]

    def initialize(self) -> bool:
        try:
            pass
            # 创建默认位图
            self._bitmaps["default"] = Bitmap(1024)
            logger.info("位图操作模块初始化完成")
            return True
        except Exception as e:
            logger.error(f"位图操作模块初始化失败: {e}")
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        _ = self.trace("execute")
        # REMOVED: metrics_collector.counter("bitmap_ops_total", labels={"action": action})self.audit("execute", f"action={action}")
        actions = {
            "create": self._exec_create,
            "set": self._exec_set,
            "get": self._exec_get,
            "flip": self._exec_flip,
            "count": self._exec_count,
            "and": self._exec_and,
            "or": self._exec_or,
            "xor": self._exec_xor,
            "not": self._exec_not,
            "find_first_set": self._exec_find_first_set,
            "fill_rate": self._exec_fill_rate,
            "delete": self._exec_delete,
            "list": self._exec_list,
            "get_stats": self._exec_get_stats,
            "batch_set": self._exec_batch_set,
        }
        handler = actions.get(action)
        if not handler:
            return {"success": False, "error": f"未知操作: {action}"}
        return handler(params)
        return {"status": "healthy", "module": "bitmap_operations"}

    def _exec_create(self, p: dict) -> dict:
        bid = self._next_id()
        size = p.get("size", 1024)
        self._bitmaps[bid] = Bitmap(size)
        return {"success": True, "result": {"bitmap_id": bid, "size": size}}

    def _exec_set(self, p: dict) -> dict:
        bid = p["bitmap_id"]
        if bid not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        ok = self._bitmaps[bid].set(p["index"], p.get("value", True))
        return {"success": True, "result": {"index": p["index"], "value": p.get("value", True), "set": ok}}

    def _exec_get(self, p: dict) -> dict:
        bid = p["bitmap_id"]
        if bid not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        return {"success": True, "result": {"index": p["index"], "value": self._bitmaps[bid].get(p["index"])}}

    def _exec_flip(self, p: dict) -> dict:
        bid = p["bitmap_id"]
        if bid not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        ok = self._bitmaps[bid].flip(p["index"])
        return {"success": True, "result": {"index": p["index"], "new_value": self._bitmaps[bid].get(p["index"])}}

    def _exec_count(self, p: dict) -> dict:
        bid = p["bitmap_id"]
        if bid not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        bmp = self._bitmaps[bid]
        start = p.get("start", 0)
        end = p.get("end", bmp.size)
        count = bmp.count_range(start, end) if start > 0 or end < bmp.size else bmp.count()
        return {"success": True, "result": {"count": count, "total_bits": bmp.size, "range": [start, end]}}

    def _exec_and(self, p: dict) -> dict:
        a, b = p["bitmap_id_a"], p["bitmap_id_b"]
        if a not in self._bitmaps or b not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        result = self._bitmaps[a].and_op(self._bitmaps[b])
        rid = self._next_id()
        self._bitmaps[rid] = result
        return {"success": True, "result": {"result_id": rid, "count": result.count()}}

    def _exec_or(self, p: dict) -> dict:
        a, b = p["bitmap_id_a"], p["bitmap_id_b"]
        if a not in self._bitmaps or b not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        result = self._bitmaps[a].or_op(self._bitmaps[b])
        rid = self._next_id()
        self._bitmaps[rid] = result
        return {"success": True, "result": {"result_id": rid, "count": result.count()}}

    def _exec_xor(self, p: dict) -> dict:
        a, b = p["bitmap_id_a"], p["bitmap_id_b"]
        if a not in self._bitmaps or b not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        result = self._bitmaps[a].xor_op(self._bitmaps[b])
        rid = self._next_id()
        self._bitmaps[rid] = result
        return {"success": True, "result": {"result_id": rid, "count": result.count()}}

    def _exec_not(self, p: dict) -> dict:
        bid = p["bitmap_id"]
        if bid not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        result = self._bitmaps[bid].not_op()
        rid = self._next_id()
        self._bitmaps[rid] = result
        return {"success": True, "result": {"result_id": rid, "count": result.count()}}

    def _exec_find_first_set(self, p: dict) -> dict:
        bid = p["bitmap_id"]
        if bid not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        idx = self._bitmaps[bid].find_first_set(p.get("start", 0))
        return {"success": True, "result": {"first_set_index": idx}}

    def _exec_fill_rate(self, p: dict) -> dict:
        bid = p["bitmap_id"]
        if bid not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        return {"success": True, "result": {"fill_rate": round(self._bitmaps[bid].fill_rate(), 4)}}

    def _exec_delete(self, p: dict) -> dict:
        bid = p["bitmap_id"]
        if bid in self._bitmaps:
            del self._bitmaps[bid]
            return {"success": True, "result": {"deleted": True}}
        return {"success": False, "error": "位图不存在"}

    def _exec_batch_set(self, p: dict) -> dict:
        bid = p["bitmap_id"]
        if bid not in self._bitmaps:
            return {"success": False, "error": "位图不存在"}
        indices = p.get("indices", [])
        value = p.get("value", True)
        set_count = 0
        for idx in indices:
            if self._bitmaps[bid].set(idx, value):
                set_count += 1
        return {"success": True, "result": {"set_count": set_count, "total_bits": self._bitmaps[bid].count()}}

    def _exec_list(self, p: dict) -> dict:
        return {
            "success": True,
            "result": {
                "total": len(self._bitmaps),
                "bitmaps": [
                    {"id": bid, "size": bmp.size, "count": bmp.count(), "fill": round(bmp.fill_rate(), 3)}
                    for bid, bmp in self._bitmaps.items()
                ],
            },
        }

    def _exec_get_stats(self, p: dict) -> dict:
        total_bits = sum(b.size for b in self._bitmaps.values())
        total_set = sum(b.count() for b in self._bitmaps.values())
        return {
            "success": True,
            "result": {
                "total_bitmaps": len(self._bitmaps),
                "total_bits": total_bits,
                "total_set_bits": total_set,
                "overall_fill_rate": round(total_set / total_bits, 4) if total_bits > 0 else 0.0,
            },
        }

    def health_check(self) -> dict[str, Any]:
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy",
                "module_id": self.MODULE_ID,
                "bitmaps": len(self._bitmaps),
                "last_check": datetime.now().isoformat(),
            }
        )
        return result

    def shutdown(self) -> bool:
        logger.info("位图操作模块关闭")
        return True

    def analyze_bitmap_distribution(self, bitmap_id: str) -> dict[str, Any]:
        """分析位图分布特征：填充率、稀疏度、聚集度、连续段统计"""
        bm = self._bitmaps.get(bitmap_id) if hasattr(self, "_bitmaps") else None
        if not bm:
            return {"error": "bitmap not found", "bitmap_id": bitmap_id}
        size = bm.size()
        count = bm.count()
        fill_rate = count / max(size, 1)
        segments = 0
        in_segment = False
        for i in range(size):
            val = bm.get(i)
            if val and not in_segment:
                segments += 1
                in_segment = True
            elif not val:
                in_segment = False
        avg_segment = count / max(segments, 1)
        chunk_size = max(1, size // 64)
        hot_zones = []
        for start in range(0, size, chunk_size):
            end = min(start + chunk_size, size)
            cc = bm.count_range(start, end)
            cr = cc / max(end - start, 1)
            if cr > 0.8 and cc > 5:
                hot_zones.append({"start": start, "end": end, "count": cc, "density": round(cr, 3)})
        return {
            "bitmap_id": bitmap_id,
            "size": size,
            "set_bits": count,
            "fill_rate": round(fill_rate, 4),
            "sparseness": round(1 - fill_rate, 4),
            "total_segments": segments,
            "avg_segment_length": round(avg_segment, 1),
            "hot_zones": hot_zones[:10],
            "storage_efficiency": "high" if fill_rate < 0.01 else "medium" if fill_rate < 0.1 else "low",
        }

    def compute_set_operations_stats(self, op: str, id_a: str, id_b: str) -> dict[str, Any]:
        """计算两个位图集合运算结果：交集/并集/差集大小、Jaccard相似度"""
        bm_a = self._bitmaps.get(id_a) if hasattr(self, "_bitmaps") else None
        bm_b = self._bitmaps.get(id_b) if hasattr(self, "_bitmaps") else None
        if not bm_a or not bm_b:
            return {"error": "bitmap not found"}
        count_a = bm_a.count()
        count_b = bm_b.count()
        if op == "and":
            result = bm_a.and_op(bm_b)
            op_name = "intersection"
        elif op == "or":
            result = bm_a.or_op(bm_b)
            op_name = "union"
        elif op == "xor":
            result = bm_a.xor_op(bm_b)
            op_name = "symmetric_difference"
        else:
            return {"error": f"unknown operation: {op}"}
        count_result = result.count()
        union_count = bm_a.or_op(bm_b).count()
        jaccard = count_result / max(union_count, 1) if op == "and" else 0
        return {
            "operation": op_name,
            "bitmap_a": id_a,
            "bitmap_b": id_b,
            "count_a": count_a,
            "count_b": count_b,
            "result_count": count_result,
            "jaccard_similarity": round(jaccard, 4),
            "overlap_ratio": round(count_result / max(count_a, 1), 4) if op == "and" else None,
        }

    def estimate_roaring_compression(self, bitmap_id: str) -> dict[str, Any]:
        """估算Roaring Bitmap压缩效果：容器数、压缩率、内存节省建议"""
        bm = self._bitmaps.get(bitmap_id) if hasattr(self, "_bitmaps") else None
        if not bm:
            return {"error": "bitmap not found"}
        size = bm.size()
        count = bm.count()
        fill_rate = count / max(size, 1)
        raw_bytes = size / 8
        num_containers = (size + 65535) // 65536
        if fill_rate < 0.01:
            estimated_bytes = count * 2 + num_containers * 16
        elif fill_rate < 0.4:
            estimated_bytes = num_containers * 40
        else:
            estimated_bytes = num_containers * 8224
        ratio = raw_bytes / max(estimated_bytes, 1)
        savings = (1 - estimated_bytes / max(raw_bytes, 1)) * 100
        return {
            "bitmap_id": bitmap_id,
            "original_bytes": int(raw_bytes),
            "estimated_roaring_bytes": int(estimated_bytes),
            "compression_ratio": round(ratio, 1),
            "savings_percent": round(savings, 1),
            "containers": num_containers,
            "fill_rate": round(fill_rate, 4),
        }

    def batch_analyze_all(self) -> dict[str, Any]:
        """批量分析所有位图的统计摘要：总内存、填充率分布、推荐操作"""
        bitmaps = self._bitmaps if hasattr(self, "_bitmaps") else {}
        if not bitmaps:
            return {"total_bitmaps": 0}
        summary = []
        total_size = 0
        total_set = 0
        fill_rates = []
        for bid, bm in bitmaps.items():
            sz = bm.size()
            cnt = bm.count()
            fr = cnt / max(sz, 1)
            total_size += sz
            total_set += cnt
            fill_rates.append(fr)
            summary.append({"id": bid, "size": sz, "set_bits": cnt, "fill_rate": round(fr, 4)})
        fill_rates.sort()
        avg_fill = sum(fill_rates) / max(len(fill_rates), 1)
        median_fill = fill_rates[len(fill_rates) // 2] if fill_rates else 0
        sparse_count = sum(1 for r in fill_rates if r < 0.01)
        dense_count = sum(1 for r in fill_rates if r > 0.5)
        total_raw_bytes = total_size / 8
        return {
            "total_bitmaps": len(bitmaps),
            "total_bits": total_size,
            "total_set_bits": total_set,
            "overall_fill_rate": round(total_set / max(total_size, 1), 4),
            "avg_fill_rate": round(avg_fill, 4),
            "median_fill_rate": round(median_fill, 4),
            "sparse_bitmaps": sparse_count,
            "dense_bitmaps": dense_count,
            "total_raw_bytes": int(total_raw_bytes),
            "per_bitmap": summary[:50],
            "recommendation": "考虑对稀疏位图使用Roaring压缩" if sparse_count > len(bitmaps) * 0.3 else "位图使用正常",
        }

    def compute_retention_analysis(self, bitmap_sets: dict[str, Bitmap], period_labels: list[str]) -> dict[str, Any]:
        """计算留存分析：多期位图的交集运算，计算1/3/7/N日留存率"""
        if len(bitmap_sets) < 2:
            return {"error": "need at least 2 period bitmaps"}
        results = []
        base_name = period_labels[0] if period_labels else "period_0"
        base_bm = list(bitmap_sets.values())[0]
        base_count = base_bm.count()
        if base_count == 0:
            return {"error": "base period has no active users"}
        for i, (name, bm) in enumerate(bitmap_sets.items()):
            if i == 0:
                results.append({"period": name, "count": base_count, "retention_rate": 1.0, "type": "base"})
                continue
            # 留存 = 当前期与基期的交集 / 基期
            intersection = base_bm.and_op(bm)
            retained = intersection.count()
            retention = retained / base_count
            results.append(
                {
                    "period": name,
                    "count": retained,
                    "retention_rate": round(retention, 4),
                    "churned": base_count - retained,
                    "type": "retained",
                }
            )
        # 计算逐期流失
        churn_rates = []
        for i in range(1, len(results)):
            prev = results[i - 1]["count"]
            curr = results[i]["count"]
            if prev > 0:
                churn_rates.append(
                    {
                        "from": results[i - 1]["period"],
                        "to": results[i]["period"],
                        "churn_rate": round(1 - curr / prev, 4),
                    }
                )
        return {
            "base_count": base_count,
            "periods": results,
            "churn_analysis": churn_rates,
            "best_retention": max(results, key=lambda x: x["retention_rate"])["period"],
            "worst_retention": min(results[1:], key=lambda x: x["retention_rate"])["period"]
            if len(results) > 1
            else None,
        }

    def find_similar_bitmaps(self, threshold: float = 0.8) -> list[dict[str, Any]]:
        """发现相似位图：通过Jaccard相似度聚类，用于标签去重和合并建议"""
        bitmaps = self._bitmaps if hasattr(self, "_bitmaps") else {}
        ids = list(bitmaps.keys())
        if len(ids) < 2:
            return []
        similar = []
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                bm_a = bitmaps[ids[i]]
                bm_b = bitmaps[ids[j]]
                union = bm_a.or_op(bm_b).count()
                intersection = bm_a.and_op(bm_b).count()
                jaccard = intersection / max(union, 1)
                if jaccard >= threshold:
                    similar.append(
                        {
                            "bitmap_a": ids[i],
                            "bitmap_b": ids[j],
                            "jaccard": round(jaccard, 4),
                            "union_size": union,
                            "recommendation": "merge" if jaccard > 0.95 else "review",
                        }
                    )
        similar.sort(key=lambda x: x["jaccard"], reverse=True)
        return similar

module_class = BitmapOperationsManager
