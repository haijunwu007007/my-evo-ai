"""
AUTO-EVO-AI V0.1 — i18n 多语言引擎
提供 /api/v1/i18n?lang=zh-CN 端点，支持 Accept-Language
"""
from fastapi import APIRouter, Request
from typing import Optional
import json, os
from pathlib import Path

router = APIRouter()

BASE = Path(__file__).resolve().parent.parent
I18N_DIR = BASE / "i18n"

# 内置翻译（覆盖前端所有页面文本）
_TRANSLATIONS = {
    "zh-CN": {
        "lang_name": "中文", "title": "AUTO-EVO-AI",
        "subtitle": "生产力级 AI 自动化编排系统",
        "login_heading": "开始使用", "login_btn": "进入系统",
        "tab_chat": "对话", "tab_dashboard": "仪表盘", "tab_enterprise": "企业管理",
        "input_placeholder": "输入你想做的事...",
        "new_chat": "新对话", "history": "历史", "logout": "退出",
        "greeting": "你好，{name}！有什么可以帮你？",
        "loading": "加载中...", "error": "出错了", "retry": "重试",
        "save": "保存", "cancel": "取消", "delete": "删除", "edit": "编辑",
        "search": "搜索", "filter": "筛选", "sort": "排序",
        "status_running": "运行中", "status_stopped": "已停止", "status_error": "异常",
        "modules": "模块", "skills": "技能", "integrations": "集成",
        "settings": "设置", "help": "帮助", "about": "关于",
        "theme_light": "亮色", "theme_dark": "暗色", "theme_system": "跟随系统",
        "api_docs": "API 文档", "workflow": "工作流",
        "no_data": "暂无数据", "confirm_delete": "确认删除？",
        "upload": "上传", "download": "下载", "copy": "复制",
        "success": "成功", "fail": "失败", "pending": "待处理",
    },
    "en": {
        "lang_name": "English", "title": "AUTO-EVO-AI",
        "subtitle": "Enterprise AI Automation Platform",
        "login_heading": "Get Started", "login_btn": "Enter",
        "tab_chat": "Chat", "tab_dashboard": "Dashboard", "tab_enterprise": "Enterprise",
        "input_placeholder": "What can I do for you...",
        "new_chat": "New Chat", "history": "History", "logout": "Logout",
        "greeting": "Hello {name}! How can I help?",
        "loading": "Loading...", "error": "Error", "retry": "Retry",
        "save": "Save", "cancel": "Cancel", "delete": "Delete", "edit": "Edit",
        "search": "Search", "filter": "Filter", "sort": "Sort",
        "status_running": "Running", "status_stopped": "Stopped", "status_error": "Error",
        "modules": "Modules", "skills": "Skills", "integrations": "Integrations",
        "settings": "Settings", "help": "Help", "about": "About",
        "theme_light": "Light", "theme_dark": "Dark", "theme_system": "System",
        "api_docs": "API Docs", "workflow": "Workflow",
        "no_data": "No data", "confirm_delete": "Confirm delete?",
        "upload": "Upload", "download": "Download", "copy": "Copy",
        "success": "Success", "fail": "Failed", "pending": "Pending",
    },
    "ja": {
        "lang_name": "日本語", "title": "AUTO-EVO-AI",
        "subtitle": "AI自動化プラットフォーム",
        "login_heading": "開始", "login_btn": "入る",
        "tab_chat": "チャット", "tab_dashboard": "ダッシュボード", "tab_enterprise": "企業管理",
        "input_placeholder": "何をしますか...",
        "new_chat": "新規", "history": "履歴", "logout": "ログアウト",
        "greeting": "{name}さん！何をしますか？",
        "loading": "読み込み中...", "error": "エラー", "retry": "再試行",
        "save": "保存", "cancel": "キャンセル", "delete": "削除", "edit": "編集",
        "search": "検索", "filter": "フィルター", "sort": "並び替え",
        "status_running": "実行中", "status_stopped": "停止", "status_error": "異常",
        "modules": "モジュール", "skills": "スキル", "integrations": "連携",
        "settings": "設定", "help": "ヘルプ", "about": "について",
        "theme_light": "ライト", "theme_dark": "ダーク", "theme_system": "システム",
        "api_docs": "API文書", "workflow": "ワークフロー",
        "no_data": "データなし", "confirm_delete": "削除しますか？",
        "upload": "アップロード", "download": "ダウンロード", "copy": "コピー",
        "success": "成功", "fail": "失敗", "pending": "待機中",
    },
}

# 加载文件系统中的 i18n JSON
for f in sorted(I18N_DIR.glob("*.json")):
    try:
        lang = f.stem
        data = json.loads(f.read_text(encoding="utf-8"))
        if lang in _TRANSLATIONS:
            _TRANSLATIONS[lang].update(data)
        else:
            _TRANSLATIONS[lang] = data
    except: pass


@router.get("/api/v1/i18n")
async def get_i18n(lang: str = "zh-CN", request: Request = None):
    """获取翻译 JSON"""
    # 支持 Accept-Language
    if request and request.headers.get("accept-language"):
        accept = request.headers["accept-language"].split(",")[0].split("-")[0]
        for code in _TRANSLATIONS:
            if code.startswith(accept):
                lang = code
                break
    
    data = _TRANSLATIONS.get(lang) or _TRANSLATIONS.get("zh-CN", {})
    return {"success": True, "lang": lang, "data": data, "available": list(_TRANSLATIONS.keys())}


@router.get("/api/v1/i18n/langs")
async def list_langs():
    return {"success": True, "languages": list(_TRANSLATIONS.keys()), "names": {k: v.get("lang_name", k) for k, v in _TRANSLATIONS.items()}}
