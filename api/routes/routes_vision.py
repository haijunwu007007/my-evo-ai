
"""
视觉理解路由 — 双通道（GLM-4V API优先 → Ollama moondream降级）
===========================================================
优先级: 1.智谱GLM-4V(旗舰级质量,无需GPU) 2.Ollama moondream(本地镜像,可用可不要求)
"""
from fastapi import APIRouter
import json, base64, httpx, os, asyncio
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
logger = get_logger("evo.api.vision")

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])
OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
ZHIPU_API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
_DOWNLOADING = False

# ── 通道1: 智谱 GLM-4V API（优先，高质量） ──
async def _zhipu_vision(img_b64: str, prompt: str) -> dict | None:
    """调用智谱GLM-4V视觉理解"""
    api_key = os.environ.get("ZHIPU_API_KEY", "")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(ZHIPU_API, json={
                "model": "glm-4v-flash",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }],
                "max_tokens": 1024,
            }, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            })
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                return {"success": True, "description": content, "model": "zhipu:glm-4v-flash"}
            logger.warning(f"[Vision] Zhipu API error {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        logger.error(f"[Vision] Zhipu API failed: {e}")
    return None

# ── 通道2: Ollama moondream（降级，本地） ──
async def _ensure_model():
    global _DOWNLOADING
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            tags = await c.get(f"{OLLAMA}/api/tags")
            models = [m["name"] for m in tags.json().get("models",[])]
            vision = [m for m in models if any(v in m for v in ['llava','moondream','minicpm','vl','vision','internvl'])]
            if vision:
                return vision[0]
            if not _DOWNLOADING:
                _DOWNLOADING = True
                asyncio.create_task(_pull_model())
            return None
    except:
        return None

async def _pull_model():
    global _DOWNLOADING
    try:
        async with httpx.AsyncClient(timeout=600) as c:
            await c.post(f"{OLLAMA}/api/pull", json={"name": "moondream"})
    except Exception as _e:
            logger.warning(f"exception: {_e}")
    _DOWNLOADING = False

async def _ollama_vision(img_b64: str, prompt: str) -> dict:
    model = await _ensure_model()
    if not model:
        return {"success": False, "error": "模型拉取中", "downloading": True}
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            resp = await c.post(f"{OLLAMA}/api/generate", json={
                "model": model, "prompt": prompt,
                "images": [img_b64], "stream": False,
                "options": {"num_predict": 512}
            })
            if resp.status_code == 200:
                return {"success": True, "description": resp.json().get("response",""), "model": model}
    except Exception as e:
        return {"success": False, "error": f"Ollama: {e}"[:100]}
    return {"success": False, "error": "Ollama识别失败"}

# ── 统一入口 ──
@router.post("/understand")
async def vision_understand(data: dict):
    """理解图片内容（智谱API优先 → Ollama降级）"""
    img_b64 = data.get("image_base64", "")
    prompt = data.get("prompt", "请详细描述这张图片的内容")
    if not img_b64:
        return {"success": False, "error": "请提供图片"}

    # 优先调智谱GLM-4V（高质量，不走本地GPU）
    zhipu = await _zhipu_vision(img_b64, prompt)
    if zhipu and zhipu.get("success"):
        return zhipu

    # 降级到Ollama moondream
    return await _ollama_vision(img_b64, prompt)

@router.get("/status")
async def vision_status():
    """检查视觉模型状态"""
    api_key = bool(os.environ.get("ZHIPU_API_KEY", ""))
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            tags = await c.get(f"{OLLAMA}/api/tags")
            models = [m["name"] for m in tags.json().get("models",[])]
            vision = [m for m in models if any(v in m for v in ['llava','moondream','minicpm','vl','vision','internvl'])]
            return {
                "success": True,
                "zhipu_api": api_key,
                "glm_4v": True,
                "ollama_ok": True,
                "models": models,
                "vision_models": vision,
                "downloading": _DOWNLOADING,
                "primary": "zhipu:glm-4v-flash" if api_key else "ollama:moondream",
            }
    except Exception as e:
        return {"success": True, "zhipu_api": api_key, "glm_4v": True,
                "ollama_ok": False, "error": str(e)[:50],
                "primary": "zhipu:glm-4v-flash" if api_key else "none"}
