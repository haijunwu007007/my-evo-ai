"""Chat2DB / Text-to-SQL — 自然语言查数据库"""
import logging
logger = logging.getLogger("evo.agent_chat2db")

import os, json
from pathlib import Path
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

# 数据库配置存储
DB_CONFIG_DIR = Path("~/.evo-db-configs").expanduser()
DB_CONFIG_FILE = DB_CONFIG_DIR / "connections.json"

def _load_db_configs() -> dict:
    if DB_CONFIG_FILE.exists():
        try:
            return json.loads(DB_CONFIG_FILE.read_text(encoding='utf-8'))
        except Exception as _e:
            logger.warning(f"error: {_e}")
    return {}

def _save_db_configs(configs: dict):
    DB_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DB_CONFIG_FILE.write_text(json.dumps(configs, ensure_ascii=False, indent=2), encoding='utf-8')

def text2sql_connect(name: str = "", db_type: str = "sqlite", 
                     host: str = "localhost", port: int = 3306,
                     database: str = "", user: str = "", password: str = "",
                     file_path: str = "") -> dict:
    """注册数据库连接
    Args:
        name: 连接名称
        db_type: 数据库类型 (sqlite/mysql/postgresql/mongodb)
        host, port, database, user, password: 连接信息
        file_path: SQLite文件路径
    Returns:
        {"success": bool, "connection_id": str}
    """
    configs = _load_db_configs()
    conn_id = name or f"db_{len(configs)+1}"
    configs[conn_id] = {
        "db_type": db_type,
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": "***",
        "file_path": file_path,
        "created": __import__('time').time()
    }
    _save_db_configs(configs)
    return {"success": True, "connection_id": conn_id, "message": f"数据库 {conn_id} 已注册"}

def text2sql_query(question: str = "", connection: str = "",
                   db_type: str = "sqlite", file_path: str = "") -> dict:
    """自然语言查询数据库
    Args:
        question: 自然语言问题（如"哪个用户消费最多"）
        connection: 连接名称（使用已注册的连接）
        db_type: 数据库类型（未注册连接时使用）
        file_path: SQLite文件路径（未注册连接时使用）
    Returns:
        {"success": bool, "sql": str, "result": list, "summary": str}
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "需要设置 OPENAI_API_KEY"}

    if not question:
        return {"success": False, "error": "请提供 question"}

    try:
        # 获取数据库schema
        schema = ""
        db_conn = None
        configs = _load_db_configs()

        if connection and connection in configs:
            cfg = configs[connection]
            db_type = cfg.get("db_type", db_type)
            file_path = cfg.get("file_path", file_path)

        if db_type == "sqlite" and file_path:
            import sqlite3
            db_conn = sqlite3.connect(file_path)
            cursor = db_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            schema_parts = []
            for (tname,) in tables:
                cursor.execute(f"PRAGMA table_info({tname})")
                cols = cursor.fetchall()
                schema_parts.append(f"表 {tname}: " + ", ".join([f"{c[1]} ({c[2]})" for c in cols]))
            schema = "\n".join(schema_parts)

        from api.agent_llm import call_llm

        # Text-to-SQL
        sql_prompt = f"""你是一个SQL专家。根据数据库schema和自然语言问题，生成SQL查询。

数据库Schema:
{schema or "（未知schema，请自动推断）"}

问题: {question}

输出JSON:
{{"sql": "完整的SQL查询语句", "explanation": "查询逻辑说明"}}

只输出JSON。"""

        msgs = [{"role": "system", "content": "你是一个SQL专家。输出纯JSON。"},
                {"role": "user", "content": sql_prompt}]
        content, _ = call_llm(msgs, None, api_key)

        if not content:
            return {"success": False, "error": "SQL生成失败"}

        try:
            sql_info = json.loads(content.strip().strip('```json').strip('```').strip())
        except:
            sql_info = {"sql": content, "explanation": ""}

        sql_query = sql_info.get("sql", content)

        # 执行SQL
        result_rows = []
        try:
            if db_conn:
                cursor = db_conn.cursor()
                cursor.execute(sql_query)
                rows = cursor.fetchall()
                col_names = [d[0] for d in cursor.description] if cursor.description else []
                result_rows = [dict(zip(col_names, row)) for row in rows[:50]]
                db_conn.close()
        except Exception as sql_e:
            result_rows = [{"error": str(sql_e)}]

        return {
            "success": True,
            "question": question,
            "sql": sql_query,
            "explanation": sql_info.get("explanation", ""),
            "result": result_rows[:10],
            "total_rows": len(result_rows),
            "summary": f"查询完成，返回 {len(result_rows)} 行结果"
        }

    except Exception as e:
        return {"success": False, "error": f"Text-to-SQL 查询失败: {e}"}
