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
        email TEXT, phone TEXT, created_at REAL, last_login REAL
    )""")
    # 迁移：给旧表加列（不会报错如果已存在）
    for col in ["email", "phone"]:
        try: conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT ''")
        except: pass
    conn.execute("""CREATE TABLE IF NOT EXISTS reset_tokens(
        id TEXT PRIMARY KEY, user_id TEXT, token TEXT, expires REAL, used INTEGER DEFAULT 0
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
    email = req.get("email", "").strip()
    phone = req.get("phone", "").strip()
    if not uname or len(uname) < 2: return JSONResponse({"success":False,"error":"用户名至少2位"})
    if not pwd or len(pwd) < 3: return JSONResponse({"success":False,"error":"密码至少3位"})
    if not email and not phone: return JSONResponse({"success":False,"error":"邮箱或手机号至少填一个"})
    try:
        uid = hashlib.md5((uname+str(time.time())).encode()).hexdigest()[:12]
        db.execute("INSERT INTO users(id,username,password,role,email,phone,created_at,last_login) VALUES(?,?,?,?,?,?,?,?)",
                   (uid,uname,_hash_pwd(pwd),"user",email,phone,time.time(),0))
        db.commit()
        return {"success":True,"user":uname,"role":"user","message":"注册成功"}
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

@router.post("/api/v1/user/password-reset/request")
async def password_reset_request(req: dict):
    """请求密码重置：通过邮箱或手机号发送重置码"""
    db = _get_db()
    email = req.get("email", "").strip()
    phone = req.get("phone", "").strip()
    if not email and not phone:
        return JSONResponse({"success":False,"error":"请输入注册时填写的邮箱或手机号"})
    # 查找用户
    if email:
        row = db.execute("SELECT id,username FROM users WHERE email=?", (email,)).fetchone()
    else:
        row = db.execute("SELECT id,username FROM users WHERE phone=?", (phone,)).fetchone()
    if not row:
        return JSONResponse({"success":False,"error":"未找到该账号"})
    # 生成重置令牌（有效期30分钟）
    token = secrets.token_hex(16)
    tid = hashlib.md5((token+str(time.time())).encode()).hexdigest()[:12]
    db.execute("INSERT INTO reset_tokens(id,user_id,token,expires,used) VALUES(?,?,?,?,0)",
               (tid, row["id"], token, time.time() + 1800))
    db.commit()
    # 生产环境这里应发邮件/短信，demo 模式直接返回 token
    return {"success":True,"reset_token":token,"user":row["username"],
            "message":"重置码已生成（演示模式直接返回token，生产环境通过邮件/短信发送）"}

@router.post("/api/v1/user/password-reset/reset")
async def password_reset_confirm(req: dict):
    """使用重置令牌设置新密码"""
    db = _get_db()
    token = req.get("token", "").strip()
    new_pwd = req.get("new_password", "").strip()
    if not token or len(token) < 8:
        return JSONResponse({"success":False,"error":"无效的重置码"})
    if not new_pwd or len(new_pwd) < 3:
        return JSONResponse({"success":False,"error":"新密码至少3位"})
    row = db.execute(
        "SELECT * FROM reset_tokens WHERE token=? AND used=0 AND expires>?",
        (token, time.time())
    ).fetchone()
    if not row:
        return JSONResponse({"success":False,"error":"重置码已过期或已使用"})
    # 更新密码
    db.execute("UPDATE reset_tokens SET used=1 WHERE id=?", (row["id"],))
    db.execute("UPDATE users SET password=? WHERE id=?", (_hash_pwd(new_pwd), row["user_id"]))
    db.commit()
    return {"success":True,"message":"密码已重置，请用新密码登录"}

# ════════════════════════════════════════════
# 3. SSO — 企业微信 / 钉钉
# ════════════════════════════════════════════

@router.get("/api/v1/auth/sso/config")
async def sso_config():
    """获取 SSO 登录配置"""
    wx_corp_id = os.environ.get("WECHAT_CORP_ID", "")
    wx_agent_id = os.environ.get("WECHAT_AGENT_ID", "")
    dingtalk_app_id = os.environ.get("DINGTALK_APP_ID", "")
    return {
        "success": True,
        "wechat_work": {"enabled": bool(wx_corp_id and wx_agent_id), "corp_id": wx_corp_id},
        "dingtalk": {"enabled": bool(dingtalk_app_id), "app_id": dingtalk_app_id},
    }

@router.get("/api/v1/auth/sso/wechat")
async def sso_wechat(code: str = ""):
    """企业微信 OAuth 登录回调"""
    corp_id = os.environ.get("WECHAT_CORP_ID", "")
    corp_secret = os.environ.get("WECHAT_CORP_SECRET", "")
    if not corp_id or not corp_secret:
        return JSONResponse({"success": False, "error": "企业微信未配置"})
    if not code:
        # 跳转到企业微信授权页
        redirect_uri = os.environ.get("EVO_DOMAIN", "https://autoevoai.com") + "/api/v1/auth/sso/wechat"
        auth_url = f"https://open.weixin.qq.com/connect/oauth2/authorize?appid={corp_id}&redirect_uri={redirect_uri}&response_type=code&scope=snsapi_base&state=STATE#wechat_redirect"
        return {"success": True, "redirect": auth_url}
    # 获取 access_token
    import httpx
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}")
        token_data = r.json()
        if token_data.get("errcode", -1) != 0:
            return JSONResponse({"success": False, "error": "企业微信认证失败"})
        access_token = token_data["access_token"]
        # 获取用户信息
        r2 = await c.get(f"https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?access_token={access_token}&code={code}")
        user_info = r2.json()
        if user_info.get("errcode", -1) != 0:
            return JSONResponse({"success": False, "error": "获取用户信息失败"})
        user_id = user_info.get("UserId", "")
        if not user_id:
            return JSONResponse({"success": False, "error": "未获取到用户ID"})
        # 自动注册/登录
        db = _get_db()
        row = db.execute("SELECT * FROM users WHERE username=?", (f"wechat_{user_id}",)).fetchone()
        if not row:
            uid = hashlib.md5((f"wechat_{user_id}" + str(time.time())).encode()).hexdigest()[:12]
            db.execute("INSERT INTO users(id,username,password,role,email,created_at,last_login) VALUES(?,?,?,?,?,?,?)",
                       (uid, f"wechat_{user_id}", _hash_pwd(secrets.token_hex(8)), "user", f"{user_id}@wechat.work", time.time(), time.time()))
            db.commit()
        else:
            db.execute("UPDATE users SET last_login=? WHERE username=?", (time.time(), f"wechat_{user_id}"))
            db.commit()
        from core.auth_provider import create_token
        return create_token(subject=f"wechat_{user_id}", role="user")

