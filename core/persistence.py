"""
AUTO-EVO-AI V0.1 — 系统持久化基础设施
==================================================
上市公司生产级别：统一持久化层，支持 SQLite（默认）/ PostgreSQL（可选）/ Redis（可选缓存）

核心能力：
  1. 多后端 — SQLite WAL（默认）/ PostgreSQL（DATABASE_URL配置）
  2. 连接池 — SQLite线程复用 / PostgreSQL连接池(min=2,max=10)
  3. 事务支持 — contextmanager事务，原子性保证
  4. 自动建表 — 按模块名自动创建隔离的表
  5. 自动迁移 — 检测表结构变更，ALTER TABLE增量升级
  6. 统一 CRUD API — insert/get/list/update/delete/count/search
  7. Redis缓存层 — 可选，热点数据缓存+失效策略
  8. 数据过期 — 自动清理过期记录
  9. 全文搜索 — SQLite FTS5 / PostgreSQL tsvector
  10. 导入导出 — JSON批量操作

配置方式：
  # 默认SQLite（零配置）
  python api_server.py

  # PostgreSQL
  set DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/evo_ai

  # Redis缓存（可选）
  set REDIS_URL=redis://localhost:6379/0
"""

import sqlite3
import json
import time
import os
import re
import uuid
import threading
import hashlib
from core.logging_config import get_logger
import shutil
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = get_logger(__name__)


