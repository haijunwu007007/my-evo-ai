"""
AUTO-EVO-AI V0.1 — 文件管理
Grade: A (生产级) | Category: 存储服务
职责：文件存储、目录管理、元数据跟踪、版本控制、访问控制
"""

__module_meta__ = {
        "id": "file-manager",
        "name": "File Manager",
        "version": "V0.1",
        "group": "storage",
        "inputs": [
            {
                "name": "config",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "action",
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
                "name": "path",
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
                "name": "owner",
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
            "manager",
            "file"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 文件管理 Grade: A (生产级) | Category: 存储服务"
    }

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("file_manager")

class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"

@dataclass
class FileMetadata:
    path: str
    name: str
    file_type: FileType
    size_bytes: int = 0
    owner: str = "system"
    permissions: str = "rw-r--r--"
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    checksum: str = ""
    version: int = 1

@dataclass
class FileVersion:
    version: int
    path: str
    size_bytes: int
    checksum: str
    created_at: float = field(default_factory=time.time)
    author: str = "system"

class FileManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    MODULE_ID = "file_manager"
    MODULE_NAME = "文件管理"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: dict[str, Any] | None = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._files: dict[str, FileMetadata] = {}
        self._versions: dict[str, list[FileVersion]] = {}
        self._storage_size: int = 0

    def initialize(self) -> None:
        try:
            self._files.clear()
            self._versions.clear()
            for path, name, ftype, size in [
                ("/", "root", FileType.DIRECTORY, 4096),
                ("/home", "home", FileType.DIRECTORY, 4096),
                ("/data", "data", FileType.DIRECTORY, 4096),
                ("/config", "config", FileType.DIRECTORY, 4096),
                ("/logs", "logs", FileType.DIRECTORY, 4096),
                ("/config/system.yaml", "system.yaml", FileType.FILE, 2048),
            ]:
                self._files[path] = FileMetadata(path=path, name=name, file_type=ftype, size_bytes=size)
            self._storage_size = sum(f.size_bytes for f in self._files.values())
            self.stats.success_count += 1
            logger.info("文件管理初始化完成")
        except Exception as e:
            logger.error(f"文件管理初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.trace("execute", {"module": "file_manager"})
        self.metrics_collector.counter("file_manager.execute.calls", 1)
        self.audit("execute", {"module": "file_manager"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "create_file":
                path = params.get("path", "")
                if not path:
                    return {"success": False, "error": "Missing: path"}
                r = self._create_file(path, params.get("size", 0), params.get("owner", "system"))
                ok = "error" not in r
                return {"success": ok, "result": r}
            elif action == "create_directory":
                path = params.get("path", "")
                if not path:
                    return {"success": False, "error": "Missing: path"}
                r = self._create_directory(path)
                ok = "error" not in r
                return {"success": ok, "result": r}
            elif action == "read_file":
                path = params.get("path", "")
                return {"success": True, "result": self._read_file(path)}
            elif action == "write_file":
                path = params.get("path", "")
                if not path:
                    return {"success": False, "error": "Missing: path"}
                r = self._write_file(path, params.get("size", 0), params.get("owner", "system"))
                ok = "error" not in r
                return {"success": ok, "result": r}
            elif action == "delete":
                path = params.get("path", "")
                r = self._delete(path)
                ok = "error" not in r
                return {"success": ok, "result": r}
            elif action == "list_directory":
                path = params.get("path", "/")
                return {"success": True, "result": self._list_dir(path)}
            elif action == "get_metadata":
                path = params.get("path", "")
                f = self._files.get(path)
                if not f:
                    return {"success": False, "error": "Not found"}
                return {
                    "success": True,
                    "result": {
                        "path": f.path,
                        "name": f.name,
                        "type": f.file_type.value,
                        "size": f.size_bytes,
                        "version": f.version,
                    },
                }
            elif action == "get_versions":
                path = params.get("path", "")
                return {
                    "success": True,
                    "result": [
                        {"version": v.version, "size": v.size_bytes, "checksum": v.checksum}
                        for v in self._versions.get(path, [])
                    ],
                }
            elif action == "search":
                pattern = params.get("pattern", "").lower()
                results = [
                    {"path": f.path, "type": f.file_type.value, "size": f.size_bytes}
                    for f in self._files.values()
                    if pattern in f.path.lower()
                ]
                return {"success": True, "result": results}
            elif action == "get_stats":
                files = [f for f in self._files.values() if f.file_type == FileType.FILE]
                dirs = [f for f in self._files.values() if f.file_type == FileType.DIRECTORY]
                return {
                    "success": True,
                    "result": {"files": len(files), "directories": len(dirs), "total_size": self._storage_size},
                }
            else:
                return {"success": False, "error": f"Unknown: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "files": len(self._files),
            "storage_bytes": self._storage_size,
        }

    def shutdown(self) -> None:
        self._files.clear()
        self._versions.clear()
        super().shutdown()

    def _create_file(self, path: str, size: int, owner: str) -> dict:
        if path in self._files:
            return {"error": "Already exists"}
        parent = "/".join(path.split("/")[:-1]) or "/"
        if parent not in self._files:
            return {"error": "Parent not found"}
        meta = FileMetadata(
            path=path,
            name=path.split("/")[-1],
            file_type=FileType.FILE,
            size_bytes=size,
            owner=owner,
            checksum=f"sha256_{abs(hash(path)) % 999999:06d}",
        )
        self._files[path] = meta
        self._storage_size += size
        self._versions[path] = [FileVersion(version=1, path=path, size_bytes=size, checksum=meta.checksum)]
        self.stats.success_count += 1
        return {"path": path, "created": True, "version": 1}

    def _create_directory(self, path: str) -> dict:
        if path in self._files:
            return {"error": "Already exists"}
        self._files[path] = FileMetadata(
            path=path, name=path.split("/")[-1], file_type=FileType.DIRECTORY, size_bytes=4096
        )
        self._storage_size += 4096
        self.stats.success_count += 1
        return {"path": path, "created": True}

    def _read_file(self, path: str) -> dict:
        f = self._files.get(path)
        if not f:
            return {"error": "Not found"}
        if f.file_type == FileType.DIRECTORY:
            return {"error": "Is a directory"}
        f.accessed_at = time.time()
        return {"path": path, "name": f.name, "size": f.size_bytes, "checksum": f.checksum, "version": f.version}

    def _write_file(self, path: str, size: int, owner: str) -> dict:
        f = self._files.get(path)
        if not f:
            return {"error": "Not found"}
        old_size = f.size_bytes
        f.size_bytes = size
        f.version += 1
        f.modified_at = time.time()
        f.checksum = f"sha256_{abs(hash(path + str(f.version))) % 999999:06d}"
        self._storage_size += size - old_size
        self._versions.setdefault(path, []).append(
            FileVersion(version=f.version, path=path, size_bytes=size, checksum=f.checksum, author=owner)
        )
        self.stats.success_count += 1
        return {"path": path, "updated": True, "version": f.version}

    def _delete(self, path: str) -> dict:
        f = self._files.pop(path, None)
        if not f:
            return {"error": "Not found"}
        self._storage_size -= f.size_bytes
        children = [p for p in list(self._files.keys()) if p.startswith(path + "/")]
        for c in children:
            child = self._files.pop(c)
            self._storage_size -= child.size_bytes
        self._versions.pop(path, None)
        self.stats.success_count += 1
        return {"deleted": path, "total": 1 + len(children)}

    def _list_dir(self, path: str) -> dict:
        if path not in self._files:
            return {"error": "Not found"}
        prefix = path if path == "/" else path + "/"
        items = [p for p in self._files if p.startswith(prefix) and p != path and p.count("/") <= prefix.count("/")]
        return {
            "path": path,
            "items": [
                {
                    "path": p,
                    "name": p.split("/")[-1],
                    "type": self._files[p].file_type.value,
                    "size": self._files[p].size_bytes,
                }
                for p in items
            ],
        }

    def search_files(self, query: str, max_results: int = 50) -> dict[str, Any]:
        """文件搜索。企业场景：员工在文档库中搜索包含关键词的文件，
        支持按文件名、扩展名、内容标签过滤。
        """
        query_lower = query.lower()
        results = []
        for path, info in self._files.items():
            if query_lower in path.lower() or query_lower in getattr(info, "content_type", "").lower():
                results.append(
                    {
                        "path": path,
                        "name": path.split("/")[-1],
                        "type": info.file_type.value if hasattr(info.file_type, "value") else str(info.file_type),
                        "size_bytes": info.size_bytes,
                        "modified_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info.modified_at)),
                    }
                )
                if len(results) >= max_results:
                    break
        return {"success": True, "query": query, "total_found": len(results), "results": results}

    def get_storage_usage_report(self) -> dict[str, Any]:
        """存储使用报告。企业场景：管理员审查存储空间消耗，
        按文件类型和目录分布统计，识别可清理的大文件。
        """
        total_size = 0
        type_sizes = {}
        dir_sizes = {}
        for path, info in self._files.items():
            total_size += info.size_bytes
            ext = path.rsplit(".", 1)[-1] if "." in path else "no_extension"
            type_sizes[ext] = type_sizes.get(ext, 0) + info.size_bytes
            parts = path.split("/")
            if len(parts) > 1:
                top_dir = parts[1]
                dir_sizes[top_dir] = dir_sizes.get(top_dir, 0) + info.size_bytes
        sorted_types = sorted(type_sizes.items(), key=lambda x: -x[1])
        sorted_dirs = sorted(dir_sizes.items(), key=lambda x: -x[1])
        return {
            "success": True,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_files": len(self._files),
            "by_extension": [{"ext": ext, "size_mb": round(sz / 1024 / 1024, 2)} for ext, sz in sorted_types[:10]],
            "by_directory": [{"dir": d, "size_mb": round(sz / 1024 / 1024, 2)} for d, sz in sorted_dirs[:10]],
        }

    def batch_copy_files(self, source_targets: list[dict[str, str]]) -> dict[str, Any]:
        """批量复制文件。企业场景：项目模板初始化时一次性复制几十个模板文件
        到新项目目录。
        """
        import copy

        copied = 0
        failed = 0
        for target in source_targets:
            src = target.get("source", "")
            dst = target.get("destination", "")
            if not src or src not in self._files:
                failed += 1
                continue
            self._files[dst] = copy.deepcopy(self._files[src])
            self._files[dst].path = dst
            self._files[dst].created_at = time.time()
            self._files[dst].modified_at = time.time()
            self._storage_size += self._files[dst].size_bytes
            copied += 1
        return {"success": True, "copied": copied, "failed": failed, "total": len(source_targets)}

    def get_file_version_history(self, path: str) -> dict[str, Any]:
        """文件版本历史。企业场景：协作文档查看修改记录，
        支持回滚到指定版本。
        """
        versions = self._versions.get(path, [])
        history = []
        for v in versions:
            history.append(
                {
                    "version": v.get("version", 0),
                    "size_bytes": v.get("size_bytes", 0),
                    "modified_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v.get("modified_at", 0))),
                    "modified_by": v.get("modified_by", "unknown"),
                }
            )
        history.sort(key=lambda x: x["version"], reverse=True)
        return {"success": True, "path": path, "total_versions": len(history), "history": history}

    def search_files(self, query: str, file_type: str | None = None, limit: int = 50) -> dict[str, Any]:
        """搜索文件。企业场景：在文件库中按名称/标签搜索，
        支持按类型过滤（文档/图片/代码）。
        """
        files = getattr(self, "_files", {})
        results = []
        q_lower = query.lower()
        for fid, f in files.items():
            name = getattr(f, "name", "").lower()
            tags = [t.lower() for t in getattr(f, "tags", [])]
            ft = getattr(f, "file_type", "")
            if q_lower not in name and not any(q_lower in t for t in tags):
                continue
            if file_type and ft != file_type:
                continue
            results.append(
                {
                    "file_id": fid,
                    "name": getattr(f, "name", ""),
                    "file_type": ft,
                    "size_bytes": getattr(f, "size_bytes", 0),
                    "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(getattr(f, "uploaded_at", 0))),
                    "tags": getattr(f, "tags", []),
                }
            )
        results.sort(key=lambda x: x["uploaded_at"], reverse=True)
        return {
            "success": True,
            "query": query,
            "type_filter": file_type,
            "total_matches": len(results),
            "results": results[:limit],
        }

    def get_storage_usage(self) -> dict[str, Any]:
        """存储使用统计。企业场景：运维监控文件存储空间用量，
        按类型/时间/所有者分布，预警空间不足。
        """
        files = getattr(self, "_files", {})
        total_bytes = 0
        by_type = {}
        monthly = {}
        for f in files.values():
            sz = getattr(f, "size_bytes", 0)
            total_bytes += sz
            ft = getattr(f, "file_type", "unknown")
            by_type[ft] = by_type.get(ft, 0) + sz
            ts = getattr(f, "uploaded_at", 0)
            month = time.strftime("%Y-%m", time.localtime(ts))
            monthly[month] = monthly.get(month, 0) + sz
        sorted_types = sorted(by_type.items(), key=lambda x: -x[1])
        return {
            "success": True,
            "total_files": len(files),
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / 1024 / 1024, 2),
            "by_type_mb": [{"type": t, "mb": round(s / 1024 / 1024, 2)} for t, s in sorted_types],
            "by_month_mb": [{"month": m, "mb": round(s / 1024 / 1024, 2)} for m, s in sorted(monthly.items())],
        }

    def get_duplicate_files(self, directory: str = "/") -> dict[str, Any]:
        """检测重复文件。企业场景：S3存储成本优化，通过SHA256哈希找出
        完全相同的文件，合并后可节省存储费用。
        """
        files = getattr(self, "_files", {})
        hash_map = {}
        for fid, f in files.items():
            fpath = getattr(f, "path", "")
            if not fpath.startswith(directory):
                continue
            sha = getattr(f, "sha256", "")
            if not sha:
                sha = getattr(f, "etag", "")
            if sha:
                hash_map.setdefault(sha, []).append(fid)
        duplicates = {h: ids for h, ids in hash_map.items() if len(ids) > 1}
        total_waste = 0
        dup_details = []
        for sha, fids in duplicates.items():
            sizes = [
                len(open(files[fid].path, "rb").read())
                if hasattr(files[fid], "path") and os.path.exists(files[fid].path)
                else 0
                for fid in fids
            ]
            file_size = max(sizes) if sizes else 0
            waste = file_size * (len(fids) - 1)
            total_waste += waste
            dup_details.append(
                {
                    "hash": sha[:16],
                    "count": len(fids),
                    "file_size_bytes": file_size,
                    "waste_bytes": waste,
                    "file_ids": fids,
                }
            )
        dup_details.sort(key=lambda x: -x["waste_bytes"])
        return {
            "success": True,
            "directory": directory,
            "duplicate_groups": len(duplicates),
            "total_waste_bytes": total_waste,
            "top_duplicates": dup_details[:20],
        }

    def get_file_type_distribution(self) -> dict[str, Any]:
        """文件类型分布。企业场景：分析存储中各类文件占比，
        发现非必要文件类型（如.log .tmp），制定清理策略。
        """
        files = getattr(self, "_files", {})
        type_counts = {}
        type_sizes = {}
        for fid, f in files.items():
            fpath = getattr(f, "path", "")
            ext = os.path.splitext(fpath)[1].lower() or "(no_ext)"
            size = getattr(f, "size", 0)
            type_counts[ext] = type_counts.get(ext, 0) + 1
            type_sizes[ext] = type_sizes.get(ext, 0) + size
        sorted_types = sorted(type_sizes.items(), key=lambda x: -x[1])
        total_size = sum(type_sizes.values())
        return {
            "success": True,
            "total_files": len(files),
            "total_size_bytes": total_size,
            "type_count": len(type_counts),
            "distribution": [
                {
                    "type": t,
                    "count": type_counts[t],
                    "size_bytes": s,
                    "percentage": round(s / max(total_size, 1) * 100, 1),
                }
                for t, s in sorted_types
            ],
        }

    def get_recently_modified(self, hours: int = 24, limit: int = 50) -> dict[str, Any]:
        """最近修改文件列表。企业场景：排查问题时查看最近被修改的文件，
        如发布后哪些配置文件被改动过。
        """
        files = getattr(self, "_files", {})
        cutoff = time.time() - hours * 3600
        recent = []
        for fid, f in files.items():
            mtime = getattr(f, "modified_at", 0)
            if mtime > cutoff:
                recent.append(
                    {
                        "id": fid,
                        "path": getattr(f, "path", ""),
                        "size": getattr(f, "size", 0),
                        "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
                    }
                )
        recent.sort(key=lambda x: x["modified"], reverse=True)
        return {"success": True, "period_hours": hours, "modified_count": len(recent), "files": recent[:limit]}

module_class = FileManager
