"""AUTO-EVO-AI V0.1 — SQLite 持久化层

替代 JSON 文件存储，提供统一的数据库访问接口。
用法:
    from api.database import db
    db.save("settings", {"key": "theme", "value": "dark"})
    results = db.query("settings", {"key": "theme"})
"""
import os, json, sqlite3, threading, time
from pathlib import Path
from typing import Any, Optional
from core.logging_config import get_logger

logger = get_logger("evo.db")

DB_DIR = Path(__file__).parent.parent / "_data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DB_DIR / "evo.db")

_thread_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """线程级连接（避免锁竞争）"""
    if not hasattr(_thread_local, "conn") or _thread_local.conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        _init_tables(conn)
        _thread_local.conn = conn
    return _thread_local.conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS kv_store (
            namespace TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL DEFAULT (strftime('%s','now')),
            PRIMARY KEY (namespace, key)
        );
        CREATE TABLE IF NOT EXISTS tool_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT NOT NULL,
            args TEXT,
            result TEXT,
            duration_ms REAL,
            created_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            actor TEXT,
            target TEXT,
            detail TEXT,
            created_at REAL DEFAULT (strftime('%s','now'))
        );
    """)


class Database:
    """数据库访问接口"""

    def save(self, namespace: str, data: dict, key_field: str = "key") -> bool:
        """保存键值数据"""
        conn = _get_conn()
        key = str(data.get(key_field, data.get("id", "")))
        if not key:
            return False
        try:
            conn.execute(
                """INSERT INTO kv_store (namespace, key, value, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(namespace, key) DO UPDATE SET
                       value=excluded.value,
                       updated_at=excluded.updated_at""",
                (namespace, key, json.dumps(data, ensure_ascii=False, default=str), time.time()),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.warning(f"[DB] save error: {e}")
            return False

    def get(self, namespace: str, key: str) -> Optional[dict]:
        """读取键值数据"""
        conn = _get_conn()
        row = conn.execute("SELECT value FROM kv_store WHERE namespace=? AND key=?", (namespace, key)).fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except:
                return {"raw": row["value"]}
        return None

    def query(self, namespace: str, filters: dict = None) -> list[dict]:
        """查询命名空间下所有记录，支持过滤"""
        conn = _get_conn()
        if filters:
            rows = conn.execute("SELECT value FROM kv_store WHERE namespace=?", (namespace,)).fetchall()
            results = []
            for row in rows:
                try:
                    data = json.loads(row["value"])
                except:
                    continue
                if all(str(data.get(k, "")).lower() == str(v).lower() for k, v in filters.items()):
                    results.append(data)
            return results
        rows = conn.execute("SELECT value FROM kv_store WHERE namespace=?", (namespace,)).fetchall()
        return [json.loads(r["value"]) for r in rows if r["value"]]

    def delete(self, namespace: str, key: str) -> bool:
        """删除记录"""
        conn = _get_conn()
        conn.execute("DELETE FROM kv_store WHERE namespace=? AND key=?", (namespace, key))
        conn.commit()
        return True

    def log_tool(self, tool_name: str, args: dict, result: dict, duration_ms: float):
        """记录工具调用日志"""
        conn = _get_conn()
        conn.execute(
            "INSERT INTO tool_log (tool_name, args, result, duration_ms) VALUES (?, ?, ?, ?)",
            (tool_name, json.dumps(args)[:500], json.dumps(result)[:500], round(duration_ms, 1)),
        )
        conn.commit()

    def log_audit(self, action: str, actor: str = "", target: str = "", detail: str = ""):
        """记录审计日志"""
        conn = _get_conn()
        conn.execute(
            "INSERT INTO audit_log (action, actor, target, detail) VALUES (?, ?, ?, ?)",
            (action, actor or "system", target or "", detail[:1000]),
        )
        conn.commit()


# 全局单例
db = Database()
