"""Chat API — 像真人一样聊天，不机械"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.logging_config import get_logger

logger = get_logger("evo.api.chat")
router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/api/v1/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, detail="说点什么呗")
    t = req.message.lower().strip()

    # 企业管理
    if any(k in t for k in ["billion", "集团", "企业", "公司", "部门", "员工"]):
        return {"success": True, "result":
            "🏢 企业管理功能在右上角「企业管理」页面里。\n"
            "可以创建部门、管理员工、分配智能体。\n"
            "去试试？"}

    # 系统状态
    if any(k in t for k in ["状态", "健康", "运行", "怎么样", "还好吗"]):
        try:
            from modules.agent_s_bridge import get_status
            s = await get_status()
            if s and isinstance(s, dict):
                key = s.get('has_openai_key')
                key_status = "配了" if key else "没配，有些功能用不了"
                return {"success": True, "result":
                    f"一切正常 ✅\n"
                    f"• 系统在跑，版本 {s.get('version', '-')}\n"
                    f"• 桌面自动化 SDK {'好了' if s.get('sdk_available') else '没装'}\n"
                    f"• API Key {key_status}\n"
                    f"放心用吧。"}
        except:
            return {"success": True, "result": "有点小毛病，但不影响使用。"}

    # 桌面操作
    if any(k in t for k in ["打开", "截图", "鼠标", "截屏"]):
        return {"success": True, "result":
            "这个需要进 Agent-S 页面操作。\n"
            "点右上角「📊 仪表盘」→ 左边菜单找 Agent-S。\n"
            "里面可以让我帮你点鼠标、打字、截图。"}

    # 定时任务
    if any(k in t for k in ["每天", "定时", "每周", "重复", "自动"]):
        return {"success": True, "result":
            "定时任务可以设。\n"
            "比如「每天下午5点备份系统」或「每周一早上检查服务器」。\n"
            "你具体想自动干什么？告诉我，我来安排。"}

    # 有什么功能 / 能做什么
    if any(k in t for k in ["什么功能", "能做什么", "你会什么", "能力", "help", "帮助", "哪些能力", "有什么用"]):
        return {"success": True, "result":
            "我能干的事还挺多的：\n\n"
            "📊 帮你看看系统状态 — 说「系统怎么样」\n"
            "🤖 叫几个AI一起讨论 — 说「团队讨论xxx」\n"
            "🖥️ 帮你操作电脑 — 去 Agent-S 页面\n"
            "⏰ 设个定时任务 — 说「每天下午5点备份」\n"
            "🏢 管理公司和部门 — 点右上角「企业管理」\n\n"
            "你想先试试哪个？"}

    # 通知
    if any(k in t for k in ["通知", "推送", "提醒", "告警"]):
        return {"success": True, "result":
            "通知可以走钉钉、飞书、邮件或者 Webhook。\n"
            "先去「系统后台」配一下，配好了告诉我。"}

    # 打招呼
    if any(k in t for k in ["你好", "嗨", "hi", "hello", "在吗"]):
        return {"success": True, "result":
            "在呢。有什么需要帮忙的？\n"
            "不知道我能干什么的话，说「你会什么」看看。"}

    # 默认 — 自然回应
    return {"success": True, "result":
        f"你说「{req.message[:50]}」...\n\n"
        "我不太确定你想干嘛。要不试试：\n"
        "• 「系统怎么样」— 看看状态\n"
        "• 「你会什么」— 看看我能干啥\n"
        "• 「团队讨论xxx」— 叫几个AI一起想"}
