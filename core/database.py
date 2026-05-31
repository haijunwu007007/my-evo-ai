"""
AUTO-EVO-AI V0.1 — 统一数据库层
上市公司级：单源数据、连接池、迁移支持、审计

所有模块通过此模块访问数据库，统一指向 data/evo.db
旧数据库文件保留以兼容旧代码，新代码应使用此模块。
"""

import sqlite3, os, json, time, threading, hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from contextlib import contextmanager

BASE_DIR = Path(__file__).parent.parent
DB_PATH = str(BASE_DIR / "data" / "evo.db")
SCHEMA_VERSION = 1

# 线程本地连接（避免多线程冲突）
_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """获取当前线程的数据库连接"""
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


@contextmanager
def transaction() -> Any:
    """事务上下文管理器 — 自动提交/回滚"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def initialize() -> sqlite3.Connection:
    """创建或升级数据库 schema"""
    conn = get_connection()
    cur = conn.execute("PRAGMA user_version")
    (version,) = cur.fetchone()

    if version >= SCHEMA_VERSION:
        return

    _create_schema(conn)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


def _create_schema(conn: sqlite3.Connection):
    """创建统一 schema"""

    # ── 会话管理 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            turn_count INTEGER DEFAULT 0
        )
    """)

    # ── 对话记录 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_turns (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_input TEXT,
            intent_data TEXT,
            response_data TEXT,
            modules_used TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """)

    # ── 决策规则 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decision_rules (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            triggers TEXT,
            conditions TEXT,
            actions TEXT,
            chain TEXT,
            priority TEXT DEFAULT 'normal',
            enabled INTEGER DEFAULT 1,
            cooldown INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 0,
            escalation_module TEXT,
            escalation_action TEXT,
            last_triggered REAL,
            trigger_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # ── 决策历史 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decision_history (
            id TEXT PRIMARY KEY,
            rule_id TEXT,
            rule_name TEXT,
            priority TEXT,
            status TEXT,
            trigger_event TEXT,
            chain_results TEXT,
            summary TEXT,
            error TEXT,
            started_at TEXT,
            finished_at TEXT,
            duration_ms INTEGER,
            created_at TEXT,
            FOREIGN KEY (rule_id) REFERENCES decision_rules(id)
        )
    """)

    # ── 事件规则 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS event_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            event_type TEXT,
            condition TEXT,
            action TEXT,
            action_params TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ── 学习分析历史 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analyzed_at TEXT NOT NULL,
            total_records INTEGER DEFAULT 0,
            insights_generated INTEGER DEFAULT 0,
            anomalies_found INTEGER DEFAULT 0,
            analysis_duration_ms INTEGER DEFAULT 0
        )
    """)

    # ── 学习洞察 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            severity TEXT DEFAULT 'info',
            title TEXT,
            description TEXT,
            evidence TEXT,
            recommendation TEXT,
            impact_score REAL DEFAULT 0,
            created_at TEXT,
            dismissed INTEGER DEFAULT 0
        )
    """)

    # ── 学习规则 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_rules (
            id TEXT PRIMARY KEY,
            rule_id TEXT,
            learning_type TEXT,
            value TEXT,
            confidence REAL DEFAULT 0,
            created_at TEXT,
            applied INTEGER DEFAULT 0
        )
    """)

    # ── 模块画像 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS module_profiles (
            module TEXT PRIMARY KEY,
            profile TEXT,
            updated_at TEXT
        )
    """)

    # ── 知识库 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            kb_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            doc_count INTEGER DEFAULT 0,
            chunk_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # ── 文档 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            kb_id TEXT NOT NULL,
            title TEXT,
            source TEXT,
            doc_type TEXT,
            char_count INTEGER DEFAULT 0,
            chunk_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (kb_id) REFERENCES knowledge_bases(kb_id)
        )
    """)

    # ── 文档切片(FTS) ──
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS doc_chunks_fts USING fts5(
            content, tokenize='unicode61'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS doc_chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT,
            kb_id TEXT,
            chunk_index INTEGER,
            content TEXT,
            tokens TEXT,
            char_count INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
        )
    """)

    # ── RBAC 角色 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            role_id TEXT PRIMARY KEY,
            permissions TEXT NOT NULL,
            inherits TEXT,
            description TEXT,
            created_at REAL
        )
    """)

    # ── 用户角色分配 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id TEXT NOT NULL,
            role_id TEXT NOT NULL,
            assigned_at REAL,
            PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (role_id) REFERENCES roles(role_id)
        )
    """)

    # ── 审计日志 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            status TEXT,
            detail TEXT,
            ip TEXT,
            created_at REAL
        )
    """)

    # ── 调度任务 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            cron_expr TEXT,
            type TEXT,
            target TEXT,
            params TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # ── 调度执行日志 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            status TEXT,
            result TEXT,
            started_at TEXT,
            finished_at TEXT,
            FOREIGN KEY (task_id) REFERENCES scheduler_tasks(id)
        )
    """)

    # ── 系统配置 ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)


