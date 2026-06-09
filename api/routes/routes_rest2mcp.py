"""
AUTO-EVO-AI V0.1 — REST→MCP (Kong风格)
给任意 OpenAPI/Swagger URL 自动生成 MCP 工具
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import json, httpx, re, urllib.parse
from pathlib import Path

logger = get_logger("evo.api.rest2mcp")
router = APIRouter()

REST2MCP_DIR = Path(__file__).resolve().parent.parent / "rest2mcp"
REST2MCP_DIR.mkdir(exist_ok=True)

# 内存注册表
_REST_MCP_TOOLS: dict = {}  # {tool_name: {...}}


@router.post("/api/v1/rest2mcp/convert")
async def convert_openapi(url: str, name: str = ""):
    """将 OpenAPI/Swagger URL 转换为 MCP 工具"""
    if not url:
        raise HTTPException(status_code=400, detail="需要提供 OpenAPI URL")
    
    # 自动补全 https://
    fetch_url = url
    if not fetch_url.startswith("http"):
        fetch_url = "https://" + fetch_url
    
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.get(fetch_url)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=f"获取 OpenAPI 失败: HTTP {resp.status_code}")
            
            spec = resp.json()
        
        # 解析 OpenAPI 规范
        info = spec.get("info", {})
        api_title = name or info.get("title", url.split("/")[-1].replace(".json","").replace(".yaml",""))
        base_url = spec.get("servers", [{}])[0].get("url", "") or spec.get("host", "")
        paths = spec.get("paths", {})
        base_path = spec.get("basePath", "")
        
        if not base_url:
            base_url = f"https://{spec.get('host', 'api.example.com')}{base_path}"
        
        converted = []
        for path, methods in paths.items():
            for method in ("get", "post", "put", "patch", "delete"):
                op = methods.get(method, {})
                if not op:
                    continue
                op_id = op.get("operationId", f"{method}_{path.replace('/','_').replace('{','').replace('}','')}")
                tool_name = f"{api_title}_{op_id}"
                full_url = f"{base_url.rstrip('/')}{path}"
                
                # 构建参数 schema
                params = op.get("parameters", [])
                properties = {}
                required = []
                for p in params:
                    p_name = p.get("name", "param")
                    p_schema = p.get("schema", {"type": "string"})
                    properties[p_name] = {
                        "type": p_schema.get("type", "string"),
                        "description": p.get("description", p_name)
                    }
                    if p.get("required", False):
                        required.append(p_name)
                
                tool_entry = {
                    "name": tool_name,
                    "description": op.get("summary", op.get("description", op_id)),
                    "method": method.upper(),
                    "url": full_url,
                    "parameters": properties,
                    "required_params": required,
                    "inputSchema": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
                _REST_MCP_TOOLS[tool_name] = tool_entry
                converted.append(tool_entry)
        
        # 保存到文件
        slug = re.sub(r'[^a-zA-Z0-9_-]', '_', api_title.lower())
        save_path = REST2MCP_DIR / f"{slug}.json"
        save_path.write_text(json.dumps(converted, ensure_ascii=False, indent=2), encoding="utf-8")
        
        return {
            "success": True,
            "title": api_title,
            "base_url": base_url,
            "tool_count": len(converted),
            "tools": [{"name": t["name"], "description": t["description"], "method": t["method"], "url": t["url"]} for t in converted[:20]]
        }
    
    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="获取 OpenAPI 超时")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="响应不是有效的 JSON")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"转换失败: {e}")


@router.get("/api/v1/rest2mcp/tools")
async def list_rest_mcp():
    return {"success": True, "tools": list(_REST_MCP_TOOLS.values()), "total": len(_REST_MCP_TOOLS)}


class RESTMCPCall(BaseModel):
    params: dict = {}


@router.post("/api/v1/rest2mcp/call/{tool_name}")
async def call_rest_mcp(tool_name: str, req: RESTMCPCall):
    tool = _REST_MCP_TOOLS.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"工具 {tool_name} 不存在")
    
    method = tool["method"]
    url = tool["url"]
    
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            if method == "GET":
                resp = await c.get(url, params=req.params)
            elif method == "POST":
                resp = await c.post(url, json=req.params)
            elif method == "PUT":
                resp = await c.put(url, json=req.params)
            elif method == "PATCH":
                resp = await c.patch(url, json=req.params)
            elif method == "DELETE":
                resp = await c.delete(url, params=req.params)
            else:
                return {"success": False, "detail": f"不支持的方法: {method}"}
            
            try:
                data = resp.json()
            except:
                data = resp.text[:2000]
            
            return {"success": resp.is_success, "status": resp.status_code, "tool": tool_name, "data": data}
    except Exception as e:
        return {"success": False, "detail": str(e)}


def get_rest_mcp_skills() -> list[dict]:
    """将 REST→MCP 工具暴露为 Skill"""
    skills = []
    for name, tool in _REST_MCP_TOOLS.items():
        skills.append({
            "name": f"restmcp:{name}",
            "version": "1.0.0",
            "description": f"[REST→MCP] {tool['description']}",
            "author": "auto-evo-ai",
            "category": "REST→MCP",
            "icon": "🔗",
            "tags": [tool.get("method","GET").lower(), "restmcp"],
            "input_schema": tool.get("inputSchema", {"type":"object","properties":{}}),
            "output_schema": {"type": "object", "properties": {"data": {"type": "string"}}},
            "handler": "",
            "endpoint": f"restmcp://{name}"
        })
    return skills
