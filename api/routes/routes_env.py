from core.logging_config import get_logger
logger = get_logger("evo.routes_env")
"""AUTO-EVO-AI V0.1 — 环境配置管理（用户输入账号即可启用）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os, json, sqlite3, time
from pathlib import Path

router = APIRouter()
BASE = Path(__file__).resolve().parent.parent.parent
DB = BASE / "data" / "env_settings.db"
ENV_FILE = BASE / ".env"

_ENV_TEMPLATES = {
    "llm": [
        {"key":"OPENAI_API_KEY","label":"OpenAI API Key","placeholder":"sk-...","doc":"用于GPT-4/GPT-3.5对话"},
        {"key":"DEEPSEEK_API_KEY","label":"DeepSeek API Key","placeholder":"sk-...","doc":"用于DeepSeek对话（国内可用）"},
        {"key":"ZHIPU_API_KEY","label":"智谱GLM API Key","placeholder":"xxx.xxx","doc":"用于GLM-4-Flash对话"},
        {"key":"ANTHROPIC_API_KEY","label":"Anthropic API Key","placeholder":"sk-ant-...","doc":"用于Claude对话"},
    ],
    "devops": [
        {"key":"GITHUB_TOKEN","label":"GitHub Personal Token","placeholder":"ghp_...","doc":"仓库操作/PR审查/Issues"},
        {"key":"GITLAB_TOKEN","label":"GitLab Token","placeholder":"glpat-...","doc":"GitLab仓库操作"},
    ],
    "comm": [
        {"key":"SMTP_HOST","label":"SMTP服务器","placeholder":"smtp.gmail.com","doc":"邮件发送"},
        {"key":"SMTP_PORT","label":"SMTP端口","placeholder":"587","doc":""},
        {"key":"SMTP_USER","label":"SMTP用户名","placeholder":"user@gmail.com","doc":""},
        {"key":"SMTP_PASS","label":"SMTP密码","placeholder":"****","doc":""},
        {"key":"DINGTALK_WEBHOOK","label":"钉钉Webhook URL","placeholder":"https://oapi.dingtalk.com/...","doc":"群消息通知"},
        {"key":"SLACK_WEBHOOK","label":"Slack Webhook URL","placeholder":"https://hooks.slack.com/...","doc":"频道消息通知"},
        {"key":"TELEGRAM_BOT_TOKEN","label":"Telegram Bot Token","placeholder":"123:ABC","doc":"Telegram机器人"},
    ],
    "storage": [
        {"key":"AWS_ACCESS_KEY_ID","label":"AWS Access Key","placeholder":"AKIA...","doc":"S3对象存储"},
        {"key":"AWS_SECRET_ACCESS_KEY","label":"AWS Secret Key","placeholder":"****","doc":""},
        {"key":"OSS_ACCESS_KEY","label":"阿里云OSS AccessKey","placeholder":"LTAI...","doc":"阿里云对象存储"},
    ],
}

def _get_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB))
    conn.execute("CREATE TABLE IF NOT EXISTS env_settings (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)")
    return conn

@router.get("/api/v1/settings")
async def list_settings():
    """列出所有可配置的环境变量（含分类）"""
    conn = _get_db()
    saved = {r[0]: r[1] for r in conn.execute("SELECT key, value FROM env_settings").fetchall()}
    conn.close()
    categories = {}
    for cat, items in _ENV_TEMPLATES.items():
        entries = []
        for item in items:
            val = saved.get(item["key"], os.environ.get(item["key"], ""))
            entry = {**item, "value": val[:20] + "..." if len(val) > 20 else val, "configured": bool(val)}
            entries.append(entry)
        categories[cat] = entries
    return {"success": True, "categories": categories, "total": sum(len(v) for v in categories.values())}

class SetSettingRequest(BaseModel):
    key: str
    value: str

@router.post("/api/v1/settings/set")
async def set_setting(req: SetSettingRequest):
    """保存配置到数据库 + 写入.env"""
    conn = _get_db()
    conn.execute("REPLACE INTO env_settings (key, value, updated_at) VALUES (?, ?, ?)",
                 (req.key, req.value, time.time()))
    conn.commit()
    conn.close()
    # 同步写入.env文件
    try:
        lines = []
        if ENV_FILE.exists():
            lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{req.key}="):
                lines[i] = f"{req.key}={req.value}"
                found = True
                break
        if not found:
            lines.append(f"{req.key}={req.value}")
        ENV_FILE.write_text("\n".join(lines), encoding="utf-8")
    except Exception as _ex:
        logger.warning(f"[routes_env]" + str(_ex)[:80])
    # 写入当前进程环境
    os.environ[req.key] = req.value
    return {"success": True, "result": f"✅ {req.key} 已配置"}

@router.get("/api/v1/settings/status")
async def settings_status():
    """返回配置概览：已配置/总项"""
    conn = _get_db()
    saved = set(r[0] for r in conn.execute("SELECT key FROM env_settings").fetchall())
    conn.close()
    total = sum(len(v) for v in _ENV_TEMPLATES.values())
    return {"success": True, "configured": len(saved), "total": total, "percent": f"{len(saved)/max(total,1)*100:.0f}%"}

def register_routes(app):
    app.include_router(router)
setup_env_routes = register_routes
