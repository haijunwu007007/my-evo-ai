"""Chat API — 用户输入自然语言，系统理解并执行"""

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
        raise HTTPException(400, detail="请输入内容")
    t = req.message.lower().strip()

    # 0. Billion Group OS / 企业管理
    if any(k in t for k in ["billion", "集团", "企业", "公司", "组织", "部门", "部门管理", "员工", "department"]):
        return {"success": True, "result":
            "🏢 **BILLION GROUP OS — 企业管理**\n\n"
            "以下功能在「企业管理」页面:\n"
            "• 创建/管理部门\n• 创建/管理智能体\n• 员工管理\n"
            "• 组织架构树\n• 权限角色分配\n\n"
            "👉 点击顶部「🏢 企业管理」按钮进入"}

    # 1. 系统状态
    if any(k in t for k in ["状态", "健康", "运行", "情况", "怎么样", "status", "health"]):
        try:
            from modules.agent_s_bridge import get_status
            s = await get_status()
            if s and isinstance(s, dict):
                return {"success": True, "result":
                    f"✅ 系统运行正常\n\n"
                    f"• 模块: {s.get('module_id', '-')}\n"
                    f"• 版本: {s.get('version', '-')}\n"
                    f"• SDK: {'就绪' if s.get('sdk_available') else '未安装'}\n"
                    f"• 系统: {s.get('os', '-')}\n"
                    f"• API Key: {'已配置' if s.get('has_openai_key') else '未配置'}"}
        except Exception as e:
            return {"success": True, "result": f"⚠️ 读取状态失败: {e}"}

    # 2. Agent-S 桌面操作
    if any(k in t for k in ["打开", "运行", "启动", "截图", "鼠标", "位置", "截屏"]):
        try:
            from modules.agent_s_bridge import check_available
            c = await check_available()
            if c and isinstance(c, dict) and c.get("available"):
                return {"success": True, "result": "✅ Agent-S 桌面自动化已就绪"}
            else:
                return {"success": True, "result": "⚠️ Agent-S SDK 未就绪，请先安装 gui-agents"}
        except:
            return {"success": True, "result": "⚠️ Agent-S 暂不可用，但系统其他功能正常"}

    # 3. 定时任务
    if any(k in t for k in ["每天", "定时", "每周", "重复", "schedule", "cron"]):
        return {"success": True, "result":
            "⏰ 定时任务支持。你可以设置:\n"
            "• 每天下午5点备份\n• 每周末清理日志\n• 每小时检查服务器\n"
            "请详细说明你的需求"}

    # 4. 模块查询
    if any(k in t for k in ["模块", "能力", "功能", "module"]):
        try:
            from api.infra import registry
            mods = list(registry.modules.keys())[:10]
            if mods:
                return {"success": True, "result":
                    "📦 系统已注册能力:\n" + "\n".join(f"  • {m}" for m in mods) + "\n\n(仅显示前10个)"}
            else:
                return {"success": True, "result": "📦 系统能力已准备就绪"}
        except:
            pass

    # 5. 通知
    if any(k in t for k in ["通知", "推送", "提醒", "告警", "alert", "notify"]):
        return {"success": True, "result": "🔔 通知推送支持: 钉钉 / 飞书 / 邮件 / Webhook，需要配置后使用"}

    # 6. 帮助
    if any(k in t for k in ["帮助", "能做什么", "help"]):
        return {"success": True, "result":
            "🤖 **我能帮你做什么？**\n\n"
            "📊 **检查状态** — \"系统怎么样\"\n"
            "📷 **截图** — \"帮我截图\"\n"
            "⏰ **定时任务** — \"每天下午5点备份\"\n"
            "📦 **模块查询** — \"有什么能力\"\n"
            "🔔 **通知** — \"通知我服务器状态\"\n"
            "🎤 **语音输入** — 点 🎤 按钮说话"}

    # 默认
    return {"success": True, "result":
        f"收到: \"{req.message[:80]}\"\n\n"
        f"我不太确定你想做什么。你可以试试:\n"
        f"• 检查系统状态 — \"系统怎么样\"\n"
        f"• 查看能力 — \"有什么功能\"\n"
        f"• 设置定时任务 — \"每天下午5点备份\"\n"
        f"• 语音输入 — 点 🎤 按钮说话"}
