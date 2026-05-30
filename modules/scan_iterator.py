# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 文件扫描迭代器（A级）"""
# Grade: A
__module_meta__ = {"id":"scan-iterator","name":"ScanIterator","version":"V0.1","group":"ops","grade":"B",
    "tags":["ops","scan","file","filesystem"],"description":"基于 os.walk 的真实文件扫描"}
import time, uuid, logging, os, fnmatch, hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin, Result)
logger = logging.getLogger("evo.scan-iterator")

class ScanIterator(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    MODULE_ID = "scan-iterator"
    MODULE_NAME = "扫描迭代器"
    VERSION = "v1.0"
    MODULE_LEVEL = "A"

    def __init__(self, config=None):
        super().__init__(config)
        self._scans: Dict[str, dict] = {}
        self._max_file_size = int(config.get("max_file_size", 50_000_000)) if config else 50_000_000
        self._max_results = int(config.get("max_results", 10_000)) if config else 10_000

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value, healthy=True,
            module_id=self.MODULE_ID,
            checks={"cached_scans": len(self._scans)}
        )

    async def execute(self, action=None, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _walk_path(self, path: str, pattern: str, max_depth: int) -> list:
        """真实目录遍历，支持 glob 匹配和深度限制"""
        root = Path(path).resolve()
        if not root.exists():
            return []
        results = []
        try:
            for i, (dirpath, dirnames, filenames) in enumerate(os.walk(root)):
                rel_depth = len(Path(dirpath).relative_to(root).parts)
                if max_depth > 0 and rel_depth >= max_depth:
                    dirnames.clear()
                for fname in filenames:
                    if pattern != "*" and not fnmatch.fnmatch(fname, pattern):
                        continue
                    fpath = Path(dirpath) / fname
                    try:
                        st = fpath.stat()
                        if st.st_size > self._max_file_size:
                            continue
                        results.append({
                            "name": fname,
                            "path": str(fpath),
                            "rel_path": str(fpath.relative_to(root)),
                            "size": st.st_size,
                            "modified": st.st_mtime,
                            "created": st.st_ctime,
                            "is_dir": False,
                        })
                        if len(results) >= self._max_results:
                            return results
                    except OSError:
                        continue
        except PermissionError:
            pass
        return results

    def _dispatch(self, p: dict) -> dict:
        a = p.get("action", "status")

        if a == "status":
            return {"success": True, "cached_scans": len(self._scans)}

        if a == "scan":
            path = p.get("path", ".")
            pattern = p.get("pattern", "*")
            max_depth = int(p.get("max_depth", 0))
            recursive = str(p.get("recursive", "true")).lower() == "true"
            if not recursive:
                max_depth = 1
            sid = uuid.uuid4().hex[:8]
            t0 = time.time()
            files = self._walk_path(path, pattern, max_depth)
            elapsed = round(time.time() - t0, 3)
            self._scans[sid] = {
                "path": path, "pattern": pattern, "count": len(files),
                "elapsed": elapsed, "timestamp": time.time()
            }
            return {
                "success": True, "scan_id": sid,
                "files": files, "total": len(files),
                "elapsed_seconds": elapsed
            }

        if a == "scan_by_ext":
            path = p.get("path", ".")
            exts = p.get("extensions", ".py,.md,.json")
            ext_list = [e.strip().lower() for e in exts.split(",")]
            max_depth = int(p.get("max_depth", 0))
            sid = uuid.uuid4().hex[:8]
            t0 = time.time()
            files = [f for f in self._walk_path(path, "*", max_depth)
                     if any(Path(f["name"]).suffix.lower() == e for e in ext_list)]
            elapsed = round(time.time() - t0, 3)
            self._scans[sid] = {
                "path": path, "extensions": ext_list, "count": len(files),
                "elapsed": elapsed, "timestamp": time.time()
            }
            return {
                "success": True, "scan_id": sid,
                "files": files, "total": len(files),
                "elapsed_seconds": elapsed
            }

        if a == "recent":
            path = p.get("path", ".")
            minutes = int(p.get("minutes", 60))
            max_depth = int(p.get("max_depth", 0))
            cutoff = time.time() - minutes * 60
            sid = uuid.uuid4().hex[:8]
            files = [f for f in self._walk_path(path, "*", max_depth)
                     if f["modified"] >= cutoff]
            files.sort(key=lambda x: x["modified"], reverse=True)
            files = files[:self._max_results]
            self._scans[sid] = {
                "path": path, "minutes": minutes, "count": len(files),
                "timestamp": time.time()
            }
            return {
                "success": True, "scan_id": sid,
                "files": files, "total": len(files)
            }

        if a == "duplicates":
            path = p.get("path", ".")
            max_depth = int(p.get("max_depth", 0))
            all_files = self._walk_path(path, "*", max_depth)
            by_size_name: Dict[str, list] = {}
            for f in all_files:
                key = f"{f['size']}:{f['name']}"
                by_size_name.setdefault(key, []).append(f)
            dupes = {k: v for k, v in by_size_name.items() if len(v) > 1}
            return {
                "success": True,
                "duplicate_count": len(dupes),
                "duplicates": [
                    {"name": v[0]["name"], "size": v[0]["size"],
                     "paths": [d["path"] for d in v]}
                    for v in dupes.values()
                ]
            }

        if a == "stats":
            path = p.get("path", ".")
            max_depth = int(p.get("max_depth", 1))
            files = self._walk_path(path, "*", max_depth)
            total_size = sum(f["size"] for f in files)
            by_ext: Dict[str, int] = {}
            for f in files:
                ext = Path(f["name"]).suffix.lower() or "(none)"
                by_ext[ext] = by_ext.get(ext, 0) + 1
            top_ext = sorted(by_ext.items(), key=lambda x: -x[1])[:10]
            return {
                "success": True,
                "total_files": len(files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1_048_576, 2),
                "avg_size_bytes": round(total_size / len(files), 1) if files else 0,
                "top_extensions": [{"ext": k, "count": v} for k, v in top_ext],
                "scan_depth": max_depth
            }

        if a == "get":
            sid = p.get("scan_id", "")
            return self._scans.get(sid, {"error": f"scan {sid} not found"})

        if a == "list_scans":
            return {
                "success": True,
                "scans": {k: {"count": v.get("count", 0), "path": v.get("path", ""),
                              "timestamp": v.get("timestamp", 0)}
                          for k, v in self._scans.items()}
            }

        return {"error": f"unknown action: {a}"}

    async def shutdown(self) -> None:
        self._scans.clear()
        self.status = ModuleStatus.STOPPED

module_class = ScanIterator
