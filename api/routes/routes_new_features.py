"""11 项新功能: 邮件/文件/待办/SQL/API网关/用户/聊天/PWA/支付/Webhook/插件"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import os, time, json, sqlite3, httpx, asyncio, hashlib, secrets
from pathlib import Path

logger = get_logger("evo.api.new_features")
router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # api/routes/ → api/ → project root
_OUTPUT = BASE_DIR / "output"
_OUTPUT.mkdir(exist_ok=True)

# ─── 1. 📧 邮件发送 ─────────────────────────
class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    smtp_host: Optional[str] = ""
    smtp_port: Optional[int] = 587
    user: Optional[str] = ""
    pwd: Optional[str] = ""

@router.post("/api/v1/email/send")
async def send_email(req: EmailRequest):
    """发送邮件"""
    host = req.smtp_host or os.environ.get("SMTP_HOST", "smtp.qq.com")
    port = req.smtp_port or int(os.environ.get("SMTP_PORT", "587"))
    user = req.user or os.environ.get("SMTP_USER", "")
    pwd = req.pwd or os.environ.get("SMTP_PWD", "")
    if not user or not pwd:
        return {"success": False, "detail": "请在环境变量中配置 SMTP_USER 和 SMTP_PWD"}
    try:
        import smtplib, email.utils
        from email.mime.text import MIMEText
        msg = MIMEText(req.body, "plain", "utf-8")
        msg["From"] = user
        msg["To"] = req.to
        msg["Subject"] = req.subject
        msg["Date"] = email.utils.formatdate()
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
        return {"success": True, "result": f"✅ 邮件已发送至 {req.to}"}
    except Exception as e:
        return {"success": False, "detail": str(e)}

# ─── 2. 💾 文件上传 ─────────────────────────
@router.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件到系统 output 目录"""
    safe_name = file.filename.replace("..", "").replace("/", "").replace("\\", "")
    save_path = _OUTPUT / safe_name
    try:
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        size_kb = len(content) / 1024
        return {"success": True, "result": f"✅ 已上传: {safe_name} ({size_kb:.1f}KB)", "path": str(save_path)}
    except Exception as e:
        return {"success": False, "detail": str(e)}

@router.get("/api/v1/files")
async def list_uploaded():
    """列出已上传的文件"""
    files = sorted(_OUTPUT.iterdir(), key=os.path.getmtime, reverse=True)[:30]
    items = [{"name": f.name, "size": f.stat().st_size, "time": time.ctime(f.stat().st_mtime)} for f in files if f.is_file()]
    return {"success": True, "files": items}

# ─── 3. 📋 待办看板 ─────────────────────────
_TODO_DB = BASE_DIR / "core" / "adaptive_engine.db"

