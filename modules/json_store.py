# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - JSON 持久化存储（A级） — 线程安全原子写入"""

import json
import os
import threading
import shutil
import time
import uuid
import logging
from typing import Any, Dict, List, Optional

from modules._base.enterprise_module import (
    EnterpriseModule, ModuleStatus, HealthReport,
    CircuitBreakerMixin, RateLimiterMixin,
)

logger = logging.getLogger("evo.json-store")

__module_meta__ = {
    "id": "json-store",
    "name": "JSON Store",
    "version": "V0.1",
    "group": "storage",
    "grade": "A",
    "tags": ["storage", "json", "persistence", "atomic-write", "backup"],
    "description": "JSON 持久化存储 — 线程安全原子写入、自动备份、目录扫描",
}


class JsonStore(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """线程安全的 JSON 文件存储模块。

    核心能力：
      - load(path)         加载 JSON 文件
      - save(path, data)   写入 JSON 文件
      - atomic_save(path, data)  先写临时文件再 rename，防止写中断损坏
      - backup(path)       创建 .bak 备份文件
      - list_keys(directory)  扫描目录下所有 .json 文件
    """

    MODULE_ID = "json-store"
    MODULE_NAME = "JSON存储"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict] = None) -> None:
        super().__init__(config)
        self._data: Dict[str, Any] = {}
        self._store_path: str = self.config.get("path", "data/json_store.json")
        self._backup_path: str = self._store_path + ".bak"
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        try:
            if os.path.exists(self._store_path):
                with open(self._store_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                self.logger.info("Loaded %d keys from %s", len(self._data), self._store_path)
            else:
                self.logger.info("Store file %s not found, starting empty", self._store_path)
        except Exception as exc:
            self.logger.warning("Failed to load store file: %s", exc)
        self.status = ModuleStatus.RUNNING

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value,
            healthy=True,
            module_id=self.MODULE_ID,
            checks={
                "keys": len(self._data),
                "store_exists": os.path.exists(self._store_path),
                "store_size": os.path.getsize(self._store_path) if os.path.exists(self._store_path) else 0,
            },
        )

    async def execute(self, action: str, params: Optional[Dict] = None) -> Any:
        return await self._safe_execute(action, params, handler=self._dispatch)

    async def shutdown(self) -> None:
        self._flush()
        self.status = ModuleStatus.STOPPED
        self.logger.info("JsonStore shut down, %d keys flushed", len(self._data))

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def load(self, path: str) -> Optional[Dict[str, Any]]:
        """加载指定路径的 JSON 文件。"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning("File not found: %s", path)
            return None
        except json.JSONDecodeError as exc:
            self.logger.error("JSON decode error in %s: %s", path, exc)
            return None

    def save(self, path: str, data: Any) -> bool:
        """直接写入 JSON 文件（非原子）。"""
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str, indent=2)
            self.logger.info("Saved %d bytes to %s", os.path.getsize(path), path)
            return True
        except Exception as exc:
            self.logger.error("Failed to save %s: %s", path, exc)
            return False

    def atomic_save(self, path: str, data: Any) -> bool:
        """原子写入：先写临时文件再 rename，防止写半途中崩溃。"""
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            tmp_path = path + ".tmp." + str(os.getpid())
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str, indent=2)
                f.flush()
                os.fsync(f.fileno())  # 确保数据刷到磁盘
            shutil.move(tmp_path, path)
            self.logger.info("Atomic save completed for %s", path)
            return True
        except Exception as exc:
            self.logger.error("Atomic save failed for %s: %s", path, exc)
            # 清理残留临时文件
            tmp = path + ".tmp." + str(os.getpid())
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
            return False

    def backup(self, path: str) -> Optional[str]:
        """创建 .bak 备份文件，返回备份路径；失败返回 None。"""
        if not os.path.exists(path):
            self.logger.warning("Cannot backup non-existent file: %s", path)
            return None
        bak_path = path + ".bak"
        try:
            shutil.copy2(path, bak_path)
            self.logger.info("Backup created: %s -> %s", path, bak_path)
            return bak_path
        except Exception as exc:
            self.logger.error("Backup failed for %s: %s", path, exc)
            return None

    def list_keys(self, directory: str) -> List[str]:
        """扫描目录下所有 .json 文件名（不含扩展名）。"""
        if not os.path.isdir(directory):
            self.logger.warning("Directory not found: %s", directory)
            return []
        try:
            keys = [f[:-5] for f in os.listdir(directory) if f.endswith(".json")]
            self.logger.info("Found %d json files in %s", len(keys), directory)
            return sorted(keys)
        except Exception as exc:
            self.logger.error("Failed to list keys in %s: %s", directory, exc)
            return []

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _flush(self) -> None:
        """将当前内存数据持久化到 store 文件。"""
        try:
            os.makedirs(os.path.dirname(self._store_path) or ".", exist_ok=True)
            self.atomic_save(self._store_path, self._data)
        except Exception as exc:
            self.logger.error("Flush failed: %s", exc)

    def _dispatch(self, p: Dict) -> Dict:
        """旧版 dispatch — 保持向后兼容。"""
        action = p.get("action", "status")
        key = p.get("key", "")

        if action == "save":
            key = key or str(uuid.uuid4())[:8]
            with self._lock:
                self._data[key] = p.get("value", {})
                self._flush()
            return {"success": True, "key": key}

        if action == "load":
            with self._lock:
                return {"success": True, "value": self._data.get(key, None)}

        if action == "delete":
            with self._lock:
                self._data.pop(key, None)
                self._flush()
            return {"success": True}

        if action == "list":
            with self._lock:
                return {"keys": list(self._data.keys()), "count": len(self._data)}

        if action == "flush":
            self._flush()
            return {"success": True}

        if action == "stats":
            return {
                "success": True,
                "total_keys": len(self._data),
                "store_path": self._store_path,
                "exists": os.path.exists(self._store_path),
                "size_bytes": os.path.getsize(self._store_path) if os.path.exists(self._store_path) else 0,
            }

        if action == "backup":
            result = self.backup(self._store_path)
            return {"success": result is not None, "backup_path": result or ""}

        if action == "restore":
            if os.path.exists(self._backup_path):
                with self._lock:
                    try:
                        with open(self._backup_path, "r", encoding="utf-8") as f:
                            self._data = json.load(f)
                        self._flush()
                        return {"success": True, "restored": len(self._data)}
                    except Exception as exc:
                        return {"success": False, "error": str(exc)}
            return {"success": False, "error": "backup_not_found"}

        if action == "clear":
            with self._lock:
                n = len(self._data)
                self._data.clear()
                self._flush()
            return {"success": True, "cleared": n}

        if action == "search_keys":
            q = p.get("query", "").lower()
            with self._lock:
                matches = [
                    k for k in self._data
                    if q in k.lower() or q in str(self._data[k]).lower()
                ]
            return {"success": True, "query": q, "matches": matches, "count": len(matches)}

        if action == "atomic_save":
            path = p.get("path", self._store_path)
            data = p.get("data", {})
            ok = self.atomic_save(path, data)
            return {"success": ok, "path": path}

        if action == "list_keys":
            directory = p.get("directory", os.path.dirname(self._store_path) or ".")
            keys = self.list_keys(directory)
            return {"success": True, "keys": keys, "count": len(keys)}

        return {"error": f"unknown:{action}"}


module_class = JsonStore
