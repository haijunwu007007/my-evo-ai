# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 数据目录（A级）"""
# Grade: A
__module_meta__ = {"id":"data-catalog","name":"Data Catalog","version":"V0.1","group":"data","grade":"B",
    "tags":["data","catalog","metadata"],"description":"数据目录 - 真实文件扫描/os.walk/fnmatch/元数据索引"}

import os, fnmatch, logging, hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)

logger = logging.getLogger("evo.data-catalog")

# ── 常见文件类型映射 ─────────────────────────────────────────────────
_FILE_TYPE_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".jsx": "react",
    ".tsx": "react-ts", ".html": "html", ".css": "css", ".scss": "scss",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".md": "markdown", ".rst": "rst", ".txt": "text",
    ".csv": "csv", ".xlsx": "excel", ".xls": "excel", ".xml": "xml",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
    ".svg": "image", ".ico": "image", ".webp": "image",
    ".pdf": "pdf", ".doc": "word", ".docx": "word", ".ppt": "powerpoint",
    ".pptx": "powerpoint",
    ".zip": "archive", ".tar": "archive", ".gz": "archive", ".rar": "archive",
    ".7z": "archive",
    ".sh": "shell", ".bat": "batch", ".ps1": "powershell",
    ".sql": "sql", ".log": "log", ".env": "env",
    ".cfg": "config", ".ini": "config", ".conf": "config",
    ".yml": "config", ".yaml": "config",
}


