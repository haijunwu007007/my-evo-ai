"""后端国际化 — 根据 Accept-Language 返回对应语言的响应"""

from fastapi import APIRouter, Request
from typing import Optional

router = APIRouter()

I18N_BACKEND = {
    "zh-CN": {
        "status_ok": "✅ 一切正常 • 版本 {version} • {sdk} • {key}",
        "sdk_ready": "桌面自动化就绪",
        "sdk_missing": "桌面自动化未安装",
        "key_ready": "API Key 已配置",
        "key_missing": "API Key 未配置",
        "what_can_do": "我能干这些事：\n📊 系统状态 — 「系统怎么样」\n🤖 AI团队讨论 — 「团队讨论xxx」\n🖥️ 桌面操作 — 「帮我截图」\n⏰ 定时任务 — 「每天下午5点备份」\n🏢 企业管理 — 点右上角「企业管理」\n🎤 语音输入 — 点 🎤 按钮\n\n你想先试哪个？",
        "help": "我能干的：\n📊 状态\n🤖 AI讨论\n🖥️ 操作\n⏰ 定时\n🏢 企业\n🎤 语音",
        "team_created": "✅ 团队已组建：{count} 个智能体正在讨论「{task}」",
        "unknown": "没太明白，试试说「你会什么」",
        "greeting": "在呢！说「你会什么」看看我能干啥",
        "biz_guide": "企业功能在右上角「企业管理」页面",
        "notify_guide": "通知支持钉钉/飞书/邮件，先配一下",
        "schedule_guide": "定时任务可以设，比如「每天下午5点备份」",
    },
    "en": {
        "status_ok": "✅ All good • Version {version} • {sdk} • {key}",
        "sdk_ready": "Desktop automation ready",
        "sdk_missing": "Desktop automation not installed",
        "key_ready": "API Key configured",
        "key_missing": "API Key not configured",
        "what_can_do": "Here's what I can do:\n📊 System status — \"check status\"\n🤖 AI team discuss — \"team discuss xxx\"\n🖥️ Desktop — \"screenshot\"\n⏰ Schedule — \"daily backup at 5pm\"\n🏢 Enterprise — click \"Enterprise\" top right\n🎤 Voice — click 🎤\n\nWhat first?",
        "help": "I can:\n📊 Status\n🤖 AI discuss\n🖥️ Desktop\n⏰ Schedule\n🏢 Enterprise\n🎤 Voice",
        "team_created": "✅ Team created: {count} agents discussing \"{task}\"",
        "unknown": "Not sure what you mean. Try \"what can you do\"",
        "greeting": "Hi! Say \"what can you do\" to see my skills",
        "biz_guide": "Enterprise features in top right \"Enterprise\" page",
        "notify_guide": "Notifications support DingTalk/Feishu/Email, configure first",
        "schedule_guide": "Scheduled tasks available, e.g. \"backup at 5pm daily\"",
    },
    "ja": {
        "status_ok": "✅ 正常稼働 • バージョン {version} • {sdk} • {key}",
        "sdk_ready": "デスクトップ自動化利用可能",
        "sdk_missing": "デスクトップ自動化未インストール",
        "key_ready": "API Key 設定済み",
        "key_missing": "API Key 未設定",
        "what_can_do": "できること：\n📊 状態確認\n🤖 AIチーム討論\n🖥️ デスクトップ操作\n⏰ 定期タスク\n🏢 企業管理\n🎤 音声入力\n\n何を試しますか？",
        "help": "対応機能：\n📊 状態\n🤖 AI討論\n🖥️ 操作\n⏰ 定期\n🏢 企業\n🎤 音声",
        "team_created": "✅ チーム編成：{count} 体のAIが「{task}」を討論中",
        "unknown": "意味がわかりません。「できること」と試してください",
        "greeting": "こんにちは！「できること」で機能一覧を表示します",
        "biz_guide": "企業機能は右上の「企業管理」ページ",
        "notify_guide": "通知はDingTalk/Feishu/メール対応。先に設定",
        "schedule_guide": "定期タスク可能。「毎日17時にバックアップ」",
    },
    "ko": {
        "status_ok": "✅ 정상 작동 • 버전 {version} • {sdk} • {key}",
        "sdk_ready": "데스크톱 자동화 준비됨",
        "sdk_missing": "데스크톱 자동화 미설치",
        "key_ready": "API Key 설정됨",
        "key_missing": "API Key 미설정",
        "what_can_do": "할 수 있는 일:\n📊 상태 확인\n🤖 AI 팀 토론\n🖥️ 데스크톱 작업\n⏰ 예약 작업\n🏢 기업 관리\n🎤 음성 입력\n\n무엇을 먼저 할까요?",
        "help": "가능한 기능:\n📊 상태\n🤖 AI 토론\n🖥️ 작업\n⏰ 예약\n🏢 기업\n🎤 음성",
        "team_created": "✅ 팀 구성: {count}개 AI가 「{task}」토론 중",
        "unknown": "이해하지 못했습니다. 「할 수 있는 일」을 입력해보세요",
        "greeting": "안녕하세요! 「할 수 있는 일」로 기능을 확인하세요",
        "biz_guide": "기업 기능은 우측 상단 「기업관리」페이지",
        "notify_guide": "알림은 DingTalk/Feishu/메일 지원. 먼저 설정",
        "schedule_guide": "예약 작업 가능. 「매일 오후5시 백업」",
    },
}

def detect_lang(request: Request) -> str:
    """从请求中检测语言"""
    # 1. URL 参数
    lang = request.query_params.get("lang", "")
    if lang in I18N_BACKEND:
        return lang
    # 2. Accept-Language 头
    accept = request.headers.get("accept-language", "")
    for supported in ["zh-CN", "en", "ja", "ko"]:
        if supported in accept:
            return supported
    # 3. 默认
    return "zh-CN"

@router.get("/api/v1/i18n")
async def get_i18n(request: Request, lang: Optional[str] = None):
    """获取指定语言或浏览器语言的翻译"""
    locale = detect_lang(request)
    return {"success": True, "locale": locale, "translations": I18N_BACKEND.get(locale, I18N_BACKEND["zh-CN"])}

@router.get("/api/v1/i18n/{key}")
async def get_translation(key: str, request: Request, lang: Optional[str] = None):
    """获取单个翻译键值"""
    locale = detect_lang(request)
    trans = I18N_BACKEND.get(locale, I18N_BACKEND["zh-CN"])
    value = trans.get(key, I18N_BACKEND["zh-CN"].get(key, key))
    return {"success": True, "locale": locale, "key": key, "value": value}
