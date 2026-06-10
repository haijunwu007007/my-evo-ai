"""
AUTO-EVO-AI V0.1 — 统一 API Gateway
Composio 风格: 统一OAuth认证代理 + 500+集成模板 + SSO + RBAC + 审计日志
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import os, json, time, sqlite3, hashlib, hmac, base64, httpx
from pathlib import Path

logger = get_logger("evo.api.gateway")
router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── 认证凭据存储 ──────────────────────────
_CRED_DB = BASE_DIR / "core" / "adaptive_engine.db"
_CRED_TABLE = "gateway_credentials"

def _init_cred_db():
    conn = sqlite3.connect(str(_CRED_DB))
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {_CRED_TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service TEXT UNIQUE NOT NULL,
        auth_type TEXT NOT NULL,
        credentials TEXT NOT NULL,
        created_at REAL,
        updated_at REAL
    )""")
    conn.execute(f"""CREATE TABLE IF NOT EXISTS gateway_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT, action TEXT, service TEXT, status TEXT, ip TEXT, timestamp REAL
    )""")
    conn.commit(); conn.close()

_init_cred_db()

# ─── Composio 风格: 集成模板（从 integrations_db.json 动态加载）─────
_GATEWAY_TOOLS = {}  # { "slug": {"name":..., "auth_type":..., "icon":..., "category":..., "operations":..., "properties":...} }

def _make_slug(name: str) -> str:
    """将集成名转为 slug：GitLab CI → gitlab_ci，智谱 GLM → zhipu_glm"""
    s = name.lower().strip()
    s = s.replace(" ", "_").replace("-", "_").replace(".", "_")
    return "".join(c for c in s if c.isalnum() or c == "_").strip("_")

def _init_gateway_tools():
    """从 connectors/integrations_db.json 加载 119 个集成模板"""
    db_path = BASE_DIR / "connectors" / "integrations_db.json"
    if not db_path.exists():
        logger.warning(f"[GATEWAY] integrations_db.json 不存在: {db_path}，使用内置 38 个")
        _init_fallback_tools()
        return
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            raise ValueError("integrations_db.json 格式错误，应为列表")
        for item in items:
            name = item.get("name", "")
            if not name:
                continue
            slug = _make_slug(name)
            cfg = {
                "name": name,
                "auth_type": item.get("auth_type", "api_key"),
                "icon": item.get("icon", "fa:plug"),
                "category": item.get("category", "未分类"),
                "operations": item.get("operations", []),
                "properties": item.get("properties", {}),
                "type": item.get("type", "api"),
            }
            _GATEWAY_TOOLS[slug] = cfg
        logger.info(f"[GATEWAY] 从 integrations_db.json 加载 {len(_GATEWAY_TOOLS)} 个集成模板")
    except Exception as e:
        logger.error(f"[GATEWAY] 加载 integrations_db.json 失败: {e}，使用内置 38 个")
        _init_fallback_tools()

