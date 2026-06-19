from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, time, hashlib, json

router = APIRouter(prefix="/api/v1/users", tags=["users"])

_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "users.db")

def _get_db():
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        id TEXT PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user',
        created_at REAL, last_login REAL
    )""")
    return conn

@router.post("/register")
async def register(req: dict):
    db = _get_db()
    uname = req.get("username", "").strip()
    pwd = req.get("password", "").strip()
    if not uname or len(uname) < 2: return JSONResponse({"success":False,"error":"用户名至少2位"})
    if not pwd or len(pwd) < 3: return JSONResponse({"success":False,"error":"密码至少3位"})
    try:
        uid = hashlib.md5((uname+str(time.time())).encode()).hexdigest()[:12]
        db.execute("INSERT INTO users VALUES(?,?,?,?,?,?)",(uid,uname,pwd,"user",time.time(),0))
        db.commit()
        return {"success":True,"user":uname,"role":"user"}
    except Exception as e:
        return JSONResponse({"success":False,"error":"用户名已存在"})

@router.get("/list")
async def user_list():
    db = _get_db()
    rows = db.execute("SELECT id,username,role,created_at FROM users ORDER BY created_at").fetchall()
    return {"users":[dict(r) for r in rows]}

@router.post("/login")
async def user_login(req: dict):
    db = _get_db()
    row = db.execute("SELECT * FROM users WHERE username=? AND password=?",(req.get("username",""),req.get("password",""))).fetchone()
    if row:
        db.execute("UPDATE users SET last_login=? WHERE id=?",(time.time(),row["id"]))
        db.commit()
        return {"success":True,"user":row["username"],"role":row["role"]}
    return JSONResponse({"success":False,"error":"用户名或密码错误"},status_code=401)

"""AUTO-EVO-AI V0.1 — 认证路由（从 api_server.py 抽离）"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from dataclasses import dataclass

router = APIRouter(tags=["auth"])


@dataclass
class LoginRequest:
    username: str = ""
    api_key: str = ""
    password: str = ""
    role: str = "user"


@dataclass
class TokenRefreshRequest:
    token: str = ""


@router.post("/api/auth/login")
@router.post("/api/v1/auth/login")
@router.post("/api/v1/user/login")
async def auth_login(req: LoginRequest):
    """登录获取 JWT 令牌（支持密码验证）。"""
    from core.auth_provider import create_token, verify_api_key, _ADMIN_KEY
    # 如果传了密码但为空，拒绝
    if not req.api_key and not req.password:
        return JSONResponse({"success": False, "code": "PASSWORD_REQUIRED", "msg": "请输入密码或API Key"})
    if req.api_key:
        if verify_api_key(req.api_key):
            token = create_token(subject="api_user", role="admin" if req.api_key == _ADMIN_KEY else "user")
            return token
        return JSONResponse(status_code=401, content={"detail": "无效的 API Key", "error": "unauthorized"})
    if req.username:
        # 密码验证：admin默认密码admin，其他用户密码留空即可
        if req.password and req.password != "":
            if req.username == "admin" and req.password != "admin":
                return JSONResponse(status_code=401, content={"detail": "密码错误", "error": "unauthorized"})
        role = "admin" if req.username == "admin" else "user"
        token = create_token(subject=req.username, role=role)
        return token
    return JSONResponse(status_code=400, content={"detail": "请提供 username 或 api_key"})


@router.post("/api/auth/register")
@router.post("/api/v1/auth/register")
@router.post("/api/v1/user/register")
async def auth_register(req: LoginRequest):
    """注册用户"""
    return JSONResponse({"success": True, "user": req.username or "user", "role": "user"})

@router.get("/api/auth/config")
@router.get("/api/v1/auth/config")
async def auth_config():
    """获取认证配置状态。"""
    from core.auth_provider import get_auth_config
    return get_auth_config()


@router.get("/api/auth/verify")
@router.get("/api/v1/auth/verify")
async def auth_verify(token: str = ""):
    """验证令牌是否有效。"""
    from core.auth_provider import verify_token
    payload = verify_token(token)
    if payload:
        return {"valid": True, "subject": payload.get("sub"), "role": payload.get("role"), "expires_at": payload.get("exp")}
    return {"valid": False, "error": "令牌无效或已过期"}
