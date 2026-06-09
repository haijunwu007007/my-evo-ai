"""LLM Chat — 国内外所有主流大模型统一接口"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import httpx, json, random

logger = get_logger("evo.api.llm_chat")
router = APIRouter()

class LLMChatRequest(BaseModel):
    message: str
    api_key: Optional[str] = None
    api_key2: Optional[str] = None  # 某些国内厂商需要两个 Key
    provider: Optional[str] = "openai"
    model: Optional[str] = None
    context: Optional[list] = []

# ── 全球模型提供商配置 ─────────────────────────
PROVIDERS = {
    # 🌐 国际
    "openai": {
        "name": "OpenAI", "emoji": "🌐",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "auth": "Bearer {key}", "default_model": "gpt-4o-mini",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "anthropic": {
        "name": "Anthropic", "emoji": "🌐",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "auth": "x-api-key {key}", "default_model": "claude-3-5-sonnet-20241022",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "anthropic_version": "2023-06-01",
    },
    "google": {
        "name": "Google Gemini", "emoji": "🌐",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        "auth": "", "default_model": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-pro", "gemini-1.5-flash"],
    },
    # 🇨🇳 国内
    "deepseek": {
        "name": "DeepSeek", "emoji": "🇨🇳",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "auth": "Bearer {key}", "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "qwen": {
        "name": "通义千问", "emoji": "🇨🇳",
        "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "auth": "Bearer {key}", "default_model": "qwen-plus",
        "models": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-long"],
    },
    "glm": {
        "name": "智谱GLM", "emoji": "🇨🇳",
        "endpoint": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "auth": "Bearer {key}", "default_model": "glm-4-plus",
        "models": ["glm-4-plus", "glm-4", "glm-4-flash", "glm-4v"],
    },
    "kimi": {
        "name": "月之暗面Kimi", "emoji": "🇨🇳",
        "endpoint": "https://api.moonshot.cn/v1/chat/completions",
        "auth": "Bearer {key}", "default_model": "moonshot-v1-8k",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    },
    "baidu": {
        "name": "文心一言", "emoji": "🇨🇳",
        "endpoint": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{model}",
        "auth": "Bearer {key}", "default_model": "ernie-4.0-8k",
        "models": ["ernie-4.0-8k", "ernie-3.5-8k", "ernie-speed-8k", "ernie-lite-8k"],
        "access_token_url": "https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={key}&client_secret={key2}",
    },
    "spark": {
        "name": "讯飞星火", "emoji": "🇨🇳",
        "endpoint": "https://spark-api.xf-yun.com/v3.5/chat",
        "auth": "Bearer {key}", "default_model": "spark-3.5",
        "models": ["spark-4.0", "spark-3.5", "spark-3.0", "spark-2.0"],
        "appid": "{key2}",
    },
    "yi": {
        "name": "零一万物Yi", "emoji": "🇨🇳",
        "endpoint": "https://api.lingyiwanwu.com/v1/chat/completions",
        "auth": "Bearer {key}", "default_model": "yi-lightning",
        "models": ["yi-lightning", "yi-medium", "yi-large", "yi-vision"],
    },
    "minimax": {
        "name": "MiniMax", "emoji": "🇨🇳",
        "endpoint": "https://api.minimax.chat/v1/text/chatcompletion_v2",
        "auth": "Bearer {key}", "default_model": "abab6.5s-chat",
        "models": ["abab7-chat", "abab6.5s-chat", "abab5.5-chat"],
    },
    # 🏠 本地
    "ollama": {
        "name": "Ollama 本地", "emoji": "🏠",
        "endpoint": "http://localhost:11434/api/chat",
        "auth": "", "default_model": "qwen2.5",
        "models": ["qwen2.5", "llama3", "deepseek-r1", "mistral"],
    },
    "onetoken": {
        "name": "OneAPI/统一网关", "emoji": "🔗",
        "endpoint": "http://localhost:8000/v1/chat/completions",
        "auth": "Bearer {key}", "default_model": "gpt-3.5-turbo",
        "models": ["*"],  # 任意模型名
    },
}

@router.get("/api/v1/providers")
async def list_providers():
    """列出所有可用模型提供商"""
    result = []
    for pid, p in PROVIDERS.items():
        result.append({"id": pid, "name": p["name"], "emoji": p["emoji"],
                        "models": p["models"], "default_model": p["default_model"]})
    return {"success": True, "providers": result}

@router.post("/api/v1/chat/llm")
async def llm_chat(req: LLMChatRequest):
    if not req.message.strip():
        raise HTTPException(400, detail="说点什么")

    provider_id = req.provider or "openai"
    provider = PROVIDERS.get(provider_id)
    if not provider:
        return {"success": False, "error": f"不支持的提供商: {provider_id}，可选: {', '.join(PROVIDERS.keys())}"}

    model = req.model or provider["default_model"]
    key = req.api_key or ""
    key2 = req.api_key2 or ""

    # 无 Key 且需要 Key → 返回提示
    if provider["auth"] and not key and provider_id not in ("ollama", "onetoken"):
        return {"success": False, "error": "no_api_key", "provider": provider["name"],
                "hint": f"请在请求中传入 api_key 参数（{provider['name']} 密钥）"}

    # 构建消息
    system_prompt = "你是 AUTO-EVO-AI 助手，专业、简洁、用中文回答。"
    messages = [{"role": "system", "content": system_prompt}]
    for ctx in (req.context or [])[-6:]:
        if isinstance(ctx, dict):
            messages.append({"role": ctx.get("role", "user"), "content": str(ctx.get("content", ""))})
    messages.append({"role": "user", "content": req.message})

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            headers = {"Content-Type": "application/json"}
            if provider["auth"]:
                headers["Authorization"] = provider["auth"].format(key=key, key2=key2)
            if provider.get("anthropic_version"):
                headers["anthropic-version"] = provider["anthropic_version"]
            if provider.get("appid"):
                headers["X-Appid"] = provider["appid"].format(key=key, key2=key2)

            # 不同提供商的不同请求格式
            if provider_id == "google":
                url = provider["endpoint"].format(model=model, key=key)
                payload = {"contents": [{"parts": [{"text": req.message}]}]}
            elif provider_id == "anthropic":
                url = provider["endpoint"]
                payload = {"model": model, "max_tokens": 1024,
                           "messages": [{"role": "user", "content": req.message}]}
            elif provider_id == "ollama":
                url = provider["endpoint"]
                payload = {"model": model, "messages": messages, "stream": False}
            elif provider_id == "baidu":
                url = provider["endpoint"].replace("{model}", model.split("/")[-1])
                payload = {"messages": messages}
            else:
                url = provider["endpoint"]
                payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 2048}

            r = await client.post(url, headers=headers, json=payload, timeout=120)

            if r.status_code == 200:
                data = r.json()
                # 统一提取回复文本
                text = ""
                if provider_id == "anthropic":
                    text = data.get("content", [{}])[0].get("text", "")
                elif provider_id == "google":
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                elif provider_id == "ollama":
                    text = data.get("message", {}).get("content", "")
                else:
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not text:
                    text = json.dumps(data, ensure_ascii=False)[:200]
                return {"success": True, "result": text, "provider": provider["name"], "model": model}
            else:
                return {"success": False, "error": f"{provider['name']} 返回 {r.status_code}", "detail": r.text[:300]}
    except Exception as e:
        return {"success": False, "error": str(e), "provider": provider["name"]}