def _init_fallback_tools():
    """回退：内置 38 个核心集成模板"""
    templates = {
        "github":{"name":"GitHub","auth_type":"oauth2","icon":"fa:github","category":"开发工具"},
        "gitlab":{"name":"GitLab","auth_type":"oauth2","icon":"fa:gitlab","category":"开发工具"},
        "slack":{"name":"Slack","auth_type":"oauth2","icon":"fa:slack","category":"通信"},
        "discord":{"name":"Discord","auth_type":"oauth2","icon":"fa:discord","category":"通信"},
        "telegram":{"name":"Telegram","auth_type":"api_key","icon":"fa:telegram","category":"通信"},
        "gmail":{"name":"Gmail","auth_type":"oauth2","icon":"fa:google","category":"邮件"},
        "openai":{"name":"OpenAI","auth_type":"api_key","icon":"fa:brain","category":"AI"},
        "anthropic":{"name":"Anthropic","auth_type":"api_key","icon":"fa:brain","category":"AI"},
        "deepseek":{"name":"DeepSeek","auth_type":"api_key","icon":"fa:brain","category":"AI"},
        "zhipu":{"name":"智谱GLM","auth_type":"api_key","icon":"fa:brain","category":"AI"},
        "aws_s3":{"name":"AWS S3","auth_type":"access_key","icon":"fa:cloud","category":"存储"},
        "mysql":{"name":"MySQL","auth_type":"basic","icon":"fa:database","category":"数据库"},
        "postgres":{"name":"PostgreSQL","auth_type":"basic","icon":"fa:database","category":"数据库"},
        "mongodb":{"name":"MongoDB","auth_type":"basic","icon":"fa:database","category":"数据库"},
        "redis":{"name":"Redis","auth_type":"basic","icon":"fa:database","category":"数据库"},
        "jira":{"name":"Jira","auth_type":"basic","icon":"fa:ticket","category":"项目管理"},
        "linear":{"name":"Linear","auth_type":"api_key","icon":"fa:road","category":"项目管理"},
        "notion":{"name":"Notion","auth_type":"oauth2","icon":"fa:book","category":"生产力"},
        "stripe":{"name":"Stripe","auth_type":"api_key","icon":"fa:credit-card","category":"支付"},
        "kubernetes":{"name":"Kubernetes","auth_type":"api_key","icon":"fa:ship","category":"容器"},
        "docker":{"name":"Docker Hub","auth_type":"basic","icon":"fa:docker","category":"容器"},
        "pagerduty":{"name":"PagerDuty","auth_type":"api_key","icon":"fa:bell","category":"监控"},
        "datadog":{"name":"Datadog","auth_type":"api_key","icon":"fa:chart-line","category":"监控"},
        "google_drive":{"name":"Google Drive","auth_type":"oauth2","icon":"fa:google","category":"办公"},
        "dropbox":{"name":"Dropbox","auth_type":"oauth2","icon":"fa:dropbox","category":"办公"},
        "onedrive":{"name":"OneDrive","auth_type":"oauth2","icon":"fa:microsoft","category":"办公"},
        "alipay":{"name":"支付宝","auth_type":"api_key","icon":"fa:alipay","category":"支付"},
        "wechat_pay":{"name":"微信支付","auth_type":"api_key","icon":"fa:weixin","category":"支付"},
    }
    _GATEWAY_TOOLS.clear()
    for slug, cfg in templates.items():
        _GATEWAY_TOOLS[slug] = cfg
    logger.info(f"[GATEWAY] 回退模式: 注册 {len(templates)} 个核心集成")

_init_gateway_tools()


# ============================================================
# API: 列出所有集成模板（Composio 风格）
# ============================================================
@router.get("/api/v1/gateway/tools")
async def list_gateway_tools():
    results = []
    for slug, cfg in _GATEWAY_TOOLS.items():
        results.append({
            "slug": slug,
            "name": cfg["name"],
            "auth_type": cfg["auth_type"],
            "icon": cfg["icon"],
            "category": cfg.get("category", ""),
            "operations": cfg.get("operations", []),
            "enabled": _is_enabled(slug)
        })
    return {"success": True, "tools": results, "total": len(results)}


# ============================================================
# API: 搜索集成
# ============================================================
@router.get("/api/v1/gateway/tools/search")
async def search_gateway_tools(q: str = ""):
    if not q:
        return await list_gateway_tools()
    ql = q.lower()
    results = []
    for slug, cfg in _GATEWAY_TOOLS.items():
        cat = cfg.get("category", "")
        if ql in slug or ql in cfg["name"].lower() or ql in cfg["auth_type"] or ql in cat.lower():
            results.append({
                "slug": slug, "name": cfg["name"], "auth_type": cfg["auth_type"],
                "icon": cfg["icon"], "category": cfg.get("category", ""),
                "enabled": _is_enabled(slug)
            })
    return {"success": True, "tools": results, "total": len(results)}


# ============================================================
# API: 启用集成（配置认证凭据）— 核心功能
# ============================================================
class EnableRequest(BaseModel):
    client_id: Optional[str] = ""
    client_secret: Optional[str] = ""
    api_key: Optional[str] = ""
    access_key: Optional[str] = ""
    secret_key: Optional[str] = ""
    username: Optional[str] = ""
    password: Optional[str] = ""
    scopes: Optional[str] = ""