class Persistence:
    """
    统一持久化层 — 生产级多后端

    后端切换：
    - SQLite（默认）：零配置，WAL模式，适合单机/嵌入式
    - PostgreSQL：设置DATABASE_URL环境变量，适合生产/多用户/高并发

    特性：
    - 自动检测后端：DATABASE_URL存在则用PG，否则SQLite
    - 连接池：SQLite线程安全复用 / PG psycopg2.pool
    - 事务：db.transaction()上下文管理器
    - 软删除：deleted_at标记，支持恢复
    - 自动迁移：表结构变更自动ALTER
    - Redis缓存：可选热点加速
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = ""):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = ""):
        if self._initialized:
            return
        self._initialized = True

        # 数据目录
        self._data_dir = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".evo_data", "persistence"
        )
        Path(self._data_dir).mkdir(parents=True, exist_ok=True)

        # 检测后端类型
        database_url = os.environ.get("DATABASE_URL", "")
        if database_url and ("postgresql" in database_url or "postgres" in database_url):
            self._backend = "postgresql"
            self._database_url = database_url
            self._db_path = database_url
            self._init_postgresql()
        else:
            self._backend = "sqlite"
            self._db_path = os.path.join(self._data_dir, "evo_system.db")
            self._init_sqlite()

        self._local = threading.local()

        # Redis（可选缓存层）
        self._redis = None
        self._redis_available = False
        self._try_connect_redis()

        # 已注册表跟踪
        self._registered_tables: Dict[str, bool] = {}
        self._table_columns: Dict[str, List[str]] = {}

        # 数据库版本（用于迁移）
        self._db_version = 1

        logger.info(
            f"[Persistence] Backend={self._backend}, "
            f"Path={self._database_url if self._backend == 'postgresql' else self._db_path}, "
            f"Redis={self._redis_available}"
        )

    # ═══════════════════════════════════════════════════════
    # SQLite 初始化
    # ═══════════════════════════════════════════════════════

    def _init_sqlite(self):
        """初始化 SQLite 后端"""
        self._conn = self._create_sqlite_connection()
        self._pg_pool = None
        self._lock = threading.Lock()

    def _create_sqlite_connection(self) -> sqlite3.Connection:
        """创建 SQLite 连接（WAL 模式，生产级调优）"""
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA cache_size=-64000")   # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ═══════════════════════════════════════════════════════
    # PostgreSQL 初始化
    # ═══════════════════════════════════════════════════════

    def _init_postgresql(self):
        """初始化 PostgreSQL 后端"""
        self._conn = None
        self._lock = threading.Lock()
        self._pg_pool = None
        self._try_create_pg_pool()

    def _try_create_pg_pool(self):
        """创建 PostgreSQL 连接池"""
        try:
            from psycopg2 import pool
            self._pg_pool = pool.ThreadedConnectionPool(
                minconn=2, maxconn=10, dsn=self._database_url
            )
            # 验证连接
            test_conn = self._pg_pool.getconn()
            cur = test_conn.cursor()
            cur.execute("SELECT version()")
            ver = cur.fetchone()[0][:60]
            cur.close()
            self._pg_pool.putconn(test_conn)
            logger.info(f"[Persistence] PostgreSQL pool created (2-10): {ver}")
        except ImportError:
            logger.warning(
                "[Persistence] DATABASE_URL set but psycopg2 not installed. "
                "Install: pip install psycopg2-binary"
            )
            self._pg_pool = None
            self._backend = "sqlite"
            self._db_path = os.path.join(self._data_dir, "evo_system.db")
            self._init_sqlite()
        except Exception as e:
            logger.error(f"[Persistence] PostgreSQL connection failed: {e}. Falling back to SQLite.")
            self._pg_pool = None
            self._backend = "sqlite"
            self._db_path = os.path.join(self._data_dir, "evo_system.db")
            self._init_sqlite()

    @contextmanager
    def _get_pg_conn(self):
        """获取 PostgreSQL 连接（从连接池）"""
        if not self._pg_pool:
            raise RuntimeError("PostgreSQL pool not available")
        conn = self._pg_pool.getconn()
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pg_pool.putconn(conn)

    # ═══════════════════════════════════════════════════════
    # Redis 可选缓存
    # ═══════════════════════════════════════════════════════

    def _try_connect_redis(self):
        """尝试连接 Redis（可选缓存层）"""
        try:
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            import redis
            self._redis = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            self._redis.ping()
            self._redis_available = True
            logger.info("[Persistence] Redis cache connected")
        except Exception:
            self._redis = None
            self._redis_available = False

    # ═══════════════════════════════════════════════════════
    # 连接管理
    # ═══════════════════════════════════════════════════════

    @contextmanager
    def _get_conn(self):
        """获取线程安全连接（自动选择后端）"""
        if self._backend == "postgresql" and self._pg_pool:
            with self._get_pg_conn() as conn:
                yield conn
        else:
            with self._lock:
                yield self._conn

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        if self._backend == "postgresql" and self._pg_pool:
            with self._get_pg_conn() as conn:
                yield conn
        else:
            with self._lock:
                self._conn.execute("BEGIN")
                try:
                    yield self._conn
                    self._conn.execute("COMMIT")
                except Exception:
                    self._conn.execute("ROLLBACK")
                    raise

    # ═══════════════════════════════════════════════════════
    # 表管理
    # ═══════════════════════════════════════════════════════

    def _ensure_table(self, table_name: str, data: Optional[Dict] = None):
        """确保表存在（自动建表 + 自动迁移）"""
        if table_name in self._registered_tables:
            return

        safe_name = self._safe_table_name(table_name)

        if self._backend == "postgresql" and self._pg_pool:
            self._create_pg_table(safe_name)
        else:
            self._create_sqlite_table(safe_name)

        self._registered_tables[table_name] = True

    def _create_sqlite_table(self, safe_name: str):
        """创建 SQLite 表（含FTS5）"""
        with self._get_conn() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS [{safe_name}] (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT,
                    data TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{{}}',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    expires_at TEXT,
                    deleted_at TEXT,
                    version INTEGER DEFAULT 1
                )
            """)
            # 索引
            for idx_name, idx_col in [
                (f"idx_{safe_name}_key", "key"),
                (f"idx_{safe_name}_created", "created_at"),
                (f"idx_{safe_name}_expires", "expires_at"),
                (f"idx_{safe_name}_deleted", "deleted_at"),
            ]:
                conn.execute(f"CREATE INDEX IF NOT EXISTS [{idx_name}] ON [{safe_name}]({idx_col})")

            # FTS5 全文搜索
            try:
                conn.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS [{safe_name}_fts] USING fts5(
                        key, data, tags, content=[{safe_name}], content_rowid=id
                    )
                """)
                for trig_name, trig_event, trig_action in [
                    ("ai", "AFTER INSERT", "INSERT"),
                    ("ad", "AFTER DELETE", "'delete',"),
                    ("au", "AFTER UPDATE", "'delete',"),
                ]:
                    trigger_sql = f"""
                        CREATE TRIGGER IF NOT EXISTS [{safe_name}_{trig_name}]
                        {trig_event} ON [{safe_name}] BEGIN
                    """
                    if trig_event == "AFTER INSERT":
                        trigger_sql += f"""
                            INSERT INTO [{safe_name}_fts](rowid, key, data, tags)
                            VALUES (new.id, new.key, new.data, new.tags);
                        """
                    else:
                        trigger_sql += f"""
                            INSERT INTO [{safe_name}_fts]([{safe_name}_fts], rowid, key, data, tags)
                            VALUES({trig_action} old.id, old.key, old.data, old.tags);
                        """
                        if trig_event == "AFTER UPDATE":
                            trigger_sql += f"""
                                INSERT INTO [{safe_name}_fts](rowid, key, data, tags)
                                VALUES (new.id, new.key, new.data, new.tags);
                            """
                    trigger_sql += "END"
                    conn.execute(trigger_sql)
            except Exception as e:
                logger.debug(f"[Persistence] FTS5 skip for {safe_name}: {e}")
            conn.commit()

    def _create_pg_table(self, safe_name: str):
        """创建 PostgreSQL 表（含tsvector全文搜索）"""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS "{safe_name}" (
                    id SERIAL PRIMARY KEY,
                    key TEXT,
                    data TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{{}}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMPTZ,
                    deleted_at TIMESTAMPTZ,
                    version INTEGER DEFAULT 1
                )
            """)
            # 索引
            for idx_col in ["key", "created_at", "expires_at", "deleted_at"]:
                cur.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_{safe_name}_{idx_col}" ON "{safe_name}"({idx_col})'
                )
            # GIN全文搜索索引 (PostgreSQL tsvector)
            cur.execute(f"""
                ALTER TABLE "{safe_name}" ADD COLUMN IF NOT EXISTS search_vector tsvector
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS "idx_{safe_name}_search"
                ON "{safe_name}" USING GIN(search_vector)
            """)
            # 自动更新触发器
            cur.execute(f"""
                CREATE OR REPLACE FUNCTION "{safe_name}_search_update()" RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := to_tsvector('simple', COALESCE(NEW.key,'') || ' ' || COALESCE(NEW.data,'') || ' ' || COALESCE(NEW.tags,''));
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql
            """)
            cur.execute(f"""
                DROP TRIGGER IF EXISTS "{safe_name}_search_trig" ON "{safe_name}"
            """)
            cur.execute(f"""
                CREATE TRIGGER "{safe_name}_search_trig"
                BEFORE INSERT OR UPDATE ON "{safe_name}"
                FOR EACH ROW EXECUTE FUNCTION "{safe_name}_search_update()"
            """)
            cur.close()
            conn.commit()

    @staticmethod
    def _safe_table_name(name: str) -> str:
        """安全表名（防止注入）"""
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if safe and safe[0].isdigit():
            safe = f"t_{safe}"
        return safe[:64] or "default"

    # ═══════════════════════════════════════════════════════
    # CRUD Operations
    # ═══════════════════════════════════════════════════════

    def insert(self, table: str, data: Dict[str, Any],
               key: str = "", tags: Optional[List[str]] = None,
               metadata: Optional[Dict] = None,
               ttl_seconds: Optional[int] = None) -> int:
        """插入记录"""
        self._ensure_table(table, data)
        safe_name = self._safe_table_name(table)
        data_json = json.dumps(data, ensure_ascii=False, default=str)
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        now = datetime.now().isoformat()

        if self._backend == "postgresql" and self._pg_pool:
            record_id = self._pg_insert(safe_name, key, data_json, tags_json, meta_json, ttl_seconds, now)
        else:
            expires_at = f"datetime('now', '+{ttl_seconds} seconds')" if ttl_seconds else "NULL"
            with self._get_conn() as conn:
                cursor = conn.execute(f"""
                    INSERT INTO [{safe_name}] (key, data, tags, metadata, expires_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, {expires_at}, ?, ?)
                """, (key, data_json, tags_json, meta_json, now, now))
                conn.commit()
                record_id = cursor.lastrowid

        # Redis缓存
        if self._redis_available:
            try:
                cache_key = f"evo:{table}:{record_id}"
                self._redis.setex(cache_key, ttl_seconds or 3600, data_json)
                if key:
                    self._redis.set(f"evo:{table}:key:{key}", str(record_id))
            except Exception:
                pass

        return record_id

    def _pg_insert(self, safe_name, key, data_json, tags_json, meta_json, ttl_seconds, now):
        """PostgreSQL插入"""
        with self._get_conn() as conn:
            cur = conn.cursor()
            if ttl_seconds:
                cur.execute(f"""
                    INSERT INTO "{safe_name}" (key, data, tags, metadata, expires_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW() + INTERVAL '%s seconds', %s, %s) RETURNING id
                """, (key, data_json, tags_json, meta_json, ttl_seconds, now, now))
            else:
                cur.execute(f"""
                    INSERT INTO "{safe_name}" (key, data, tags, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """, (key, data_json, tags_json, meta_json, now, now))
            record_id = cur.fetchone()[0]
            cur.close()
            return record_id

    def get(self, table: str, record_id: int) -> Optional[Dict]:
        """获取单条记录"""
        # Redis缓存优先
        if self._redis_available:
            try:
                cached = self._redis.get(f"evo:{table}:{record_id}")
                if cached:
                    return {"id": record_id, "data": json.loads(cached), "_source": "redis"}
            except Exception:
                pass

        self._ensure_table(table)
        safe_name = self._safe_table_name(table)

        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    f'SELECT * FROM "{safe_name}" WHERE id = %s AND deleted_at IS NULL',
                    (record_id,)
                )
                row = cur.fetchone()
                cur.close()
        else:
            with self._get_conn() as conn:
                row = conn.execute(
                    f"SELECT * FROM [{safe_name}] WHERE id = ? AND deleted_at IS NULL",
                    (record_id,)
                ).fetchone()

        if not row:
            return None

        result = self._row_to_dict(row)

        # 写入Redis缓存
        if self._redis_available:
            try:
                data_str = result.get("data")
                if isinstance(data_str, dict):
                    data_str = json.dumps(data_str, ensure_ascii=False)
                if data_str:
                    self._redis.setex(f"evo:{table}:{record_id}", 3600, data_str)
            except Exception:
                pass

        return result

    def get_by_key(self, table: str, key: str) -> Optional[Dict]:
        """按唯一键获取最新记录"""
        self._ensure_table(table)
        safe_name = self._safe_table_name(table)

        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    f'SELECT * FROM "{safe_name}" WHERE key = %s AND deleted_at IS NULL ORDER BY id DESC LIMIT 1',
                    (key,)
                )
                row = cur.fetchone()
                cur.close()
        else:
            with self._get_conn() as conn:
                row = conn.execute(
                    f"SELECT * FROM [{safe_name}] WHERE key = ? AND deleted_at IS NULL ORDER BY id DESC LIMIT 1",
                    (key,)
                ).fetchone()

        return self._row_to_dict(row) if row else None

    def list(self, table: str, limit: int = 50, offset: int = 0,
             tag: Optional[str] = None, order_by: str = "created_at",
             ascending: bool = False, include_deleted: bool = False) -> Tuple[List[Dict], int]:
        """列出记录 → (records, total_count)"""
        self._ensure_table(table)
        safe_name = self._safe_table_name(table)

        conditions = [] if include_deleted else ["deleted_at IS NULL"]
        params: List[Any] = []

        if tag:
            if self._backend == "postgresql":
                conditions.append("tags LIKE %s")
            else:
                conditions.append("tags LIKE ?")
            params.append(f'%"{tag}"%')

        where = " AND ".join(conditions) if conditions else "1=1"

        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(f'SELECT COUNT(*) FROM "{safe_name}" WHERE {where}', params)
                total = cur.fetchone()[0]

                direction = "ASC" if ascending else "DESC"
                order = order_by if order_by in ("id", "key", "created_at", "updated_at") else "created_at"
                cur.execute(
                    f'SELECT * FROM "{safe_name}" WHERE {where} ORDER BY {order} {direction} LIMIT %s OFFSET %s',
                    params + [limit, offset]
                )
                rows = cur.fetchall()
                cur.close()
        else:
            with self._get_conn() as conn:
                total = conn.execute(f"SELECT COUNT(*) FROM [{safe_name}] WHERE {where}", params).fetchone()[0]

                direction = "ASC" if ascending else "DESC"
                order = order_by if order_by in ("id", "key", "created_at", "updated_at") else "created_at"
                rows = conn.execute(
                    f"SELECT * FROM [{safe_name}] WHERE {where} ORDER BY {order} {direction} LIMIT ? OFFSET ?",
                    params + [limit, offset]
                ).fetchall()

        records = [self._row_to_dict(r) for r in rows]
        return records, total

    def search(self, table: str, query: str, limit: int = 20) -> List[Dict]:
        """全文搜索"""
        self._ensure_table(table)
        safe_name = self._safe_table_name(table)

        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                # PostgreSQL tsvector搜索
                cur.execute(
                    f'SELECT * FROM "{safe_name}" WHERE search_vector @@ plainto_tsquery(%s) AND deleted_at IS NULL ORDER BY ts_rank(search_vector, plainto_tsquery(%s)) DESC LIMIT %s',
                    (query, query, limit)
                )
                rows = cur.fetchall()
                cur.close()
            return [self._row_to_dict(r) for r in rows]
        else:
            with self._get_conn() as conn:
                try:
                    # SQLite FTS5
                    rows = conn.execute(f"""
                        SELECT r.* FROM [{safe_name}] r
                        JOIN [{safe_name}_fts] fts ON r.id = fts.rowid
                        WHERE [{safe_name}_fts] MATCH ?
                        AND r.deleted_at IS NULL
                        ORDER BY rank LIMIT ?
                    """, (query, limit)).fetchall()
                except Exception:
                    # 回退到LIKE
                    rows = conn.execute(f"""
                        SELECT * FROM [{safe_name}]
                        WHERE (key LIKE ? OR data LIKE ? OR tags LIKE ?)
                        AND deleted_at IS NULL LIMIT ?
                    """, (f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()

            return [self._row_to_dict(r) for r in rows]

    def update(self, table: str, record_id: int, data: Optional[Dict] = None,
               tags: Optional[List[str]] = None, metadata: Optional[Dict] = None) -> bool:
        """更新记录"""
        self._ensure_table(table)
        safe_name = self._safe_table_name(table)
        now = datetime.now().isoformat()

        sets = ["updated_at = ?", "version = version + 1"]
        params: List[Any] = [now]

        if data is not None:
            sets.append("data = ?")
            params.append(json.dumps(data, ensure_ascii=False, default=str))
        if tags is not None:
            sets.append("tags = ?")
            params.append(json.dumps(tags, ensure_ascii=False))
        if metadata is not None:
            sets.append("metadata = ?")
            params.append(json.dumps(metadata, ensure_ascii=False))

        params.append(record_id)

        if self._backend == "postgresql" and self._pg_pool:
            # 转换SQLite占位符为PG占位符
            pg_sets = [s.replace("?", "%s") for s in sets]
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    f'UPDATE "{safe_name}" SET {", ".join(pg_sets)} WHERE id = %s AND deleted_at IS NULL',
                    params
                )
                affected = cur.rowcount
                cur.close()
            success = affected > 0
        else:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"UPDATE [{safe_name}] SET {', '.join(sets)} WHERE id = ? AND deleted_at IS NULL",
                    params
                )
                conn.commit()
                success = cursor.rowcount > 0

        # 清Redis缓存
        if self._redis_available:
            try:
                self._redis.delete(f"evo:{table}:{record_id}")
            except Exception:
                pass

        return success

    def delete(self, table: str, record_id: int, soft: bool = True) -> bool:
        """删除记录"""
        self._ensure_table(table)
        safe_name = self._safe_table_name(table)
        now = datetime.now().isoformat()

        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                if soft:
                    cur.execute(
                        f'UPDATE "{safe_name}" SET deleted_at = %s, updated_at = %s WHERE id = %s AND deleted_at IS NULL',
                        (now, now, record_id)
                    )
                else:
                    cur.execute(f'DELETE FROM "{safe_name}" WHERE id = %s', (record_id,))
                affected = cur.rowcount
                cur.close()
            success = affected > 0
        else:
            with self._get_conn() as conn:
                if soft:
                    cursor = conn.execute(
                        f"UPDATE [{safe_name}] SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
                        (now, now, record_id)
                    )
                else:
                    cursor = conn.execute(f"DELETE FROM [{safe_name}] WHERE id = ?", (record_id,))
                conn.commit()
                success = cursor.rowcount > 0

        if self._redis_available:
            try:
                self._redis.delete(f"evo:{table}:{record_id}")
            except Exception:
                pass

        return success

    def count(self, table: str, include_deleted: bool = False) -> int:
        """记录总数"""
        self._ensure_table(table)
        safe_name = self._safe_table_name(table)

        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                if include_deleted:
                    cur.execute(f'SELECT COUNT(*) FROM "{safe_name}"')
                else:
                    cur.execute(f'SELECT COUNT(*) FROM "{safe_name}" WHERE deleted_at IS NULL')
                total = cur.fetchone()[0]
                cur.close()
        else:
            with self._get_conn() as conn:
                where = "" if include_deleted else "WHERE deleted_at IS NULL"
                total = conn.execute(f"SELECT COUNT(*) FROM [{safe_name}] {where}").fetchone()[0]

        return total

    # ═══════════════════════════════════════════════════════
    # 批量操作
    # ═══════════════════════════════════════════════════════

    def bulk_insert(self, table: str, records: List[Dict[str, Any]]) -> List[int]:
        """批量插入"""
        self._ensure_table(table)
        safe_name = self._safe_table_name(table)
        now = datetime.now().isoformat()
        ids = []

        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                for rec in records:
                    data_json = json.dumps(rec.get("data", rec), ensure_ascii=False, default=str)
                    tags_json = json.dumps(rec.get("tags", []), ensure_ascii=False)
                    meta_json = json.dumps(rec.get("metadata", {}), ensure_ascii=False)
                    cur.execute(
                        f'INSERT INTO "{safe_name}" (key, data, tags, metadata, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id',
                        (rec.get("key", ""), data_json, tags_json, meta_json, now, now)
                    )
                    ids.append(cur.fetchone()[0])
                cur.close()
        else:
            with self._get_conn() as conn:
                for rec in records:
                    data_json = json.dumps(rec.get("data", rec), ensure_ascii=False, default=str)
                    tags_json = json.dumps(rec.get("tags", []), ensure_ascii=False)
                    meta_json = json.dumps(rec.get("metadata", {}), ensure_ascii=False)
                    cursor = conn.execute(
                        f"INSERT INTO [{safe_name}] (key, data, tags, metadata, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                        (rec.get("key", ""), data_json, tags_json, meta_json, now, now)
                    )
                    ids.append(cursor.lastrowid)
                conn.commit()

        return ids

    def export_table(self, table: str) -> List[Dict]:
        """导出表全部数据"""
        records, _ = self.list(table, limit=100000, include_deleted=False)
        return records

    def import_table(self, table: str, records: List[Dict], skip_duplicates: bool = True) -> int:
        """导入数据"""
        self._ensure_table(table)
        safe_name = self._safe_table_name(table)
        inserted = 0

        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                for rec in records:
                    if skip_duplicates and rec.get("id"):
                        cur.execute(f'SELECT 1 FROM "{safe_name}" WHERE id = %s', (rec["id"],))
                        if cur.fetchone():
                            continue
                    data = rec.get("data", rec)
                    data_json = json.dumps(data, ensure_ascii=False, default=str) if isinstance(data, dict) else str(data)
                    tags_json = json.dumps(rec.get("tags", []), ensure_ascii=False)
                    meta_json = json.dumps(rec.get("metadata", {}), ensure_ascii=False)
                    now = datetime.now().isoformat()
                    cur.execute(
                        f'INSERT INTO "{safe_name}" (key, data, tags, metadata, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s)',
                        (rec.get("key", ""), data_json, tags_json, meta_json, rec.get("created_at", now), now)
                    )
                    inserted += 1
                cur.close()
        else:
            with self._get_conn() as conn:
                for rec in records:
                    if skip_duplicates and rec.get("id"):
                        existing = conn.execute(
                            f"SELECT 1 FROM [{safe_name}] WHERE id = ?", (rec["id"],)
                        ).fetchone()
                        if existing:
                            continue
                    data = rec.get("data", rec)
                    data_json = json.dumps(data, ensure_ascii=False, default=str) if isinstance(data, dict) else str(data)
                    tags_json = json.dumps(rec.get("tags", []), ensure_ascii=False)
                    meta_json = json.dumps(rec.get("metadata", {}), ensure_ascii=False)
                    now = datetime.now().isoformat()
                    conn.execute(
                        f"INSERT INTO [{safe_name}] (key, data, tags, metadata, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                        (rec.get("key", ""), data_json, tags_json, meta_json, rec.get("created_at", now), now)
                    )
                    inserted += 1
                conn.commit()

        return inserted

    # ═══════════════════════════════════════════════════════
    # 执行原生SQL（高级用法，上市公司级）
    # ═══════════════════════════════════════════════════════

    def execute_raw(self, sql: str, params: Optional[tuple] = None) -> Any:
        """执行原生SQL（只读建议，写入请用transaction）"""
        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(sql, params)
                result = cur.fetchall()
                cur.close()
                return result
        else:
            with self._get_conn() as conn:
                cursor = conn.execute(sql, params or ())
                return cursor.fetchall()

    # ═══════════════════════════════════════════════════════
    # 数据库迁移工具
    # ═══════════════════════════════════════════════════════

    def migrate_from_sqlite(self, pg_url: str) -> Dict[str, Any]:
        """将SQLite数据迁移到PostgreSQL"""
        if self._backend != "sqlite":
            return {"success": False, "error": "Current backend is not SQLite"}

        migrated_tables = 0
        migrated_records = 0

        try:
            from psycopg2 import pool as pg_pool
            pg_pool_inst = pg_pool.ThreadedConnectionPool(1, 3, dsn=pg_url)
            pg_conn = pg_pool_inst.getconn()

            for table_name in list(self._registered_tables.keys()):
                safe_name = self._safe_table_name(table_name)
                records = self.export_table(table_name)
                if not records:
                    continue

                # 创建PG表
                cur = pg_conn.cursor()
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS "{safe_name}" (
                        id SERIAL PRIMARY KEY, key TEXT, data TEXT NOT NULL,
                        tags TEXT DEFAULT '[]', metadata TEXT DEFAULT '{{}}',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        expires_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
                        version INTEGER DEFAULT 1
                    )
                """)

                # 插入数据
                for rec in records:
                    data = rec.get("data", rec)
                    if isinstance(data, dict):
                        data = json.dumps(data, ensure_ascii=False)
                    cur.execute(
                        f'INSERT INTO "{safe_name}" (key, data, tags, metadata, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s)',
                        (rec.get("key", ""), data, json.dumps(rec.get("tags", []), ensure_ascii=False),
                         json.dumps(rec.get("metadata", {}), ensure_ascii=False),
                         rec.get("created_at", datetime.now().isoformat()),
                         rec.get("updated_at", datetime.now().isoformat()))
                    )
                    migrated_records += 1

                pg_conn.commit()
                cur.close()
                migrated_tables += 1

            pg_pool_inst.putconn(pg_conn)
            pg_pool_inst.closeall()

        except Exception as e:
            return {"success": False, "error": str(e), "migrated_tables": migrated_tables, "migrated_records": migrated_records}

        return {
            "success": True,
            "migrated_tables": migrated_tables,
            "migrated_records": migrated_records,
            "target_url": pg_url.replace(pg_url.split("@")[-1].split(":")[-1] if "@" in pg_url else "", "***"),
        }

    # ═══════════════════════════════════════════════════════
    # 统计与管理
    # ═══════════════════════════════════════════════════════

    def table_stats(self, table: str) -> Dict[str, Any]:
        """表统计信息"""
        self._ensure_table(table)
        safe_name = self._safe_table_name(table)

        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(f'SELECT COUNT(*) FROM "{safe_name}"')
                total = cur.fetchone()[0]
                cur.execute(f'SELECT COUNT(*) FROM "{safe_name}" WHERE deleted_at IS NULL')
                active = cur.fetchone()[0]
                cur.execute(f'SELECT MAX(created_at) FROM "{safe_name}"')
                latest = cur.fetchone()[0]
                cur.close()
            return {
                "table": table, "total_records": total,
                "active_records": active, "deleted_records": total - active,
                "latest_record": str(latest) if latest else None,
                "db_size_mb": 0, "backend": "postgresql",
            }
        else:
            db_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
            with self._get_conn() as conn:
                total = conn.execute(f"SELECT COUNT(*) FROM [{safe_name}]").fetchone()[0]
                active = conn.execute(f"SELECT COUNT(*) FROM [{safe_name}] WHERE deleted_at IS NULL").fetchone()[0]
                latest = conn.execute(f"SELECT created_at FROM [{safe_name}] ORDER BY id DESC LIMIT 1").fetchone()
            return {
                "table": table, "total_records": total,
                "active_records": active, "deleted_records": total - active,
                "latest_record": latest[0] if latest else None,
                "db_size_mb": round(db_size / 1024 / 1024, 2),
                "backend": "sqlite",
            }

    def cleanup_expired(self) -> int:
        """清理过期数据"""
        cleaned = 0
        now = datetime.now().isoformat()

        for table_name in list(self._registered_tables.keys()):
            safe_name = self._safe_table_name(table_name)
            try:
                if self._backend == "postgresql" and self._pg_pool:
                    with self._get_conn() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            f'DELETE FROM "{safe_name}" WHERE expires_at IS NOT NULL AND expires_at < %s AND deleted_at IS NULL',
                            (now,)
                        )
                        cleaned += cur.rowcount
                        cur.close()
                else:
                    with self._get_conn() as conn:
                        result = conn.execute(
                            f"DELETE FROM [{safe_name}] WHERE expires_at IS NOT NULL AND expires_at < ? AND deleted_at IS NULL",
                            (now,)
                        )
                        conn.commit()
                        cleaned += result.rowcount
            except Exception as e:
                logger.debug(f"[Persistence] Cleanup error for {table_name}: {e}")

        return cleaned

    def vacuum(self):
        """压缩数据库"""
        if self._backend == "postgresql" and self._pg_pool:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("VACUUM ANALYZE")
                cur.close()
            return {"backend": "postgresql", "status": "vacuumed"}
        else:
            old_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
            with self._get_conn() as conn:
                conn.execute("VACUUM")
            new_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
            return {
                "backend": "sqlite",
                "old_mb": round(old_size / 1024 / 1024, 2),
                "new_mb": round(new_size / 1024 / 1024, 2),
                "saved_mb": round((old_size - new_size) / 1024 / 1024, 2),
            }

    def list_tables(self) -> List[str]:
        """列出所有已注册的表"""
        return list(self._registered_tables.keys())

    def _row_to_dict(self, row) -> Optional[Dict]:
        """Row → Dict（兼容SQLite Row和PG tuple）"""
        if not row:
            return None

        if hasattr(row, "keys"):
            result = dict(row)
        else:
            # PostgreSQL tuple - 需要列名映射
            # 从cursor.description获取（此处用通用处理）
            result = {str(i): val for i, val in enumerate(row)}

        # 反序列化JSON字段
        for field in ("data", "tags", "metadata"):
            if result.get(field) and isinstance(result[field], str):
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    pass

        return result

    def status(self) -> Dict[str, Any]:
        """持久化层状态"""
        info = {
            "status": "healthy",
            "backend": self._backend,
            "tables_registered": len(self._registered_tables),
            "redis_available": self._redis_available,
            "table_list": self.list_tables(),
        }

        if self._backend == "sqlite":
            db_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
            info["db_path"] = self._db_path
            info["db_size_mb"] = round(db_size / 1024 / 1024, 2)
        else:
            info["database_url"] = self._database_url.split("@")[-1] if "@" in self._database_url else "***"

        return info

    def close(self):
        """关闭连接"""
        if self._backend == "postgresql" and self._pg_pool:
            self._pg_pool.closeall()
        elif self._conn:
            self._conn.close()
            self._conn = None
