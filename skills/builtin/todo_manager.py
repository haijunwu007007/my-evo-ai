"""待办管理技能 — SQLite 持久化"""
import sqlite3, time
from pathlib import Path

skill_def = {
    "name": "todo-manager", "version": "1.0.0",
    "description": "待办创建/查询/完成/删除",
    "author": "AUTO-EVO-AI", "category": "工具", "icon": "📋",
    "tags": ["待办", "任务", "提醒"],
    "input_schema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["create", "list", "complete", "delete"]}, "title": {"type": "string"}, "priority": {"type": "string", "enum": ["高", "中", "低"]}}},
    "output_schema": {"type": "object", "properties": {"todos": {"type": "array"}}}
}

DB = Path(__file__).resolve().parent.parent.parent / "core" / "skill_todo.db"

def _get_db():
    conn = sqlite3.connect(str(DB))
    conn.execute("CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, priority TEXT, done INTEGER DEFAULT 0, created REAL)")
    return conn

def execute(params, context=None):
    action = params.get("action", "list")
    title = params.get("title", "")
    priority = params.get("priority", "中")
    conn = _get_db()
    try:
        if action == "create" and title:
            conn.execute("INSERT INTO todos (title, priority, created) VALUES (?, ?, ?)", (title, priority, time.time()))
            conn.commit()
        elif action == "complete":
            conn.execute("UPDATE todos SET done=1 WHERE title=?", (title,))
            conn.commit()
        elif action == "delete":
            conn.execute("DELETE FROM todos WHERE title=?", (title,))
            conn.commit()
        cur = conn.execute("SELECT id, title, priority, done FROM todos ORDER BY id DESC LIMIT 50")
        todos = [{"id": r[0], "title": r[1], "priority": r[2], "done": bool(r[3])} for r in cur.fetchall()]
        return {"todos": todos}
    finally:
        conn.close()