def migrate_from_legacy():
    """
    从旧数据库迁移数据到 evo.db
    保留旧文件，只复制数据。
    """
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

    data_dir = BASE_DIR / "data"
    # 关闭已有连接后开新连接（WAL锁问题）
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
                src_conn.close()
                continue
            col_names = [d[1] for d in src_conn.execute(f'PRAGMA table_info("{src_table}")').fetchall()]
            src_conn.close()
            placeholders = ','.join('?' for _ in col_names)
            cols_str = ','.join(f'"{c}"' for c in col_names)
        except Exception as e:
            print(f'  [{db_name}] {src_table}: READ FAIL: {str(e)[:120]}')
            continue

        try:
            insert_sql = f'INSERT OR IGNORE INTO "{dst_table}" ({cols_str}) VALUES ({placeholders})'
            ok = 0
            for row in rows:
                try:
                    target_conn.execute(insert_sql, row)
                    ok += 1
                except Exception as e2:
                    if ok == 0:
                        print(f'  [{db_name}] {src_table}: first row FAIL: {str(e2)[:100]}')
                    break
            print(f'  [{db_name}] {src_table} -> {dst_table}: {ok}/{len(rows)} rows')
        except Exception as e:
            print(f'  [{db_name}] {src_table} -> {dst_table}: FAIL: {str(e)[:120]}')

    try:
        target_conn.commit()
    except Exception as e:
        print(f'  COMMIT FAIL: {e}')
    print('\n迁移完成')

    target_conn.commit()
    print("\n迁移完成")


def health_check() -> dict[str, Any]:
    """数据库健康检查"""
    conn = get_connection()
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    stats = {}
    for name in tables:
        if name.startswith('sqlite_') or name.startswith('doc_chunks_fts'):
            continue
        count = conn.execute(f"SELECT COUNT(*) FROM \"{name}\"").fetchone()[0]
        stats[name] = count
    return {
        "status": "healthy",
        "db_path": DB_PATH,
        "tables": len(tables),
        "rows_by_table": stats,
    }


# ── 引擎数据库路由 ──
# 每个核心引擎使用 evo.db 中的独立表，通过前缀隔离
ENGINE_TABLES = {
    "decision": ["decision_rules", "decision_history"],
    "conversation": ["sessions", "conversation_turns"],
    "scheduler": ["scheduler_tasks", "execution_logs"],
    "event": ["event_rules"],
    "message_bus": ["event_rules"],  # 共享 event 表
    "queue": [],      # 队列数据暂存内存
    "learning": ["analysis_history", "insights", "learning_rules", "module_profiles"],
    "rbac": ["roles", "user_roles", "audit_logs"],
    "github": [],     # GitHub Scanner 使用独立缓存
    "autonomous": [], # Auto Agent 使用内存
}


def get_engine_connection(engine_name: str) -> sqlite3.Connection:
    """
    获取指定引擎的统一数据库连接。
    所有引擎共用 evo.db，通过表名隔离。
    """
    engine_name = engine_name.lower().strip()
    conn = get_connection()

    # 确保引擎所需表已存在
    tables = ENGINE_TABLES.get(engine_name, [])
    if tables:
        existing = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        missing = [t for t in tables if t not in existing]
        if missing:
            # 触发全量 schema 创建
            initialize()
    return conn


def engine_table(engine_name: str, table_short: str) -> str:
    """返回引擎表全名（当前直接用统一表名）"""
    return table_short


def execute(
    engine_name: str,
    sql: str,
    params: tuple = (),
) -> sqlite3.Cursor:
    """便捷方法：在指定引擎的数据库上执行 SQL"""
    conn = get_engine_connection(engine_name)
    return conn.execute(sql, params)


@contextmanager
def engine_transaction(engine_name: str):
    """引擎级事务"""
    conn = get_engine_connection(engine_name)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# 自动初始化
initialize()
