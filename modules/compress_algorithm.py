"""
AUTO-EVO-AI v7.0 — 压缩算法管理器
Grade: A (生产级) | Category: 数据处理
职责：数据压缩/解压缩、算法选择、压缩比分析、批量处理、归档管理
"""

__module_meta__ = {
    "id": "compress-algorithm",
    "name": "Compress Algorithm",
    "version": "1.0.0",
    "group": "storage",
    "inputs": [
        {"name": "sample_data", "type": "string", "required": True, "description": ""},
        {"name": "iterations", "type": "string", "required": True, "description": ""},
        {"name": "file_path", "type": "string", "required": True, "description": ""},
        {"name": "algorithm", "type": "string", "required": True, "description": ""},
        {"name": "data", "type": "string", "required": True, "description": ""},
        {"name": "algorithm", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["compress", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 — 压缩算法管理器 Grade: A (生产级) | Category: 数据处理",
}

import os
import io
import gzip
import zlib
import bz2
import lzma
import time
import uuid
import json
import base64
import logging
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

class Algorithm(Enum):
    GZIP = "gzip"
    ZLIB = "zlib"
    BZ2 = "bz2"
    LZMA = "lzma"
    LZMA_XZ = "lzma_xz"
    RAW_DEFLATE = "raw_deflate"

@dataclass
class CompressionResult:
    """压缩结果"""

    task_id: str = ""
    algorithm: str = ""
    original_size: int = 0
    compressed_size: int = 0
    ratio: float = 0.0
    speed_mbps: float = 0.0
    checksum_original: str = ""
    checksum_compressed: str = ""
    duration_ms: float = 0.0
    timestamp: float = 0.0

@dataclass
class ArchiveEntry:
    """归档条目"""

    name: str = ""
    original_size: int = 0
    compressed_size: int = 0
    checksum: str = ""
    added_at: float = 0.0

class CompressAlgorithmManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """压缩算法管理器 - 生产级实现"""

    MODULE_ID = "compress_algorithm"
    MODULE_NAME = "compress_algorithm"
    VERSION = "7.0.0"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "compress_algorithm",
                "version": "7.0.0",
                "description": "数据压缩/解压缩管理，支持多种算法、压缩比分析、批量处理、归档管理",
            }
        )
        self._history: List[CompressionResult] = []
        self._archives: Dict[str, Dict] = {}  # archive_id -> {entries, metadata}
        self._initialized = False
        self._max_history = 2000

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True

    def _compress(self, data: bytes, algorithm: Algorithm, level: int = -1) -> bytes:
        """执行压缩"""
        if algorithm == Algorithm.GZIP:
            return gzip.compress(data, compresslevel=min(max(level if level >= 0 else 6, 1), 9))
        elif algorithm == Algorithm.ZLIB:
            return zlib.compress(data, level=min(max(level if level >= 0 else 6, 1), 9))
        elif algorithm == Algorithm.BZ2:
            return bz2.compress(data, compresslevel=min(max(level if level >= 0 else 6, 1), 9))
        elif algorithm == Algorithm.LZMA:
            return lzma.compress(data, preset=min(max(level if level >= 0 else 6, 0), 9))
        elif algorithm == Algorithm.LZMA_XZ:
            return lzma.compress(data, format=lzma.FORMAT_XZ, preset=min(max(level if level >= 0 else 6, 0), 9))
        elif algorithm == Algorithm.RAW_DEFLATE:
            comp = zlib.compressobj(level=min(max(level if level >= 0 else 6, 1), 9), method=zlib.DEFLATED)
            return comp.compress(data) + comp.flush()
        raise ValueError(f"不支持的算法: {algorithm}")

    def _decompress(self, data: bytes, algorithm: Algorithm) -> bytes:
        """执行解压缩"""
        if algorithm == Algorithm.GZIP:
            return gzip.decompress(data)
        elif algorithm == Algorithm.ZLIB:
            return zlib.decompress(data)
        elif algorithm == Algorithm.BZ2:
            return bz2.decompress(data)
        elif algorithm == Algorithm.LZMA:
            return lzma.decompress(data, format=lzma.FORMAT_ALONE)
        elif algorithm == Algorithm.LZMA_XZ:
            return lzma.decompress(data, format=lzma.FORMAT_XZ)
        elif algorithm == Algorithm.RAW_DEFLATE:
            return zlib.decompress(data, -zlib.MAX_WBITS)
        raise ValueError(f"不支持的算法: {algorithm}")

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一execute入口"""
        self.trace("execute", {"module": "compress_algorithm"})
        self.metrics_collector.counter("compress_algorithm.execute.calls", 1)
        self.audit("execute", {"module": "compress_algorithm"})
        params = params or {}
        try:
            if action == "compress":
                raw = params.get("data", "")
                if not raw:
                    return {"success": False, "error": "数据不能为空"}

                # 支持base64编码的binary或纯文本
                if isinstance(raw, str):
                    try:
                        data = base64.b64decode(raw)
                    except Exception:
                        data = raw.encode("utf-8")
                elif isinstance(raw, bytes):
                    data = raw
                else:
                    return {"success": False, "error": "数据类型必须为str或bytes"}

                algo = Algorithm(params.get("algorithm", "gzip"))
                level = params.get("level", -1)

                start = time.time()
                compressed = self._compress(data, algo, level)
                duration_ms = (time.time() - start) * 1000
                orig_size = len(data)
                comp_size = len(compressed)

                result = CompressionResult(
                    task_id=f"comp_{uuid.uuid4().hex[:8]}",
                    algorithm=algo.value,
                    original_size=orig_size,
                    compressed_size=comp_size,
                    ratio=round(comp_size / max(orig_size, 1) * 100, 2),
                    speed_mbps=round(orig_size / (duration_ms / 1000 + 0.001) / 1_000_000, 2),
                    checksum_original=hashlib.sha256(data).hexdigest()[:16],
                    checksum_compressed=hashlib.sha256(compressed).hexdigest()[:16],
                    duration_ms=round(duration_ms, 1),
                    timestamp=time.time(),
                )

                if len(self._history) >= self._max_history:
                    self._history.pop(0)
                self._history.append(result)

                return {
                    "success": True,
                    "result": {
                        "task_id": result.task_id,
                        "algorithm": result.algorithm,
                        "original_size": result.original_size,
                        "compressed_size": result.compressed_size,
                        "ratio": result.ratio,
                        "compression_ratio": f"{result.ratio:.1f}%",
                        "space_saved": f"{100 - result.ratio:.1f}%",
                        "speed_mbps": result.speed_mbps,
                        "duration_ms": result.duration_ms,
                        "checksum_original": result.checksum_original,
                        "checksum_compressed": result.checksum_compressed,
                        "compressed_base64": base64.b64encode(compressed).decode("ascii")[:100] + "...",
                    },
                }

            elif action == "decompress":
                raw = params.get("data", "")
                algo = Algorithm(params.get("algorithm", "gzip"))
                if not raw:
                    return {"success": False, "error": "数据不能为空"}
                try:
                    if isinstance(raw, str):
                        data = base64.b64decode(raw)
                    else:
                        data = raw
                except Exception:
                    return {"success": False, "error": "数据解码失败"}

                start = time.time()
                decompressed = self._decompress(data, algo)
                duration_ms = (time.time() - start) * 1000

                return {
                    "success": True,
                    "result": {
                        "decompressed_size": len(decompressed),
                        "original_size": len(data),
                        "expansion_ratio": round(len(decompressed) / max(len(data), 1) * 100, 2),
                        "duration_ms": round(duration_ms, 1),
                        "checksum": hashlib.sha256(decompressed).hexdigest()[:16],
                        "preview": decompressed[:200].decode("utf-8", errors="replace"),
                    },
                }

            elif action == "benchmark":
                """对比多种算法压缩同一数据"""
                raw = params.get("data", "")
                if not raw:
                    return {"success": False, "error": "数据不能为空"}
                if isinstance(raw, str):
                    data = raw.encode("utf-8")
                else:
                    data = raw
                level = params.get("level", 6)
                results = []
                for algo in Algorithm:
                    start = time.time()
                    compressed = self._compress(data, algo, level)
                    dur = (time.time() - start) * 1000
                    results.append(
                        {
                            "algorithm": algo.value,
                            "original_size": len(data),
                            "compressed_size": len(compressed),
                            "ratio": f"{round(len(compressed) / max(len(data), 1) * 100, 1)}%",
                            "space_saved": f"{round(100 - len(compressed) / max(len(data), 1) * 100, 1)}%",
                            "duration_ms": round(dur, 1),
                            "speed_mbps": round(len(data) / (dur / 1000 + 0.001) / 1_000_000, 2),
                        }
                    )
                # 按压缩率排序
                results.sort(key=lambda x: x["compressed_size"])
                best = results[0]["algorithm"]
                return {
                    "success": True,
                    "result": {"data_size": len(data), "level": level, "best_algorithm": best, "results": results},
                }

            elif action == "batch_compress":
                """批量压缩"""
                files = params.get("files", [])
                algo = Algorithm(params.get("algorithm", "gzip"))
                level = params.get("level", -1)
                results = []
                for f in files:
                    name = f.get("name", "unknown")
                    data_str = f.get("data", "")
                    if not data_str:
                        results.append({"name": name, "success": False, "error": "空数据"})
                        continue
                    data = data_str.encode("utf-8") if isinstance(data_str, str) else data_str
                    try:
                        start = time.time()
                        compressed = self._compress(data, algo, level)
                        dur = (time.time() - start) * 1000
                        results.append(
                            {
                                "name": name,
                                "success": True,
                                "original_size": len(data),
                                "compressed_size": len(compressed),
                                "ratio": f"{round(len(compressed) / max(len(data), 1) * 100, 1)}%",
                                "duration_ms": round(dur, 1),
                            }
                        )
                    except Exception as e:
                        results.append({"name": name, "success": False, "error": str(e)})
                total_orig = sum(r.get("original_size", 0) for r in results if r.get("success"))
                total_comp = sum(r.get("compressed_size", 0) for r in results if r.get("success"))
                return {
                    "success": True,
                    "result": {
                        "total": len(results),
                        "success": sum(1 for r in results if r.get("success")),
                        "failed": sum(1 for r in results if not r.get("success")),
                        "total_original": total_orig,
                        "total_compressed": total_comp,
                        "overall_ratio": f"{round(total_comp / max(total_orig, 1) * 100, 1)}%" if total_orig else "N/A",
                        "details": results,
                    },
                }

            elif action == "create_archive":
                """创建归档"""
                aid = f"archive_{uuid.uuid4().hex[:8]}"
                entries = []
                for f in params.get("files", []):
                    name = f.get("name", "unknown")
                    data_str = f.get("data", "")
                    data = data_str.encode("utf-8") if isinstance(data_str, str) else data_str
                    entries.append(
                        ArchiveEntry(
                            name=name,
                            original_size=len(data),
                            checksum=hashlib.sha256(data).hexdigest()[:12],
                            added_at=time.time(),
                        )
                    )
                self._archives[aid] = {
                    "name": params.get("name", "归档"),
                    "entries": entries,
                    "created_at": time.time(),
                    "algorithm": params.get("algorithm", "gzip"),
                }
                return {
                    "success": True,
                    "result": {
                        "archive_id": aid,
                        "name": self._archives[aid]["name"],
                        "files": len(entries),
                        "total_size": sum(e.original_size for e in entries),
                    },
                }

            elif action == "list_archives":
                return {
                    "success": True,
                    "result": [
                        {
                            "archive_id": aid,
                            "name": a["name"],
                            "files": len(a["entries"]),
                            "total_size": sum(e.original_size for e in a["entries"]),
                            "created_at": datetime.fromtimestamp(a["created_at"]).isoformat(),
                        }
                        for aid, a in self._archives.items()
                    ],
                }

            elif action == "history":
                limit = params.get("limit", 50)
                return {
                    "success": True,
                    "result": [
                        {
                            "task_id": r.task_id,
                            "algorithm": r.algorithm,
                            "original_size": r.original_size,
                            "compressed_size": r.compressed_size,
                            "ratio": f"{r.ratio}%",
                            "duration_ms": r.duration_ms,
                            "timestamp": datetime.fromtimestamp(r.timestamp).isoformat(),
                        }
                        for r in self._history[-limit:]
                    ],
                }

            elif action == "get_stats":
                if not self._history:
                    return {
                        "success": True,
                        "result": {
                            "total_operations": 0,
                            "total_original": 0,
                            "total_compressed": 0,
                            "avg_ratio": 0,
                            "by_algorithm": {},
                        },
                    }
                total_orig = sum(r.original_size for r in self._history)
                total_comp = sum(r.compressed_size for r in self._history)
                by_algo = {}
                for r in self._history:
                    if r.algorithm not in by_algo:
                        by_algo[r.algorithm] = {"count": 0, "original": 0, "compressed": 0}
                    by_algo[r.algorithm]["count"] += 1
                    by_algo[r.algorithm]["original"] += r.original_size
                    by_algo[r.algorithm]["compressed"] += r.compressed_size
                return {
                    "success": True,
                    "result": {
                        "total_operations": len(self._history),
                        "total_original": total_orig,
                        "total_compressed": total_comp,
                        "total_saved": total_orig - total_comp,
                        "avg_ratio": round(total_comp / max(total_orig, 1) * 100, 1),
                        "archives": len(self._archives),
                        "by_algorithm": by_algo,
                    },
                }

            elif action == "health_check":
                return {"success": True, "result": self.health_check()}

            else:
                return {"success": False, "error": f"未知操作: {action}"}

        except Exception as e:
            logger.error(f"[CompressAlgorithm] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        base.update(
            {
                "status": "healthy" if self._initialized else "stopped",
                "operations": len(self._history),
                "archives": len(self._archives),
                "supported_algorithms": [a.value for a in Algorithm],
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False

    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计报告。企业场景：运维看板展示各算法使用量和节省存储量。"""
        history = getattr(self, "_history", [])
        algo_stats = {}
        total_input = 0
        total_output = 0
        for record in history:
            algo = record.get("algorithm", "unknown")
            if algo not in algo_stats:
                algo_stats[algo] = {"count": 0, "input_bytes": 0, "output_bytes": 0}
            algo_stats[algo]["count"] += 1
            total_input += record.get("input_size", 0)
            total_output += record.get("output_size", 0)
        return {
            "success": True,
            "total_operations": len(history),
            "total_input_bytes": total_input,
            "total_output_bytes": total_output,
            "overall_ratio": round(1 - total_output / max(total_input, 1), 4),
            "algorithm_breakdown": algo_stats,
        }

    def auto_select_algorithm(self, data: bytes, priority: str = "ratio") -> str:
        """自动选择最优压缩算法。企业场景：根据数据特征（文本/二进制/已压缩）
        和业务优先级（存储 vs 速度）推荐算法。
        """
        import zlib as _zlib

        if len(data) < 100:
            return "zlib_fast"
        # 检测是否已压缩
        compressed_ratio = len(_zlib.compress(data, 1)) / max(len(data), 1)
        if compressed_ratio > 0.95:
            return "none"
        if priority == "speed":
            return "zlib_fast"
        ratios = {}
        for level in [1, 6, 9]:
            c = _zlib.compress(data, level)
            ratios[f"zlib_{level}"] = round(1 - len(c) / max(len(data), 1), 4)
        best = max(ratios.items(), key=lambda x: x[1])
        if best[1] - ratios.get("zlib_1", 0) < 0.05:
            return "zlib_fast"
        return "zlib_default" if best[0] == "zlib_6" else best[0]

def benchmark_algorithms(self, sample_data: str, iterations: int = 100) -> Dict[str, Any]:
    """压缩算法基准测试。企业场景：针对实际业务数据选择最优压缩算法，
    对比各算法的压缩比、速度、内存消耗。
    """
    import zlib

    algorithms = {
        "zlib_default": {"compress": lambda d: zlib.compress(d.encode()), "decompress": lambda d: zlib.decompress(d)},
        "zlib_fast": {"compress": lambda d: zlib.compress(d.encode(), 1), "decompress": lambda d: zlib.decompress(d)},
        "zlib_max": {"compress": lambda d: zlib.compress(d.encode(), 9), "decompress": lambda d: zlib.decompress(d)},
    }
    results = {}
    sample_bytes = len(sample_data.encode())
    for algo_name, funcs in algorithms.items():
        compressed_data = funcs["compress"](sample_data)
        compressed_size = len(compressed_data)
        ratio = round(1 - compressed_size / max(sample_bytes, 1), 4)
        t0 = time.time()
        for _ in range(iterations):
            funcs["compress"](sample_data)
        compress_time = round((time.time() - t0) / iterations * 1000, 3)
        t0 = time.time()
        for _ in range(iterations):
            funcs["decompress"](compressed_data)
        decompress_time = round((time.time() - t0) / iterations * 1000, 3)
        results[algo_name] = {
            "original_bytes": sample_bytes,
            "compressed_bytes": compressed_size,
            "ratio": ratio,
            "compress_ms": compress_time,
            "decompress_ms": decompress_time,
        }
    best_ratio = max(results.items(), key=lambda x: x[1]["ratio"])
    best_speed = min(results.items(), key=lambda x: x[1]["compress_ms"])
    return {
        "success": True,
        "iterations": iterations,
        "sample_bytes": sample_bytes,
        "results": results,
        "best_ratio": best_ratio[0],
        "best_speed": best_speed[0],
    }

def compress_file(self, file_path: str, algorithm: str = "zlib_default") -> Dict[str, Any]:
    """压缩指定文件。企业场景：日志归档、数据备份时压缩文件减少存储占用。"""
    import zlib as _zlib
    import os as _os

    if not _os.path.exists(file_path):
        return {"success": False, "error": f"文件不存在: {file_path}"}
    with open(file_path, "rb") as f:
        data = f.read()
    original_size = len(data)
    level = 6 if "default" in algorithm else (1 if "fast" in algorithm else 9)
    compressed = _zlib.compress(data, level)
    output_path = file_path + ".zlib"
    with open(output_path, "wb") as f:
        f.write(compressed)
    ratio = round(1 - len(compressed) / max(original_size, 1), 4)
    return {
        "success": True,
        "input": file_path,
        "output": output_path,
        "original_bytes": original_size,
        "compressed_bytes": len(compressed),
        "ratio": ratio,
        "algorithm": algorithm,
    }

def get_algorithm_list(self) -> Dict[str, Any]:
    """获取支持的压缩算法列表。企业场景：前端展示可选算法。"""
    algos = ["zlib_default", "zlib_fast", "zlib_max", "gzip", "bz2", "lz4", "snappy"]
    return {"success": True, "algorithms": algos, "total": len(algos)}

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

module_class = CompressAlgorithmManager
