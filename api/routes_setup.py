"""
首次运行配置 API — 用户下载后首次打开时引导配置
"""
import os, json, secrets, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.logging_config import get_logger

logger = get_logger("evo.api.setup")
router = APIRouter()

# 配置文件存放位置
_EVO_DATA = Path(os.environ.get("EVO_DATA_DIR", "D:/AUTO-EVO-AI-V0.1/.evo_data"))
_SETUP_FLAG = _EVO_DATA / "setup_complete.flag"
_USERS_FILE = _EVO_DATA / "users.json"

class SetupRequest(BaseModel):
    username: str
    password: str
    api_keys: dict = {}  # {"zhipu": "xxx", "openai": "sk-..."}
    admin_key: str = ""  # 自动生成，可选自定义

def _is_first_run() -> bool:
    """检测是否为首次运行"""
    return not _SETUP_FLAG.exists()

@router.get("/api/v1/setup/status")
@router.get("/api/setup/status")
async def setup_status():
    """返回系统是否已配置"""
    if _is_first_run():
        return {
            "success": True,
            "setup_required": True,
            "message": "首次运行，请先完成系统配置"
        }
    return {
        "success": True,
        "setup_required": False,
        "message": "系统已配置，可以登录"
    }

@router.post("/api/v1/setup/complete")
@router.post("/api/setup/complete")
async def setup_complete(req: SetupRequest):
    """完成首次配置：创建管理员用户 + 保存 API Key + 生成 JWT 密钥"""
    if not _is_first_run():
        raise HTTPException(400, detail="系统已配置，不能重复配置")

    if not req.username or len(req.username) < 2:
        raise HTTPException(400, detail="用户名至少2个字符")
    if not req.password or len(req.password) < 4:
        raise HTTPException(400, detail="密码至少4个字符")

    # 创建数据目录
    _EVO_DATA.mkdir(parents=True, exist_ok=True)

    # 1. 保存用户
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((req.password + salt).encode()).hexdigest()
    users = {
        "admin": {
            "username": req.username,
            "password_hash": pwd_hash,
            "salt": salt,
            "role": "admin",
            "created_at": datetime.now().isoformat(),
        }
    }
    with open(_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

    # 2. 保存 API Key 到环境变量 / .env
    env_path = Path("D:/AUTO-EVO-AI-V0.1/.env")
    env_lines = []
    if env_path.exists():
        env_lines = env_path.read_text(encoding="utf-8").splitlines()
    
    api_key_env_map = {
        "zhipu": "ZHIPU_API_KEY",
        "openai": "OPENAI_API_KEY",
        "api2d": "API2D_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "github": "GITHUB_TOKEN",
    }
    new_env = []
    for line in env_lines:
        key = line.split("=")[0] if "=" in line else ""
        if key not in api_key_env_map.values() and key:  # 保留非 API 的配置
            new_env.append(line)
    
    for k, v in req.api_keys.items():
        if v and k in api_key_env_map:
            new_env.append(f"{api_key_env_map[k]}={v}")
            os.environ[api_key_env_map[k]] = v  # 立即生效

    # 3. 生成/保存 Admin Key
    admin_key = req.admin_key or secrets.token_urlsafe(32)
    new_env.append(f"# EVO_ADMIN_KEY={admin_key}")  # 注释掉，日志可见
    new_env.append(f"EVO_ADMIN_KEY={admin_key}")

    env_path.write_text("\n".join(new_env) + "\n", encoding="utf-8")

    # 4. 写入完成标记
    _SETUP_FLAG.write_text(datetime.now().isoformat(), encoding="utf-8")

    logger.info("[SETUP] 首次配置完成: username=%s, admin_key前8位=%s", req.username, admin_key[:8])

    return {
        "success": True,
        "message": "配置完成，请使用用户名和密码登录",
        "admin_key_preview": admin_key[:8] + "...",
    }

@router.get("/api/v1/setup/info")
@router.get("/api/setup/info")
async def setup_info():
    """返回系统信息（用于下载页面展示）"""
    return {
        "success": True,
        "system": "AUTO-EVO-AI V0.1",
        "version": "V0.1",
        "features": [
            "452 个智能模块",
            "30 个外部工具集成",
            "多模型 LLM 网关",
            "13 通道通知推送",
            "桌面自动化 (Agent-S)",
            "语音输入",
            "定时调度 / 事件引擎",
        ],
        "docs_url": "/scalar",
    }
