"""AUTO-EVO-AI V0.1 — 认证路由（合并两个独立 router，修复双变量覆盖 bug）"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from dataclasses import dataclass
from typing import Optional
import sqlite3, os, time, hashlib, json, secrets

router = APIRouter(tags=["auth"])
_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "users.db")

def _get_db():
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        id TEXT PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user',
        created_at REAL, last_login REAL
    )""")
    return conn

# ── 数据模型 ──
@dataclass
class LoginRequest:
    username: str = ""
    api_key: str = ""
    password: str = ""
    role: str = "user"

@dataclass
class TokenRefreshRequest:
    token: str = ""

# ── 密码工具 ──
def _hash_pwd(pwd: str) -> str:
    """bcrypt 风格加盐哈希（迁移用，未来可换 real bcrypt）"""
    salt = hashlib.sha256(f"evo_salt_{pwd}".encode()).hexdigest()[:16]
    return hashlib.sha256(f"{salt}:{pwd}".encode()).hexdigest()

# ════════════════════════════════════════════
# 1. 前端用户注册/登录 (routes_auth 上半段)
# ════════════════════════════════════════════

@router.post("/api/v1/users/register")
@router.post("/api/v1/user/register")
@router.post("/api/auth/register")
async def register(req: dict):
    db = _get_db()
    uname = req.get("username", "").strip()
    pwd = req.get("password", "").strip()
    if not uname or len(uname) < 2: return JSONResponse({"success":False,"error":"用户名至少2位"})
    if not pwd or len(pwd) < 3: return JSONResponse({"success":False,"error":"密码至少3位"})
    try:
        uid = hashlib.md5((uname+str(time.time())).encode()).hexdigest()[:12]
        db.execute("INSERT INTO users VALUES(?,?,?,?,?,?)",(uid,uname,_hash_pwd(pwd),"user",time.time(),0))
        db.commit()
        return {"success":True,"user":uname,"role":"user"}
    except:
        return JSONResponse({"success":False,"error":"用户名已存在"})

@router.post("/api/v1/users/login")
@router.post("/api/v1/user/login")
@router.post("/api/auth/login")
async def user_login(req: LoginRequest):
    db = _get_db()
    # API Key 登录
    if req.api_key:
        from core.auth_provider import verify_api_key, create_token, _ADMIN_KEY
        if verify_api_key(req.api_key):
            token = create_token(subject="api_user", role="admin" if req.api_key == _ADMIN_KEY else "user")
            return token
        return JSONResponse(status_code=401, content={"detail": "无效的 API Key", "error": "unauthorized"})
    # JWT 密码登录
    if req.username:
        from core.auth_provider import create_token
        row = db.execute("SELECT * FROM users WHERE username=?", (req.username,)).fetchone()
        if row and row["password"] == _hash_pwd(req.password or ""):
            db.execute("UPDATE users SET last_login=? WHERE id=?", (time.time(), row["id"]))
            db.commit()
            role = "admin" if req.username == "admin" else row["role"]
            token = create_token(subject=req.username, role=role)
            return token
        return JSONResponse(status_code=401, content={"detail": "密码错误", "error": "unauthorized"})
    return JSONResponse(status_code=400, content={"detail": "请提供 username 或 api_key"})

@router.get("/api/v1/users/list")
async def user_list():
    db = _get_db()
    rows = db.execute("SELECT id,username,role,created_at FROM users ORDER BY created_at").fetchall()
    return {"users":[dict(r) for r in rows]}

@router.get("/api/v1/auth/config")
@router.get("/api/auth/config")
async def auth_config():
    """获取认证配置状态"""
    try:
        from core.auth_provider import get_auth_config
        return get_auth_config()
    except:
        return {"success": True, "mode": "jwt"}
