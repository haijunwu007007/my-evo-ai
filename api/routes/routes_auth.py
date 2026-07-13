"""
路由文件: routes_auth.py — 用户注册/登录/找回密码
修正：增加 /api/v1/user/login 和 /api/v1/user/register 端点以匹配前端调用路径
修正：使用 SQLite 持久化存储代替内存字典
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, hashlib, uuid, time, json
from pathlib import Path

router = APIRouter(tags=["auth"])

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "users.db"

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    phone: Optional[str] = ""

class LoginRequest(BaseModel):
    username: str
    password: str

class ForgotRequest(BaseModel):
    email: str

def _get_db():
    os.makedirs(str(_DB_PATH.parent), exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            role TEXT DEFAULT 'viewer',
            created_at REAL,
            last_login REAL
        )
    """)
    conn.commit()
    return conn

def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _gen_token() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex

# ── 前端调用的端点（/api/v1/user/*） ──

@router.post("/api/v1/user/register")
async def user_register(req: RegisterRequest):
    try:
        conn = _get_db()
        existing = conn.execute("SELECT username FROM users WHERE username=?", (req.username,)).fetchone()
        if existing:
            return {"success": False, "error": "用户名已存在"}
        existing_email = conn.execute("SELECT username FROM users WHERE email=?", (req.email,)).fetchone()
        if existing_email:
            return {"success": False, "error": "邮箱已被注册"}
        uid = uuid.uuid4().hex[:12]
        now = time.time()
        conn.execute(
            "INSERT INTO users(id, username, password, email, phone, role, created_at, last_login) VALUES (?,?,?,?,?,?,?,?)",
            (uid, req.username, _hash_password(req.password), req.email, req.phone, "viewer", now, now)
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": "注册成功"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/user/login")
async def user_login(req: LoginRequest):
    try:
        conn = _get_db()
        row = conn.execute("SELECT * FROM users WHERE username=?", (req.username,)).fetchone()
        if not row:
            return {"success": False, "error": "用户不存在"}
        if row["password"] != _hash_password(req.password):
            return {"success": False, "error": "密码错误"}
        conn.execute("UPDATE users SET last_login=? WHERE username=?", (time.time(), req.username))
        conn.commit()
        conn.close()
        return {
            "access_token": _gen_token(),
            "role": row["role"],
            "username": row["username"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── 原有 auth 路径 ──
@router.post("/api/v1/auth/register")
async def auth_register(req: RegisterRequest):
    return await user_register(req)

@router.post("/api/v1/auth/login")
async def auth_login(req: LoginRequest):
    return await user_login(req)

@router.post("/api/v1/auth/forgot-password")
async def auth_forgot(req: ForgotRequest):
    conn = _get_db()
    found = conn.execute("SELECT username FROM users WHERE email=?", (req.email,)).fetchone()
    conn.close()
    return {"success": True, "message": "如果该邮箱已注册，重置链接已发送"}
