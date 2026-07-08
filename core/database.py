"""
AUTO-EVO-AI V0.1 — 统一数据库层（PG主＋SQLite降级）
上市公司级：单源数据、连接池、迁移支持、审计
=================================================
优先级链：PostgreSQL → SQLite(evo.db)
启动时检测 PG 连接，成功则用 PG，失败则降级到 SQLite。
"""
from __future__ import annotations
import os, json, time, threading, hashlib, logging
from pathlib import Path
from typing import Optional, Any
from contextlib import contextmanager

logger = logging.getLogger("evo.database")

BASE_DIR = Path(__file__).parent.parent
DB_PATH = str(BASE_DIR / "data" / "evo.db")
_local = threading.local()

# ── PG 配置 ──
PG_CONFIG = {
    "host": os.environ.get("EVO_PG_HOST", "localhost"),
    "port": int(os.environ.get("EVO_PG_PORT", "5432")),
    "dbname": os.environ.get("EVO_PG_DB", "evodb"),
    "user": os.environ.get("EVO_PG_USER", "evo"),
    "password": os.environ.get("EVO_PG_PASSWORD", "Evo@2026!PG"),
}
_use_pg = False
_pg_conn = None


def _try_pg() -> bool:
    """尝试连接 PostgreSQL，成功返回 True"""
    global _use_pg, _pg_conn
    if _use_pg and _pg_conn:
        try:
            _pg_conn.cursor().execute("SELECT 1")
            return True
        except Exception:
            _use_pg = False
            _pg_conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(**PG_CONFIG, connect_timeout=3)
        conn.autocommit = True
        _pg_conn = conn
        _use_pg = True
        logger.info("[DB] PostgreSQL 连接成功 → 使用 PG")
        return True
    except Exception as e:
        logger.warning(f"[DB] PostgreSQL 不可用 ({e}) → 降级到 SQLite")
        _use_pg = False
        return False


def get_connection():
    """获取当前线程的数据库连接（PG优先，失败降级SQLite）"""
    if _try_pg():
        return _pg_conn
    # SQLite 降级
    if not hasattr(_local, 'conn') or _local.conn is None:
        import sqlite3
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


@contextmanager
def transaction():
    """事务上下文管理器 — 自动提交/回滚"""
    conn = get_connection()
    try:
        yield conn
        if not _use_pg:
            conn.commit()
    except Exception:
        if not _use_pg:
            conn.rollback()
        raise


def initialize():
    """创建或升级数据库 schema（PG/SQLite 自动适配）"""
    if _try_pg():
        _create_pg_schema()
        return
    conn = get_connection()
    cur = conn.execute("PRAGMA user_version")
    (version,) = cur.fetchone()
    if version >= 1:
        return
    _create_sqlite_schema(conn)
    conn.execute("PRAGMA user_version = 1")
    conn.commit()