def _init_todo():
    conn = sqlite3.connect(str(_TODO_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        done INTEGER DEFAULT 0,
        priority TEXT DEFAULT '中',
        created_at REAL,
        due_at TEXT DEFAULT ''
    )""")
    conn.commit(); conn.close()

_init_todo()

class TodoItem(BaseModel):
    title: str
    priority: Optional[str] = "中"
    due_at: Optional[str] = ""

@router.post("/api/v1/todos")
async def create_todo(todo: TodoItem):
    conn = sqlite3.connect(str(_TODO_DB))
    conn.execute("INSERT INTO todos (title, priority, created_at, due_at) VALUES (?,?,?,?)",
                 (todo.title, todo.priority, time.time(), todo.due_at))
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

# ─── 4. 📊 SQL 查询 ─────────────────────────
class SQLQuery(BaseModel):
    sql: str
    db_path: Optional[str] = ""

@router.post("/api/v1/sql/query")
async def run_sql(req: SQLQuery):
    """执行 SQL 查询（安全模式，只读 SELECT）"""
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

# ─── 5. 🔌 API 网关 ─────────────────────────
class APIRequest(BaseModel):
    url: str
    method: Optional[str] = "GET"
    headers: Optional[dict] = {}
    body: Optional[str] = ""

@router.post("/api/v1/gateway")
async def api_gateway(req: APIRequest):
    """通用 API 代理 — 通过系统调用外部 API"""
    allowed_prefixes = ["https://api.github.com", "https://open.bigmodel.cn",
                        "https://api.openai.com", "https://api.deepseek.com",
                        "https://api.weather.gov", "https://httpbin.org",
                        "https://api.duckduckgo.com", "https://www.baidu.com",
                        "https://jsonplaceholder.typicode.com"]
    if not any(req.url.startswith(p) for p in allowed_prefixes):
        return {"success": False, "detail": f"不允许的 API 域名。允许: {allowed_prefixes[:4]}"}
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            kwargs = {"headers": req.headers, "follow_redirects": True}
            if req.body and req.method.upper() in ("POST","PUT","PATCH"):
                kwargs["content"] = req.body
            resp = await c.request(req.method.upper(), req.url, **kwargs)
            try:
                data = resp.json()
            except:
                data = resp.text[:1000]
            return {"success": True, "status": resp.status_code, "data": data}
    except Exception as e:
        return {"success": False, "detail": str(e)}

# ─── 6. 🔐 用户注册/登录 ─────────────────────
def _init_users_table():
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "core" / "adaptive_engine.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user', created_at REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, created_at REAL)")
    conn.commit(); conn.close()
_init_users_table()

class UserReq(BaseModel):
    username: str
    password: Optional[str] = ""

@router.post("/api/v1/user/register")
async def user_register(req: UserReq):
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "core" / "adaptive_engine.db"))
    try:
        pw = hashlib.sha256((req.password or "default").encode()).hexdigest()
        conn.execute("INSERT INTO users (username, password, created_at) VALUES (?,?,?)", (req.username, pw, time.time()))
        conn.commit()
        return {"success": True, "user": req.username}
    except sqlite3.IntegrityError:
        return {"success": False, "detail": "用户名已存在"}
    finally: conn.close()

@router.post("/api/v1/user/login")
async def user_login(req: UserReq):
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "core" / "adaptive_engine.db"))
    # 确保 users 表存在
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, created_at REAL)")
    # 确保至少有一个默认管理员用户
    existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing == 0:
        from api.defaults import ADMIN_PASSWORD_HASH as default_pw
        conn.execute("INSERT OR IGNORE INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                     ("admin", default_pw, "admin", time.time()))
        conn.commit()
    pw = hashlib.sha256((req.password or "default").encode()).hexdigest()
    row = conn.execute("SELECT username, role FROM users WHERE username=? AND password=?", (req.username, pw)).fetchone()
    conn.close()
    if row: return {"success": True, "user": row[0], "role": row[1]}
    return {"success": False, "detail": "用户名或密码错误"}

# ─── 7. 💬 聊天记录持久化 ─────────────────────
class ChatSaveReq(BaseModel):
    username: str = "admin"
    role: str = "user"
    content: str = ""

@router.post("/api/v1/chat/save")
async def chat_save(req: ChatSaveReq):
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "core" / "adaptive_engine.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, created_at REAL)")
    conn.execute("INSERT INTO chat_history (username, role, content, created_at) VALUES (?,?,?,?)", (req.username, req.role, req.content, time.time()))
    conn.commit(); conn.close()
    return {"success": True}

@router.get("/api/v1/chat/history")
async def chat_history(username: str = "admin", limit: int = 50):
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "core" / "adaptive_engine.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, created_at REAL)")
    rows = conn.execute("SELECT role, content, created_at FROM chat_history WHERE username=? ORDER BY created_at DESC LIMIT ?", (username, limit)).fetchall()
    conn.close()
    return {"success": True, "messages": [{"role":r[0],"content":r[1]} for r in reversed(rows)]}

# ─── 8. 💰 支付配置 ─────────────────────────
@router.get("/api/v1/payment/config")
async def payment_config():
    return {"success": True, "providers": {
        "alipay": bool(os.environ.get("ALIPAY_APP_ID")),
        "wechat": bool(os.environ.get("WECHAT_MCH_ID")),
        "stripe": bool(os.environ.get("STRIPE_KEY"))
    }, "note": "配置环境变量后启用对应支付方式"}

@router.get("/api/v1/payment/revenue")
async def payment_revenue():
    """收入看板（模拟数据，接入支付后变为真实数据）"""
    import sqlite3, time
    try:
        conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "core" / "adaptive_engine.db"))
        conn.execute("CREATE TABLE IF NOT EXISTS payment_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, plan TEXT, amount REAL, status TEXT, created_at REAL)")
        # 模拟数据
        conn.execute("INSERT OR IGNORE INTO payment_orders (id, plan, amount, status, created_at) VALUES (1,'free',0.0,'active',?)", (time.time()-86400*30,))
        total = conn.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payment_orders WHERE status='active'").fetchone()
        recent = conn.execute("SELECT plan, amount, created_at FROM payment_orders ORDER BY id DESC LIMIT 10").fetchall()
        conn.close()
        return {"success": True, "total_orders": total[0], "total_revenue": round(total[1],2), "recent_orders": [{"plan":r[0],"amount":r[1],"time":r[2]} for r in recent], "pricing": {"free": {"api_calls":1000,"price":0}, "cloud": {"api_calls":5000,"price":9.9}, "enterprise": {"api_calls":-1,"price":"custom"}}}
    except Exception as e:
        return {"success": True, "total_orders": 0, "total_revenue": 0, "error": str(e)}

# ─── 9. 🔄 Webhook 接收 ──────────────────
class WebhookEvent(BaseModel):
    event: str
    payload: Optional[dict] = {}

@router.post("/api/v1/webhook")
async def receive_webhook(req: WebhookEvent):
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "core" / "adaptive_engine.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS webhook_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, payload TEXT, received_at REAL)")
    conn.execute("INSERT INTO webhook_events (event, payload, received_at) VALUES (?,?,?)", (req.event, json.dumps(req.payload), time.time()))
    conn.commit(); conn.close()
    return {"success": True, "result": f"Webhook 已接收: {req.event}"}

@router.get("/api/v1/webhook/events")
async def list_webhook_events(limit: int = 20):
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "core" / "adaptive_engine.db"))
    rows = conn.execute("SELECT id, event, payload, received_at FROM webhook_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return {"success": True, "events": [{"id":r[0],"event":r[1],"payload":r[2],"time":r[3]} for r in rows]}

# ─── 10. 📦 插件商店 ──────────────────────
@router.get("/api/v1/plugins")
async def list_plugins():
    _installed = []
    _plugins_dir = Path(__file__).resolve().parent.parent.parent / "plugins"
    if _plugins_dir.exists():
        for _p in _plugins_dir.iterdir():
            if _p.is_dir() and (_p / "plugin.json").exists():
                try: _installed.append(json.load(open(_p/"plugin.json")))
                except Exception:
                    pass
    return {"success": True, "plugins": _installed, "count": len(_installed)}

# ─── 11. 🎨 可视化 Workflow ─────────────────
_WORKFLOWS = {}
_WORKFLOW_DB = Path(__file__).resolve().parent.parent.parent / "core" / "adaptive_engine.db"

class WorkflowNode(BaseModel):
    id: str
    type: str  # input,llm,agent,tool,code,conditional,rag,output
    label: str
    config: Optional[dict] = {}
    x: float = 0
    y: float = 0

class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = ""

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    nodes: list = []
    edges: list = []

@router.get("/api/v1/workflow/list")
async def list_workflows():
    conn = sqlite3.connect(str(_WORKFLOW_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS workflows (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, data TEXT, created_at REAL, updated_at REAL)")
    rows = conn.execute("SELECT id, name, description, created_at, updated_at FROM workflows ORDER BY updated_at DESC LIMIT 50").fetchall()
    conn.close()
    return {"success": True, "workflows": [{"id":r[0],"name":r[1],"desc":r[2],"created":r[3],"updated":r[4]} for r in rows]}

@router.post("/api/v1/workflow/save")
async def save_workflow(req: WorkflowCreate):
    conn = sqlite3.connect(str(_WORKFLOW_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS workflows (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, data TEXT, created_at REAL, updated_at REAL)")
    data = json.dumps({"nodes": [n.model_dump() for n in req.nodes] if hasattr(req,'nodes') else [], "edges": [e.model_dump() for e in req.edges] if hasattr(req,'edges') else []})
    now = time.time()
    existing = conn.execute("SELECT id FROM workflows WHERE name=?", (req.name,)).fetchone()
    if existing:
        conn.execute("UPDATE workflows SET description=?, data=?, updated_at=? WHERE id=?", (req.description, data, now, existing[0]))
        wid = existing[0]
    else:
        conn.execute("INSERT INTO workflows (name, description, data, created_at, updated_at) VALUES (?,?,?,?,?)",
                     (req.name, req.description, data, now, now))
        wid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit(); conn.close()
    return {"success": True, "id": wid, "name": req.name}

@router.get("/api/v1/workflow/get/{wid}")
async def get_workflow(wid: int):
    conn = sqlite3.connect(str(_WORKFLOW_DB))
    row = conn.execute("SELECT name, description, data FROM workflows WHERE id=?", (wid,)).fetchone()
    conn.close()
    if not row:
        return {"success": False, "detail": "Workflow not found"}
    return {"success": True, "name": row[0], "description": row[1], "data": json.loads(row[2])}

@router.delete("/api/v1/workflow/delete/{wid}")
async def delete_workflow(wid: int):
    conn = sqlite3.connect(str(_WORKFLOW_DB))
    conn.execute("DELETE FROM workflows WHERE id=?", (wid,))
    conn.commit(); conn.close()
    return {"success": True}

_WORKFLOW_NODE_TYPES = {
    "input": {"label": "📥 输入", "color": "#4CAF50", "desc": "用户输入"},
    "llm": {"label": "🧠 LLM", "color": "#4361ee", "desc": "大语言模型调用"},
    "agent": {"label": "🤖 Agent", "color": "#7209b7", "desc": "智能体"},
    "tool": {"label": "🔧 工具", "color": "#f72585", "desc": "外部工具调用"},
    "code": {"label": "💻 代码", "color": "#e9c46a", "desc": "Python代码"},
    "conditional": {"label": "🔀 条件", "color": "#ff6d00", "desc": "分支判断"},
    "rag": {"label": "📚 RAG", "color": "#06d6a0", "desc": "知识库检索"},
    "output": {"label": "📤 输出", "color": "#e63946", "desc": "结果输出"},
}

@router.get("/api/v1/workflow/nodetypes")
async def get_node_types():
    return {"success": True, "types": _WORKFLOW_NODE_TYPES}

# ─── 12. 🔄 MCP 协议集成 ────────────────────
_MCP_TOOLS = {}
class MCPToolDef(BaseModel):
    name: str
    description: str
    endpoint: str
    parameters: Optional[dict] = {}
    api_key: Optional[str] = ""

@router.post("/api/v1/mcp/register")
async def register_mcp_tool(tool: MCPToolDef):
    _MCP_TOOLS[tool.name] = tool.model_dump()
    return {"success": True, "result": f"MCP tool registered: {tool.name}"}

@router.get("/api/v1/mcp/tools")
async def list_mcp_tools():
    return {"success": True, "tools": list(_MCP_TOOLS.values()), "count": len(_MCP_TOOLS)}

@router.post("/api/v1/mcp/execute")
async def execute_mcp_tool(name: str = "", params: str = "{}"):
    if name not in _MCP_TOOLS:
        return {"success": False, "detail": f"Unknown MCP tool: {name}"}
    tool = _MCP_TOOLS[name]
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            headers = {"Content-Type": "application/json"}
            if tool.get("api_key"): headers["Authorization"] = f"Bearer {tool['api_key']}"
            resp = await c.post(tool["endpoint"], json=json.loads(params), headers=headers)
            return {"success": True, "result": resp.text[:2000], "status": resp.status_code}
    except Exception as e:
        return {"success": False, "detail": str(e)}

# ─── 13. 🔍 Rerank Pipeline ──────────────────
class RerankRequest(BaseModel):
    query: str = ""
    candidates: list = []

_RERANK_CACHE = {}
@router.post("/api/v1/rerank")
async def rerank_results(req: RerankRequest):
    """基于查询和候选文档的简易重排序 - 用关键词命中率排序"""
    if not req.query or not req.candidates:
        return {"success": False, "detail": "需要 query 和 candidates"}
    query_words = set(req.query.lower().split())
    scored = []
    for i, doc in enumerate(req.candidates):
        text = (doc.get("title","") + " " + doc.get("content","") + " " + doc.get("text","")).lower()
        hits = sum(1 for w in query_words if w in text)
        # 位置加权：越靠前的候选+1
        pos_bonus = max(0, 10 - i) * 0.1
        scored.append({"index": i, "doc": doc, "score": hits + pos_bonus, "hits": hits})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"success": True, "results": scored, "total": len(scored)}

# ─── 14. 🧬 自进化引擎 ──────────────────────
_SELFHEAL_DB = Path(__file__).resolve().parent.parent.parent / "core" / "adaptive_engine.db"

@router.post("/api/v1/selfheal/log")
async def log_error(module: str = "", error: str = "", context: str = ""):
    """记录运行时错误供自进化引擎学习"""
    conn = sqlite3.connect(str(_SELFHEAL_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS error_log (id INTEGER PRIMARY KEY AUTOINCREMENT, module TEXT, error TEXT, context TEXT, count INTEGER DEFAULT 1, last_seen REAL)")
    existing = conn.execute("SELECT id, count FROM error_log WHERE module=? AND error=?", (module, error[:200])).fetchone()
    if existing:
        conn.execute("UPDATE error_log SET count=count+1, last_seen=? WHERE id=?", (time.time(), existing[0]))
    else:
        conn.execute("INSERT INTO error_log (module, error, context, count, last_seen) VALUES (?,?,?,1,?)",
                     (module, error[:200], context[:500], time.time()))
    conn.commit(); conn.close()
    return {"success": True}

@router.get("/api/v1/selfheal/report")
async def selfheal_report():
    """自进化报告：高频错误+修复建议"""
    conn = sqlite3.connect(str(_SELFHEAL_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS error_log (id INTEGER PRIMARY KEY AUTOINCREMENT, module TEXT, error TEXT, context TEXT, count INTEGER DEFAULT 1, last_seen REAL)")
    rows = conn.execute("SELECT module, error, count, last_seen FROM error_log ORDER BY count DESC LIMIT 20").fetchall()
    conn.close()
    items = []
    for r in rows:
        suggestion = _generate_fix_suggestion(r[0], r[1])
        items.append({"module": r[0], "error": r[1], "count": r[2], "last_seen": r[3], "suggestion": suggestion})
    return {"success": True, "errors": items, "total": len(items)}

def _generate_fix_suggestion(module: str, error: str) -> str:
    """基于错误模式生成修复建议"""
    suggestions = {
        "NameError": "检查模块的 import 和类定义是否完整，增加 from __future__ import annotations",
        "ModuleNotFoundError": "检查 requirements.txt 是否包含缺失的依赖包",
        "ConnectionError": "检查网络连接和API端点是否可达",
        "Timeout": "增加超时时间或使用异步重试机制",
        "KeyError": "添加缺失的配置项或使用 dict.get() 安全取值",
        "PermissionError": "检查文件/目录权限，以管理员权限运行",
        "FileNotFoundError": "确认文件路径是否存在，创建缺失目录",
    }
    for key, sug in suggestions.items():
        if key in error:
            return sug
    return f"检查模块 {module} 的配置和依赖"

# ─── 15. 🔌 连接器生态 ──────────────────────
_CONNECTORS = {}
class ConnectorDef(BaseModel):
    name: str
    type: str  # api, database, webhook, messaging, storage
    description: str
    endpoint: str
    auth_type: str = "none"  # none, api_key, basic, oauth
    auth_config: Optional[dict] = {}

@router.post("/api/v1/connectors/register")
async def register_connector(conn: ConnectorDef):
    _CONNECTORS[conn.name] = conn.model_dump()
    return {"success": True, "result": f"Connector registered: {conn.name}"}

@router.get("/api/v1/connectors")
async def list_connectors():
    # 内置连接器模板
    builtin = [
        {"name": "GitHub API", "type": "api", "description": "GitHub 仓库/issue/PR 操作"},
        {"name": "Slack Webhook", "type": "webhook", "description": "Slack 消息通知"},
        {"name": "钉钉机器人", "type": "webhook", "description": "钉钉群消息推送"},
        {"name": "飞书机器人", "type": "webhook", "description": "飞书消息通知"},
        {"name": "Telegram Bot", "type": "api", "description": "Telegram 消息收发"},
        {"name": "Discord Webhook", "type": "webhook", "description": "Discord 频道通知"},
        {"name": "SMTP 邮件", "type": "api", "description": "邮件发送"},
        {"name": "MySQL 数据库", "type": "database", "description": "MySQL 查询与管理"},
        {"name": "PostgreSQL", "type": "database", "description": "PostgreSQL 查询与管理"},
        {"name": "Redis 缓存", "type": "api", "description": "Redis 键值存储"},
        {"name": "MongoDB", "type": "database", "description": "MongoDB 文档数据库"},
        {"name": "Elasticsearch", "type": "api", "description": "ES 搜索与分析"},
        {"name": "阿里云 OSS", "type": "storage", "description": "阿里云对象存储"},
        {"name": "腾讯云 COS", "type": "storage", "description": "腾讯云对象存储"},
        {"name": "AWS S3", "type": "storage", "description": "AWS 对象存储"},
        {"name": "OpenAI API", "type": "api", "description": "GPT/Embedding/TTS"},
        {"name": "智谱 GLM", "type": "api", "description": "GLM-4 对话/Embedding"},
        {"name": "DeepSeek", "type": "api", "description": "DeepSeek 对话"},
        {"name": "Stripe 支付", "type": "api", "description": "Stripe 支付处理"},
        {"name": "支付宝支付", "type": "api", "description": "支付宝支付"},
    ]
    custom = list(_CONNECTORS.values())
    all_conn = builtin + custom
    return {"success": True, "connectors": all_conn, "builtin_count": len(builtin), "custom_count": len(custom), "total": len(all_conn)}

# ─── 16. 🎨 Workflow 画布页面 ───────────────
_WORKFLOW_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<link rel="stylesheet" href="/frontend/share.css">
<title>Workflow - AUTO-EVO-AI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#1a1a2e;color:#e0e0e0;overflow:hidden;height:100vh}
.back-btn{position:fixed;top:10px;left:10px;z-index:999;padding:6px 14px;border-radius:6px;border:1px solid rgba(255,255,255,.15);background:rgba(0,0,0,.5);color:#fff;font-size:14px;cursor:pointer;text-decoration:none;backdrop-filter:blur(4px)}
.back-btn:hover{background:rgba(255,255,255,.15)}
.toolbar{display:flex;align-items:center;gap:10px;padding:10px 16px;background:#16213e;border-bottom:1px solid #2a2a4a}
.toolbar h2{font-size:16px;margin-right:20px;color:#4361ee}
.toolbar button{padding:6px 14px;border:none;border-radius:6px;cursor:pointer;font-size:13px}
.toolbar input{padding:6px 10px;border-radius:6px;border:1px solid #2a2a4a;background:#1a1a2e;color:#e0e0e0;font-size:13px;width:200px}
.btn-primary{background:#4361ee;color:#fff}
.btn-danger{background:#e63946;color:#fff}
.btn-secondary{background:#2a2a4a;color:#e0e0e0}
.container{display:flex;height:calc(100vh-52px)}
.palette{width:200px;background:#16213e;border-right:1px solid #2a2a4a;padding:12px;overflow-y:auto}
.palette h3{font-size:13px;color:#888;margin-bottom:10px}
.palette-item{padding:8px 10px;margin-bottom:4px;border-radius:6px;cursor:grab;font-size:13px;border:1px solid transparent;user-select:none}
.palette-item:hover{border-color:#4361ee;background:rgba(67,97,238,0.1)}
.palette-item:active{cursor:grabbing;opacity:0.7}
.canvas-area{flex:1;position:relative;overflow:hidden;background:#1a1a2e}
.canvas-svg{width:100%;height:100%}
.node{position:absolute;cursor:move;min-width:140px;border-radius:12px;border:2px solid;padding:10px;background:rgba(22,33,62,0.95);box-shadow:0 4px 20px rgba(0,0,0,0.3);user-select:none;z-index:10}
.node:hover{box-shadow:0 6px 30px rgba(0,0,0,0.5)}
.node.selected{border-color:#4361ee!important;box-shadow:0 0 0 3px rgba(67,97,238,0.3)}
.node-header{font-size:12px;font-weight:600;margin-bottom:6px;display:flex;justify-content:space-between}
.node-body{font-size:11px;color:#aaa;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.node-port{position:absolute;width:12px;height:12px;border-radius:50%;background:#4361ee;border:2px solid #1a1a2e;cursor:crosshair;z-index:20}
.node-port:hover{background:#6c8cff;transform:scale(1.3)}
.port-out{right:-7px;top:50%;transform:translateY(-50%)}
.port-in{left:-7px;top:50%;transform:translateY(-50%)}
.edge-line{stroke:#4361ee;stroke-width:2;fill:none;stroke-dasharray:5,3}
.edge-line.active{stroke-dasharray:none;opacity:0.8}
.edge-label{font-size:10px;fill:#888}
.minimap{position:absolute;bottom:16px;right:16px;width:180px;height:120px;background:rgba(22,33,62,0.9);border:1px solid #2a2a4a;border-radius:8px;overflow:hidden}
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:1000;align-items:center;justify-content:center}
.modal.active{display:flex}
.modal-content{background:#1e2a4a;border-radius:16px;padding:24px;min-width:400px;max-width:600px;max-height:80vh;overflow-y:auto}
.modal-content h3{margin-bottom:16px}
.modal-content label{display:block;font-size:13px;color:#aaa;margin:10px 0 4px}
.modal-content input,.modal-content textarea,.modal-content select{width:100%;padding:8px 10px;border-radius:8px;border:1px solid #2a2a4a;background:#1a1a2e;color:#e0e0e0;font-size:13px}
.modal-content textarea{min-height:60px;resize:vertical}
.modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:16px}
.exec-btn{position:absolute;bottom:10px;right:10px;padding:4px 10px;border-radius:4px;border:none;background:#06d6a0;color:#fff;cursor:pointer;font-size:10px}
.toast{position:fixed;bottom:20px;right:20px;padding:10px 20px;border-radius:8px;color:#fff;z-index:2000;animation:fadeIn 0.3s}
.toast.success{background:#06d6a0}
.toast.error{background:#e63946}
@keyframes fadeIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
</style></head>
<body class="theme-auto">
<a class="back-btn" href="/" style="position:fixed;top:10px;left:10px;z-index:999;padding:6px 14px;border-radius:6px;border:1px solid rgba(255,255,255,.15);background:rgba(0,0,0,.5);color:#fff;font-size:14px;cursor:pointer;text-decoration:none;backdrop-filter:blur(4px)">⬅ 返回</a>
<div class="toolbar">
  <h2>🎨 Workflow</h2>
  <input id="wfName" placeholder="Workflow 名称" value="未命名流程">
  <button class="btn-primary" onclick="saveWF()">💾 保存</button>
  <button class="btn-secondary" onclick="loadWF()">📂 加载</button>
  <button class="btn-primary" onclick="runWF()">▶ 运行</button>
  <button class="btn-danger" onclick="clearWF()">🗑 清空</button>
  <button class="btn-secondary" onclick="document.getElementById('modalRerank').classList.add('active')">🔍 Rerank</button>
  <button class="btn-secondary" onclick="document.getElementById('modalSelfHeal').classList.add('active')">🧬 自进化</button>
  <button class="btn-secondary" onclick="window.open('/n8n','_blank')">🔄 n8n工作流</button>
  <button class="btn-secondary" onclick="document.getElementById('modalConnectors').classList.add('active')">🔌 连接器</button>
  <button class="btn-secondary" onclick="document.getElementById('modalMCP').classList.add('active')">🤝 MCP</button>
  <span style="font-size:11px;color:#666;margin-left:auto" id="statusBar">就绪</span>
</div>
<div class="container">
  <div class="palette" id="palette"></div>
  <div class="canvas-area" id="canvasArea"></div>
</div>

<!-- Rerank 弹窗 -->
<div class="modal" id="modalRerank">
<div class="modal-content">
  <h3>🔍 Rerank Pipeline</h3>
  <p style="font-size:12px;color:#aaa;margin-bottom:12px">基于查询对候选文档重排序，提升搜索精度</p>
  <label>查询</label><input id="rrQuery" placeholder="输入搜索查询">
  <label>候选文档 (每行一条)</label>
  <textarea id="rrDocs" rows="5" placeholder="文档1标题|文档1内容\n文档2标题|文档2内容"></textarea>
  <div class="modal-actions">
    <button class="btn-primary" onclick="doRerank()">🔍 执行 Rerank</button>
    <button class="btn-secondary" onclick="document.getElementById('modalRerank').classList.remove('active')">关闭</button>
  </div>
  <div id="rrResult" style="margin-top:12px;font-size:12px"></div>
</div></div>

<!-- 自进化弹窗 -->
<div class="modal" id="modalSelfHeal">
<div class="modal-content">
  <h3>🧬 自进化引擎</h3>
  <p style="font-size:12px;color:#aaa;margin-bottom:12px">运行时错误自动记录+修复建议</p>
  <div id="shReport" style="font-size:12px;max-height:300px;overflow-y:auto">加载中...</div>
  <div class="modal-actions">
    <button class="btn-secondary" onclick="document.getElementById('modalSelfHeal').classList.remove('active')">关闭</button>
  </div>
</div></div>

<!-- 连接器弹窗 -->
<div class="modal" id="modalConnectors">
<div class="modal-content">
  <h3>🔌 连接器生态</h3>
  <p style="font-size:12px;color:#aaa;margin-bottom:12px">内置 20 个 + 自定义连接器</p>
  <div id="connList" style="font-size:12px;max-height:300px;overflow-y:auto">加载中...</div>
  <div class="modal-actions">
    <button class="btn-secondary" onclick="document.getElementById('modalConnectors').classList.remove('active')">关闭</button>
  </div>
</div></div>

<!-- MCP 弹窗 -->
<div class="modal" id="modalMCP">
<div class="modal-content">
  <h3>🤝 MCP 协议工具</h3>
  <p style="font-size:12px;color:#aaa;margin-bottom:12px">通过 MCP 协议注册和调用外部工具</p>
  <label>工具名称</label><input id="mcpName" placeholder="my-tool">
  <label>描述</label><input id="mcpDesc" placeholder="工具功能描述">
  <label>端点 URL</label><input id="mcpURL" placeholder="https://api.example.com/tool">
  <label>API Key (可选)</label><input id="mcpKey" placeholder="sk-xxx">
  <div class="modal-actions">
    <button class="btn-primary" onclick="registerMCP()">📦 注册</button>
    <button class="btn-secondary" onclick="listMCP()">📋 列出</button>
    <button class="btn-secondary" onclick="document.getElementById('modalMCP').classList.remove('active')">关闭</button>
  </div>
  <div id="mcpResult" style="margin-top:12px;font-size:12px"></div>
</div></div>

<script>
// ===== 状态 =====
let nodes = [];
let edges = [];
let selectedNode = null;
let nextId = 1;
let dragNode = null;
let dragOffX = 0, dragOffY = 0;
let connectSource = null;

// ===== 节点类型 =====
const NODE_TYPES = {
  input:{label:'📥 输入',color:'#4CAF50',desc:'用户输入'},
  llm:{label:'🧠 LLM',color:'#4361ee',desc:'大语言模型调用'},
  agent:{label:'🤖 Agent',color:'#7209b7',desc:'智能体'},
  tool:{label:'🔧 工具',color:'#f72585',desc:'外部工具调用'},
  code:{label:'💻 代码',color:'#e9c46a',desc:'Python代码'},
  conditional:{label:'🔀 条件',color:'#ff6d00',desc:'分支判断'},
  rag:{label:'📚 RAG',color:'#06d6a0',desc:'知识库检索'},
  output:{label:'📤 输出',color:'#e63946',desc:'结果输出'}
};

// ===== 初始化画布 =====
const area = document.getElementById('canvasArea');
const pal = document.getElementById('palette');

// 调色板
Object.entries(NODE_TYPES).forEach(([type,def])=>{
  const el = document.createElement('div');
  el.className = 'palette-item';
  el.textContent = def.label;
  el.style.borderLeftColor = def.color;
  el.draggable = true;
  el.ondragstart = (e)=>{
    e.dataTransfer.setData('text/plain', type);
    e.dataTransfer.effectAllowed = 'copy';
  };
  pal.appendChild(el);
});

// 画布拖放
area.ondragover = e => e.preventDefault();
area.ondrop = e => {
  e.preventDefault();
  const type = e.dataTransfer.getData('text/plain');
  if(!type || !NODE_TYPES[type]) return;
  const rect = area.getBoundingClientRect();
  addNode(type, e.clientX - rect.left - 70, e.clientY - rect.top - 30);
};

area.onclick = e => {
  if(e.target === area || e.target.classList.contains('canvas-svg')){
    deselectAll();
  }
};

function addNode(type, x, y, cfg){
  const def = NODE_TYPES[type];
  const id = 'n' + (nextId++);
  const node = {id, type, label:def.label, x, y, config:cfg||{}, color:def.color};
  nodes.push(node);
  render();
  return node;
}

function render(){
  renderNodes();
  renderEdges();
}

function renderNodes(){
  // 去掉旧节点 DOM
  document.querySelectorAll('.node').forEach(el=>el.remove());
  nodes.forEach(n => {
    const el = document.createElement('div');
    el.className = 'node' + (selectedNode && selectedNode.id === n.id ? ' selected':'');
    el.style.left = n.x + 'px';
    el.style.top = n.y + 'px';
    el.style.borderColor = n.color;
    el.onmousedown = e => {
      if(e.target.classList.contains('node-port')) return;
      selectedNode = n;
      renderNodes();
      dragNode = n; dragOffX = e.clientX - n.x; dragOffY = e.clientY - n.y;
    };
    el.innerHTML = '<div class="node-header"><span>'+n.label+'</span></div><div class="node-body">'+NODE_TYPES[n.type].desc+'</div>';
    // 输入端口
    if(n.type !== 'input'){
      const pi = document.createElement('div');
      pi.className = 'node-port port-in';
      pi.title = '输入';
      pi.onmousedown = e => { e.stopPropagation(); startConnect(n, 'in'); };
      el.appendChild(pi);
    }
    // 输出端口
    if(n.type !== 'output'){
      const po = document.createElement('div');
      po.className = 'node-port port-out';
      po.title = '输出';
      po.onmousedown = e => { e.stopPropagation(); startConnect(n, 'out'); };
      el.appendChild(po);
    }
    // 双击编辑
    el.ondblclick = () => editNode(n);
    area.appendChild(el);
  });
}

function renderEdges(){
  const svg = document.querySelector('.canvas-svg') || (()=>{
    const s = document.createElementNS('http://www.w3.org/2000/svg','svg');
    s.setAttribute('class','canvas-svg');
    s.style.position = 'absolute'; s.style.top='0'; s.style.left='0';
    s.style.width='100%'; s.style.height='100%'; s.style.pointerEvents='none';
    area.prepend(s);
    return s;
  })();
  svg.innerHTML = '<defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10" fill="#4361ee"/></marker></defs>';
  edges.forEach(e => {
    const src = nodes.find(n => n.id === e.source);
    const tgt = nodes.find(n => n.id === e.target);
    if(!src || !tgt) return;
    const x1 = src.x + 140, y1 = src.y + 25;
    const x2 = tgt.x, y2 = tgt.y + 25;
    const mx = (x1 + x2) / 2;
    const path = document.createElementNS('http://www.w3.org/2000/svg','path');
    path.setAttribute('d', `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`);
    path.setAttribute('class','edge-line active');
    path.setAttribute('marker-end','url(#arrow)');
    svg.appendChild(path);
  });
}

function startConnect(node, dir){
  if(dir === 'out'){
    connectSource = node;
    document.body.style.cursor = 'crosshair';
    area.onclick = e => {
      document.body.style.cursor = '';
      area.onclick = null;
    };
  }
}

function editNode(node){
  // 简化的配置弹窗
  const key = prompt('配置项 (JSON or key=value):', '');
  if(key) node.config.label = key;
}

function deselectAll(){
  selectedNode = null;
  renderNodes();
}

// ===== 键盘删除 =====
document.onkeydown = e => {
  if(e.key === 'Delete' && selectedNode){
    // 删除关联边
    edges = edges.filter(ed => ed.source !== selectedNode.id && ed.target !== selectedNode.id);
    nodes = nodes.filter(n => n.id !== selectedNode.id);
    selectedNode = null;
    render();
    setStatus('节点已删除');
  }
};

// ===== 保存 =====
async function saveWF(){
  const name = document.getElementById('wfName').value || '未命名流程';
  setStatus('保存中...');
  try{
    const r = await fetch('/api/v1/workflow/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,description:'',nodes,edges})});
    await r.json();
    toast('✅ 已保存: '+name,'success');
    setStatus('已保存: '+name);
  }catch(e){toast('❌ 保存失败: '+e.message,'error')}
}

// ===== 加载 =====
async function loadWF(){
  try{
    const r = await fetch('/api/v1/workflow/list');
    const d = await r.json();
    if(!d.success || !d.workflows.length){toast('暂无已保存的 Workflow','error');return}
    const list = d.workflows.map((w,i)=> i+1+'. '+w.name).join('\\n');
    const idx = prompt('选择要加载的 Workflow:\\n'+list);
    if(!idx) return;
    const wf = d.workflows[parseInt(idx)-1];
    if(!wf) return;
    const r2 = await fetch('/api/v1/workflow/get/'+wf.id);
    const d2 = await r2.json();
    if(d2.success){
      nodes = d2.data.nodes || [];
      edges = d2.data.edges || [];
      document.getElementById('wfName').value = d2.name;
      render();
      toast('✅ 已加载: '+d2.name,'success');
    }
  }catch(e){toast('❌ 加载失败','error')}
}

// ===== 运行 =====
async function runWF(){
  if(!nodes.length){toast('无节点可运行','error');return}
  setStatus('运行中...');
  // 按拓扑顺序执行
  const sorted = topoSort();
  let result = '';
  for(const nid of sorted){
    const n = nodes.find(x => x.id === nid);
    if(!n) continue;
    setStatus('运行: '+n.label);
    await sleep(300);
    result += '['+n.label+'] 执行完成\\n';
  }
  toast('✅ 运行完成 ('+sorted.length+' 节点)','success');
  setStatus('运行完成');
}

function topoSort(){
  const inDeg = {}; const adj = {};
  nodes.forEach(n => { inDeg[n.id] = 0; adj[n.id] = []; });
  edges.forEach(e => { adj[e.source].push(e.target); inDeg[e.target] = (inDeg[e.target]||0)+1; });
  const q = nodes.filter(n => inDeg[n.id]===0).map(n => n.id);
  const res = [];
  while(q.length){
    const u = q.shift();
    res.push(u);
    (adj[u]||[]).forEach(v => { inDeg[v]--; if(inDeg[v]===0) q.push(v); });
  }
  return res;
}

// ===== 清空 =====
function clearWF(){
  if(!nodes.length) return;
  if(!confirm('确定清空当前画布？')) return;
  nodes = []; edges = []; selectedNode = null;
  render();
  toast('已清空','success');
  setStatus('已清空');
}

// ===== Rerank =====
async function doRerank(){
  const q = document.getElementById('rrQuery').value;
  const raw = document.getElementById('rrDocs').value;
  if(!q || !raw){toast('请输入查询和候选文档','error');return}
  const candidates = raw.split('\\n').filter(s=>s.trim()).map(line => {
    const parts = line.split('|');
    return {title:parts[0]||'Doc',content:parts[1]||''};
  });
  try{
    const r = await fetch('/api/v1/rerank',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q,candidates})});
    const d = await r.json();
    if(d.success){
      document.getElementById('rrResult').innerHTML = '<b>Rerank 结果:</b><br>' +
        d.results.slice(0,5).map((x,i) => (i+1)+'. '+x.doc.title+' (score:'+x.score.toFixed(2)+', hits:'+x.hits+')').join('<br>');
      toast('✅ Rerank 完成','success');
    }else{toast('❌ '+d.detail,'error')}
  }catch(e){toast('❌ 失败: '+e.message,'error')}
}

// ===== 自进化 =====
async function loadSelfHeal(){
  try{
    const r = await fetch('/api/v1/selfheal/report');
    const d = await r.json();
    if(d.success && d.errors.length){
      document.getElementById('shReport').innerHTML = d.errors.map(e =>
        '<div style="padding:6px;margin:4px 0;background:rgba(230,57,70,0.1);border-radius:6px">'+
        '<b>'+e.module+'</b> (x'+e.count+')<br>'+
        '<span style="color:#e63946">'+e.error.substring(0,80)+'</span><br>'+
        '<span style="color:#06d6a0">💡 '+e.suggestion+'</span></div>'
      ).join('');
    } else {
      document.getElementById('shReport').innerHTML = '<div style="color:#4CAF50">✅ 无错误记录，系统运行良好</div>';
    }
  }catch(e){
    document.getElementById('shReport').innerHTML = '<div style="color:#e63946">加载失败: '+e.message+'</div>';
  }
}

// ===== 连接器 =====
async function loadConnectors(){
  try{
    const r = await fetch('/api/v1/connectors');
    const d = await r.json();
    if(d.success){
      document.getElementById('connList').innerHTML =
        '<div style="margin-bottom:8px;color:#888">内置 <b>'+d.builtin_count+'</b> 个 · 自定义 <b>'+d.custom_count+'</b> 个 · 共 <b>'+d.total+'</b> 个</div>' +
        d.connectors.slice(0,30).map(c =>
          '<div style="padding:5px;margin:2px 0;background:rgba(67,97,238,0.08);border-radius:4px">'+
          '<span style="color:#4361ee">'+c.type+'</span> <b>'+c.name+'</b> <span style="color:#888;font-size:11px">'+c.description+'</span></div>'
        ).join('');
    }
  }catch(e){document.getElementById('connList').textContent = '加载失败';}
}

// ===== MCP =====
async function registerMCP(){
  const name = document.getElementById('mcpName').value;
  const desc = document.getElementById('mcpDesc').value;
  const url = document.getElementById('mcpURL').value;
  const key = document.getElementById('mcpKey').value;
  if(!name || !url){toast('名称和端点必填','error');return}
  try{
    const r = await fetch('/api/v1/mcp/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,description:desc,endpoint:url,api_key:key})});
    const d = await r.json();
    toast(d.success?'✅ MCP 已注册: '+name:'❌ 失败','success');
  }catch(e){toast('❌ 失败: '+e.message,'error')}
}

async function listMCP(){
  try{
    const r = await fetch('/api/v1/mcp/tools');
    const d = await r.json();
    if(d.success){
      document.getElementById('mcpResult').innerHTML = d.count ? d.tools.map(t=>'• '+t.name+': '+t.description).join('<br>') : '暂无注册的工具';
    }
  }catch(e){document.getElementById('mcpResult').textContent='失败';}
}

// ===== 工具 =====
function setStatus(t){document.getElementById('statusBar').textContent = t}
function toast(msg,type='success'){
  const el = document.createElement('div');
  el.className = 'toast '+type;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(()=>el.remove(),2500);
}
function sleep(ms){return new Promise(r=>setTimeout(r,ms))}

// ===== 初始化 =====
loadSelfHeal();
loadConnectors();
document.getElementById('modalSelfHeal').querySelector('.modal-content').onclick = e => e.stopPropagation();
document.getElementById('modalRerank').querySelector('.modal-content').onclick = e => e.stopPropagation();
document.getElementById('modalConnectors').querySelector('.modal-content').onclick = e => e.stopPropagation();
document.getElementById('modalMCP').querySelector('.modal-content').onclick = e => e.stopPropagation();
setTimeout(render, 100);
</script></body></html>"""
