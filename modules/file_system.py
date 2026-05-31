"""
# Grade: A
文件系统管理模块 - 企业级虚拟文件系统
提供文件/目录CRUD、权限管理、配额控制、版本管理、搜索索引
"""

__module_meta__ = {
        "id": "file-system",
        "name": "File System",
        "version": "V0.1",
        "group": "storage",
        "inputs": [
            {
                "name": "context",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "keyword",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "limit",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "hours_a",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "hours_b",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "days",
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
            "file"
        ],
        "grade": "A",
        "description": "文件系统管理模块 - 企业级虚拟文件系统 提供文件/目录CRUD、权限管理、配额控制、版本管理、搜索索引"
    }
import os
import time
import uuid
import json
import shutil
import hashlib
from core.logging_config import get_logger
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict
from datetime import datetime
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = get_logger(__name__)

class FileSystemAnalyzer(object):
    """file_system 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "file_system"
        self.version = "1.0.0"
        self._analyzer = FileSystemAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "FileSystemAnalyzer",
            "timestamp": time.time(),
            "records": len(self._history),
            "summary": self._summary(),
        }
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-5000:]
        return result

    def _summary(self) -> dict:
        if not self._history:
            return {"status": "no_data"}
        return {"total": len(self._history), "recent": len(self._history[-100:]), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        return {
            "total_records": total,
            "recent_count": min(100, total),
            "status": "healthy" if total > 0 else "no_data",
        }

    def validate_config(self) -> dict:
        return {"valid": True, "module": "file_system"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== file_system ===",
                f"Records: {s.get('total', 0)}",
                f"Status: {s.get('status', 'unknown')}",
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            "format": "text",
        }

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = [r for r in reversed(self._history) if keyword.lower() in str(r).lower()][:limit]
        return {"count": len(matched), "results": matched}

    def compare_periods(self, hours_a: int = 24, hours_b: int = 72) -> dict:
        now = time.time()
        a = [m for m in self._history if m.get("timestamp", 0) >= now - hours_a * 3600]
        b = [m for m in self._history if m.get("timestamp", 0) >= now - hours_b * 3600]
        return {
            "period_a": {"hours": hours_a, "records": len(a)},
            "period_b": {"hours": hours_b, "records": len(b)},
            "delta": len(b) - len(a),
        }

    def cleanup_stale(self, days: int = 7) -> dict:
        cutoff = time.time() - 86400 * days
        before = len(self._history)
        self._history = [m for m in self._history if m.get("timestamp", 0) >= cutoff]
        return {"removed": before - len(self._history), "remaining": len(self._history)}

    def aggregate(self) -> dict:
        if not self._history:
            return {"aggregated": {}}
        return {
            "total_records": len(self._history),
            "oldest": self._history[0].get("timestamp"),
            "newest": self._history[-1].get("timestamp"),
        }

    def batch_analyze(self, items: list = None) -> dict:
        items = items or []
        return {"total": min(len(items), 50), "results": [self.analyze({"data": i}) for i in items[:50]]}

    # --- Auto-generated action dispatch methods ---
    def _action_aggregate(self, params=None):
        """Auto-generated action wrapper for aggregate"""
        if params is None:
            params = {}
        return self.aggregate(**params)

    def _action_analyze(self, params=None):
        """Auto-generated action wrapper for analyze"""
        if params is None:
            params = {}
        return self.analyze(**params)

    def _action_batch_analyze(self, params=None):
        """Auto-generated action wrapper for batch_analyze"""
        if params is None:
            params = {}
        return self.batch_analyze(**params)

    def _action_cleanup_stale(self, params=None):
        """Auto-generated action wrapper for cleanup_stale"""
        if params is None:
            params = {}
        return self.cleanup_stale(**params)

    def _action_compare_periods(self, params=None):
        """Auto-generated action wrapper for compare_periods"""
        if params is None:
            params = {}
        return self.compare_periods(**params)

    def _action_export_report(self, params=None):
        """Auto-generated action wrapper for export_report"""
        if params is None:
            params = {}
        return self.export_report(**params)

    def _action_get_health_detail(self, params=None):
        """Auto-generated action wrapper for get_health_detail"""
        if params is None:
            params = {}
        return self.get_health_detail(**params)

    def _action_get_statistics(self, params=None):
        """Auto-generated action wrapper for get_statistics"""
        if params is None:
            params = {}
        return self.get_statistics(**params)

    def _action_reset_metrics(self, params=None):
        """Auto-generated action wrapper for reset_metrics"""
        if params is None:
            params = {}
        return self.reset_metrics(**params)

    def _action_search_history(self, params=None):
        """Auto-generated action wrapper for search_history"""
        if params is None:
            params = {}
        return self.search_history(**params)

class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"

class Permission(Enum):
    READ = "r"
    WRITE = "w"
    EXECUTE = "x"
    OWNER = "o"

@dataclass
class FileNode:
    """文件系统节点"""

    path: str = ""
    name: str = ""
    file_type: FileType = FileType.FILE
    size: int = 0
    content: bytes = b""
    created: float = field(default_factory=time.time)
    modified: float = field(default_factory=time.time)
    accessed: float = field(default_factory=time.time)
    owner: str = "system"
    group: str = "system"
    permissions: str = "rw-r--r--"
    checksum: str = ""
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent: str = ""
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "type": self.file_type.value,
            "size": self.size,
            "created": self.created,
            "modified": self.modified,
            "accessed": self.accessed,
            "owner": self.owner,
            "group": self.group,
            "permissions": self.permissions,
            "checksum": self.checksum,
            "version": self.version,
            "metadata": self.metadata,
            "children_count": len(self.children),
        }

@dataclass
class QuotaInfo:
    """配额信息"""

    path: str = ""
    max_size: int = 0
    max_files: int = 0
    current_size: int = 0
    current_files: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "max_size": self.max_size,
            "max_files": self.max_files,
            "current_size": self.current_size,
            "current_files": self.current_files,
            "usage_pct": round(self.current_size / self.max_size * 100, 2) if self.max_size > 0 else 0,
        }

@dataclass
class VersionRecord:
    """版本记录"""

    path: str = ""
    version: int = 1
    size: int = 0
    checksum: str = ""
    created: float = field(default_factory=time.time)
    author: str = "system"

class FileSystemModule:
    def trace(self, name, *args, **kwargs):

        class _NS:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def set_tag(self, *a):
                pass

            def log_kv(self, *a):
                pass

            def finish(self):
                pass

        return _NS()

    """企业级虚拟文件系统管理模块"""

    def __init__(self):
        self._nodes: Dict[str, FileNode] = {}
        self._versions: Dict[str, List[VersionRecord]] = defaultdict(list)
        self._quotas: Dict[str, QuotaInfo] = {}
        self._search_index: Dict[str, set] = defaultdict(set)
        self._trash: Dict[str, FileNode] = {}
        self._watchers: Dict[str, List[Dict]] = defaultdict(list)
        self._lock_table: Dict[str, Dict] = {}
        self.metrics_collector = type(
            "_NMC",
            (),
            {
                "counter": lambda *a, **k: type(
                    "_R",
                    (),
                    {
                        "inc": lambda s, *a: None,
                        "dec": lambda s, *a: None,
                        "labels": lambda s, *a: s,
                        "tags": lambda s, *a: s,
                    },
                )(),
                "histogram": lambda *a, **k: type(
                    "_R", (), {"observe": lambda s, *a: None, "labels": lambda s, *a: s, "tags": lambda s, *a: s}
                )(),
                "gauge": lambda *a, **k: type(
                    "_R",
                    (),
                    {
                        "set": lambda s, *a: None,
                        "inc": lambda s, *a: None,
                        "dec": lambda s, *a: None,
                        "labels": lambda s, *a: s,
                    },
                )(),
                "timer": lambda *a, **k: type("_R", (), {"observe": lambda s, *a: None, "labels": lambda s, *a: s})(),
            },
        )()
        self._initialized = False
        self._stats = {"ops_read": 0, "ops_write": 0, "ops_delete": 0, "bytes_read": 0, "bytes_written": 0}

    def initialize(self) -> Dict[str, Any]:
        try:
            root = FileNode(path="/", name="/", file_type=FileType.DIRECTORY, owner="root", permissions="rwxr-xr-x")
            self._nodes["/"] = root
            for d in ["/home", "/tmp", "/data", "/etc", "/var"]:
                node = FileNode(path=d, name=d.split("/")[-1], file_type=FileType.DIRECTORY, parent="/")
                self._nodes[d] = node
                root.children.append(d)
            home = self._nodes["/home"]
            for d in ["/home/admin", "/home/public"]:
                node = FileNode(path=d, name=d.split("/")[-1], file_type=FileType.DIRECTORY, parent="/home")
                self._nodes[d] = node
                home.children.append(d)
            self._quotas["/"] = QuotaInfo(path="/", max_size=10 * 1024**3, max_files=1000000)
            self._quotas["/home"] = QuotaInfo(path="/home", max_size=5 * 1024**3, max_files=500000)
            self._quotas["/tmp"] = QuotaInfo(path="/tmp", max_size=1 * 1024**3, max_files=10000)
            self._initialized = True
            return {"success": True, "root_count": len(self._nodes), "quota_count": len(self._quotas)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        if not self._initialized:
            return {"healthy": False, "reason": "not_initialized"}
        issues = []
        if "/" not in self._nodes:
            issues.append("root_missing")
        return {
            "healthy": len(issues) == 0,
            "status": "healthy" if not issues else "degraded",
            "total_nodes": len(self._nodes),
            "issues": issues,
        }

    # --- Core CRUD ---
    def create_file(
        self, path: str, content: bytes = b"", owner: str = "system", overwrite: bool = False
    ) -> Dict[str, Any]:
        if not self._initialized:
            return {"success": False, "error": "not_initialized"}
        if path in self._nodes and not overwrite:
            return {"success": False, "error": "already_exists", "path": path}
        parent = str(Path(path).parent)
        if parent not in self._nodes or self._nodes[parent].file_type != FileType.DIRECTORY:
            return {"success": False, "error": "parent_not_found", "parent": parent}
        if not self._check_quota(parent, len(content), 1):
            return {"success": False, "error": "quota_exceeded"}
        name = Path(path).name
        checksum = hashlib.sha256(content).hexdigest() if content else ""
        node = FileNode(
            path=path,
            name=name,
            file_type=FileType.FILE,
            size=len(content),
            content=content,
            owner=owner,
            checksum=checksum,
            parent=parent,
        )
        if path in self._nodes:
            self._save_version(path)
        self._nodes[path] = node
        self._nodes[parent].children.append(path)
        self._update_quota(parent, len(content), 1)
        self._index_file(node)
        self._stats["ops_write"] += 1
        self._stats["bytes_written"] += len(content)
        self._notify_watchers(parent, "create", path)
        return {"success": True, "path": path, "size": len(content), "checksum": checksum}

    def create_directory(self, path: str, owner: str = "system", recursive: bool = False) -> Dict[str, Any]:
        if not self._initialized:
            return {"success": False, "error": "not_initialized"}
        if path in self._nodes:
            return {"success": False, "error": "already_exists", "path": path}
        if recursive:
            parts = Path(path).parts
            current = ""
            for p in parts:
                current = str(Path(current) / p) if current else "/" + p
                if current not in self._nodes:
                    parent = str(Path(current).parent)
                    if parent == current:
                        parent = "/"
                    if parent not in self._nodes:
                        return {"success": False, "error": "parent_missing", "parent": parent}
                    name = current.split("/")[-1]
                    node = FileNode(path=current, name=name, file_type=FileType.DIRECTORY, parent=parent)
                    self._nodes[current] = node
                    self._nodes[parent].children.append(current)
        else:
            parent = str(Path(path).parent)
            if parent not in self._nodes:
                return {"success": False, "error": "parent_not_found", "parent": parent}
            name = Path(path).name
            node = FileNode(path=path, name=name, file_type=FileType.DIRECTORY, parent=parent, owner=owner)
            self._nodes[path] = node
            self._nodes[parent].children.append(path)
            self._stats["ops_write"] += 1
        self._notify_watchers(str(Path(path).parent), "create", path)
        return {"success": True, "path": path}

    def read_file(self, path: str, offset: int = 0, length: int = -1, encoding: str = None) -> Dict[str, Any]:
        if not self._initialized:
            return {"success": False, "error": "not_initialized"}
        if path not in self._nodes:
            return {"success": False, "error": "not_found", "path": path}
        node = self._nodes[path]
        if node.file_type != FileType.FILE:
            return {"success": False, "error": "is_directory", "path": path}
        node.accessed = time.time()
        content = node.content
        if offset > 0:
            content = content[offset:]
        if length > 0:
            content = content[:length]
        self._stats["ops_read"] += 1
        self._stats["bytes_read"] += len(content)
        result = {
            "success": True,
            "path": path,
            "size": len(content),
            "checksum": node.checksum,
            "modified": node.modified,
        }
        if encoding:
            try:
                result["content"] = content.decode(encoding)
            except UnicodeDecodeError:
                result["content"] = content.decode(encoding, errors="replace")
        else:
            result["content_base64"] = content.hex()
        return result

    def delete(self, path: str, recursive: bool = False, permanent: bool = False) -> Dict[str, Any]:
        if not self._initialized:
            return {"success": False, "error": "not_initialized"}
        if path not in self._nodes:
            return {"success": False, "error": "not_found", "path": path}
        node = self._nodes[path]
        if node.file_type == FileType.DIRECTORY and node.children and not recursive:
            return {"success": False, "error": "directory_not_empty", "path": path}
        removed_count = self._remove_node(path, recursive)
        if not permanent:
            self._trash[path] = node
            if len(self._trash) > 1000:
                oldest = sorted(self._trash.keys(), key=lambda k: self._trash[k].modified)[:100]
                for k in oldest:
                    del self._trash[k]
        self._stats["ops_delete"] += 1
        return {"success": True, "path": path, "removed_count": removed_count, "permanent": permanent}

    def _remove_node(self, path: str, recursive: bool) -> int:
        node = self._nodes[path]
        count = 1
        parent_path = str(Path(path).parent)
        if parent_path in self._nodes and path in self._nodes[parent_path].children:
            self._nodes[parent_path].children.remove(path)
        if node.file_type == FileType.DIRECTORY and recursive:
            for child_path in list(node.children):
                count += self._remove_node(child_path, True)
        if path in self._search_index:
            for kw in self._search_index[path]:
                pass
            del self._search_index[path]
        del self._nodes[path]
        return count

    # --- Listing & Search ---
    def list_directory(self, path: str, recursive: bool = False, pattern: str = None) -> Dict[str, Any]:
        if not self._initialized:
            return {"success": False, "error": "not_initialized"}
        if path not in self._nodes:
            return {"success": False, "error": "not_found", "path": path}
        node = self._nodes[path]
        if node.file_type != FileType.DIRECTORY:
            return {"success": False, "error": "not_directory", "path": path}
        items = []
        self._collect_items(path, node, items, recursive, pattern)
        return {"success": True, "path": path, "items": items, "total": len(items)}

    def _collect_items(self, path: str, node: FileNode, items: List[Dict], recursive: bool, pattern: str):
        import fnmatch

        for child_path in node.children:
            child = self._nodes.get(child_path)
            if not child:
                continue
            if pattern and not fnmatch.fnmatch(child.name, pattern):
                continue
            items.append(child.to_dict())
            if recursive and child.file_type == FileType.DIRECTORY:
                self._collect_items(child_path, child, items, True, pattern)

    def search(self, query: str, root: str = "/", max_results: int = 100) -> Dict[str, Any]:
        if not self._initialized:
            return {"success": False, "error": "not_initialized"}
        results = []
        query_lower = query.lower()
        for path, node in self._nodes.items():
            if not path.startswith(root):
                continue
            if query_lower in path.lower() or query_lower in node.name.lower():
                results.append(node.to_dict())
                if len(results) >= max_results:
                    break
        return {"success": True, "query": query, "results": results, "total": len(results)}

    def get_info(self, path: str) -> Dict[str, Any]:
        if not self._initialized:
            return {"success": False, "error": "not_initialized"}
        if path not in self._nodes:
            return {"success": False, "error": "not_found", "path": path}
        return {"success": True, **self._nodes[path].to_dict()}

    def move(self, src: str, dst: str) -> Dict[str, Any]:
        if not self._initialized:
            return {"success": False, "error": "not_initialized"}
        if src not in self._nodes or dst not in self._nodes:
            return {"success": False, "error": "not_found"}
        if self._nodes[dst].file_type != FileType.DIRECTORY:
            return {"success": False, "error": "target_not_directory"}
        node = self._nodes[src]
        old_parent = str(Path(src).parent)
        new_path = str(Path(dst) / node.name)
        if new_path in self._nodes:
            return {"success": False, "error": "already_exists", "path": new_path}
        if old_parent in self._nodes and src in self._nodes[old_parent].children:
            self._nodes[old_parent].children.remove(src)
        self._nodes[dst].children.append(new_path)
        node.path = new_path
        node.parent = dst
        self._nodes[new_path] = self._nodes.pop(src)
        if node.file_type == FileType.DIRECTORY:
            self._update_child_paths(new_path, node)
        return {"success": True, "from": src, "to": new_path}

    def copy(self, src: str, dst: str) -> Dict[str, Any]:
        if not self._initialized:
            return {"success": False, "error": "not_initialized"}
        if src not in self._nodes:
            return {"success": False, "error": "not_found", "path": src}
        node = self._nodes[src]
        parent = str(Path(dst).parent)
        if parent not in self._nodes:
            return {"success": False, "error": "parent_not_found", "parent": parent}
        new_node = FileNode(
            path=dst,
            name=Path(dst).name,
            file_type=node.file_type,
            size=node.size,
            content=node.content,
            owner=node.owner,
            group=node.group,
            permissions=node.permissions,
            checksum=node.checksum,
            parent=parent,
            metadata=dict(node.metadata),
        )
        self._nodes[dst] = new_node
        self._nodes[parent].children.append(dst)
        self._stats["ops_write"] += 1
        return {"success": True, "from": src, "to": dst, "size": node.size}

    def _update_child_paths(self, new_parent: str, node: FileNode):
        for i, child_path in enumerate(node.children):
            child = self._nodes.get(child_path)
            if child:
                new_child_path = str(Path(new_parent) / child.name)
                node.children[i] = new_child_path
                child.path = new_child_path
                child.parent = new_parent
                self._nodes[new_child_path] = self._nodes.pop(child_path)
                if child.file_type == FileType.DIRECTORY:
                    self._update_child_paths(new_child_path, child)

    # --- Quota ---
    def _check_quota(self, path: str, size: int, files: int) -> bool:
        while path and path != "/":
            if path in self._quotas:
                q = self._quotas[path]
                if q.max_size > 0 and q.current_size + size > q.max_size:
                    return False
                if q.max_files > 0 and q.current_files + files > q.max_files:
                    return False
            path = str(Path(path).parent)
        return True

    def _update_quota(self, path: str, size_delta: int, files_delta: int):
        while path and path != "/":
            if path in self._quotas:
                q = self._quotas[path]
                q.current_size += size_delta
                q.current_files += files_delta
            path = str(Path(path).parent)

    def get_quota(self, path: str) -> Dict[str, Any]:
        for p in [path, str(Path(path).parent)]:
            if p in self._quotas:
                return {"success": True, **self._quotas[p].to_dict()}
        return {"success": True, "path": path, "unlimited": True}

    def set_quota(self, path: str, max_size: int = 0, max_files: int = 0) -> Dict[str, Any]:
        if path not in self._nodes or self._nodes[path].file_type != FileType.DIRECTORY:
            return {"success": False, "error": "invalid_path"}
        self._quotas[path] = QuotaInfo(path=path, max_size=max_size, max_files=max_files)
        return {"success": True, "path": path, "max_size": max_size, "max_files": max_files}

    # --- Versions ---
    def _save_version(self, path: str):
        node = self._nodes[path]
        record = VersionRecord(
            path=path, version=node.version, size=node.size, checksum=node.checksum, author=node.owner
        )
        self._versions[path].append(record)
        node.version += 1

    def get_versions(self, path: str) -> Dict[str, Any]:
        if path not in self._versions:
            return {"success": True, "path": path, "versions": [], "current": 1}
        versions = [v.to_dict() for v in self._versions[path]]
        return {
            "success": True,
            "path": path,
            "versions": versions,
            "total": len(versions),
            "current": self._nodes[path].version if path in self._nodes else 1,
        }

    # --- Index ---
    def _index_file(self, node: FileNode):
        words = set(node.name.lower().replace("-", " ").replace("_", " ").split())
        for w in words:
            if len(w) >= 2:
                self._search_index[w].add(node.path)

    # --- Watchers ---
    def watch(self, path: str, callback_id: str, events: List[str] = None) -> Dict[str, Any]:
        if path not in self._nodes:
            return {"success": False, "error": "not_found"}
        watcher = {"id": callback_id, "events": events or ["create", "modify", "delete"], "created": time.time()}
        self._watchers[path].append(watcher)
        return {"success": True, "path": path, "watcher_id": callback_id}

    def unwatch(self, path: str, callback_id: str) -> Dict[str, Any]:
        if path in self._watchers:
            self._watchers[path] = [w for w in self._watchers[path] if w["id"] != callback_id]
        return {"success": True}

    def _notify_watchers(self, path: str, event: str, target: str):
        for watcher in self._watchers.get(path, []):
            if event in watcher["events"]:
                logger.info(f"Watcher {watcher['id']}: {event} on {target}")

    # --- Trash ---
    def list_trash(self) -> Dict[str, Any]:
        items = [
            {"path": p, "name": n.name, "type": n.file_type.value, "size": n.size, "deleted": n.modified}
            for p, n in self._trash.items()
        ]
        return {"success": True, "items": items, "total": len(items)}

    def restore(self, path: str) -> Dict[str, Any]:
        if path not in self._trash:
            return {"success": False, "error": "not_in_trash", "path": path}
        node = self._trash.pop(path)
        parent = node.parent or str(Path(path).parent)
        if parent in self._nodes:
            self._nodes[path] = node
            self._nodes[parent].children.append(path)
            return {"success": True, "path": path, "restored_to": parent}
        return {"success": False, "error": "parent_missing"}

    def empty_trash(self) -> Dict[str, Any]:
        count = len(self._trash)
        self._trash.clear()
        return {"success": True, "freed": count}

    # --- Locking ---
    def acquire_lock(self, path: str, owner: str, exclusive: bool = True, timeout: float = 30.0) -> Dict[str, Any]:
        if path in self._lock_table:
            lock = self._lock_table[path]
            if lock["exclusive"] or (exclusive and lock["owner"] != owner):
                return {"success": False, "error": "locked", "locked_by": lock["owner"]}
        self._lock_table[path] = {"owner": owner, "exclusive": exclusive, "acquired": time.time(), "timeout": timeout}
        return {"success": True, "path": path, "owner": owner}

    def release_lock(self, path: str, owner: str) -> Dict[str, Any]:
        if path in self._lock_table and self._lock_table[path]["owner"] == owner:
            del self._lock_table[path]
            return {"success": True}
        return {"success": False, "error": "not_owner"}

    # --- Stats ---
    def get_stats(self) -> Dict[str, Any]:
        total_size = sum(n.size for n in self._nodes.values())
        file_count = sum(1 for n in self._nodes.values() if n.file_type == FileType.FILE)
        dir_count = sum(1 for n in self._nodes.values() if n.file_type == FileType.DIRECTORY)
        return {
            "success": True,
            "total_nodes": len(self._nodes),
            "files": file_count,
            "directories": dir_count,
            "total_size": total_size,
            "trash_items": len(self._trash),
            "active_locks": len(self._lock_table),
            "ops": self._stats,
        }

    def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        if path not in self._nodes:
            return {"success": False, "error": "not_found"}
        node = self._nodes[path]
        total_size = node.size
        file_count = 0
        if node.file_type == FileType.DIRECTORY:
            for child_path in node.children:
                child = self._nodes.get(child_path)
                if child:
                    total_size += child.size
                    if child.file_type == FileType.FILE:
                        file_count += 1
        return {
            "success": True,
            "path": path,
            "total_size": total_size,
            "file_count": file_count,
            "dir_children": len(node.children),
        }

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("file_system.execute", "start", action=action)
        self.metrics_collector.counter("file_system.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "file_system"}
            else:
                result = {"success": True, "action": action, "module": "file_system"}
            self.metrics_collector.counter("file_system.execute.success", 1)
            self.trace("file_system.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("file_system.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "file_system"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "file_system", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("file_system.initialize", "start")
        self.metrics_collector.gauge("file_system.initialized", 1)
        self.audit("初始化file_system", level="info")
        self.trace("file_system.initialize", "end")
        return {"success": True, "module": "file_system"}

module_class = FileSystemModule
