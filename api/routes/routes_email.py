"""
Email/SMTP 配置路由
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from api._rbac import require_role

router = APIRouter(tags=["email"])

@router.get("/api/v1/email/config")
async def get_email_config(req: Request):
    from core.email_sender import get_config
    role = getattr(req.state, "role", None)
    if role is None and hasattr(req, 'headers'):
        role = req.headers.get('X-User-Role', 'viewer')
    cfg = get_config()
    if 'password' in cfg:
        cfg['password'] = '****' if cfg['password'] else ''
    return JSONResponse(cfg)

@router.post("/api/v1/email/config")
async def save_email_config(req: Request):
    data = await req.json()
    from core.email_sender import save_config
    result = save_config(
        host=data.get('host', ''),
        port=int(data.get('port', 587)),
        user=data.get('user', ''),
        password=data.get('password', ''),
        from_addr=data.get('from_addr', '')
    )
    return JSONResponse(result)

@router.post("/api/v1/email/test")
async def test_email(req: Request):
    data = await req.json()
    to = data.get('to', '')
    if not to:
        return JSONResponse({"success": False, "error": "Missing recipient"})
    from core.email_sender import send_email
    result = send_email(to, 'AUTO-EVO-AI Test Email', '<h2>Test OK</h2><p>Your SMTP config is working.</p>')
    return JSONResponse(result)