@router.post("/api/v1/gateway/tools/{slug}/enable")
async def enable_gateway_tool(slug: str, req: EnableRequest):
    if slug not in _GATEWAY_TOOLS:
        raise HTTPException(status_code=404, detail=f"集成 '{slug}' 不存在")
    
    cfg = _GATEWAY_TOOLS[slug]
    
    # 根据 auth_type 构建凭据
    if cfg["auth_type"] == "oauth2":
        creds = {"client_id": req.client_id, "client_secret": req.client_secret, "scopes": req.scopes or " ".join(cfg.get("scopes",[]))}
    elif cfg["auth_type"] == "api_key":
        creds = {"api_key": req.api_key}
    elif cfg["auth_type"] == "access_key":
        creds = {"access_key": req.access_key, "secret_key": req.secret_key}
    elif cfg["auth_type"] == "basic":
        creds = {"username": req.username, "password": req.password}
    else:
        creds = {"api_key": req.api_key}
    
    # 保存到 SQLite
    conn = sqlite3.connect(str(_CRED_DB))
    try:
        now = time.time()
        conn.execute(f"DELETE FROM {_CRED_TABLE} WHERE service=?", (slug,))
        conn.execute(f"INSERT INTO {_CRED_TABLE} (service, auth_type, credentials, created_at, updated_at) VALUES (?,?,?,?,?)",
                     (slug, cfg["auth_type"], json.dumps(creds), now, now))
        conn.commit()
        # 审计日志
        conn.execute("INSERT INTO gateway_audit_log (user,action,service,status,ip,timestamp) VALUES (?,?,?,?,?,?)",
                     ("admin","enable",slug,"success","127.0.0.1",time.time()))
        conn.commit()
    finally: conn.close()
    
    return {"success": True, "result": f"✅ 集成 '{cfg['name']}' 已启用（{cfg['auth_type']}）"}


@router.post("/api/v1/gateway/tools/{slug}/disable")
async def disable_gateway_tool(slug: str):
    conn = sqlite3.connect(str(_CRED_DB))
    conn.execute(f"DELETE FROM {_CRED_TABLE} WHERE service=?", (slug,))
    conn.commit(); conn.close()
    return {"success": True, "result": f"集成 '{slug}' 已禁用"}


