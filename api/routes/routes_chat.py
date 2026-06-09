"""Chat API — 更聪明地理解用户想干什么"""

import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.logging_config import get_logger

logger = get_logger("evo.api.chat")
router = APIRouter()

# ── 导入后端翻译 ──
try:
    from api.routes.routes_i18n import I18N_BACKEND
except:
    I18N_BACKEND = {}

def _t(key: str, lang: str = "zh-CN") -> str:
    """获取翻译，回退到中文"""
    d = I18N_BACKEND.get(lang) or I18N_BACKEND.get("zh-CN") or {}
    val = d.get(key) or I18N_BACKEND.get("zh-CN", {}).get(key)
    if val is None:
        val = key
    return val

class ChatRequest(BaseModel):
    message: str
    lang: str = "zh-CN"

# ── 意图定义 ─────────────────────────────────
INTENTS = [
    {"id": "status", "patterns": ["状态", "健康", "运行", "还好", "正常", "情况", "怎么样", "status", "health"],
     "priority": 3},
    {"id": "capabilities", "patterns": ["什么功能", "能做什么", "你会什么", "能力", "用途", "help", "使用", "哪些", "能干"],
     "priority": 2},
    {"id": "greeting", "patterns": ["你好", "嗨", "hi", "hello", "在吗", "在不在"],
     "priority": 2},
    {"id": "biz", "patterns": ["billion", "集团", "企业", "公司", "部门", "员工"],
     "priority": 1},
    {"id": "agent", "patterns": ["截图", "操作", "鼠标", "桌面", "agent", "Agent"],
     "priority": 1},
    {"id": "schedule", "patterns": ["每天", "定时", "每周", "重复", "自动", "备份", "schedule", "cron"],
     "priority": 1},
    {"id": "notify", "patterns": ["通知", "推送", "提醒", "告警", "钉钉", "alert"],
     "priority": 1},
]

def _detect_intent(text: str) -> list:
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

@router.post("/api/v1/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        return {"success": True, "result": _t("unknown", req.lang)}
    lang = req.lang if req.lang in I18N_BACKEND else "zh-CN"
    t = req.message.lower().strip()
    intents = _detect_intent(t)

    # 1. 问候
    if "greeting" in intents and intents[0] == "greeting":
        return {"success": True, "result": _t("greeting", lang)}

    # 2. 状态
    if "status" in intents:
        try:
            from modules.agent_s_bridge import get_status
            s = await get_status()
            if s and isinstance(s, dict):
                ver = s.get('version', '-')
                sdk = _t("sdk_ready" if s.get('sdk_available') else "sdk_missing", lang)
                key = _t("key_ready" if s.get('has_openai_key') else "key_missing", lang)
                st = _t("status_ok", lang)
                st = st.replace("{version}", ver).replace("{sdk}", sdk).replace("{key}", key)
                return {"success": True, "result": st}
        except:
            pass
        return {"success": True, "result": _t("unknown", lang)}

    # 3. 能力
    if "capabilities" in intents:
        return {"success": True, "result": _t("what_can_do", lang)}

    # 4. 企业
    if "biz" in intents:
        return {"success": True, "result": _t("biz_guide", lang)}

    # 5. 桌面操作
    if "agent" in intents:
        try:
            from modules.agent_s_bridge import check_available
            c = await check_available()
            if c and isinstance(c, dict) and c.get("available"):
                return {"success": True, "result": "✅ " + _t("sdk_ready", lang)}
            else:
                return {"success": True, "result": "⚠️ " + _t("sdk_missing", lang)}
        except:
            pass
        return {"success": True, "result": _t("unknown", lang)}

    # 6. 定时
    if "schedule" in intents:
        return {"success": True, "result": _t("schedule_guide", lang)}

    # 7. 通知
    if "notify" in intents:
        return {"success": True, "result": _t("notify_guide", lang)}

    # 默认
    return {"success": True, "result": _t("unknown", lang)}
