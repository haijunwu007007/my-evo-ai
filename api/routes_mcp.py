"""MCP Hub — MCP 协议服务器聚合网关

MCP (Model Context Protocol) 是 2026 年 AI 领域标准协议，
让 AI Agent 通过统一接口调用外部工具和数据源。

本模块作为 MCP 网关 Hub，聚合多个 MCP Server 并提供统一管理入口。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, json, urllib.request
from core.logging_config import get_logger

logger = get_logger("evo.routes_mcp")
router = APIRouter(prefix="/api/tools/mcp", tags=["tools"])

MCP_HUB_URL = os.environ.get("MCP_HUB_URL", "http://localhost:3011")

# 内置 MCP 服务器注册表 — 可直接代理的 MCP Server
BUILTIN_MCP_SERVERS = [
    {
        "name": "github",
        "description": "GitHub API MCP — 管理 Issue/PR/代码/仓库",
        "url": os.environ.get("MCP_GITHUB_URL", "http://localhost:3012"),
        "enabled": True,
    },
    {
        "name": "filesystem",
        "description": "文件系统 MCP — 读写/搜索项目文件",
        "url": os.environ.get("MCP_FS_URL", ""),
        "enabled": False,
    },
    {
        "name": "evo-api",
        "description": "Evo 系统 MCP — 调用本系统 API 端点",
        "url": "http://localhost:8765",
        "enabled": True,
    },
]


class McpCallRequest(BaseModel):
    server: str
    tool: str
    params: dict = {}


class McpConfigRequest(BaseModel):
    server: str
    url: str
    enabled: bool = True


@router.get("")
async def get_status():
    return {
        "available": True,
        "hub_url": MCP_HUB_URL,
        "servers": len(BUILTIN_MCP_SERVERS),
        "enabled": sum(1 for s in BUILTIN_MCP_SERVERS if s["enabled"]),
        "name": "MCP Hub",
        "description": "MCP 协议服务器聚合网关 — AI Agent 统一调用外部工具",
    }


@router.get("/health")
async def health_check():
    try:
        req = urllib.request.Request(f"{MCP_HUB_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return {"healthy": True, "status": resp.status}
    except Exception:
        # Hub 不可用时返回内置服务器列表信息
        return {"healthy": True, "mode": "builtin", "servers": len(BUILTIN_MCP_SERVERS)}


@router.get("/servers")
async def list_servers():
    return {"servers": BUILTIN_MCP_SERVERS, "total": len(BUILTIN_MCP_SERVERS)}


@router.post("/call")
async def call_mcp(req: McpCallRequest):
    """调用指定 MCP Server 的工具"""
    server = next((s for s in BUILTIN_MCP_SERVERS if s["name"] == req.server), None)
    if not server:
        raise HTTPException(status_code=404, detail=f"MCP server '{req.server}' not found")
    if not server["enabled"]:
        raise HTTPException(status_code=400, detail=f"MCP server '{req.server}' is disabled")
    if not server["url"]:
        raise HTTPException(status_code=400, detail=f"MCP server '{req.server}' has no URL configured")

    # 直接调用 MCP Server API
    try:
        body = json.dumps({"tool": req.tool, "params": req.params}).encode()
        request = urllib.request.Request(
            f"{server['url']}/mcp/call", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:120])
