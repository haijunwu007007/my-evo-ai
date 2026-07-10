"""core_plugins — 插件/工作流API/MCP/Rerank/自愈/连接器"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import os, time, json, sqlite3, httpx
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.features.plugins")
router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DB = BASE_DIR / "core" / "adaptive_engine.db"

# -- 10. 插件商店 --
@router.get("/api/v1/plugins")
async def list_plugins():
    installed = []
    plugins_dir = Path(__file__).resolve().parent.parent.parent / "plugins"
    if plugins_dir.exists():
        for p in plugins_dir.iterdir():
            if p.is_dir() and (p / "plugin.json").exists():
                try: installed.append(json.load(open(p/"plugin.json")))
                except: pass
    return {"success": True, "plugins": installed, "count": len(installed)}

# -- 11. 工作流 API --
@router.get("/api/v1/workflow/list")
async def list_workflows():
    conn = sqlite3.connect(str(_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS workflows (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, data TEXT, created_at REAL, updated_at REAL)")
    rows = conn.execute("SELECT id, name, description, created_at, updated_at FROM workflows ORDER BY updated_at DESC LIMIT 50").fetchall()
    conn.close()
    return {"success": True, "workflows": [{"id":r[0],"name":r[1],"desc":r[2],"created":r[3],"updated":r[4]} for r in rows]}

class WfCreate(BaseModel):
    name: str; description: Optional[str] = ""; nodes: list = []; edges: list = []

@router.post("/api/v1/workflow/save")
async def save_workflow(req: WfCreate):
    conn = sqlite3.connect(str(_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS workflows (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, data TEXT, created_at REAL, updated_at REAL)")
    data = json.dumps({"nodes": [n.model_dump() for n in req.nodes] if hasattr(req,'nodes') else [], "edges": [e.model_dump() for e in req.edges] if hasattr(req,'edges') else []})
    now = time.time()
    existing = conn.execute("SELECT id FROM workflows WHERE name=?", (req.name,)).fetchone()
    if existing:
        conn.execute("UPDATE workflows SET description=?, data=?, updated_at=? WHERE id=?", (req.description, data, now, existing[0]))
        wid = existing[0]
    else:
        conn.execute("INSERT INTO workflows (name, description, data, created_at, updated_at) VALUES (?,?,?,?,?)", (req.name, req.description, data, now, now))
        wid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit(); conn.close()
    return {"success": True, "id": wid, "name": req.name}

@router.get("/api/v1/workflow/get/{wid}")
async def get_workflow(wid: int):
    conn = sqlite3.connect(str(_DB))
    row = conn.execute("SELECT name, description, data FROM workflows WHERE id=?", (wid,)).fetchone()
    conn.close()
    if not row: return {"success": False, "detail": "Workflow not found"}
    return {"success": True, "name": row[0], "description": row[1], "data": json.loads(row[2])}

@router.delete("/api/v1/workflow/delete/{wid}")
async def delete_workflow(wid: int):
    conn = sqlite3.connect(str(_DB))
    conn.execute("DELETE FROM workflows WHERE id=?", (wid,))
    conn.commit(); conn.close()
    return {"success": True}

WF_NODE_TYPES = {
    "input": {"label": "input", "color": "#4CAF50", "desc": "user input"},
    "llm": {"label": "LLM", "color": "#4361ee", "desc": "llm call"},
    "output": {"label": "output", "color": "#e63946", "desc": "result output"},
}
@router.get("/api/v1/workflow/nodetypes")
async def get_node_types():
    return {"success": True, "types": WF_NODE_TYPES}

# -- 12. MCP --
MCP_TOOLS = {}
class MCPToolDef(BaseModel):
    name: str; description: str; endpoint: str
    parameters: Optional[dict] = {}; api_key: Optional[str] = ""

@router.post("/api/v1/mcp/register")
async def register_mcp_tool(tool: MCPToolDef):
    MCP_TOOLS[tool.name] = tool.model_dump()
    return {"success": True, "result": "MCP tool registered: " + tool.name}

@router.get("/api/v1/mcp/tools")
async def list_mcp_tools():
    return {"success": True, "tools": list(MCP_TOOLS.values()), "count": len(MCP_TOOLS)}

@router.post("/api/v1/mcp/execute")
async def execute_mcp_tool(name: str = "", params: str = "{}"):
    if name not in MCP_TOOLS:
        return {"success": False, "detail": "Unknown MCP tool: " + name}
    tool = MCP_TOOLS[name]
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            headers = {"Content-Type": "application/json"}
            if tool.get("api_key"): headers["Authorization"] = "Bearer " + tool["api_key"]
            resp = await c.post(tool["endpoint"], json=json.loads(params), headers=headers)
            return {"success": True, "result": resp.text[:2000], "status": resp.status_code}
    except Exception as e:
        return {"success": False, "detail": str(e)}

# -- 13. Rerank --
class RerankRequest(BaseModel):
    query: str = ""; candidates: list = []

@router.post("/api/v1/rerank")
async def rerank_results(req: RerankRequest):
    if not req.query or not req.candidates:
        return {"success": False, "detail": "need query and candidates"}
    qw = set(req.query.lower().split())
    scored = []
    for i, doc in enumerate(req.candidates):
        text = (doc.get("title","") + " " + doc.get("content","") + " " + doc.get("text","")).lower()
        hits = sum(1 for w in qw if w in text)
        scored.append({"index": i, "doc": doc, "score": hits + max(0, 10-i)*0.1, "hits": hits})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"success": True, "results": scored, "total": len(scored)}

# -- 14. SelfHeal --
@router.post("/api/v1/selfheal/log")
async def log_error(module: str = "", error: str = "", context: str = ""):
    conn = sqlite3.connect(str(_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS error_log (id INTEGER PRIMARY KEY AUTOINCREMENT, module TEXT, error TEXT, context TEXT, count INTEGER DEFAULT 1, last_seen REAL)")
    existing = conn.execute("SELECT id, count FROM error_log WHERE module=? AND error=?", (module, error[:200])).fetchone()
    if existing:
        conn.execute("UPDATE error_log SET count=count+1, last_seen=? WHERE id=?", (time.time(), existing[0]))
    else:
        conn.execute("INSERT INTO error_log (module, error, context, count, last_seen) VALUES (?,?,?,1,?)", (module, error[:200], context[:500], time.time()))
    conn.commit(); conn.close()
    return {"success": True}

@router.get("/api/v1/selfheal/report")
async def selfheal_report():
    conn = sqlite3.connect(str(_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS error_log (id INTEGER PRIMARY KEY AUTOINCREMENT, module TEXT, error TEXT, context TEXT, count INTEGER DEFAULT 1, last_seen REAL)")
    rows = conn.execute("SELECT module, error, count, last_seen FROM error_log ORDER BY count DESC LIMIT 20").fetchall()
    conn.close()
    items = []
    suggestions = {
        "NameError": "check imports",
        "ModuleNotFoundError": "check requirements.txt",
        "Timeout": "increase timeout or use retry",
    }
    for r in rows:
        sug = "check module " + r[0]
        for key, s in suggestions.items():
            if key in r[1]: sug = s; break
        items.append({"module": r[0], "error": r[1], "count": r[2], "last_seen": r[3], "suggestion": sug})
    return {"success": True, "errors": items, "total": len(items)}

# -- 15. Connectors --
CONNECTORS = {}
class ConnectorDef(BaseModel):
    name: str; type: str; description: str; endpoint: str
    auth_type: str = "none"; auth_config: Optional[dict] = {}

@router.post("/api/v1/connectors/register")
async def register_connector(conn: ConnectorDef):
    CONNECTORS[conn.name] = conn.model_dump()
    return {"success": True, "result": "Connector registered: " + conn.name}

@router.get("/api/v1/connectors")
async def list_connectors():
    builtin = [
        {"name": "GitHub API", "type": "api", "description": "GitHub"},
        {"name": "Slack Webhook", "type": "webhook", "description": "Slack"},
        {"name": "钉钉机器人", "type": "webhook", "description": "DingTalk"},
        {"name": "MySQL", "type": "database", "description": "MySQL"},
        {"name": "OpenAI API", "type": "api", "description": "GPT"},
        {"name": "DeepSeek", "type": "api", "description": "DeepSeek"},
    ]
    all_conn = builtin + list(CONNECTORS.values())
    return {"success": True, "connectors": all_conn, "builtin_count": len(builtin), "custom_count": len(CONNECTORS), "total": len(all_conn)}
