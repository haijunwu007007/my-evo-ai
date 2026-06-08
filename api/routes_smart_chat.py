"""智能体 — 路由（80行，只做转发）"""
from fastapi import APIRouter
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os, random, json
from core.logging_config import get_logger
logger = get_logger("evo.api.smart")
router = APIRouter()

BASE = Path(__file__).resolve().parent.parent
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

class Req(BaseModel):
    message: str; api_key: Optional[str] = ""; lang: Optional[str] = "zh-CN"; context: Optional[list] = []

@router.post("/api/v1/smart")
async def smart_chat(req: Req):
    msg = (req.message or "").strip()
    for keyword, (mode, result) in DIRECT_ROUTES.items():
        if keyword in msg:
            return {"success": True, "result": result, "mode": mode}
    if ("PPT" in msg or "做一份" in msg) and "app_" not in msg:
        try:
            from api.routes_pptx import generate_presentation
            r = generate_presentation(msg.replace("做一份","").replace("PPT","").strip() or "主题")
            if r["success"]: return {"success":True,"result":r["result"],"mode":"ppt"}
        except: pass
    from .agent_core import create_engine
    engine = create_engine(BASE, OUT, TOOLS_DIR, MEM_DB)
    import asyncio
    result = await asyncio.to_thread(engine, req.message, req.api_key, req.lang, req.context)
    return result

def register_routes(app):
    """兼容性入口：挂载router到app"""
    app.include_router(router)

setup_smart_chat_routes = register_routes  # 别名

@router.post("/api/v1/smart/stream")
async def smart_stream(req: Req):
    """流式输出 — 边生成边返回"""
    from .agent_llm import call_llm_stream
    msg = req.message or ""
    is_dev = any(k in msg for k in ["开发","创建","写一个","做一个","生成","设计","实现"])
    sp = f"你是AUTO-EVO-AI。{f'直接生成完整HTML代码，只输出```html```代码块，不要加解释。' if is_dev else '简洁回答。'}"
    async def generate():
        yield '{"type":"start"}\n'
        for chunk in call_llm_stream([{"role":"user","content":req.message}], req.api_key, sp):
            if chunk == "__DONE__":
                yield '{"type":"done"}\n'
                return
            yield json.dumps({"type":"chunk","text":chunk}, ensure_ascii=False) + "\n"
    return StreamingResponse(generate(), media_type="application/x-ndjson")