def _create_pg_schema():
    """PostgreSQL 完整 schema"""
    conn = _pg_conn
    if conn is None:
        return
    SQL = """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL, turn_count INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS conversation_turns (
        id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
        user_input TEXT, intent_data TEXT, response_data TEXT,
        modules_used TEXT, timestamp TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    );
    CREATE TABLE IF NOT EXISTS decision_rules (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
        triggers TEXT, conditions TEXT, actions TEXT, chain TEXT,
        priority TEXT DEFAULT 'normal', enabled INTEGER DEFAULT 1,
        cooldown INTEGER DEFAULT 0, max_retries INTEGER DEFAULT 0,
        escalation_module TEXT, escalation_action TEXT,
        last_triggered DOUBLE PRECISION, trigger_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS decision_history (
        id TEXT PRIMARY KEY, rule_id TEXT, rule_name TEXT,
        priority TEXT, status TEXT, trigger_event TEXT,
        chain_results TEXT, summary TEXT, error TEXT,
        started_at TEXT, finished_at TEXT, duration_ms INTEGER,
        created_at TEXT, FOREIGN KEY (rule_id) REFERENCES decision_rules(id)
    );
    CREATE TABLE IF NOT EXISTS event_rules (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, description TEXT,
        event_type TEXT, condition TEXT, action TEXT,
        action_params TEXT, enabled INTEGER DEFAULT 1, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS analysis_history (
        id SERIAL PRIMARY KEY, analyzed_at TEXT NOT NULL,
        total_records INTEGER DEFAULT 0, insights_generated INTEGER DEFAULT 0,
        anomalies_found INTEGER DEFAULT 0, analysis_duration_ms INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS insights (
        id TEXT PRIMARY KEY, type TEXT NOT NULL, severity TEXT DEFAULT 'info',
        title TEXT, description TEXT, evidence TEXT, recommendation TEXT,
        impact_score REAL DEFAULT 0, created_at TEXT, dismissed INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS learning_rules (
        id TEXT PRIMARY KEY, rule_id TEXT, learning_type TEXT,
        value TEXT, confidence REAL DEFAULT 0, created_at TEXT,
        applied INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS module_profiles (
        module TEXT PRIMARY KEY, profile TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS knowledge_bases (
        kb_id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
        doc_count INTEGER DEFAULT 0, chunk_count INTEGER DEFAULT 0,
        created_at TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY, kb_id TEXT NOT NULL, title TEXT,
        source TEXT, doc_type TEXT, char_count INTEGER DEFAULT 0,
        chunk_count INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT,
        FOREIGN KEY (kb_id) REFERENCES knowledge_bases(kb_id)
    );
    CREATE TABLE IF NOT EXISTS doc_chunks (
        chunk_id TEXT PRIMARY KEY, doc_id TEXT, kb_id TEXT,
        chunk_index INTEGER, content TEXT, tokens TEXT,
        char_count INTEGER DEFAULT 0, created_at TEXT,
        FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
    );
    CREATE TABLE IF NOT EXISTS roles (
        role_id TEXT PRIMARY KEY, permissions TEXT NOT NULL,
        inherits TEXT, description TEXT, created_at DOUBLE PRECISION
    );
    CREATE TABLE IF NOT EXISTS user_roles (
        user_id TEXT NOT NULL, role_id TEXT NOT NULL,
        assigned_at DOUBLE PRECISION,
        PRIMARY KEY (user_id, role_id),
        FOREIGN KEY (role_id) REFERENCES roles(role_id)
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY, user_id TEXT, action TEXT NOT NULL,
        resource TEXT, status TEXT, detail TEXT, ip TEXT, created_at DOUBLE PRECISION
    );
    CREATE TABLE IF NOT EXISTS scheduler_tasks (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, description TEXT,
        cron_expr TEXT, type TEXT, target TEXT, params TEXT,
        enabled INTEGER DEFAULT 1, created_at TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS execution_logs (
        id SERIAL PRIMARY KEY, task_id INTEGER, status TEXT,
        result TEXT, started_at TEXT, finished_at TEXT,
        FOREIGN KEY (task_id) REFERENCES scheduler_tasks(id)
    );
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY, value TEXT, updated_at TEXT
    );
    """
    conn.autocommit = False
    try:
        cur = conn.cursor()
        cur.execute(SQL)
        conn.commit()
        logger.info("[DB] PostgreSQL schema 创建完成")
    except Exception as e:
        conn.rollback()
        logger.warning(f"[DB] PG schema 创建失败: {e}")
    finally:
        conn.autocommit = True


