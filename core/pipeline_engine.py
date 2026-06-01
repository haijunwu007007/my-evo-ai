"""
管线引擎 — 模块自动串联执行 + 失败回滚 + SQLite 持久化
A.execute() -> B.execute() -> C.execute()

修复：
- 删除硬编码路径 D:/AUTO-EVO-AI-V0.1.modules.{name}（兼容任意部署路径）
- 新增 PipelineStore SQLite 持久化（与 scheduler_engine 一致）
- 自动重连：启动时从 SQLite 恢复历史
"""
import traceback, sqlite3
from core.logging_config import get_logger
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = get_logger(__name__)


class PipelineStore:
    """管线持久化（SQLite，与 scheduler_engine 的 ScheduleStore 一致）"""

    def __init__(self, data_dir: str = ".evo_data/pipeline") -> None:
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "pipeline.db"
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id TEXT PRIMARY KEY,
                    chain TEXT NOT NULL,
                    steps INTEGER DEFAULT 0,
                    completed INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    success INTEGER DEFAULT 0,
                    error TEXT DEFAULT '',
                    final_params TEXT DEFAULT '{}',
                    results TEXT DEFAULT '[]',
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                );
                CREATE INDEX IF NOT EXISTS idx_runs_created ON pipeline_runs(created_at);

                CREATE TABLE IF NOT EXISTS pipeline_definitions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    chain TEXT NOT NULL,
                    initial_params TEXT DEFAULT '{}',
                    tags TEXT DEFAULT '[]',
                    version INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'active',
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime'))
                );
                CREATE INDEX IF NOT EXISTS idx_defs_status ON pipeline_definitions(status);
            """)
            conn.commit()
        finally:
            conn.close()

    # ── 运行记录 ──

    def save_run(self, record: dict) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO pipeline_runs
                (id, chain, steps, completed, failed, success, error, final_params, results)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("id", ""),
                json.dumps(record.get("chain", []), ensure_ascii=False),
                record.get("steps", 0),
                record.get("completed", 0),
                record.get("failed", 0),
                1 if record.get("success") else 0,
                record.get("error", "") or "",
                json.dumps(record.get("final_params", {}), ensure_ascii=False),
                json.dumps(record.get("results", []), ensure_ascii=False),
            ))
            conn.commit()
        finally:
            conn.close()

    def get_recent_runs(self, limit: int = 10) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM pipeline_runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_run(r) for r in rows]
        finally:
            conn.close()

    def get_run(self, run_id: str) -> dict | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)
            ).fetchone()
            return self._row_to_run(row) if row else None
        finally:
            conn.close()

    def get_stats(self) -> dict:
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) as c FROM pipeline_runs").fetchone()["c"]
            success = conn.execute("SELECT COUNT(*) as c FROM pipeline_runs WHERE success=1").fetchone()["c"]
            failed = total - success
            steps_row = conn.execute("SELECT COALESCE(SUM(steps),0) as s FROM pipeline_runs").fetchone()
            total_steps = steps_row["s"] if steps_row else 0
            return {
                "total_pipelines": total,
                "success": success,
                "failed": failed,
                "total_steps": total_steps,
                "avg_steps": round(total_steps / total, 1) if total else 0,
            }
        finally:
            conn.close()

    def delete_run(self, run_id: str) -> bool:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM pipeline_runs WHERE id = ?", (run_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ── 管线定义 ──

    def save_definition(self, definition: dict) -> None:
        conn = self._get_conn()
        try:
            existing = conn.execute(
                "SELECT version FROM pipeline_definitions WHERE id = ?",
                (definition.get("id", ""),)
            ).fetchone()
            version = (existing["version"] + 1) if existing else 1
            conn.execute("""
                INSERT OR REPLACE INTO pipeline_definitions
                (id, name, description, chain, initial_params, tags, version, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            """, (
                definition.get("id", ""),
                definition.get("name", ""),
                definition.get("description", ""),
                json.dumps(definition.get("chain", []), ensure_ascii=False),
                json.dumps(definition.get("initial_params", {}), ensure_ascii=False),
                json.dumps(definition.get("tags", []), ensure_ascii=False),
                version,
                definition.get("status", "active"),
            ))
            conn.commit()
        finally:
            conn.close()

    def list_definitions(self, tag: str = "", active_only: bool = False) -> list[dict]:
        conn = self._get_conn()
        try:
            parts = ["SELECT * FROM pipeline_definitions"]
            params: list = []
            conditions = []
            if active_only:
                conditions.append("status = 'active'")
            if tag:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
            if conditions:
                parts.append("WHERE " + " AND ".join(conditions))
            parts.append("ORDER BY updated_at DESC")
            rows = conn.execute(" ".join(parts), params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_definition(self, pipeline_id: str) -> dict | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM pipeline_definitions WHERE id = ?", (pipeline_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_definition_versions(self, pipeline_id: str) -> list[dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT version, updated_at, status FROM pipeline_definitions WHERE id = ?",
                (pipeline_id,)
            ).fetchone()
            if row:
                return [dict(row)]
            return []
        finally:
            conn.close()

    def delete_definition(self, pipeline_id: str) -> bool:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM pipeline_definitions WHERE id = ?", (pipeline_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ── 内部 ──

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> dict:
        d = dict(row)
        try:
            d["chain"] = json.loads(d.get("chain") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["chain"] = []
        try:
            d["results"] = json.loads(d.get("results") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["results"] = []
        try:
            d["final_params"] = json.loads(d.get("final_params") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["final_params"] = {}
        d["success"] = bool(d.get("success", 0))
        return d


class PipelineEngine:
    def __init__(self, data_dir: str = ".evo_data/pipeline") -> None:
        self._store = PipelineStore(data_dir)
        self._history: list[dict] = []
        self._max_history = 100
        # 启动时从 SQLite 恢复最近历史
        self._recover_history()

    def _recover_history(self) -> None:
        """重启时从 SQLite 恢复最近运行记录"""
        try:
            recent = self._store.get_recent_runs(self._max_history)
            self._history = recent
            logger.info("[PIPELINE] 从 SQLite 恢复 %d 条运行记录", len(recent))
        except Exception as e:
            logger.warning("[PIPELINE] 恢复历史失败（首次运行可忽略）: %s", e)

    async def run(self, chain: list[str], initial_params: dict = None) -> dict:
        """
        执行模块链
        chain: ["module_a", "module_b", "module_c"]
        initial_params: 传给第一个模块的参数
        """
        pipeline_id = f"pipe_{datetime.datetime.now().strftime('%H%M%S')}_{len(self._history)}"
        results = []
        rollback_stack = []
        params = initial_params or {}
        success = True
        error = None

        logger.info("[PIPELINE] %s 开始执行 %d 个模块", pipeline_id, len(chain))

        for idx, module_name in enumerate(chain):
            step_result = {
                "step": idx + 1,
                "module": module_name,
                "status": "pending",
                "input": dict(params) if params else {},
                "output": None,
                "error": None,
            }

            try:
                mod = self._load_module(module_name)
                output = await mod.execute(params) if hasattr(mod, 'execute') and callable(mod.execute) else mod(params)
                step_result["output"] = output
                step_result["status"] = "success"

                # Pass output to next module
                if isinstance(output, dict):
                    for k, v in output.items():
                        if k not in ("success", "error"):
                            params[k] = v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)

                rollback_stack.append((module_name, step_result.copy()))
                logger.info("[PIPELINE] %s 步骤%d %s ✅", pipeline_id, idx + 1, module_name)

            except Exception as e:
                step_result["status"] = "failed"
                step_result["error"] = str(e)
                error = str(e)
                success = False
                logger.error("[PIPELINE] %s 步骤%d %s ❌ %s", pipeline_id, idx + 1, module_name, e)

                # Rollback: undo completed steps
                logger.info("[PIPELINE] %s 开始回滚 %d 个步骤", pipeline_id, len(rollback_stack))
                for rollback_mod, rollback_result in reversed(rollback_stack):
                    try:
                        mod = self._load_module(rollback_mod)
                        if hasattr(mod, "rollback") and callable(mod.rollback):
                            await mod.rollback(rollback_result.get("output", {}))
                        logger.info("[PIPELINE] %s 回滚 %s ✅", pipeline_id, rollback_mod)
                    except Exception as rb_e:
                        logger.warning("[PIPELINE] %s 回滚 %s 失败: %s", pipeline_id, rollback_mod, rb_e)

                results.append(step_result)
                break

            results.append(step_result)

        pipeline_record = {
            "id": pipeline_id,
            "chain": chain,
            "steps": len(chain),
            "completed": sum(1 for r in results if r.get("status") == "success"),
            "failed": sum(1 for r in results if r.get("status") == "failed"),
            "success": success,
            "error": error or "",
            "results": results,
            "final_params": params,
        }

        self._history.append(pipeline_record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # 持久化到 SQLite
        try:
            self._store.save_run(pipeline_record)
        except Exception as e:
            logger.warning("[PIPELINE] SQLite 持久化失败（不影响主流程）: %s", e)

        return pipeline_record

    def _load_module(self, name: str) -> Any:
        """动态加载模块（修复：删除硬编码路径，兼容任意部署目录）"""
        import importlib
        # sys.path 已在 api_server.py 中设好（BASE_DIR 和 modules/）
        mod_path = f"modules.{name}"
        try:
            mod = importlib.import_module(mod_path)
        except ImportError:
            # 尝试直接 import（部分模块名称可能与文件名不一致）
            try:
                mod = importlib.import_module(name)
            except ImportError:
                raise ImportError(f"无法加载模块 `{name}`：请确认模块文件名和 __module_meta__ 中的 class_name")

        # Find the class — 支持多种命名约定
        for attr_name in dir(mod):
            if attr_name.lower() == name.replace('-', '_').lower():
                cls = getattr(mod, attr_name)
                if isinstance(cls, type):
                    return cls()
            # 也匹配包含模块名的类名（如 ModuleA 匹配 module_a）
            if name.replace('-', '_').lower() in attr_name.lower():
                cls = getattr(mod, attr_name)
                if isinstance(cls, type):
                    return cls()
        # Fallback: 返回模块本身（假设模块有 execute 函数）
        return mod

    def get_history(self, limit: int = 10) -> list[dict]:
        return self._history[-limit:]

    def get_stats(self) -> dict:
        # 优先从 SQLite 获取准确统计
        try:
            return self._store.get_stats()
        except Exception:
            pass
        # fallback: 内存统计
        total = len(self._history)
        success = sum(1 for h in self._history if h.get("success"))
        failed = total - success
        total_steps = sum(h.get("steps", 0) for h in self._history)
        return {
            "total_pipelines": total,
            "success": success,
            "failed": failed,
            "total_steps": total_steps,
            "avg_steps": round(total_steps / total, 1) if total else 0,
        }

    def get_status(self) -> dict:
        """兼容 routes_scheduler.py 的接口：返回运行状态"""
        try:
            defs = self._store.list_definitions()
        except Exception:
            defs = []
        stats = self.get_stats()
        return {
            "running": True,
            "pipelines": defs,
            "stats": stats,
        }

    def list_pipelines(self, tag: str = "", active_only: bool = False) -> list:
        """兼容 routes_scheduler.py 的接口：返回管线定义列表"""
        try:
            return self._store.list_definitions(tag, active_only)
        except Exception:
            return []


# ── 模块级单例 ──

_engine = None
_pipeline_store_instance = None


def get_pipeline() -> PipelineEngine:
    global _engine
    if _engine is None:
        _engine = PipelineEngine()
    return _engine


def get_pipeline_engine() -> Any:
    """旧版兼容别名"""
    return get_pipeline()


def get_pipeline_store() -> Any:
    """
    旧版兼容：存储层
    v2: 返回真正的 PipelineStore（SQLite 持久化），保持全部兼容接口
    """
    global _pipeline_store_instance
    if _pipeline_store_instance is None:
        engine = get_pipeline()
        store = engine._store

        class PipelineStoreCompat:
            """兼容包装器：保持原有 list/get/delete 接口签名"""
            def get_execution_stats(self) -> dict:
                return store.get_stats()

            def list_executions(self, pipeline_id: str = "", limit: int = 10, offset: int = 0) -> list:
                return store.get_recent_runs(limit)

            def get_execution(self, exec_id: str) -> Any:
                return store.get_run(exec_id)

            def list_pipelines(self, tag: str = "", active_only: bool = False) -> list:
                return store.list_definitions(tag, active_only)

            def get_pipeline(self, pipeline_id: str) -> Any:
                return store.get_definition(pipeline_id)

            def get_pipeline_versions(self, pipeline_id: str) -> list:
                return store.get_definition_versions(pipeline_id)

            def delete_pipeline(self, pipeline_id: str) -> bool:
                return store.delete_definition(pipeline_id)

        _pipeline_store_instance = PipelineStoreCompat()
    return _pipeline_store_instance


def reset_pipeline_engine() -> None:
    """旧版兼容：重置引擎"""
    global _engine, _pipeline_store_instance
    _engine = PipelineEngine()
    _pipeline_store_instance = None
