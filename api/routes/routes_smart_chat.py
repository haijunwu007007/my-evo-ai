"""智能体 — 路由（流式+工具完整支持）"""
from fastapi import APIRouter
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os, random, json, asyncio, httpx
from core.logging_config import get_logger
logger = get_logger("evo.api.smart")
router = APIRouter()

BASE = Path(__file__).resolve().parent.parent.parent
OUT = BASE / "output"; OUT.mkdir(exist_ok=True)
TOOLS_DIR = OUT / "tools"; TOOLS_DIR.mkdir(exist_ok=True)
MEM_DB = BASE / "data" / "agent_memory.db"; MEM_DB.parent.mkdir(parents=True, exist_ok=True)

DIRECT_ROUTES = {
    "游戏": ("games", "🎮 **游戏**\n• ⚫ [五子棋](/gomoku.html)\n• 👩 [老婆跳井](/wife_well.html)\n• 🐺 [狼吃娃](/wolf)\n• 🐍 [贪吃蛇](/snake)\n• 🛩️ [打飞机](/shooter)"),
    "系统怎么样": ("status", "✅ 系统运行正常 · 457模块"),
    "做一个计算器": ("app", "✅ **计算器**\n[📄 打开](/app_calc.html)"),
    "五子棋": ("app", "✅ **五子棋**\n[📄 打开](/gomoku.html)"),
    "老婆跳井": ("app", "✅ **老婆跳井**\n[📄 打开](/wife_well.html)"),
    "狼吃娃": ("app", "✅ **狼吃娃**\n[📄 打开](/wolf)"),
    "贪吃蛇": ("app", "✅ **贪吃蛇**\n[📄 打开](/snake)"),
    "打飞机": ("app", "✅ **打飞机**\n[📄 打开](/shooter)"),
}

# 需要工具调用的关键词（匹配到这些词走完整agent_core管道或Agent引擎）
_TOOL_KEYWORDS = [
    "浏览器", "自动化", "研究", "全栈", "生成项目", "记忆", "composio",
    "外部工具", "分析代码", "进化", "学习技能", "桌面", "API发现",
    "toolbench", "browser", "research", "openhands", "letta",
    "self_evolving", "moltron", "accomplish", "抓取", "爬取",
    "操控浏览器", "搜索API", "发现API", "画", "搜索", "开发",
    "创建", "写一个", "做一个", "生成", "设计", "实现", "模块",
    # ── 外部Skill关键字路由 ──
    "openclaw", "autogen", "crewai", "langgraph", "langchain",
    "dify", "flowise", "n8n", "ragflow", "ollama",
    "mem0", "browser-use", "firecrawl", "autogpt", "openhands",
    "metagpt", "mastra", "headroom", "odysseus",
    "股票分析", "套利", "量化", "金融", "hedge fund",
    "网络安全", "cyber", "hack", "渗透",
    "视频生成", "文生视频", "图生视频",
]

# 外部Skill名称列表（启动时加载）
_EXT_SKILL_NAMES: list[str] = []

def _load_ext_skill_names():
    """加载外部Skill名称到内存，用于聊天路由"""
    global _EXT_SKILL_NAMES
    # 直接从 Agent Engine 的目录获取
    try:
        from api.routes.routes_agent_engine import _SKILL_CATALOG
        _EXT_SKILL_NAMES = [s["name"] for s in _SKILL_CATALOG]
    except Exception:
            pass

_load_ext_skill_names()

class Req(BaseModel):
    message: str; api_key: Optional[str] = ""; lang: Optional[str] = "zh-CN"; context: Optional[list] = []
    _internal: Optional[bool] = False  # 内部调用标记，防止循环路由

def _needs_tools(msg: str) -> bool:
    """判断消息是否需要工具调用"""
    lower = msg.lower()
    return any(kw.lower() in lower for kw in _TOOL_KEYWORDS)

