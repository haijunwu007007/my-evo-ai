"""core_auth — API网关/用户/聊天/支付/Webhook"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import os, time, sqlite3, json, hashlib, httpx
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.features.auth")
router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DB = BASE_DIR / "core" / "adaptive_engine.db"

# ─── 5. API 网关 ─────────────────────────
class APIRequest(BaseModel):
    url: str; method: Optional[str] = "GET"
    headers: Optional[dict] = {}; body: Optional[str] = ""

@router.post("/api/v1/gateway")
async def api_gateway(req: APIRequest):
    allowed = ["https://api.github.com", "https://open.bigmodel.cn", "https://api.openai.com",
               "https://api.deepseek.com", "https://api.weather.gov", "https://httpbin.org",
               "https://api.duckduckgo.com", "https://www.baidu.com", "https://jsonplaceholder.typicode.com"]
    if not any(req.url.startswith(p) for p in allowed):
        return {"success": False, "detail": f"不允许的 API 域名"}
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            kwargs = {"headers": req.headers, "follow_redirects": True}
            if req.body and req.method.upper() in ("POST","PUT","PATCH"):
                kwargs["content"] = req.body
            resp = await c.request(req.method.upper(), req.url, **kwargs)
            try: data = resp.json()
            except: data = resp.text[:1000]
            return {"success": True, "status": resp.status_code, "data": data}
    except Exception as e:
        return {"success": False, "detail": str(e)}

# ─── 6. 用户注册/登录 ─────────────────────
def _init_users():
    conn = sqlite3.connect(str(_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user', email TEXT DEFAULT '', created_at REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, created_at REAL)")
    conn.commit(); conn.close()
_init_users()

class UserReq(BaseModel):
    username: str; password: Optional[str] = ""; email: Optional[str] = ""

@router.post("/api/v1/user/register")
async def user_register(req: UserReq):
    conn = sqlite3.connect(str(_DB))
    try:
        pw = hashlib.sha256((req.password or "default").encode()).hexdigest()
        conn.execute("INSERT INTO users (username, password, email, created_at) VALUES (?,?,?,?)",
                     (req.username, pw, (req.email or "").strip(), time.time()))
        conn.commit()
        return {"success": True, "user": req.username}
    except sqlite3.IntegrityError:
        return {"success": False, "detail": "用户名已存在"}
    finally: conn.close()

@router.post("/api/v1/user/login")
async def user_login(req: UserReq):
    conn = sqlite3.connect(str(_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, created_at REAL)")
    existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing == 0:
        from api.defaults import ADMIN_PASSWORD_HASH as default_pw
        conn.execute("INSERT OR IGNORE INTO users (username, password, role, created_at) VALUES (?,?,?,?)",
                     ("admin", default_pw, "admin", time.time()))
        conn.commit()
    pw = hashlib.sha256((req.password or "default").encode()).hexdigest()
    row = conn.execute("SELECT username, role FROM users WHERE username=? AND password=?", (req.username, pw)).fetchone()
    conn.close()
    if row: return {"success": True, "user": row[0], "role": row[1]}
    return {"success": False, "detail": "用户名或密码错误"}

@router.post("/api/v1/user/password-reset")
async def password_reset(req: UserReq):
    if not req.email or not req.username:
        return {"success": False, "detail": "需要用户名和邮箱"}
    conn = sqlite3.connect(str(_DB))
    try:
        row = conn.execute("SELECT id FROM users WHERE username=? AND email=?", (req.username, req.email)).fetchone()
        if not row: return {"success": False, "detail": "用户名或邮箱不匹配"}
        new_pw = hashlib.sha256("123456".encode()).hexdigest()
        conn.execute("UPDATE users SET password=? WHERE id=?", (new_pw, row[0]))
        conn.commit()
        return {"success": True, "detail": "密码已重置为 123456"}
    finally: conn.close()

# ─── 7. 聊天记录 ─────────────────────
class ChatSaveReq(BaseModel):
    username: str = "admin"; role: str = "user"; content: str = ""

@router.post("/api/v1/chat/save")
async def chat_save(req: ChatSaveReq):
    conn = sqlite3.connect(str(_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, created_at REAL)")
    conn.execute("INSERT INTO chat_history (username, role, content, created_at) VALUES (?,?,?,?)", (req.username, req.role, req.content, time.time()))
    conn.commit(); conn.close()
    return {"success": True}

@router.get("/api/v1/chat/history")
async def chat_history(username: str = "admin", limit: int = 50):
    conn = sqlite3.connect(str(_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, created_at REAL)")
    rows = conn.execute("SELECT role, content, created_at FROM chat_history WHERE username=? ORDER BY created_at DESC LIMIT ?", (username, limit)).fetchall()
    conn.close()
    return {"success": True, "messages": [{"role":r[0],"content":r[1]} for r in reversed(rows)]}

# ─── 8. 支付 ─────────────────────────
@router.get("/api/v1/payment/config")
async def payment_config():
    return {"success": True, "providers": {"alipay": bool(os.environ.get("ALIPAY_APP_ID")), "wechat": bool(os.environ.get("WECHAT_MCH_ID")), "stripe": bool(os.environ.get("STRIPE_KEY"))}}

@router.get("/api/v1/payment/revenue")
async def payment_revenue():
    try:
        conn = sqlite3.connect(str(_DB))
        conn.execute("CREATE TABLE IF NOT EXISTS payment_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, plan TEXT, amount REAL, status TEXT, created_at REAL)")
        conn.execute("INSERT OR IGNORE INTO payment_orders (id, plan, amount, status, created_at) VALUES (1,'free',0.0,'active',?)", (time.time()-86400*30,))
        total = conn.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payment_orders WHERE status='active'").fetchone()
        recent = conn.execute("SELECT plan, amount, created_at FROM payment_orders ORDER BY id DESC LIMIT 10").fetchall()
        conn.close()
        return {"success": True, "total_orders": total[0], "total_revenue": round(total[1],2), "recent_orders": [{"plan":r[0],"amount":r[1],"time":r[2]} for r in recent]}
    except Exception as e:
        return {"success": True, "total_orders": 0, "total_revenue": 0, "error": str(e)}

# ─── 9. Webhook ─────────────────────────
class WebhookEvent(BaseModel):
    event: str; payload: Optional[dict] = {}

@router.post("/api/v1/webhook")
async def receive_webhook(req: WebhookEvent):
    conn = sqlite3.connect(str(_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS webhook_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, payload TEXT, received_at REAL)")
    conn.execute("INSERT INTO webhook_events (event, payload, received_at) VALUES (?,?,?)", (req.event, json.dumps(req.payload), time.time()))
    conn.commit(); conn.close()
    return {"success": True, "result": f"Webhook 已接收: {req.event}"}

@router.get("/api/v1/webhook/events")
async def list_webhook_events(limit: int = 20):
    conn = sqlite3.connect(str(_DB))
    rows = conn.execute("SELECT id, event, payload, received_at FROM webhook_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return {"success": True, "events": [{"id":r[0],"event":r[1],"payload":r[2],"time":r[3]} for r in rows]}
