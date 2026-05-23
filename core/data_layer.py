"""AUTO-EVO-AI V0.1 — 共享数据基础设施层

SQLite 抽象：线程安全连接池、Schema 迁移、JSON 序列化、自动建表、批量操作。
所有模块通过 DataEngine 接口存取数据，不再各自写 JSON 文件。
"""
import sqlite3, json, os, time, threading, logging, csv, io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager

logger = logging.getLogger("evo.data-engine")

DATA_DIR = Path(".evo_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Migration:
    """数据库迁移。"""
    def __init__(self, version: int, description: str, sql: str):
        self.version = version
        self.description = description
        self.sql = sql


class DataEngine:
    """线程安全的 SQLite 数据引擎。

    用法:
        db = DataEngine("my_module")
        db.create_table("users", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
        db.insert("users", {"name": "alice"})
        rows = db.fetch_all("SELECT * FROM users")
    """

    _instances: Dict[str, 'DataEngine'] = {}
    _lock = threading.Lock()
    _GLOBAL_MIGRATIONS: List[Migration] = []
    _CONNECTION_POOL: Dict[str, sqlite3.Connection] = {}

    @classmethod
    def register_migration(cls, version: int, description: str, sql: str):
        cls._GLOBAL_MIGRATIONS.append(Migration(version, description, sql))

    @classmethod
    def get(cls, name: str = "default") -> 'DataEngine':
        """获取或创建命名 DataEngine 实例（单例）。"""
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    cls._instances[name] = cls(name)
        return cls._instances[name]

    @classmethod
    def reset_all(cls):
        """重置所有连接（用于测试）。"""
        for name, conn in cls._CONNECTION_POOL.items():
            try:
                conn.close()
            except Exception:
                pass
        cls._CONNECTION_POOL.clear()
        cls._instances.clear()

    def __init__(self, name: str = "default"):
        self._name = name
        self._db_path = str(DATA_DIR / f"{name}.db")
        self._local = threading.local()
        self._init_engine()

    def _init_engine(self):
        """初始化数据库并运行迁移。"""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._run_migrations()
        logger.info("[DataEngine] %s 就绪: %s", self._name, self._db_path)

    @contextmanager
    def connect(self):
        """获取线程安全的数据库连接。"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield self._local.conn
        except Exception:
            self._local.conn.rollback()
            raise

    @contextmanager
    def transaction(self):
        """事务上下文管理器。"""
        with self.connect() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    # ---- Schema ----

    def create_table(self, table: str, columns: Dict[str, str], if_not_exists: bool = True) -> bool:
        """自动建表。columns: {"col_name": "TYPE CONSTRAINTS", ...}"""
        cols = ", ".join(f"{k} {v}" for k, v in columns.items())
        ie = "IF NOT EXISTS " if if_not_exists else ""
        sql = f"CREATE TABLE {ie}[{table}] ({cols})"
        try:
            with self.connect() as conn:
                conn.execute(sql)
                conn.commit()
            return True
        except Exception as e:
            logger.error("[DataEngine] create_table %s 失败: %s", table, e)
            return False

    def drop_table(self, table: str, if_exists: bool = True):
        ie = "IF EXISTS " if if_exists else ""
        with self.connect() as conn:
            conn.execute(f"DROP TABLE {ie}[{table}]")
            conn.commit()

    def table_exists(self, table: str) -> bool:
        row = self.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        return row is not None

    def table_info(self, table: str) -> List[Dict]:
        """返回表结构信息。"""
        return self.fetch_all(f"PRAGMA table_info([{table}])")

    def list_tables(self) -> List[str]:
        rows = self.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '_%' ORDER BY name")
        return [r["name"] for r in rows]

    # ---- CRUD ----

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.connect() as conn:
            return conn.execute(sql, params)

    def execute_many(self, sql: str, params_list: List[tuple]):
        with self.connect() as conn:
            conn.executemany(sql, params_list)
            conn.commit()

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict]:
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def insert(self, table: str, data: Dict) -> int:
        """插入一行并返回 lastrowid。"""
        cols = ", ".join(f"[{k}]" for k in data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO [{table}] ({cols}) VALUES ({placeholders})"
        with self.connect() as conn:
            cur = conn.execute(sql, tuple(data.values()))
            conn.commit()
            return cur.lastrowid

    def bulk_insert(self, table: str, rows: List[Dict]) -> int:
        """批量插入，返回插入行数。"""
        if not rows:
            return 0
        cols = ", ".join(f"[{k}]" for k in rows[0].keys())
        placeholders = ", ".join(["?"] * len(rows[0]))
        sql = f"INSERT INTO [{table}] ({cols}) VALUES ({placeholders})"
        params_list = [tuple(r.get(k) for k in rows[0].keys()) for r in rows]
        with self.connect() as conn:
            conn.executemany(sql, params_list)
            conn.commit()
            return len(rows)

    def upsert(self, table: str, data: Dict, conflict_col: str):
        """插入或更新。"""
        cols = ", ".join(f"[{k}]" for k in data.keys())
        placeholders = ", ".join(["?"] * len(data))
        updates = ", ".join(f"[{k}]=excluded.[{k}]" for k in data.keys())
        sql = f"INSERT INTO [{table}] ({cols}) VALUES ({placeholders}) ON CONFLICT([{conflict_col}]) DO UPDATE SET {updates}"
        with self.connect() as conn:
            cur = conn.execute(sql, tuple(data.values()))
            conn.commit()
            return cur.lastrowid

    def update(self, table: str, data: Dict, where: str, where_params: tuple = ()):
        sets = ", ".join(f"[{k}]=?" for k in data.keys())
        sql = f"UPDATE [{table}] SET {sets} WHERE {where}"
        with self.connect() as conn:
            conn.execute(sql, tuple(data.values()) + where_params)
            conn.commit()

    def delete(self, table: str, where: str, params: tuple = ()):
        sql = f"DELETE FROM [{table}] WHERE {where}"
        with self.connect() as conn:
            conn.execute(sql, params)
            conn.commit()

    def count(self, table: str, where: str = "1=1", params: tuple = ()) -> int:
        row = self.fetch_one(f"SELECT COUNT(*) as c FROM [{table}] WHERE {where}", params)
        return row["c"] if row else 0

    # ---- JSON 迁移 ----

    def import_json_file(self, path: Union[str, Path], table: str = None) -> Dict:
        """将 JSON 文件导入 SQLite 表。
        
        支持:
        - JSON 对象: {"key": value, ...} → 转为单行
        - JSON 数组: [{"k": "v"}, ...] → 每元素一行
        - JSON 字符串: 任意 JSON 结构
        
        返回: {"table": 表名, "rows": 行数, "source": 文件路径}
        """
        path = Path(path)
        if not path.exists():
            return {"error": f"文件不存在: {path}"}
        
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return {"error": f"JSON 解析失败: {e}"}
        
        # 确定表名
        tbl = table or path.stem.replace("-", "_").replace(".", "_")
        
        # 转换为行列表
        if isinstance(raw, dict):
            rows = [raw]
        elif isinstance(raw, list):
            rows = raw if all(isinstance(r, dict) for r in raw) else [{"value": json.dumps(raw, ensure_ascii=False)}]
        else:
            rows = [{"value": json.dumps(raw, ensure_ascii=False)}]
        
        # 收集所有字段
        all_keys = set()
        for r in rows:
            all_keys.update(r.keys())
        
        # 创建表
        columns = {k: "TEXT" for k in all_keys}
        if "id" in all_keys:
            columns["id"] = "TEXT PRIMARY KEY"
        elif all_keys:
            # 添加自增主键
            columns["_rowid"] = "INTEGER PRIMARY KEY AUTOINCREMENT"
        columns["_imported_at"] = "TEXT"
        
        # 添加时间戳
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        for r in rows:
            r["_imported_at"] = ts
        if "_rowid" in columns:
            for i, r in enumerate(rows):
                r["_rowid"] = i + 1
        all_keys.add("_imported_at")
        if "_rowid" in columns:
            all_keys.add("_rowid")
        
        # 清理不存在的列
        final_cols = {k: v for k, v in columns.items() if k in all_keys}
        
        if self.table_exists(tbl):
            self.drop_table(tbl)
        self.create_table(tbl, final_cols)
        
        # 批量插入
        inserted = self.bulk_insert(tbl, rows)
        
        return {
            "table": tbl,
            "rows": inserted,
            "columns": list(all_keys),
            "source": str(path),
            "size_bytes": path.stat().st_size
        }

    # ---- 搜索 / 工具 ----

    def search(self, table: str, query: str, fields: List[str] = None,
               limit: int = 20, offset: int = 0) -> Dict:
        """简单 LIKE 搜索。"""
        if not fields:
            info = self.table_info(table)
            fields = [c["name"] for c in info if c["type"].upper() in ("TEXT", "VARCHAR")]
        
        conditions = " OR ".join(f"[{f}] LIKE ?" for f in fields)
        params = tuple(f"%{query}%" for _ in fields)
        
        total = self.count(table, conditions, params)
        rows = self.fetch_all(
            f"SELECT * FROM [{table}] WHERE {conditions} LIMIT ? OFFSET ?",
            params + (limit, offset)
        )
        
        return {
            "table": table,
            "query": query,
            "total": total,
            "results": rows,
            "limit": limit,
            "offset": offset
        }

    def stats(self) -> Dict:
        """数据库统计信息。"""
        size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
        tables = self.fetch_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_info = []
        for t in tables:
            try:
                cnt = self.fetch_one(f"SELECT COUNT(*) as c FROM [{t['name']}]")
                table_info.append({"name": t["name"], "rows": cnt["c"] if cnt else 0})
            except Exception:
                table_info.append({"name": t["name"], "rows": -1})
        return {
            "name": self._name,
            "db_path": self._db_path,
            "size_bytes": size,
            "size_kb": round(size / 1024, 1),
            "tables": table_info,
            "total_tables": len(table_info),
        }

    def vacuum(self):
        """回收空间。"""
        with self.connect() as conn:
            conn.execute("VACUUM")

    def backup_to(self, target_path: str):
        """备份数据库到指定路径。"""
        import shutil
        with self.connect() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        shutil.copy2(self._db_path, target_path)
        return {"backup": target_path, "size": os.path.getsize(target_path)}

    # ---- 迁移系统 ----

    def _run_migrations(self):
        """运行未执行过的迁移。"""
        if not self._GLOBAL_MIGRATIONS:
            return
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _migrations (version INTEGER PRIMARY KEY, description TEXT, applied_at TEXT)"
            )
            conn.commit()
        applied = {r["version"] for r in self.fetch_all("SELECT version FROM _migrations")}
        for m in sorted(self._GLOBAL_MIGRATIONS, key=lambda x: x.version):
            if m.version in applied:
                continue
            logger.info("[DataEngine] 迁移 v%d: %s", m.version, m.description)
            with self.connect() as conn:
                conn.executescript(m.sql)
                conn.execute(
                    "INSERT INTO _migrations (version, description, applied_at) VALUES (?, ?, ?)",
                    (m.version, m.description, time.strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()


class JSONStore:
    """兼容旧 JSON 文件接口的数据引擎封装。

    用法:
        store = JSONStore("my_data")
        store.save({"key": "value"})
        store.load()
    """

    def __init__(self, name: str, default: Any = None):
        self._name = name
        self._default = default or {}
        self._db = DataEngine.get(name)
        self._ensure_table()

    def _ensure_table(self):
        if not self._db.table_exists("kvstore"):
            self._db.create_table("kvstore", {
                "key": "TEXT PRIMARY KEY",
                "value": "TEXT",
                "updated_at": "TEXT"
            })

    def save(self, key: str = "default", value: Any = None):
        val = value if value is not None else self._default
        self._db.upsert("kvstore", {
            "key": key,
            "value": json.dumps(val, ensure_ascii=False),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }, "key")

    def load(self, key: str = "default") -> Any:
        row = self._db.fetch_one("SELECT value FROM kvstore WHERE key=?", (key,))
        if row:
            return json.loads(row["value"])
        return self._default

    def delete(self, key: str = "default"):
        self._db.delete("kvstore", "key=?", (key,))

    def keys(self) -> List[str]:
        rows = self._db.fetch_all("SELECT key FROM kvstore")
        return [r["key"] for r in rows]

    def stats(self) -> Dict:
        return self._db.stats()


class AutoMigrator:
    """自动扫描将 JSON 数据文件迁移到 SQLite。

    扫描 .evo_data/ 目录及指定路径下所有 .json 文件，
    自动导入到对应命名的 SQLite 表中。
    """

    def __init__(self, db: DataEngine = None):
        self._db = db or DataEngine.get("evo_system")
        self._results = []

    def scan_and_migrate(self, paths: List[Union[str, Path]] = None) -> Dict:
        """扫描并迁移所有 JSON 文件到 SQLite。

        Args:
            paths: 要扫描的目录/文件列表。None 时默认扫描 .evo_data/

        Returns: 迁移报告
        """
        targets = paths or [DATA_DIR]
        json_files = []
        
        for p in targets:
            p = Path(p)
            if p.is_file() and p.suffix == ".json":
                json_files.append(p)
            elif p.is_dir():
                json_files.extend(p.rglob("*.json"))
        
        # 排除数据库备份目录
        json_files = [f for f in json_files if "backup" not in str(f)]
        
        results = []
        total_rows = 0
        for jf in sorted(json_files):
            # 跳过 > 10MB 的大文件
            if jf.stat().st_size > 10 * 1024 * 1024:
                results.append({"file": str(jf), "skipped": True, "reason": "文件过大"})
                continue
            
            # 使用 JSONStore 的 db 名称
            table_name = jf.stem.replace("-", "_").replace(".", "_")
            r = self._db.import_json_file(jf, table_name)
            results.append(r)
            if "rows" in r:
                total_rows += r["rows"]
        
        self._results = results
        return {
            "total_files": len(json_files),
            "total_rows_imported": total_rows,
            "results": results
        }

    def report(self) -> str:
        """生成迁移报告文本。"""
        if not self._results:
            return "未执行迁移"
        lines = ["=== 数据迁移报告 ==="]
        total_rows = 0
        for r in self._results:
            if "error" in r:
                lines.append(f"  ❌ {r.get('source', '?')}: {r['error']}")
            elif r.get("skipped"):
                lines.append(f"  ⏭️ {r['file']}: 跳过 ({r['reason']})")
            else:
                lines.append(f"  ✅ {r['source']} → [{r['table']}]  {r['rows']} 行")
                total_rows += r["rows"]
        lines.append(f"总计: {total_rows} 行数据已迁移")
        return "\n".join(lines)