@router.post("/api/v1/smart")
async def smart_chat(req: Req):
    msg = (req.message or "").strip()
    # ── 外部Skill快速路由（跳过内部LLM调用，防止循环） ──
    if not (msg.startswith("你是一个AI任务规划器") or msg.startswith("请用中文总结以下执行结果") or msg.startswith("你是一个技能执行专家")):
        lower_msg = msg.lower()
        for skill_name in _EXT_SKILL_NAMES:
            if skill_name.lower() in lower_msg:
                try:
                    async with httpx.AsyncClient(timeout=120) as c:
                        ar = await c.post("http://127.0.0.1:8765/api/v1/agent/run",
                            json={"task": msg, "context": req.context or ""})
                        ad = ar.json()
                        if ad.get("success"):
                            return {"success": True, "result": ad.get("result", ""),
                                    "mode": "agent_engine", "details": ad.get("details", [])}
                except Exception:
                    pass
    for keyword, (mode, result) in DIRECT_ROUTES.items():
        if keyword in msg:
            return {"success": True, "result": result, "mode": mode}
    if ("PPT" in msg or "做一份" in msg) and "app_" not in msg:
        try:
            from api.routes.routes_pptx import generate_presentation
            r = generate_presentation(msg.replace("做一份","").replace("PPT","").strip() or "主题")
            if r["success"]: return {"success":True,"result":r["result"],"mode":"ppt"}
        except Exception:
            pass
    # ── 智能工具路由层 ──
    try:
        from api.tools.tool_router import route_and_execute
        result = route_and_execute(msg)
        rtype = result.get("type", "chat")
        output = result.get("data", "")
        if rtype == "tool" or rtype == "direct":
            return {"success": True, "result": output, "mode": rtype, "tool": result.get("name","")}
    except Exception:
        pass
    # ── 检查是否有可用的 API Key ──
    _has_key = any(os.environ.get(k) for k in ("OPENAI_API_KEY", "ZHIPU_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"))
    if not _has_key:
        return {"success": True, "result": "⚠️ 系统尚未配置 API Key。\n\n请在 `.env` 文件中设置至少一个 LLM API Key（如 `ZHIPU_API_KEY`、`OPENAI_API_KEY`、`DEEPSEEK_API_KEY`），然后重启服务。\n\n当前支持的直达命令：\n- 「系统怎么样」- 查看系统状态\n- 「游戏」- 查看小游戏列表\n- 直接发送文件生成请求", "mode": "no_key"}
    from api.agent_core import create_engine
    engine = create_engine(BASE, OUT, TOOLS_DIR, MEM_DB)
    result = await asyncio.to_thread(engine, req.message, req.api_key, req.lang, req.context)
    return result

def register_routes(app):
    """兼容性入口：挂载router到app"""
    app.include_router(router)

setup_smart_chat_routes = register_routes  # 别名

@router.post("/api/v1/smart/stream")
async def smart_stream(req: Req):
    """流式输出 — 支持工具调用的完整管道"""
    msg = req.message or ""
    
    # 1. 直达路由检查
    for keyword, (mode, result) in DIRECT_ROUTES.items():
        if keyword in msg:
            async def direct_gen():
                yield json.dumps({"type":"start"}, ensure_ascii=False) + "\n"
                yield json.dumps({"type":"chunk","text":result}, ensure_ascii=False) + "\n"
                yield json.dumps({"type":"done"}, ensure_ascii=False) + "\n"
            return StreamingResponse(direct_gen(), media_type="application/x-ndjson")
    
    # 2. 判断是否需要工具调用
    if _needs_tools(msg):
        # 走完整 agent_core 管道（支持工具），结果流式返回
        from api.agent_core import create_engine
        engine = create_engine(BASE, OUT, TOOLS_DIR, MEM_DB)
        
        async def tool_gen():
            yield json.dumps({"type":"start"}, ensure_ascii=False) + "\n"
            try:
                result = await asyncio.to_thread(engine, req.message, req.api_key, req.lang, req.context)
                if isinstance(result, dict) and result.get("success"):
                    text = result.get("result", "")
                    # 分块流式输出（模拟流式体验）
                    chunk_size = 20
                    for i in range(0, len(text), chunk_size):
                        yield json.dumps({"type":"chunk","text":text[i:i+chunk_size]}, ensure_ascii=False) + "\n"
                    yield json.dumps({"type":"done"}, ensure_ascii=False) + "\n"
                else:
                    err_text = result.get("detail", result.get("result", "处理失败")) if isinstance(result, dict) else str(result)
                    yield json.dumps({"type":"chunk","text":str(err_text)}, ensure_ascii=False) + "\n"
                    yield json.dumps({"type":"done"}, ensure_ascii=False) + "\n"
            except Exception as e:
                yield json.dumps({"type":"chunk","text":f"处理出错: {e}"}, ensure_ascii=False) + "\n"
                yield json.dumps({"type":"done"}, ensure_ascii=False) + "\n"
        return StreamingResponse(tool_gen(), media_type="application/x-ndjson")
    
    # 3. 简单聊天 — 纯流式LLM输出
    from api.agent_llm import call_llm_stream
    is_dev = any(k in msg for k in ["开发","创建","写一个","做一个","生成","设计","实现"])
    sp = f"你是AUTO-EVO-AI。{f'直接生成完整HTML代码，只输出```html```代码块，不要加解释。' if is_dev else '简洁回答。'}"
    async def generate():
        yield json.dumps({"type":"start"}, ensure_ascii=False) + "\n"
        for chunk in call_llm_stream([{"role":"user","content":req.message}], req.api_key, sp):
            if chunk == "__DONE__":
                yield json.dumps({"type":"done"}, ensure_ascii=False) + "\n"
                return
            if chunk == "local":
                continue
            yield json.dumps({"type":"chunk","text":chunk}, ensure_ascii=False) + "\n"
        yield json.dumps({"type":"done"}, ensure_ascii=False) + "\n"
    return StreamingResponse(generate(), media_type="application/x-ndjson")
