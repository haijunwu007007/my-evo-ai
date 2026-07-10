"""core_basic — 邮件/文件/待办/SQL 查询"""
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import os, time, sqlite3, email.utils
from email.mime.text import MIMEText
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.features.basic")
router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
_OUTPUT = BASE_DIR / "output"
_OUTPUT.mkdir(exist_ok=True)

# ─── 1. 邮件发送 ─────────────────────────
class EmailRequest(BaseModel):
    to: str; subject: str; body: str
    smtp_host: Optional[str] = ""; smtp_port: Optional[int] = 587
    user: Optional[str] = ""; pwd: Optional[str] = ""

@router.post("/api/v1/email/send")
async def send_email(req: EmailRequest):
    host = req.smtp_host or os.environ.get("SMTP_HOST", "smtp.qq.com")
    port = req.smtp_port or int(os.environ.get("SMTP_PORT", "587"))
    user = req.user or os.environ.get("SMTP_USER", "")
    pwd = req.pwd or os.environ.get("SMTP_PWD", "")
    if not user or not pwd:
        return {"success": False, "detail": "请在环境变量中配置 SMTP_USER 和 SMTP_PWD"}
    try:
        import smtplib
        msg = MIMEText(req.body, "plain", "utf-8")
        msg["From"] = user; msg["To"] = req.to; msg["Subject"] = req.subject
        msg["Date"] = email.utils.formatdate()
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(); s.login(user, pwd); s.send_message(msg)
        return {"success": True, "result": f"✅ 邮件已发送至 {req.to}"}
    except Exception as e:
        return {"success": False, "detail": str(e)}

# ─── 2. 文件上传 ─────────────────────────
@router.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    safe_name = file.filename.replace("..", "").replace("/", "").replace("\\", "")
    save_path = _OUTPUT / safe_name
    try:
        content = await file.read()
        with open(save_path, "wb") as f: f.write(content)
        return {"success": True, "result": f"✅ 已上传: {safe_name} ({len(content)/1024:.1f}KB)", "path": str(save_path)}
    except Exception as e:
        return {"success": False, "detail": str(e)}

@router.get("/api/v1/files")
async def list_uploaded():
    files = sorted(_OUTPUT.iterdir(), key=os.path.getmtime, reverse=True)[:30]
    items = [{"name": f.name, "size": f.stat().st_size, "time": time.ctime(f.stat().st_mtime)} for f in files if f.is_file()]
    return {"success": True, "files": items}

# ─── 3. 待办看板 ─────────────────────────
_TODO_DB = BASE_DIR / "core" / "adaptive_engine.db"
conn = sqlite3.connect(str(_TODO_DB))
conn.execute("CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER DEFAULT 0, priority TEXT DEFAULT '中', created_at REAL, due_at TEXT DEFAULT '')")
conn.commit(); conn.close()

class TodoItem(BaseModel):
    title: str; priority: Optional[str] = "中"; due_at: Optional[str] = ""

@router.post("/api/v1/todos")
async def create_todo(todo: TodoItem):
    conn = sqlite3.connect(str(_TODO_DB))
    conn.execute("INSERT INTO todos (title, priority, created_at, due_at) VALUES (?,?,?,?)", (todo.title, todo.priority, time.time(), todo.due_at))
    conn.commit(); conn.close()
    return {"success": True, "result": f"✅ 已创建待办: {todo.title}"}

@router.get("/api/v1/todos")
async def list_todos(done: int = 0):
    conn = sqlite3.connect(str(_TODO_DB))
    rows = conn.execute("SELECT id, title, done, priority, due_at FROM todos WHERE done=? ORDER BY created_at DESC LIMIT 50", (done,)).fetchall()
    conn.close()
    return {"success": True, "todos": [{"id":r[0],"title":r[1],"done":r[2],"priority":r[3],"due":r[4]} for r in rows]}

@router.post("/api/v1/todos/{tid}/done")
async def done_todo(tid: int):
    conn = sqlite3.connect(str(_TODO_DB))
    conn.execute("UPDATE todos SET done=1 WHERE id=?", (tid,))
    conn.commit(); conn.close()
    return {"success": True, "result": f"✅ 待办 {tid} 已完成"}

# ─── 4. SQL 查询 ─────────────────────────
class SQLQuery(BaseModel):
    sql: str; db_path: Optional[str] = ""

@router.post("/api/v1/sql/query")
async def run_sql(req: SQLQuery):
    sql = req.sql.strip().lower()
    if not sql.startswith("select") and not sql.startswith("pragma"):
        return {"success": False, "detail": "仅支持 SELECT 查询"}
    db = req.db_path or str(_TODO_DB)
    if not os.path.isfile(db):
        return {"success": False, "detail": f"数据库文件不存在: {db}"}
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(req.sql)
        rows = [dict(row) for row in cur.fetchall()[:100]]
        cols = [desc[0] for desc in cur.description] if cur.description else []
        conn.close()
        return {"success": True, "columns": cols, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"success": False, "detail": str(e)}