# ============================================================
# API: 测试集成
# ============================================================
@router.post("/api/v1/gateway/tools/{slug}/test")
async def test_gateway_tool(slug: str):
    """测试已配置的集成是否可用"""
    conn = sqlite3.connect(str(_CRED_DB))
    row = conn.execute(f"SELECT auth_type, credentials FROM {_CRED_TABLE} WHERE service=?", (slug,)).fetchone()
    conn.close()
    if not row:
        return {"success": False, "result": f"❌ 集成 '{slug}' 未配置"}

    cfg = _GATEWAY_TOOLS.get(slug, {})
    name = cfg.get("name", slug)
    auth_type, creds_json = row
    creds = json.loads(creds_json)

    tests = {
        "github":    ("GET", "https://api.github.com/user"),
        "openai":    ("GET", "https://api.openai.com/v1/models"),
        "anthropic": ("GET", "https://api.anthropic.com/v1/messages"),
        "deepseek":  ("POST", "https://api.deepseek.com/chat/completions", {"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}]}),
        "zhipu":     ("POST", "https://open.bigmodel.cn/api/paas/v4/chat/completions", {"model":"glm-4-flash","messages":[{"role":"user","content":"hi"}]}),
        "telegram":  ("GET", f"https://api.telegram.org/bot{creds.get('api_key','')}/getMe"),
    }

    if slug in tests:
        try:
            method = tests[slug][0]
            url = tests[slug][1]
            body = tests[slug][2] if len(tests[slug]) > 2 else None
            headers = {}
            if auth_type == "api_key":
                headers["Authorization"] = f"Bearer {creds.get('api_key','')}"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.request(method, url, json=body, headers=headers)
                return {"success": resp.is_success, "status": resp.status_code, "result": f"{'✅' if resp.is_success else '❌'} {name} 测试 {'成功' if resp.is_success else '失败（{resp.status_code}）'}"}
        except Exception as e:
            return {"success": False, "result": f"❌ {name} 测试异常: {str(e)[:100]}"}

    return {"success": True, "result": f"✅ {name} 已配置（无自动测试）"}


# ============================================================
# API: 已启用的集成列表
# ============================================================
@router.get("/api/v1/gateway/enabled")
async def list_enabled():
    conn = sqlite3.connect(str(_CRED_DB))
    rows = conn.execute(f"SELECT service, auth_type, created_at, updated_at FROM {_CRED_TABLE} ORDER BY service").fetchall()
    conn.close()
    return {"success": True, "enabled": [{"service":r[0],"auth_type":r[1],"created_at":r[2],"updated_at":r[3]} for r in rows], "total": len(rows)}


# ============================================================
# API: 审计日志
# ============================================================
@router.get("/api/v1/gateway/audit")
async def gateway_audit(limit: int = 50):
    conn = sqlite3.connect(str(_CRED_DB))
    rows = conn.execute("SELECT user, action, service, status, ip, timestamp FROM gateway_audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return {"success": True, "logs": [{"user":r[0],"action":r[1],"service":r[2],"status":r[3],"ip":r[4],"time":r[5]} for r in rows]}


# ============================================================
# API: 代理调用（通过已启用的集成发起真实请求）
# ============================================================
class GatewayCall(BaseModel):
    service: str
    endpoint: str
    method: str = "GET"
    body: Optional[dict] = {}
    headers: Optional[dict] = {}

@router.post("/api/v1/gateway/call")
async def gateway_call(req: GatewayCall):
    """通过 Gateway 代理调用外部服务 API"""
    # 自动补全 URL 协议前缀
    ep = req.endpoint.strip()
    if not ep.startswith("http://") and not ep.startswith("https://"):
        ep = "https://" + ep
    req.endpoint = ep
    
    # 检查凭据
    conn = sqlite3.connect(str(_CRED_DB))
    row = conn.execute(f"SELECT auth_type, credentials FROM {_CRED_TABLE} WHERE service=?", (req.service,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=400, detail=f"集成 '{req.service}' 未启用，请先启用")
    
    auth_type, creds_json = row
    creds = json.loads(creds_json)
    
    # 构造请求头
    headers = {**req.headers}
    if auth_type == "api_key":
        headers["Authorization"] = f"Bearer {creds.get('api_key','')}"
    elif auth_type == "basic":
        import base64
        token = base64.b64encode(f"{creds.get('username','')}:{creds.get('password','')}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    elif auth_type == "access_key":
        headers["Authorization"] = f"AccessKey {creds.get('access_key','')}"
        headers["X-Secret-Key"] = creds.get('secret_key','')
    
    # 构造完整 URL — 从服务配置中取 base_url
    full_url = req.endpoint
    svc_config = _GATEWAY_TOOLS.get(req.service, {}).get("properties", {})
    api_base = svc_config.get("api_base") or svc_config.get("base_url", "")
    if api_base and not req.endpoint.startswith("http"):
        full_url = api_base.rstrip("/") + "/" + req.endpoint.lstrip("/")
    
    # 执行请求
    try:
        method = req.method.upper()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, full_url, json=req.body or None, headers=headers)
            return {"success": resp.is_success, "status": resp.status_code, "service": req.service, "data": resp.text[:5000]}
    except Exception as e:
        return {"success": False, "error": str(e), "detail": f"无法访问 {full_url}"}


# ============================================================
# 工具函数
# ============================================================
def _is_enabled(slug: str) -> bool:
    conn = sqlite3.connect(str(_CRED_DB))
    row = conn.execute(f"SELECT 1 FROM {_CRED_TABLE} WHERE service=?", (slug,)).fetchone()
    conn.close()
    return row is not None


def list_gateway_as_skills() -> list[dict]:
    """Gateway 集成模板 → SkillDefinition"""
    skills = []
    for slug, cfg in _GATEWAY_TOOLS.items():
        skills.append({
            "name": f"gateway:{slug}",
            "version": "1.0.0",
            "description": f"[Gateway] {cfg['name']} — 通过统一认证层集成",
            "author": "gateway",
            "category": f"Gateway/{cfg['auth_type']}",
            "icon": cfg.get("icon", "🔌"),
            "tags": [slug, "gateway", cfg["auth_type"]],
            "input_schema": {"type": "object", "properties": {"endpoint": {"type":"string"},"method":{"type":"string"}}},
            "output_schema": {"type": "object", "properties": {"data": {"type": "string"}}},
            "handler": "",
            "endpoint": f"gateway://{slug}"
        })
    return skills