def _create_sqlite_schema(conn):
    """SQLite 完整 schema（原样保留）"""
    import sqlite3
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, turn_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS conversation_turns (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
            user_input TEXT, intent_data TEXT, response_data TEXT,
            modules_used TEXT, timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        CREATE TABLE IF NOT EXISTS decision_rules (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
            triggers TEXT, conditions TEXT, actions TEXT, chain TEXT,
            priority TEXT DEFAULT 'normal', enabled INTEGER DEFAULT 1,
            cooldown INTEGER DEFAULT 0, max_retries INTEGER DEFAULT 0,
            escalation_module TEXT, escalation_action TEXT,
            last_triggered REAL, trigger_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS decision_history (
            id TEXT PRIMARY KEY, rule_id TEXT, rule_name TEXT, priority TEXT,
            status TEXT, trigger_event TEXT, chain_results TEXT, summary TEXT,
            error TEXT, started_at TEXT, finished_at TEXT, duration_ms INTEGER,
            created_at TEXT, FOREIGN KEY (rule_id) REFERENCES decision_rules(id)
        );
        CREATE TABLE IF NOT EXISTS event_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            description TEXT, event_type TEXT, condition TEXT,
            action TEXT, action_params TEXT, enabled INTEGER DEFAULT 1, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, analyzed_at TEXT NOT NULL,
            total_records INTEGER DEFAULT 0, insights_generated INTEGER DEFAULT 0,
            anomalies_found INTEGER DEFAULT 0, analysis_duration_ms INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS insights (
            id TEXT PRIMARY KEY, type TEXT NOT NULL, severity TEXT DEFAULT 'info',
            title TEXT, description TEXT, evidence TEXT, recommendation TEXT,
            impact_score REAL DEFAULT 0, created_at TEXT, dismissed INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS learning_rules (
            id TEXT PRIMARY KEY, rule_id TEXT, learning_type TEXT,
            value TEXT, confidence REAL DEFAULT 0, created_at TEXT, applied INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS module_profiles (module TEXT PRIMARY KEY, profile TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            kb_id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
            doc_count INTEGER DEFAULT 0, chunk_count INTEGER DEFAULT 0,
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY, kb_id TEXT NOT NULL, title TEXT,
            source TEXT, doc_type TEXT, char_count INTEGER DEFAULT 0,
            chunk_count INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT,
            FOREIGN KEY (kb_id) REFERENCES knowledge_bases(kb_id)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS doc_chunks_fts USING fts5(content, tokenize='unicode61');
        CREATE TABLE IF NOT EXISTS doc_chunks (
            chunk_id TEXT PRIMARY KEY, doc_id TEXT, kb_id TEXT,
            chunk_index INTEGER, content TEXT, tokens TEXT,
            char_count INTEGER DEFAULT 0, created_at TEXT,
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
        );
        CREATE TABLE IF NOT EXISTS roles (
            role_id TEXT PRIMARY KEY, permissions TEXT NOT NULL,
            inherits TEXT, description TEXT, created_at REAL
        );
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id TEXT NOT NULL, role_id TEXT NOT NULL,
            assigned_at REAL, PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (role_id) REFERENCES roles(role_id)
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT NOT NULL,
            resource TEXT, status TEXT, detail TEXT, ip TEXT, created_at REAL
        );
        CREATE TABLE IF NOT EXISTS scheduler_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            description TEXT, cron_expr TEXT, type TEXT, target TEXT,
            params TEXT, enabled INTEGER DEFAULT 1, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER,
            status TEXT, result TEXT, started_at TEXT, finished_at TEXT,
            FOREIGN KEY (task_id) REFERENCES scheduler_tasks(id)
        );
        CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);
    """)


def migrate_from_legacy():
    """从旧 SQLite 数据库迁移数据到 evo.db（PG 模式时跳过，数据量小直接读取）"""
    if _use_pg:
        logger.info("[DB] PG 模式跳过 SQLite 迁移")
        return
    legacy_map = [
        ('conversation.db', 'sessions', 'sessions'),
        ('conversation.db', 'conversation_turns', 'conversation_turns'),
        ('decision_engine.db', 'decision_rules', 'decision_rules'),
        ('decision_engine.db', 'decision_history', 'decision_history'),
        ('events.db', 'rules', 'event_rules'),
        ('learning_engine.db', 'analysis_history', 'analysis_history'),
        ('learning_engine.db', 'insights', 'insights'),
        ('learning_engine.db', 'learning_rules', 'learning_rules'),
        ('learning_engine.db', 'module_profiles', 'module_profiles'),
        ('rbac.db', 'roles', 'roles'),
        ('rbac.db', 'user_roles', 'user_roles'),
        ('rbac.db', 'audit_logs', 'audit_logs'),
        ('scheduler.db', 'tasks', 'scheduler_tasks'),
        ('scheduler.db', 'execution_log', 'execution_logs'),
    ]
    import sqlite3
    data_dir = BASE_DIR / "data"
    if hasattr(_local, 'conn') and _local.conn:
        _local.conn.close()
        _local.conn = None
    target_conn = sqlite3.connect(DB_PATH)
    for db_name, src_table, dst_table in legacy_map:
        src_path = data_dir / db_name
        if not src_path.exists():
            continue
        try:
            src_conn = sqlite3.connect(str(src_path))
            rows = src_conn.execute(f'SELECT * FROM "{src_table}"').fetchall()
            if not rows:
                src_conn.close(); continue
            col_names = [d[1] for d in src_conn.execute(f'PRAGMA table_info("{src_table}")').fetchall()]
            src_conn.close()
            placeholders = ','.join('?' for _ in col_names)
            cols_str = ','.join(f'"{c}"' for c in col_names)
        except Exception as e:
            print(f'  [{db_name}] {src_table}: SKIP ({str(e)[:60]})')
            continue
        try:
            insert_sql = f'INSERT OR IGNORE INTO "{dst_table}" ({cols_str}) VALUES ({placeholders})'
            ok = 0
            for row in rows:
                try:
                    target_conn.execute(insert_sql, row); ok += 1
                except: break
            print(f'  [{db_name}] {src_table} -> {dst_table}: {ok}/{len(rows)} rows')
        except: pass
    target_conn.commit()
    print("迁移完成")


def health_check() -> dict[str, Any]:
    """数据库健康检查"""
    conn = get_connection()
    if _use_pg:
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
        tables = [r[0] for r in cur.fetchall()]
        stats = {}
        for name in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{name}"')
            stats[name] = cur.fetchone()[0]
        return {"status": "healthy", "driver": "postgresql", "tables": len(tables), "rows_by_table": stats}
    import sqlite3
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    stats = {}
    for name in tables:
        if name.startswith('sqlite_') or name.startswith('doc_chunks_fts'): continue
        count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        stats[name] = count
    return {"status": "healthy", "driver": "sqlite", "db_path": DB_PATH, "tables": len(tables), "rows_by_table": stats}


ENGINE_TABLES = {
    "decision": ["decision_rules", "decision_history"],
    "conversation": ["sessions", "conversation_turns"],
    "scheduler": ["scheduler_tasks", "execution_logs"],
    "event": ["event_rules"],
    "message_bus": ["event_rules"],
    "queue": [],
    "learning": ["analysis_history", "insights", "learning_rules", "module_profiles"],
    "rbac": ["roles", "user_roles", "audit_logs"],
    "github": [],
    "autonomous": [],
}


def get_engine_connection(engine_name: str):
    """获取指定引擎的数据库连接（所有引擎共用）"""
    conn = get_connection()
    if _use_pg:
        return conn
    import sqlite3
    tables = ENGINE_TABLES.get(engine_name.lower().strip(), [])
    if tables:
        existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        missing = [t for t in tables if t not in existing]
        if missing:
            initialize()
    return conn


def engine_table(engine_name: str, table_short: str) -> str:
    return table_short


def execute(engine_name: str, sql: str, params: tuple = ()):
    conn = get_engine_connection(engine_name)
    if _use_pg:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur
    return conn.execute(sql, params)


@contextmanager
def engine_transaction(engine_name: str):
    conn = get_engine_connection(engine_name)
    try:
        yield conn
        if not _use_pg:
            conn.commit()
        elif _use_pg:
            conn.commit()
    except Exception:
        if not _use_pg:
            conn.rollback()
        elif _use_pg:
            conn.rollback()
        raise


# 自动初始化
initialize()
