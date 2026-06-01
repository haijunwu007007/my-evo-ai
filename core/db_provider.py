"""AUTO-EVO-AI V0.1 — 数据库引擎抽象层
支持 SQLite（默认）和 PostgreSQL（可选）
通过 EVO_DB_URL 环境变量切换：
  不设置 / sqlite:// → SQLite
  postgresql://user:pass@host:5432/db → PostgreSQL
"""
import os, json, time
from typing import Any, Optional
from contextlib import asynccontextmanager
from core.logging_config import get_logger

logger = get_logger("evo.db_provider")

DB_URL = os.environ.get("EVO_DB_URL", "sqlite:///data/evo.db")

# ── SQLite Engine (默认) ──
class SqliteEngine:
    def __init__(self):
        import sqlite3
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self):
        import sqlite3
        from pathlib import Path
        db_path = DB_URL.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def execute(self, sql: str, params: tuple = ()):
        if not self._conn: self.connect()
        return self._conn.execute(sql, params)

    def commit(self):
        if self._conn: self._conn.commit()

    def rollback(self):
        if self._conn: self._conn.rollback()

    def close(self):
        if self._conn: self._conn.close(); self._conn = None

    @property
    def engine_type(self) -> str: return "sqlite"

# ── PostgreSQL Engine (可选) ──
class PostgresEngine:
    def __init__(self):
        self._pool = None

    async def connect(self):
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                dsn=DB_URL, min_size=2, max_size=10
            )
            logger.info(f"[PG] 连接池已创建: {DB_URL}")
        except ImportError:
            logger.error("[PG] asyncpg 未安装, 回退 SQLite")
            raise

    async def execute(self, sql: str, params: tuple = ()):
        if not self._pool: await self.connect()
        async with self._pool.acquire() as conn:
            return await conn.execute(sql, *params)

    async def fetch(self, sql: str, params: tuple = ()):
        if not self._pool: await self.connect()
        async with self._pool.acquire() as conn:
            return await conn.fetch(sql, *params)

    async def close(self):
        if self._pool: await self._pool.close(); self._pool = None

    @property
    def engine_type(self) -> str: return "postgresql"

# ── Factory ──
def create_engine():
    if DB_URL.startswith("postgresql"):
        logger.info(f"[DB] 使用 PostgreSQL: {DB_URL}")
        return PostgresEngine()
    logger.info(f"[DB] 使用 SQLite: {DB_URL}")
    return SqliteEngine()

engine = create_engine()
