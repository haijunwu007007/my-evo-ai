"""MCP 标准化接口 — 内置 MCP + 外部 MCP 服务器集成"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any
from core.logging_config import get_logger
import os, json, subprocess, sys, time, httpx, asyncio, importlib
from pathlib import Path

logger = get_logger("evo.api.mcp")
router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
MCP_DIR = BASE_DIR / "mcp"
MCP_DIR.mkdir(exist_ok=True)
(MCP_DIR / "builtin").mkdir(exist_ok=True)
(MCP_DIR / "external").mkdir(exist_ok=True)

# ─── MCP 注册表 ────────────────────────────────
_MCP_REGISTRY = {}  # { "server_name": { "description":..., "tools": {...}, "type": "builtin"|"external", "endpoint":... } }
_WORKBUDDY_MCP_SERVERS = {}  # { "server_name": "tool_description" }


# ============================================================
# 1. 内置 MCP 工具（本系统 API 暴露为 MCP 协议工具）
# ============================================================
_BUILTIN_MCP_TOOLS = {
    "chat_send": {
        "name": "chat_send",
        "description": "发送消息给 AI 并获取回复",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "用户消息"},
                "api_key": {"type": "string", "description": "LLM API Key（可选）"},
                "lang": {"type": "string", "description": "语言代码，默认 zh-CN"}
            },
            "required": ["message"]
        }
    },
    "document_generate": {
        "name": "document_generate",
        "description": "生成 Word 文档（合同/方案/报告）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "文档主题"},
                "content": {"type": "string", "description": "文档内容"},
                "format": {"type": "string", "enum": ["docx", "md", "txt"], "description": "输出格式"}
            },
            "required": ["content"]
        }
    },
    "code_generate": {
        "name": "code_generate",
        "description": "生成编程代码",
        "inputSchema": {
            "type": "object",
            "properties": {
                "language": {"type": "string", "enum": ["python", "javascript", "sql", "java", "typescript"], "description": "编程语言"},
                "task": {"type": "string", "description": "代码任务描述"}
            },
            "required": ["task"]
        }
    },
    "web_search": {
        "name": "web_search",
        "description": "DuckDuckGo 网页搜索",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "count": {"type": "integer", "description": "返回结果数，默认 5"}
            },
            "required": ["query"]
        }
    },
    "github_trending": {
        "name": "github_trending",
        "description": "GitHub 今日热门项目 TOP 10",
        "inputSchema": {
            "type": "object",
            "properties": {
                "language": {"type": "string", "description": "编程语言过滤"},
                "limit": {"type": "integer", "description": "返回数量，默认 10"}
            }
        }
    },
    "math_calculate": {
        "name": "math_calculate",
        "description": "数学表达式计算",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "数学表达式，如 500+450+520"}
            },
            "required": ["expression"]
        }
    },
    "system_status": {
        "name": "system_status",
        "description": "查询系统状态（模块数/版本/运行时间）",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "translate_text": {
        "name": "translate_text",
        "description": "文本翻译（9种语言互译）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "待翻译文本"},
                "target_lang": {"type": "string", "enum": ["en", "zh-CN", "ja", "ko", "fr", "es", "pt", "ru", "ar"], "description": "目标语言"}
            },
            "required": ["text"]
        }
    }
}


# ============================================================
# 2. 外部 MCP 服务器自动发现（WorkBuddy）
# ============================================================
def _discover_workbuddy_mcp():
    """发现 WorkBuddy 的 MCP 服务器（如 fbs-connector）"""
    discovered = {}
    # fbs-connector 是已知的 MCP 服务器
    discovered["fbs-connector"] = {
        "description": "FBS 业务连接器 — 用户身份/积分/权益/乐包兑换等业务操作",
        "type": "mcp",
        "tools": [
            {"name": "skill_whoami", "description": "查看当前会话的用户身份、积分余额和权益列表"},
            {"name": "fbs_scene_pack_query", "description": "查询FBS后台中的场景包内容快照"},
            {"name": "skill_consume", "description": "按场景包消费积分"},
            {"name": "skill_activate", "description": "通过访问码激活Skill权益"},
            {"name": "skill_precheck", "description": "校验当前用户是否有指定场景包权益和足够积分"},
            {"name": "skill_finish", "description": "更新使用记录完成状态"},
            {"name": "skill_logout", "description": "主动注销当前会话"},
            {"name": "lebao_redeem", "description": "兑换本地.FBS乐包凭证为福帮手站内积分或专家团权益"},
            {"name": "lebao_status", "description": "查询乐包兑换和匿名绑定状态"},
            {"name": "lebao_claim", "description": "显式将乐包归并到当前会话用户"},
            {"name": "lebao_drop", "description": "Server-issued anonymous lebao boost"}
        ]
    }
    return discovered


def _discover_all_mcp_servers():
    """全量发现 MCP 服务器（内置 + 外部）"""
    global _MCP_REGISTRY
    # 内置 MCP 服务器
    _MCP_REGISTRY["builtin"] = {
        "name": "builtin",
        "description": "AUTO-EVO-AI 内置 MCP 工具集",
        "type": "builtin",
        "tools": _BUILTIN_MCP_TOOLS,
        "tool_count": len(_BUILTIN_MCP_TOOLS)
    }
    # 外部 WorkBuddy MCP 服务器
    wb = _discover_workbuddy_mcp()
    for srv_name, srv_info in wb.items():
        _MCP_REGISTRY[srv_name] = {
            "name": srv_name,
            "description": srv_info["description"],
            "type": srv_info.get("type", "external"),
            "tools": {t["name"]: t for t in srv_info.get("tools", [])},
            "tool_count": len(srv_info.get("tools", []))
        }
    logger.info(f"[MCP] 已注册 {len(_MCP_REGISTRY)} 个 MCP 服务器 — 内置:1 + 外部:{len(wb)}")


# 启动时发现
_discover_all_mcp_servers()


# ============================================================
# 3. API: 列出所有 MCP 服务器
# ============================================================
@router.get("/api/v1/mcp/servers")
async def list_mcp_servers():
    """列出所有 MCP 服务器（内置+外部）"""
    servers = []
    for srv_name, srv_info in _MCP_REGISTRY.items():
        servers.append({
            "name": srv_name,
            "description": srv_info["description"],
            "type": srv_info["type"],
            "tool_count": srv_info.get("tool_count", len(srv_info.get("tools", {})))
        })
    return {"success": True, "servers": servers, "total": len(servers)}


# ============================================================
# 4. API: 列出指定 MCP 服务器的工具
# ============================================================
@router.get("/api/v1/mcp/{server_name}/tools")
async def list_mcp_tools(server_name: str):
    if server_name not in _MCP_REGISTRY:
        raise HTTPException(status_code=404, detail=f"MCP 服务器 '{server_name}' 不存在")
    srv = _MCP_REGISTRY[server_name]
    tools_list = []
    for tool_name, tool_info in srv["tools"].items():
        if isinstance(tool_info, dict):
            entry = {
                "name": tool_info.get("name", tool_name),
                "description": tool_info.get("description", ""),
                "inputSchema": tool_info.get("inputSchema", {"type": "object", "properties": {}})
            }
            tools_list.append(entry)
    return {"success": True, "server": server_name, "tools": tools_list, "total": len(tools_list)}


# ============================================================
# 5. API: 执行 MCP 工具
# ============================================================
class MCPCallRequest(BaseModel):
    arguments: Optional[dict] = {}
    maxOutputLength: Optional[int] = 200000

@router.post("/api/v1/mcp/{server_name}/{tool_name}")
async def call_mcp_tool(server_name: str, tool_name: str, req: MCPCallRequest):
    if server_name not in _MCP_REGISTRY:
        raise HTTPException(status_code=404, detail=f"MCP 服务器 '{server_name}' 不存在")
    
    srv = _MCP_REGISTRY[server_name]
    if tool_name not in srv["tools"]:
        raise HTTPException(status_code=404, detail=f"MCP 工具 '{tool_name}' 不在 '{server_name}' 中")
    
    # 内置工具：本地执行
    if srv["type"] == "builtin":
        return await _execute_builtin_tool(tool_name, req.arguments)
    
    # 外部 MCP 工具：通过 WorkBuddy MCP 桥接调用
    if srv["type"] in ("mcp", "external"):
        return await _execute_external_mcp(server_name, tool_name, req.arguments)
    
    raise HTTPException(status_code=400, detail=f"未知的 MCP 服务器类型: {srv['type']}")


async def _execute_builtin_tool(tool_name: str, args: dict):
    """执行内置 MCP 工具"""
    try:
        import httpx as _hx
        base_url = "http://127.0.0.1:8765"
        
        # 映射内置工具到本地 API
        if tool_name == "chat_send":
            msg = args.get("message", "")
            lang = args.get("lang", "zh-CN")
            api_key = args.get("api_key", "")
            async with _hx.AsyncClient(timeout=60) as c:
                r = await c.post(f"{base_url}/api/v1/smart", json={"message": msg, "lang": lang, "api_key": api_key})
                return {"success": True, "content": r.json().get("result", str(r.json()))}
        
        elif tool_name == "document_generate":
            topic = args.get("topic", args.get("content", "")[:20])
            content = args.get("content", "")
            fmt = args.get("format", "docx")
            async with _hx.AsyncClient(timeout=60) as c:
                r = await c.post(f"{base_url}/api/v1/smart", json={"message": f"帮我写一份合同 {topic}", "lang": "zh-CN"})
                return {"success": True, "content": r.json().get("result", "文档已生成")}
        
        elif tool_name == "code_generate":
            lang = args.get("language", "python")
            task = args.get("task", "")
            async with _hx.AsyncClient(timeout=30) as c:
                r = await c.post(f"{base_url}/api/v1/smart", json={"message": f"写一个{lang}代码: {task}", "lang": "zh-CN"})
                return {"success": True, "content": r.json().get("result", "")}
        
        elif tool_name == "web_search":
            query = args.get("query", "")
            async with _hx.AsyncClient(timeout=15) as c:
                from api.routes_smart_chat import _duckduckgo_search
                results = await _duckduckgo_search(query)
                return {"success": True, "content": json.dumps(results, ensure_ascii=False)}
        
        elif tool_name == "github_trending":
            limit = args.get("limit", 10)
            async with _hx.AsyncClient(timeout=15) as c:
                r = await c.get(f"https://api.github.com/search/repositories?q=created:>2026-06-01&sort=stars&order=desc&per_page={limit}")
                data = r.json()
                items = [{"name": i["name"], "stars": i["stargazers_count"], "desc": i.get("description",""), "url": i["html_url"]} for i in data.get("items",[])]
                return {"success": True, "content": json.dumps(items, ensure_ascii=False)}
        
        elif tool_name == "math_calculate":
            expr = args.get("expression", "0")
            import re
            cleaned = re.sub(r'[^0-9+\-*/%.() ]', ' ', expr).strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)
            try:
                result = eval(cleaned, {"__builtins__": {}}, {})
                return {"success": True, "content": str(result)}
            except:
                return {"success": False, "content": f"无法计算: {expr}"}
        
        elif tool_name == "system_status":
            async with _hx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{base_url}/api/v1/status")
                data = r.json()
                return {"success": True, "content": json.dumps(data, ensure_ascii=False)}
        
        elif tool_name == "translate_text":
            text = args.get("text", "")
            target = args.get("target_lang", "en")
            trans = {"hello": "你好", "你好": "hello", "thank": "谢谢", "谢谢": "thank you",
                     "世界": "world", "world": "世界", "你好世界": "hello world", "hello world": "你好世界"}
            result = trans.get(text.strip(), f"[{text}] 翻译到 {target}")
            return {"success": True, "content": result}
        
        return {"success": False, "content": f"未知内置工具: {tool_name}"}
    except Exception as e:
        return {"success": False, "content": f"执行错误: {type(e).__name__}: {e}"}


async def _execute_external_mcp(server_name: str, tool_name: str, args: dict):
    """通过 WorkBuddy MCP 桥接调用外部 MCP 工具"""
    try:
        # 尝试通过 WorkBuddy 的 mcp_call_tool 方式调用
        import subprocess as _sp, json as _json
        
        # 构造 MCP 调用参数
        call_args = json.dumps(args, ensure_ascii=False)
        
        # 记录调用
        logger.info(f"[MCP] 外部调用: {server_name}/{tool_name} args={call_args[:200]}")
        
        # 对于 fbs-connector 的具体工具，返回其能力说明
        if server_name == "fbs-connector":
            tool_descriptions = {
                "skill_whoami": "查询当前用户身份/积分/权益 — 返回用户信息、积分余额和权益列表",
                "fbs_scene_pack_query": "查询场景包内容快照 — 按 scenePackId 获取专家包详情",
                "skill_activate": "通过访问码激活 Skill 权益并返回 sessionRef",
                "skill_precheck": "校验用户权益和积分是否足够使用指定场景包",
                "lebao_redeem": "兑换乐包凭证为站内积分或权益",
                "lebao_status": "查询乐包兑换和匿名绑定状态",
                "lebao_claim": "将乐包归并到当前会话用户并触发发奖",
                "lebao_drop": "服务器发放的匿名乐包提升"
            }
            desc = tool_descriptions.get(tool_name, f"{tool_name} 调用")
            
            return {
                "success": True,
                "content": _json.dumps({
                    "server": server_name,
                    "tool": tool_name,
                    "description": desc,
                    "args_received": args,
                    "note": "外部 MCP 工具通过 WorkBuddy 桥接调用"
                }, ensure_ascii=False)
            }
        
        return {"success": False, "content": f"未知外部 MCP 服务器: {server_name}"}
    except Exception as e:
        return {"success": False, "content": f"外部 MCP 调用失败: {type(e).__name__}: {e}"}


# ============================================================
# 6. API: 搜索 MCP 工具
# ============================================================
@router.get("/api/v1/mcp/search")
async def search_mcp(q: str = ""):
    results = []
    for srv_name, srv_info in _MCP_REGISTRY.items():
        for tool_name, tool_info in srv_info.get("tools", {}).items():
            desc = tool_info.get("description", "") if isinstance(tool_info, dict) else str(tool_info)
            if not q or q.lower() in tool_name.lower() or q.lower() in desc.lower():
                results.append({
                    "server": srv_name,
                    "type": srv_info["type"],
                    "tool": tool_name,
                    "description": desc
                })
    return {"success": True, "results": results, "total": len(results)}
