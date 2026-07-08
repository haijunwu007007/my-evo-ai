"""多云模型切换GUI后端 — 可视化切换5大模型（借鉴 WorkBuddy）
支持智谱/DeepSeek/OpenAI/Anthropic/Kimi 一键切换。
"""
from fastapi import APIRouter
from pydantic import BaseModel
from core.logging_config import get_logger
from api.agent_llm import call_llm
import os, json

logger = get_logger("evo.api.llm_config_gui")
router = APIRouter()

PROVIDER_MAP = {
    "zhipu": {"env_key": "ZHIPU_API_KEY", "env_base": "", "model": "glm-4-flash", "name": "智谱 GLM-4-Flash"},
    "deepseek": {"env_key": "DEEPSEEK_API_KEY", "env_base": "DEEPSEEK_BASE_URL", "model": "deepseek-chat", "name": "DeepSeek"},
    "openai": {"env_key": "OPENAI_API_KEY", "env_base": "OPENAI_BASE_URL", "model": "gpt-4o", "name": "OpenAI"},
    "anthropic": {"env_key": "ANTHROPIC_API_KEY", "env_base": "", "model": "claude-3-5-sonnet", "name": "Anthropic"},
    "kimi": {"env_key": "MOONSHOT_API_KEY", "env_base": "MOONSHOT_BASE_URL", "model": "moonshot-v1", "name": "Kimi"},
}

class LLMConfigInput(BaseModel):
    provider: str; model: str = ""; api_key: str = ""; api_base: str = ""

@router.post("/api/v1/config/llm/save")
async def save_llm_config(m: LLMConfigInput):
    if m.provider not in PROVIDER_MAP:
        return {"success": False, "message": f"不支持的Provider: {m.provider}"}
    p = PROVIDER_MAP[m.provider]
    key = m.api_key or os.environ.get(p["env_key"], "")
    if not key:
        return {"success": False, "message": "请提供 API Key"}
    # 保存 API Key（写入 .env 文件）
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        lines = []
        found_key = False
        if os.path.exists(env_path):
            with open(env_path) as f:
                lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.startswith(p["env_key"] + "="):
                new_lines.append(f"{p['env_key']}={key}\n")
                found_key = True
            elif p["env_base"] and line.startswith(p["env_base"] + "="):
                new_lines.append(f"{p['env_base']}={m.api_base}\n" if m.api_base else line)
            else:
                new_lines.append(line)
        if not found_key:
            new_lines.append(f"{p['env_key']}={key}\n")
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        os.environ[p["env_key"]] = key
        logger.info(f"[LLM-CONFIG] 已保存 Provider: {m.provider}")
        return {"success": True, "message": f"✅ {p['name']} 配置已保存"}
    except Exception as e:
        return {"success": False, "message": f"保存失败: {e}"}

@router.post("/api/v1/config/llm/fallback")
async def save_llm_fallback(m: dict):
    fb = m.get("fallback_models", "")
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path) as f:
                lines = f.readlines()
        found = False
        for i, line in enumerate(lines):
            if line.startswith("EVO_FALLBACK_MODELS="):
                lines[i] = f"EVO_FALLBACK_MODELS={fb}\n"
                found = True
                break
        if not found:
            lines.append(f"EVO_FALLBACK_MODELS={fb}\n")
        with open(env_path, "w") as f:
            f.writelines(lines)
        os.environ["EVO_FALLBACK_MODELS"] = fb
        logger.info(f"[LLM-CONFIG] 备用模型已保存: {fb}")
        return {"success": True, "message": "✅ 备用模型配置已保存"}
    except Exception as e:
        return {"success": False, "message": f"保存失败: {e}"}

@router.post("/api/v1/config/llm/test")
async def test_llm(m: dict):
    provider = m.get("provider", "")
    if not provider:
        return {"success": False, "message": "请指定 Provider"}
    try:
        content, _ = call_llm([{"role": "user", "content": "回复OK表示连接正常"}], timeout=10)
        if content and len(content) > 1:
            return {"success": True, "message": f"✅ {provider} 连接成功: {content[:60]}"}
        return {"success": False, "message": f"❌ {provider} 无响应"}
    except Exception as e:
        return {"success": False, "message": f"❌ {provider} 测试失败: {e}"}

@router.get("/api/v1/config/llm/providers")
async def list_providers():
    result = []
    for pid, p in PROVIDER_MAP.items():
        has_key = bool(os.environ.get(p["env_key"], ""))
        result.append({"id": pid, "name": p["name"], "model": p["model"], "configured": has_key, "active": has_key})
    fb = os.environ.get("EVO_FALLBACK_MODELS", "")
    return {"success": True, "providers": result, "fallback_models": fb}
