"""
Role permission middleware - JWT + role check
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import jwt, time

JWT_SECRET = "evo-secret-key-2026"
ROLE_HIERARCHY = {"viewer": 1, "editor": 2, "admin": 3}

def create_token(username, role="admin"):
    return jwt.encode({"sub": username, "role": role, "iat": int(time.time()), "exp": int(time.time()) + 86400*7}, JWT_SECRET, algorithm="HS256")

def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except:
        return None

def check_role(required):
    req_level = ROLE_HIERARCHY.get(required, 0)
    async def middleware(request: Request, call_next):
        public = ["/", "/chat.html", "/api/v1/version", "/login", "/register", "/docs", "/openapi.json",
                  "/enterprise.html", "/admin", "/billion-os.html", "/faq", "/tutorial", "/editor",
                  "/install/install.sh", "/marketplace", "/bi", "/realtime", "/api-keys", "/team",
                  "/sw.js", "/manifest.json", "/chat_engine.js", "/i18n.js"]
        if request.url.path in public:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "")
        payload = decode_token(token) if token else None

        if not payload:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        role = payload.get("role", "viewer")
        if ROLE_HIERARCHY.get(role, 0) < req_level:
            return JSONResponse({"error": "Forbidden"}, status_code=403)

        return await call_next(request)
    return middleware
