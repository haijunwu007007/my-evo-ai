# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 对象存储（A级）"""
__module_meta__ = {"id":"object-storage","name":"ObjectStorage","version":"V0.1","group":"storage","grade":"A",
    "tags":["storage","object","file","persistence"],"description":"基于DataEngine SQLite的对象存储"}
import time, uuid, logging, os, json
from pathlib import Path
from typing import Any, Dict
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
from core.data_layer import DataEngine
logger = logging.getLogger("evo.object-storage")

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "object_storage"

class ObjectStorage(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    MODULE_ID = "object-storage"
    MODULE_NAME = "对象存储"
    VERSION = "v2.0"
    MODULE_LEVEL = "A"

    def __init__(self, config=None):
        super().__init__(config)
        config = config or {}
        data_dir = config.get("data_dir", str(DEFAULT_DATA_DIR))
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._db = DataEngine.get("object_storage")
        self._ensure_schema()
        self._max_objects = int(config.get("max_objects", 10_000))
        self._cache: Dict[str, dict] = {}
        self._load_cache()

    def _ensure_schema(self):
        self._db.create_table("objects", {
            "key": "TEXT PRIMARY KEY",
            "size": "INTEGER DEFAULT 0",
            "content_type": "TEXT DEFAULT 'text/plain'",
            "bucket": "TEXT DEFAULT 'default'",
            "metadata": "TEXT DEFAULT '{}'",
            "disk_path": "TEXT",
            "created": "REAL",
            "modified": "REAL"
        })

    def _load_cache(self):
        rows = self._db.fetch_all("SELECT * FROM objects ORDER BY key")
        for r in rows:
            self._cache[r["key"]] = r
        logger.info("loaded %d objects from SQLite", len(self._cache))

    def _object_path(self, bucket: str, key: str) -> Path:
        obj_dir = self._data_dir / (bucket or "default")
        obj_dir.mkdir(parents=True, exist_ok=True)
        return obj_dir / key.replace("/", "_").replace("\\", "_")

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value, healthy=True,
            module_id=self.MODULE_ID,
            checks={
                "objects_db": len(self._cache),
                "data_dir": str(self._data_dir),
                "engine": "SQLite"
            }
        )

    def _disk_free_mb(self) -> int:
        try:
            st = os.statvfs(self._data_dir) if hasattr(os, 'statvfs') else None
            if st:
                return st.f_frsize * st.f_bfree // 1_048_576
            import ctypes
            free = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(str(self._data_dir)), None, None, ctypes.pointer(free))
            return free.value // 1_048_576
        except Exception:
            return 0

    async def execute(self, action=None, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _dispatch(self, p: dict) -> dict:
        a = p.get("action", "status")

        if a == "status":
            return {"success": True, "objects": len(self._cache),
                    "data_dir": str(self._data_dir), "engine": "SQLite"}

        if a == "put":
            key = p.get("key", uuid.uuid4().hex)
            data = p.get("data", "")
            meta = p.get("metadata", {})
            content_type = p.get("content_type", "text/plain")
            bucket = p.get("bucket", meta.get("bucket", "default"))
            data_bytes = str(data).encode("utf-8")
            obj_path = self._object_path(bucket, key)
            obj_path.write_bytes(data_bytes)
            now = time.time()
            md_json = json.dumps(meta, ensure_ascii=False)
            self._db.upsert("objects", {
                "key": key, "size": len(data_bytes),
                "content_type": content_type, "bucket": bucket,
                "metadata": md_json, "disk_path": str(obj_path),
                "created": now, "modified": now
            }, "key")
            self._cache[key] = {"key": key, "size": len(data_bytes),
                "content_type": content_type, "bucket": bucket,
                "metadata": md_json, "disk_path": str(obj_path),
                "created": now, "modified": now}
            return {"success": True, "key": key, "size": len(data_bytes)}

        if a == "get":
            key = p.get("key", "")
            entry = self._cache.get(key) or self._db.fetch_one(
                "SELECT * FROM objects WHERE key=?", (key,))
            if not entry:
                return {"error": f"key not found: {key}"}
            obj_path = Path(entry["disk_path"])
            if obj_path.exists():
                data = obj_path.read_bytes()
                return {"success": True, "key": key,
                    "data_base64": __import__("base64").b64encode(data).decode("ascii"),
                    "size": len(data), "content_type": entry.get("content_type", "application/octet-stream"),
                    "metadata": json.loads(entry.get("metadata", "{}"))}
            return {"error": f"data file missing: {entry['disk_path']}"}

        if a == "delete":
            key = p.get("key", "")
            self._delete_object(key)
            self._db.delete("objects", "key=?", (key,))
            self._cache.pop(key, None)
            return {"success": True, "deleted": key}

        if a == "list":
            bucket = p.get("bucket", "")
            prefix = p.get("prefix", "")
            max_keys = int(p.get("max_keys", 100))
            where = "1=1"
            params = []
            if bucket:
                where += " AND bucket=?"
                params.append(bucket)
            if prefix:
                where += " AND key LIKE ?"
                params.append(prefix + "%")
            rows = self._db.fetch_all(
                f"SELECT key,size,content_type,bucket,created,modified FROM objects WHERE {where} ORDER BY key LIMIT ?",
                tuple(params) + (max_keys,))
            return {"success": True, "objects": rows, "count": len(rows),
                    "total_objects": len(self._cache), "truncated": len(rows) < len(self._cache)}

        if a == "list_buckets":
            rows = self._db.fetch_all("SELECT bucket, COUNT(*) as cnt FROM objects GROUP BY bucket ORDER BY bucket")
            return {"success": True, "buckets": [{"name": r["bucket"], "count": r["cnt"]} for r in rows]}

        if a == "exists":
            key = p.get("key", "")
            if key in self._cache:
                return {"success": True, "exists": True}
            row = self._db.fetch_one("SELECT 1 FROM objects WHERE key=?", (key,))
            return {"success": True, "exists": row is not None}

        if a == "stats":
            rs = self._db.fetch_one(
                "SELECT COUNT(*) as cnt, COALESCE(SUM(size),0) as total_bytes, COUNT(DISTINCT bucket) as buckets FROM objects")
            return {"success": True, "stats": {
                "object_count": rs["cnt"] if rs else 0,
                "total_size_bytes": rs["total_bytes"] if rs else 0,
                "total_size_mb": round((rs["total_bytes"] if rs else 0) / 1_048_576, 2),
                "buckets": rs["buckets"] if rs else 0,
                "engine": "SQLite",
                "disk_free_mb": self._disk_free_mb()}}

        if a == "search":
            q = p.get("query", "")
            rows = self._db.search("objects", q, fields=["key", "bucket", "content_type"],
                                   limit=p.get("limit", 20))
            return {"success": True, **rows}

        return {"error": f"unknown action: {a}"}

    def _delete_object(self, key: str):
        entry = self._cache.get(key) or self._db.fetch_one(
            "SELECT disk_path FROM objects WHERE key=?", (key,))
        if entry and Path(entry.get("disk_path", "")).exists():
            try:
                Path(entry["disk_path"]).unlink()
            except OSError:
                pass

    async def shutdown(self) -> None:
        self._cache.clear()
        self.status = ModuleStatus.STOPPED

module_class = ObjectStorage
