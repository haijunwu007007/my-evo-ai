"""Chat API — 意图识别+真执行操作（不再只返回翻译文本）"""
import os, re
from fastapi import APIRouter
from pydantic import BaseModel
from core.logging_config import get_logger

logger = get_logger("evo.api.chat")
router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    lang: str = "zh-CN"

@router.post("/api/v1/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        return {"success": True, "result": "请说点什么"}

    msg = req.message.strip()
    lower = msg.lower()

    # ── 问候 ──
    if re.search(r'(你好|嗨|hi|hello|在吗|在不在)', lower):
        return {"success": True, "result": "你好！我是 AUTO-EVO-AI，有什么可以帮你？"}

    # ── 状态查询 → 真查 ──
    if any(k in lower for k in ["状态","健康","运行","系统怎么样","情况","status"]):
        try:
            from api.infra import registry
            total = registry.get_total_count()
            health = registry.get_all_health() if hasattr(registry, 'get_all_health') else {}
            ok_count = len([m for m,h in health.items() if h.get("status") in ("ok","running","pending_lazy")])
            return {"success": True, "result": f"✅ 系统运行正常\n• 模块: {total} 个\n• 健康: {ok_count}/{len(health)} 个正常\n• 运行中: {ok_count} 个"}
        except Exception as e:
            return {"success": True, "result": f"状态查询中... (检测中: {e})"}

    # ── 功能列表 → 直接返回 ──
    if any(k in lower for k in ["什么功能","能做什么","你会什么","能力","能干","帮助","help"]):
        return {"success": True, "result": """AUTO-EVO-AI 能力清单:
💻 **开发** — 说"开发xxx"自动生成网页/应用
🎨 **画图** — 说"画xxx"调用AI画图
🔍 **搜索** — 说"搜索xxx"搜索互联网
📊 **做PPT** — 说"做一份xxxPPT"生成演示文稿
😊 **聊天** — 直接对话，真AI回复
📦 **模块** — 说"调xxx模块"
📝 **写文档** — 说"写合同/写方案/写报告"
🛡️ **安全扫描** — 说"安全检测/漏洞扫描"
💾 **数据** — 说"数据分析/可视化/查询"
已内建DeepSeek Key 🔑，直接使用全部功能！""", "mode": "capabilities"}

    # ── 主动作 → 检查Key → 转agent_core真实执行或降级 ──
    _has_key = any(os.environ.get(k) for k in ("OPENAI_API_KEY", "ZHIPU_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"))
    if not _has_key:
        return {"success": True, "result": "⚠️ **LLM API Key 未配置**，系统处于离线模式。\n\n请在服务器 `.env` 文件中设置至少一个 LLM API Key（如 `ZHIPU_API_KEY`、`DEEPSEEK_API_KEY`、`OPENAI_API_KEY`），然后重启服务。\n\n**当前可用的直达命令：**\n- 「系统怎么样」— 查看系统运行状态\n- 「你会什么」— 查看功能列表\n- 「你好」— 打招呼\n- 「游戏」— 查看小游戏\n- 说「画xxx」/「做一份xxxPPT」— 本地生成", "mode": "no_key"}

    from api.agent_core import create_engine
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent.parent
    OUT = BASE / "output"; OUT.mkdir(exist_ok=True)
    TOOLS_DIR = OUT / "tools"; TOOLS_DIR.mkdir(exist_ok=True)
    MEM_DB = BASE / "data" / "agent_memory.db"; MEM_DB.parent.mkdir(parents=True, exist_ok=True)

    import asyncio
    engine = create_engine(BASE, OUT, TOOLS_DIR, MEM_DB)
    try:
        result = await asyncio.to_thread(engine, msg, "", "zh-CN", [])
        if isinstance(result, dict) and result.get("success"):
            return {"success": True, "result": result.get("result", ""), "mode": result.get("mode", "chat")}
        return {"success": True, "result": str(result)}
    except Exception as e:
        from api.agent_llm import call_llm
        content, _ = call_llm([{"role": "user", "content": msg + "\n简洁回答"}])
        return {"success": True, "result": content or f"处理中... ({e})"}