@router.get("/api/v1/auth/sso/dingtalk")
async def sso_dingtalk(authCode: str = ""):
    """钉钉 OAuth 登录回调"""
    app_id = os.environ.get("DINGTALK_APP_ID", "")
    app_secret = os.environ.get("DINGTALK_APP_SECRET", "")
    if not app_id or not app_secret:
        return JSONResponse({"success": False, "error": "钉钉未配置"})
    if not authCode:
        redirect_uri = os.environ.get("EVO_DOMAIN", "https://autoevoai.com") + "/api/v1/auth/sso/dingtalk"
        auth_url = f"https://login.dingtalk.com/oauth2/auth?client_id={app_id}&response_type=code&redirect_uri={redirect_uri}&scope=openid&state=STATE"
        return {"success": True, "redirect": auth_url}
    import httpx
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post("https://api.dingtalk.com/v1.0/oauth2/userAccessToken", json={
            "clientId": app_id, "clientSecret": app_secret, "code": authCode, "grantType": "authorization_code"
        })
        token_data = r.json()
        access_token = token_data.get("accessToken", "")
        if not access_token:
            return JSONResponse({"success": False, "error": "钉钉认证失败"})
        r2 = await c.get("https://api.dingtalk.com/v1.0/contact/users/me", headers={"x-acs-dingtalk-access-token": access_token})
        user_info = r2.json()
        user_id = user_info.get("openId", "") or user_info.get("unionId", "")
        nick = user_info.get("nick", user_id)
        if not user_id:
            return JSONResponse({"success": False, "error": "获取钉钉用户信息失败"})
        db = _get_db()
        row = db.execute("SELECT * FROM users WHERE username=?", (f"dingtalk_{user_id}",)).fetchone()
        if not row:
            uid = hashlib.md5((f"dingtalk_{user_id}" + str(time.time())).encode()).hexdigest()[:12]
            db.execute("INSERT INTO users(id,username,password,role,email,created_at,last_login) VALUES(?,?,?,?,?,?,?)",
                       (uid, f"dingtalk_{user_id}", _hash_pwd(secrets.token_hex(8)), "user", f"{user_id}@dingtalk", time.time(), time.time()))
            db.commit()
        else:
            db.execute("UPDATE users SET last_login=? WHERE username=?", (time.time(), f"dingtalk_{user_id}"))
            db.commit()
        from core.auth_provider import create_token
        return create_token(subject=f"dingtalk_{user_id}", role="user")

@router.get("/api/v1/auth/config")
@router.get("/api/auth/config")
async def auth_config():
    """获取认证配置状态"""
    try:
        from core.auth_provider import get_auth_config
        return get_auth_config()
    except:
        return {"success": True, "mode": "jwt"}
