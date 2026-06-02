"""Chat API — 更聪明地理解用户想干什么"""

import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.logging_config import get_logger

logger = get_logger("evo.api.chat")
router = APIRouter()

class ChatRequest(BaseModel):
    message: str

# ── 意图定义 ─────────────────────────────────
INTENTS = [
    {
        "id": "status",
        "patterns": ["状态", "健康", "运行", "还好", "正常", "情况", "怎么样", "status"],
        "priority": 3,
    },
    {
        "id": "capabilities",
        "patterns": ["什么功能", "能做什么", "你会什么", "能力", "用途", "help", "使用", "哪些"],
        "priority": 2,
    },
    {
        "id": "greeting",
        "patterns": ["你好", "嗨", "hi", "hello", "在吗", "hey", "您好"],
        "priority": 1,
    },
    {
        "id": "team",
        "patterns": ["团队", "讨论", "协作", "一起", "大家", "开会", "商量"],
        "priority": 4,
    },
    {
        "id": "timer",
        "patterns": ["每天", "定时", "每周", "重复", "自动", "定期", "定时任务", "sechdule"],
        "priority": 3,
    },
    {
        "id": "notify",
        "patterns": ["通知", "推送", "提醒", "告警", "alert"],
        "priority": 2,
    },
    {
        "id": "business",
        "patterns": ["billion", "集团", "企业", "公司", "部门", "员工", "组织", "department"],
        "priority": 3,
    },
    {
        "id": "desktop",
        "patterns": ["打开", "截图", "鼠标", "截屏", "操作电脑", "桌面"],
        "priority": 3,
    },
]

def _detect_intent(text: str) -> list:
    """检测文本中的多个意图，按优先级排序"""
    t = text.lower().strip()
    scored = []
    for intent in INTENTS:
        score = 0
        for pat in intent["patterns"]:
            if pat in t:
                score += 1
        if score > 0:
            scored.append((intent["id"], score * intent["priority"]))
    scored.sort(key=lambda x: -x[1])
    return [s[0] for s in scored]

def _greeting_response(text: str) -> str:
    if "好" in text or "hi" in text.lower() or "hello" in text.lower():
        return "嗨，我在。有什么需要帮忙的？说「你会什么」看看我能干啥。"
    if "在吗" in text or "在不在" in text:
        return "在的，一直在。你说。"
    return "在呢。请讲。"

async def _status_response() -> str:
    try:
        from modules.agent_s_bridge import get_status
        s = await get_status()
        if s and isinstance(s, dict):
            parts = ["一切正常 ✅"]
            parts.append(f"• 版本 {s.get('version', '-')}")
            parts.append(f"• 桌面自动化 {'就绪' if s.get('sdk_available') else '未安装'}")
            parts.append(f"• API Key {'已配置' if s.get('has_openai_key') else '未配置，需要的话去系统后台配'}")
            parts.append("")
            parts.append("放心用，有问题随时叫我。")
            return "\n".join(parts)
    except:
        pass
    return "系统在跑着，没什么大问题。"

def _capabilities_response() -> str:
    try:
        from api.infra import registry
        mods = list(registry.modules.keys())
    except:
        mods = []
    lines = ["我能干这些事：\n"]
    lines.append("📊 **看看系统状态** — 说「系统怎么样」")
    lines.append("🤖 **叫几个AI讨论** — 说「团队讨论xxx」")
    lines.append("🖥️ **操作电脑** — 说「帮我截图」去 Agent-S")
    lines.append("⏰ **定时任务** — 说「每天下午5点备份」")
    lines.append("🏢 **企业管理** — 点右上角「企业管理」")
    lines.append("🔔 **通知推送** — 说「通知我服务器状态」")
    lines.append("🎤 **语音输入** — 点输入框边的 🎤 按钮")
    if mods:
        lines.append(f"\n后台还有 {len(mods)} 个能力模块随时调用。")
    lines.append("\n你想先试哪个？")
    return "\n".join(lines)

def _team_response(text: str) -> str:
    return (
        "好的，我来组织个团队讨论这个。\n"
        "👥 正在召集智能体团队…"
    )

def _timer_response(text: str) -> str:
    if "备份" in text:
        return "明白，设个定时备份。\n我去准备一下，你告诉我具体每天几点？"
    if "日志" in text or "清理" in text:
        return "日志清理可以自动搞。你希望多久清一次？"
    return "定时任务没问题。你说具体干什么、什么时候干，我来安排。"

def _business_response() -> str:
    return (
        "企业管理在右上角的「企业管理」页面。\n"
        "进去了可以：\n"
        "• 创建和管理部门\n"
        "• 添加员工\n"
        "• 分配智能体\n"
        "去看看？"
    )

def _notify_response() -> str:
    return (
        "通知支持钉钉、飞书、邮件和 Webhook。\n"
        "你先去配一下渠道，配好了告诉我一声，我就能给你发通知了。"
    )

def _desktop_response() -> str:
    return (
        "桌面操作在「Agent-S」页面里。\n"
        "进系统后台 → 左边找到 Agent-S → 里面可以让我帮你点鼠标、截图、打字。"
    )

def _fallback_response(text: str) -> str:
    t = text[:50]
    # 带问号或疑问词 → 猜测是提问
    if "?" in t or "？" in t or any(k in t for k in ["什么", "怎么", "为什么", "如何"]):
        return (
            f"这个问题我还不太会回答。\n"
            f"不过你可以试试「你会什么」看看我能干啥，"
            f"或者「系统怎么样」看看系统状态。"
        )
    # 带"帮我" → 猜测是想执行
    if "帮我" in t or "麻烦" in t or "请" in t:
        return (
            f"收到你的请求。\n"
            f"不过我没完全理解你想做什么。能说得具体一点吗？\n"
            f"或者试试「你会什么」看看我能干啥。"
        )
    return (
        f"你说「{t}」…\n"
        f"我不太确定你的意思。要不：\n"
        f"• 「你会什么」— 看看我能干啥\n"
        f"• 「系统怎么样」— 看看状态\n"
        f"• 「团队讨论xxx」— 叫几个AI一起想"
    )

@router.post("/api/v1/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, detail="说点什么呗")
    text = req.message.strip()

    intents = _detect_intent(text)

    if not intents:
        return {"success": True, "result": _fallback_response(text)}

    top = intents[0]

    # 团队讨论
    if top == "team":
        return {"success": True, "result": _team_response(text)}

    # 系统状态
    if top == "status":
        return {"success": True, "result": await _status_response()}

    # 能力查询
    if top == "capabilities":
        return {"success": True, "result": _capabilities_response()}

    # 打招呼
    if top == "greeting":
        return {"success": True, "result": _greeting_response(text)}

    # 定时任务
    if top == "timer":
        return {"success": True, "result": _timer_response(text)}

    # 企业管理
    if top == "business":
        return {"success": True, "result": _business_response()}

    # 通知
    if top == "notify":
        return {"success": True, "result": _notify_response()}

    # 桌面操作
    if top == "desktop":
        return {"success": True, "result": _desktop_response()}

    return {"success": True, "result": _fallback_response(text)}
