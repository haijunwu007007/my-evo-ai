"""
AUTO-EVO-AI V0.1 — 万能 MCPize 集成桥
任何软件/网站/API/命令行 → MCP 工具 / Skill
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import os, json, time, subprocess, sys, re, urllib.request, urllib.parse
from pathlib import Path
import importlib.util, inspect, httpx

logger = get_logger("evo.api.mcpize")
router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
MCPIZE_DIR = BASE_DIR / "mcpize"
MCPIZE_DIR.mkdir(exist_ok=True)

# 注册表：{ "name": { type, config, created_at, tools: [...] } }
_INTEGRATED: dict = {}

# ============================================================
# 1. 网站 → MCP 工具
# ============================================================
class WebsiteSpec(BaseModel):
    url: str
    name: str = ""

@router.post("/api/v1/mcpize/website")
async def mcpize_website(spec: WebsiteSpec):
    """把任意网站封装为 MCP 工具"""
    url = spec.url
    name = spec.name
    if not url:
        return {"success": False, "detail": "需要提供 url 参数"}
    slug = name or re.sub(r'[^a-z0-9]', '-', url.split('//')[-1].split('/')[0].split('.')[-2] if '.' in url else url[:20].lower())
    
    tools = [
        {"name": f"{slug}_scrape", "description": f"抓取 {url} 的页面内容", "inputSchema": {"type":"object","properties":{"path":{"type":"string","description":"页面路径"}}}},
        {"name": f"{slug}_search", "description": f"在 {url} 上搜索关键词", "inputSchema": {"type":"object","properties":{"q":{"type":"string","description":"搜索词"}}}}
    ]
    
    entry = {
        "type": "website", "source": url, "name": slug, "created_at": time.time(),
        "tools": tools, "tool_count": len(tools)
    }
    _INTEGRATED[slug] = entry
    _save_entry(slug, entry)
    
    return {"success": True, "result": f"网站 {url} 已封装为 MCP 工具集（{len(tools)} 个工具）", "slug": slug, "tools": tools}

# ============================================================
# 2. API → MCP 工具
# ============================================================
class APISpec(BaseModel):
    url: str
    method: str = "GET"
    headers: dict = {}
    description: str = ""

@router.post("/api/v1/mcpize/api")
async def mcpize_api(spec: APISpec):
    """把任意 REST API 封装为 MCP 工具"""
    slug = re.sub(r'[^a-z0-9]', '-', spec.url.split('//')[-1].split('/')[0].split('.')[0]) + "-api"
    
    tools = [
        {"name": f"{slug}_call", "description": spec.description or f"调用 {spec.method} {spec.url}", "inputSchema": {"type":"object","properties":{
            "params": {"type":"object","description":"请求参数"},
            "headers": {"type":"object","description":"额外请求头"}
        }}}
    ]
    
    entry = {
        "type": "api", "source": spec.url, "name": slug, "method": spec.method,
        "headers": spec.headers, "created_at": time.time(),
        "tools": tools, "tool_count": len(tools)
    }
    _INTEGRATED[slug] = entry
    _save_entry(slug, entry)
    
    return {"success": True, "result": f"API {spec.method} {spec.url} 已封装为 MCP 工具", "slug": slug, "tools": tools}

# ============================================================
# 3. 命令行 → MCP 工具
# ============================================================
class CLISpec(BaseModel):
    command: str
    name: str = ""

@router.post("/api/v1/mcpize/cli")
async def mcpize_cli(spec: CLISpec):
    """把任意命令行工具封装为 MCP 工具"""
    command = spec.command
    name = spec.name
    if not command:
        return {"success": False, "detail": "需要提供 command 参数"}
    slug = name or re.sub(r'[^a-z0-9]', '-', command.split()[0])
    
    tools = [
        {"name": f"{slug}_run", "description": f"执行命令: {command}", "inputSchema": {"type":"object","properties":{
            "args": {"type":"string","description":"命令行参数"},
            "timeout": {"type":"integer","description":"超时秒数", "default":30}
        }}}
    ]
    
    entry = {
        "type": "cli", "source": command, "name": slug, "created_at": time.time(),
        "tools": tools, "tool_count": len(tools)
    }
    _INTEGRATED[slug] = entry
    _save_entry(slug, entry)
    
    return {"success": True, "result": f"命令 `{command}` 已封装为 MCP 工具", "slug": slug, "tools": tools}

# ============================================================
# 4. Python 模块 → MCP 工具
# ============================================================
class PythonSpec(BaseModel):
    module: str
    name: str = ""

@router.post("/api/v1/mcpize/python")
async def mcpize_python(spec: PythonSpec):
    """把任意 Python 模块封装为 MCP 工具"""
    module = spec.module
    name = spec.name
    if not module:
        return {"success": False, "detail": "需要提供 module 参数"}
    slug = name or module.replace(".", "-")
    
    try:
        mod = importlib.import_module(module)
        funcs = [f for f in dir(mod) if callable(getattr(mod, f)) and not f.startswith('_')]
        sigs = {}
        for f in funcs[:10]:
            try:
                sig = inspect.signature(getattr(mod, f))
                sigs[f] = str(sig)
            except: sigs[f] = "(unknown)"
        
        tools = [{"name": f"{slug}_{f}", "description": f"调用 {module}.{f}{sigs.get(f,'')}", "inputSchema": {"type":"object","properties":{}}} for f in funcs[:10]]
    except Exception as e:
        tools = [{"name": f"{slug}_call", "description": f"调用 Python 模块 {module}", "inputSchema": {"type":"object","properties":{"func":{"type":"string"},"args":{"type":"object"}}}}]
        sigs = {"error": str(e)}
    
    entry = {
        "type": "python", "source": module, "name": slug, "created_at": time.time(),
        "tools": tools, "tool_count": len(tools), "signatures": sigs
    }
    _INTEGRATED[slug] = entry
    _save_entry(slug, entry)
    
    return {"success": True, "result": f"Python 模块 `{module}` 已封装为 MCP 工具（{len(tools)} 个函数）", "slug": slug, "tools": tools}

# ============================================================
# 5. 执行已集成的 MCP 工具
# ============================================================
class MCPizeExec(BaseModel):
    params: dict = {}
    args: Optional[dict] = None  # 兼容直接传 args

@router.post("/api/v1/mcpize/execute/{name}/{tool}")
async def mcpize_execute(name: str, tool: str, req: MCPizeExec):
    """执行已集成的 MCPize 工具"""
    if name not in _INTEGRATED:
        return {"success": False, "detail": f"未找到集成: {name}"}
    
    # 统一参数来源：params > args > {}
    call_params = req.params if req.params else (req.args if req.args else {})
    
    entry = _INTEGRATED[name]
    entry_type = entry["type"]
    
    try:
        if entry_type == "website":
            base_url = entry["source"]
            if "scrape" in tool:
                path = call_params.get("path", "")
                async with httpx.AsyncClient(timeout=15) as c:
                    r = await c.get(base_url + path, follow_redirects=True)
                    return {"success": True, "content": r.text[:2000]}
            elif "search" in tool:
                q = call_params.get("q", "")
                async with httpx.AsyncClient(timeout=15) as c:
                    r = await c.get(f"{base_url}/search?q={urllib.parse.quote(q)}", follow_redirects=True)
                    return {"success": True, "content": r.text[:2000]}
        
        elif entry_type == "api":
            method = entry.get("method", "GET")
            headers = entry.get("headers", {})
            url = entry["source"]
            async with httpx.AsyncClient(timeout=30) as c:
                if method == "GET":
                    r = await c.get(url, params=call_params, headers=headers)
                else:
                    r = await c.request(method, url, json=call_params, headers=headers)
                return {"success": True, "status": r.status_code, "content": r.text[:2000]}
        
        elif entry_type == "cli":
            cmd = entry["source"]
            args = call_params.get("args", "")
            timeout = int(call_params.get("timeout", 30))
            full_cmd = f"{cmd} {args}" if args else cmd
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return {"success": result.returncode == 0, "content": result.stdout[:2000], "stderr": result.stderr[:500]}
        
        elif entry_type == "python":
            mod_name = entry["source"]
            try:
                mod = importlib.import_module(mod_name)
                func_name = tool.replace(f"{name}_", "")
                if hasattr(mod, func_name):
                    func = getattr(mod, func_name)
                    py_args = call_params.get("args", call_params)
                    if isinstance(py_args, dict):
                        result = func(**py_args)
                    else:
                        result = func(py_args)
                    return {"success": True, "content": str(result)[:2000]}
                return {"success": False, "content": f"函数 {func_name} 不在模块 {mod_name} 中"}
            except Exception as e:
                return {"success": False, "content": f"执行失败: {e}"}
        
        return {"success": False, "content": f"不支持的类型: {entry_type}"}
    except Exception as e:
        return {"success": False, "content": f"错误: {type(e).__name__}: {str(e)[:200]}"}

# ============================================================
# 6. 状态/列表
# ============================================================
@router.get("/api/v1/mcpize/status")
async def mcpize_status():
    """列出所有已集成的 MCPize 工具"""
    items = []
    for name, entry in _INTEGRATED.items():
        items.append({"name": name, "type": entry["type"], "source": entry.get("source",""), "tool_count": entry.get("tool_count", 0), "created_at": entry.get("created_at", 0)})
    return {"success": True, "integrated": items, "total": len(items)}

# ============================================================
# 7. 存储
# ============================================================
def _save_entry(slug: str, entry: dict):
    try:
        (MCPIZE_DIR / f"{slug}.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    except: pass

def _load_all():
    for f in MCPIZE_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            _INTEGRATED[f.stem] = data
        except: pass

_load_all()

# ============================================================
# 8. MCPize → Skills 桥接
# ============================================================
def get_mcpize_skills() -> list[dict]:
    skills = []
    for name, entry in _INTEGRATED.items():
        for tool in entry.get("tools", []):
            skills.append({
                "name": f"mcpize:{name}/{tool['name']}",
                "version": "1.0.0",
                "description": f"[MCPize/{entry['type']}] {tool['description']}",
                "author": "mcpize-bridge",
                "category": f"MCPize/{entry['type']}",
                "icon": "🧩",
                "tags": [name, entry['type'], "mcpize"],
                "input_schema": tool.get("inputSchema", {"type":"object","properties":{}}),
                "output_schema": {"type":"object","properties":{"content":{"type":"string"}}},
                "handler": "",
                "endpoint": f"mcpize://{name}/{tool['name']}"
            })
    return skills

# === MCPize → MCP 桥接 ===
def get_mcpize_mcp_tools() -> dict:
    """将 MCPize 工具暴露为 MCP 协议工具"""
    tools = {}
    for name, entry in _INTEGRATED.items():
        for tool in entry.get("tools", []):
            tname = f"mcpize_{name}_{tool['name']}"
            tools[tname] = {
                "name": tname,
                "description": f"[MCPize/{entry['type']}] {tool['description']}",
                "inputSchema": tool.get("inputSchema", {"type":"object","properties":{}})
            }
    return tools
