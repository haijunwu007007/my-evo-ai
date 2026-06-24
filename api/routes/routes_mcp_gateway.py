
import hashlib
def _check_auth(req):
    """简单API Key认证"""
    key = req.headers.get("X-API-Key", "") or req.query_params.get("api_key", "")
    expected = os.environ.get("MCP_GATEWAY_KEY", "evo-mcp-default")
    return key == expected
"""
万能MCP聚合网关 — 连接 Smithery / MCP.so / Glama 三大MCP市场
支持一键搜索、安装、执行外部MCP服务器
"""
import os,hashlib, json, logging, subprocess, tempfile, urllib.request
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("mcp_gateway")
router = APIRouter(prefix="/api/v1/mcp-gateway", tags=["mcp_gateway"])

REGISTRIES = {
    "smithery": "https://registry.smithery.ai/servers",
    "mcplist": "https://raw.githubusercontent.com/punkpeye/awesome-mcp-servers/main/README.md",
}

class SearchQuery(BaseModel):
    q: str = ""
    platform: str = "smithery"
    limit: int = 20

class InstallRequest(BaseModel):
    name: str
    platform: str = "smithery"

_mcp_cache = {"servers": [], "skills": []}

@router.get("/status")
def status():
    return {"success": True, "platforms": list(REGISTRIES.keys()), "cached_servers": len(_mcp_cache["servers"])}

@router.post("/search")
def search_mcp(req: SearchQuery):
    results = []
    if req.platform == "smithery":
        try:
            r = urllib.request.urlopen(REGISTRIES["smithery"], timeout=10)
            data = json.loads(r.read())
            servers = data if isinstance(data, list) else data.get("servers", data.get("data", []))
            for s in servers:
                name = s.get("name", s.get("id", str(s)))[:100]
                desc = s.get("description", "")[:200]
                if not req.q or req.q.lower() in name.lower() or req.q.lower() in desc.lower():
                    results.append({"name": name, "description": desc, "platform": "smithery"})
        except Exception as e:
            logger.warning(f"Smithery search failed: {e}")
    if not results and req.platform == "mcplist":
        try:
            r = urllib.request.urlopen(REGISTRIES["mcplist"], timeout=10)
            html = r.read().decode()
            import re
            for m in re.finditer(r'\[([^\]]+)\]\(https?://github\.com/([^)]+)\)', html):
                if not req.q or req.q.lower() in m.group(1).lower():
                    results.append({"name": m.group(1), "repo": m.group(2), "platform": "mcplist"})
        except: pass
    _mcp_cache["servers"] = results
    return {"success": True, "total": len(results), "results": results[:req.limit]}

@router.post("/install")
def install_mcp(req: InstallRequest):
    try:
        result = subprocess.run(
            ["npx", "-y", "@smithery/cli@latest", "install", req.name, "--client", "claude"],
            capture_output=True, text=True, timeout=60
        )
        return {"success": result.returncode == 0, "output": result.stdout[-300:]}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

@router.get("/convert/{repo:path}")
def convert_repo(repo: str):
    """GitMCP: 任意GitHub仓库→MCP工具"""
    try:
        r = urllib.request.urlopen(f"https://gitmcp.io/{repo}", timeout=15)
        tools = json.loads(r.read())
        _mcp_cache["servers"].append({"name": repo, "type": "gitmcp", "tools": tools})
        return {"success": True, "repo": repo, "tools": tools}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

@router.get("/discover")
def discover_all():
    """发现所有本地可用的外部MCP服务器"""
    results = _mcp_cache["servers"]
    return {"success": True, "total": len(results), "results": results[:50]}