class DataCatalog(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    MODULE_ID = "data-catalog"
    MODULE_NAME = "数据目录"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config=None):
        super().__init__(config)
        self._catalog: Dict[str, Dict[str, Any]] = {}
        self._last_scan: Optional[str] = None

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING
        logger.info("DataCatalog initialized")

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value, healthy=True, module_id=self.MODULE_ID,
            checks={"files_indexed": len(self._catalog), "last_scan": self._last_scan or "never"}
        )

    async def execute(self, action, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _dispatch(self, p):
        a = p.get("action", "status")
        if a == "status":
            return {"success": True, "files_indexed": len(self._catalog),
                    "last_scan": self._last_scan or "never"}
        if a == "scan_directory":
            return self._action_scan_directory(p)
        if a == "get_summary":
            return self._action_get_summary(p)
        if a == "search_files":
            return self._action_search_files(p)
        if a == "list":
            return {"success": True, "files": list(self._catalog.keys()),
                    "count": len(self._catalog)}
        if a == "get_file_info":
            return self._action_get_file_info(p)
        if a == "list_by_type":
            return self._action_list_by_type(p)
        return {"error": f"unknown:{a}"}

    # ── public API: scan_directory ──────────────────────────────────────
    def scan_directory(self, path: str) -> Dict[str, Any]:
        """扫描目录，建立文件元数据索引"""
        if not os.path.isdir(path):
            logger.error("scan_directory: not a directory: %s", path)
            return {"success": False, "error": f"directory not found: {path}"}

        abs_path = os.path.abspath(path)
        indexed = 0
        errors = 0

        for root, dirs, files in os.walk(abs_path):
            # 跳过常见无关目录
            skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv",
                         ".idea", ".vscode", ".workbuddy", "_archive", ".mypy_cache",
                         ".pytest_cache", "dist", "build", ".tox", ".egg-info"}
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    meta = self._index_file(fpath)
                    if meta:
                        self._catalog[fpath] = meta
                        indexed += 1
                except Exception as e:
                    logger.warning("scan_directory: error indexing %s: %s", fpath, e)
                    errors += 1

        self._last_scan = datetime.now().isoformat()
        logger.info("scan_directory: indexed %d files from %s (errors=%d)",
                    indexed, abs_path, errors)
        return {
            "success": True,
            "path": abs_path,
            "files_indexed": indexed,
            "errors": errors,
            "total_in_catalog": len(self._catalog)
        }

    def _index_file(self, fpath: str) -> Optional[Dict[str, Any]]:
        stat = os.stat(fpath)
        ext = os.path.splitext(fpath)[1].lower()
        ftype = _FILE_TYPE_MAP.get(ext, "other")
        size = stat.st_size
        # 大文件不做 hash（节省时间）
        if size < 10 * 1024 * 1024:  # < 10MB
            try:
                with open(fpath, "rb") as f:
                    file_hash = hashlib.md5(f.read(65536)).hexdigest()
            except Exception:
                file_hash = ""
        else:
            file_hash = ""

        return {
            "name": os.path.basename(fpath),
            "path": fpath,
            "ext": ext,
            "type": ftype,
            "size_bytes": size,
            "size_kb": round(size / 1024, 1),
            "size_mb": round(size / (1024 * 1024), 2) if size > 1024 * 1024 else 0,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "md5_prefix": file_hash[:16] if file_hash else "",
            "dir": os.path.dirname(fpath)
        }

    # ── public API: get_summary ─────────────────────────────────────────
    def get_summary(self, path: Optional[str] = None) -> Dict[str, Any]:
        """返回已索引文件的摘要统计"""
        if path:
            # 只统计某个目录下的文件
            files = [v for v in self._catalog.values()
                     if v["path"].startswith(os.path.abspath(path))]
        else:
            files = list(self._catalog.values())

        if not files:
            return {"success": True, "total_files": 0, "message": "no files indexed"}

        # 按类型分组
        by_type: Dict[str, int] = {}
        total_size = 0
        largest = None
        latest = None

        for f in files:
            by_type[f["type"]] = by_type.get(f["type"], 0) + 1
            total_size += f["size_bytes"]
            if largest is None or f["size_bytes"] > largest["size_bytes"]:
                largest = f
            if latest is None or f["modified"] > latest["modified"]:
                latest = f

        return {
            "success": True,
            "total_files": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
            "largest_file": {"name": largest["name"], "size_mb": largest["size_mb"]} if largest else None,
            "latest_modified": {"name": latest["name"], "modified": latest["modified"]} if latest else None,
            "path_filter": path or "(all)"
        }

    # ── public API: search_files ────────────────────────────────────────
    def search_files(self, pattern: str,
                     directory: Optional[str] = None) -> List[Dict[str, Any]]:
        """使用 fnmatch 搜索文件名，支持通配符"""
        results = []
        for fpath, meta in self._catalog.items():
            if fnmatch.fnmatch(os.path.basename(fpath), pattern):
                if directory and not fpath.startswith(os.path.abspath(directory)):
                    continue
                results.append(meta)

        # 按修改时间倒序
        results.sort(key=lambda x: x["modified"], reverse=True)
        logger.info("search_files: pattern='%s' found %d results", pattern, len(results))
        return results

    # ── action wrappers ─────────────────────────────────────────────────
    def _action_scan_directory(self, p):
        path = p.get("path", ".")
        result = self.scan_directory(path)
        return result

    def _action_get_summary(self, p):
        path = p.get("path")
        return self.get_summary(path)

    def _action_search_files(self, p):
        pattern = p.get("pattern", "*")
        directory = p.get("directory")
        results = self.search_files(pattern, directory)
        return {"success": True, "pattern": pattern, "results": results,
                "count": len(results)}

    def _action_get_file_info(self, p):
        fpath = p.get("path", "")
        if fpath in self._catalog:
            return {"success": True, "info": self._catalog[fpath]}
        # 尝试实时索引
        if os.path.isfile(fpath):
            meta = self._index_file(fpath)
            if meta:
                self._catalog[fpath] = meta
                return {"success": True, "info": meta}
        return {"success": False, "error": "file not indexed or not found"}

    def _action_list_by_type(self, p):
        ftype = p.get("type", "")
        files = [v for v in self._catalog.values() if v["type"] == ftype]
        return {"success": True, "type": ftype, "files": files, "count": len(files)}

    async def shutdown(self) -> None:
        self._catalog.clear()
        self.status = ModuleStatus.STOPPED
        logger.info("DataCatalog shut down")


module_class = DataCatalog
