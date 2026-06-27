"""持久记忆技能 — SQLite 存储和查询"""
import sqlite3, json, time, os
from pathlib import Path

skill_def = {
    "name": "memory-save", "version": "1.0.0",
    "description": "保存和查询持久记忆",
    "author": "AUTO-EVO-AI", "category": "系统", "icon": "🧠",
    "tags": ["记忆", "记住", "回忆"],
    "input_schema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["save", "recall"]}, "content": {"type": "string"}}},
    "output_schema": {"type": "object", "properties": {"memories": {"type": "array"}}}
}

DB = Path(__file__).resolve().parent.parent.parent / "core" / "skill_memory.db"

def _get_db():
    conn = sqlite3.connect(str(DB))
    conn.execute("CREATE TABLE IF NOT EXISTS skill_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created REAL)")
    return conn

def execute(params, context=None):
    action = params.get("action", "recall")
    content = params.get("content", "")
    conn = _get_db()
    try:
        if action == "save" and content:
            conn.execute("INSERT INTO skill_memory (content, created) VALUES (?, ?)", (content, time.time()))
            conn.commit()
            return {"memories": [{"content": content, "saved": True}]}
        else:
            cur = conn.execute("SELECT content, created FROM skill_memory ORDER BY created DESC LIMIT 20")
            rows = [{"content": r[0], "time": r[1]} for r in cur.fetchall()]
            return {"memories": rows}
    finally:
        conn.close()
