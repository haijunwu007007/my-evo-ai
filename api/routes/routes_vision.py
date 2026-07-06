
"""视觉理解路由 — Ollama VLM 图片内容理解（含自动拉取）"""
from fastapi import APIRouter
import json, base64, httpx, os, asyncio
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])
OLLAMA = "http://localhost:11434"
_DOWNLOADING = False

async def _ensure_model():
    """确保至少有一个视觉模型，没有则自动拉取moondream"""
    global _DOWNLOADING
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            tags = await c.get(f"{OLLAMA}/api/tags")
            models = [m["name"] for m in tags.json().get("models",[])]
            vision = [m for m in models if any(v in m for v in ['llava','moondream','minicpm','vl','vision','internvl'])]
            if vision:
                return vision[0]
            # Auto-pull if not downloading already
            if not _DOWNLOADING:
                _DOWNLOADING = True
                asyncio.create_task(_pull_model())
            return None
    except:
        return None

async def _pull_model():
    """后台拉取视觉模型"""
    global _DOWNLOADING
    try:
        async with httpx.AsyncClient(timeout=600) as c:
            await c.post(f"{OLLAMA}/api/pull", json={"name": "moondream"})
    except:
        pass
    _DOWNLOADING = False

@router.post("/understand")
async def vision_understand(data: dict):
    """理解图片内容"""
    img_b64 = data.get("image_base64", "")
    prompt = data.get("prompt", "请详细描述这张图片的内容")
    if not img_b64:
        return {"success": False, "error": "请提供图片"}
    
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
        return {"success": False, "error": str(e)[:100]}
    return {"success": False, "error": "识别失败"}

@router.get("/status")
async def vision_status():
    """检查视觉模型状态"""
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            tags = await c.get(f"{OLLAMA}/api/tags")
            models = [m["name"] for m in tags.json().get("models",[])]
            vision = [m for m in models if any(v in m for v in ['llava','moondream','minicpm','vl','vision','internvl'])]
            return {"success": True, "ollama_ok": True, "models": models, "vision_models": vision, "downloading": _DOWNLOADING}
    except Exception as e:
        return {"success": False, "ollama_ok": False, "error": str(e)[:100]}
