"""智能SQL查询路由 — 自然语言→SQL，支持SQLite"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import sqlite3, json, re
from core.logging_config import get_logger

logger = get_logger("evo.api.query")
router = APIRouter()

BASE = Path(__file__).resolve().parent.parent.parent

class QueryRequest(BaseModel):
    sql: str = ""
    question: str = ""
    db: Optional[str] = "default"
    limit: Optional[int] = 100

def _get_db_path(name: str) -> Path:
    if name == "default":
        return BASE / "_data" / "evo.db"
    return Path(name)

@router.post("/api/v1/query")
async def query_sql(req: QueryRequest):
    """执行SQL查询"""
    if not req.sql and not req.question:
        return {"success": False, "error": "请提供SQL语句或自然语言问题"}
    
    sql = req.sql
    if not sql and req.question:
        from api.agent_llm import call_llm
        prompt = f"将以下自然语言转成SQL: {req.question}。只输出SQL，不要解释。"
        sql, _ = call_llm([{"role": "user", "content": prompt}], timeout=15)
        if not sql:
            return {"success": False, "error": "无法将问题转为SQL"}
    
    db_path = _get_db_path(req.db)
    if not db_path.exists():
        return {"success": False, "error": f"数据库不存在: {db_path}"}
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql)
        results = [dict(row) for row in cursor.fetchmany(req.limit)]
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        return {
            "success": True,
            "data": results,
            "columns": columns,
            "count": len(results),
            "sql": sql,
        }
    except Exception as e:
        logger.error("SQL查询失败: %s", e)
        return {"success": False, "error": f"查询失败: {str(e)}", "sql": sql}

@router.get("/api/v1/query/dbs")
async def list_databases():
    """列出可用数据库"""
    dbs = [{"name": "default", "path": str(BASE / "_data" / "evo.db")}]
    data_dir = BASE / "_data"
    if data_dir.exists():
        for f in data_dir.glob("*.db"):
            name = f.stem
            if name not in ("evo", "chat_history"):
                dbs.append({"name": name, "path": str(f)})
    return {"success": True, "databases": dbs}

@router.get("/api/v1/query/tables")
async def list_tables(db: str = "default"):
    """列出数据库中的表"""
    db_path = _get_db_path(db)
    if not db_path.exists():
        return {"success": False, "error": "数据库不存在"}
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        schema = {}
        conn2 = sqlite3.connect(str(db_path))
        for tbl in tables:
            cols = conn2.execute(f"PRAGMA table_info('{tbl}')").fetchall()
            schema[tbl] = [{"name": c[1], "type": c[2]} for c in cols]
        conn2.close()
        return {"success": True, "tables": tables, "schema": schema}
    except Exception as e:
        return {"success": False, "error": str(e)}
