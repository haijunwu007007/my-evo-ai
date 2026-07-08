"""
路由文件: routes_auth.py — 用户注册/登录/找回密码
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["auth"])

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class ForgotRequest(BaseModel):
    email: str

# 内存用户存储（重启清空，生产环境应使用数据库）
_users = {}  # username -> {email, password, role}

@router.post("/api/v1/auth/register")
async def auth_register(req: RegisterRequest):
    if req.username in _users:
        return {"success": False, "error": "用户名已存在"}
    if any(u["email"] == req.email for u in _users.values()):
        return {"success": False, "error": "邮箱已被注册"}
    _users[req.username] = {"email": req.email, "password": req.password, "role": "viewer"}
    return {"success": True, "message": "注册成功"}

@router.post("/api/v1/auth/forgot-password")
async def auth_forgot(req: ForgotRequest):
    found = any(u["email"] == req.email for u in _users.values())
    # 无论是否存在都返回成功（防止邮箱枚举）
    return {"success": True, "message": "如果该邮箱已注册，重置链接已发送"}
