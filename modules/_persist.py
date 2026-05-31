"""
AUTO-EVO-AI V0.1 — 真实持久化Mixin
给任何模块添加SQLite持久化能力，替换内存模拟数据
"""
import os, json, threading, time, logging
from typing import Any, Dict

logger = logging.getLogger("evo.persist")

class PersistMixin:
    """持久化Mixin — 模块数据自动保存到SQLite"""

    _db_path: str = ""
    _db_lock: threading.Lock = threading.Lock()

    def _init_db(self, module_id: str) -> None:
        from modules._client import get_client
        base = os.environ.get("EVO_DATA_DIR", "data")
        os.makedirs(base, exist_ok=True)
        self._db_path = os.path.join(base, f"{module_id}.db")
        self._client = get_client()
        self._module_id = module_id
        self._table_ready = False

    def _ensure_table(self) -> None:
        if self._table_ready:
            return
        with self._db_lock:
            self._client.sqlite_query(self._db_path, """
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at REAL
                )
            """)
            self._table_ready = True

    def kv_get(self, key: str, default: Any = None) -> Any:
        self._ensure_table()
        r = self._client.sqlite_query(self._db_path,
            "SELECT value FROM kv_store WHERE key=?", (key,))
        if r.get("success") and r["data"]:
            try:
                return json.loads(r["data"][0]["value"])
            except Exception:
                return r["data"][0]["value"]
        return default

    def kv_set(self, key: str, value: Any) -> bool:
        self._ensure_table()
        raw = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        r = self._client.sqlite_query(self._db_path,
            "INSERT OR REPLACE INTO kv_store (key, value, updated_at) VALUES (?,?,?)",
            (key, raw, time.time()))
        return r.get("success", False)

    def kv_delete(self, key: str) -> bool:
        self._ensure_table()
        r = self._client.sqlite_query(self._db_path,
            "DELETE FROM kv_store WHERE key=?", (key,))
        return r.get("success", False)

    def kv_list(self, prefix: str = "") -> dict[str, Any]:
        self._ensure_table()
        if prefix:
            r = self._client.sqlite_query(self._db_path,
                "SELECT key, value FROM kv_store WHERE key LIKE ?", (prefix + "%",))
        else:
            r = self._client.sqlite_query(self._db_path,
                "SELECT key, value FROM kv_store")
        if r.get("success") and r["data"]:
            result = {}
            for row in r["data"]:
                try:
                    result[row["key"]] = json.loads(row["value"])
                except Exception:
                    result[row["key"]] = row["value"]
            return result
        return {}

    def kv_count(self) -> int:
        self._ensure_table()
        r = self._client.sqlite_query(self._db_path,
            "SELECT COUNT(*) as c FROM kv_store")
        if r.get("success") and r["data"]:
            return r["data"][0]["c"]
        return 0
