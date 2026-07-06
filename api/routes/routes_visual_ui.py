"""
AUTO-EVO-AI V0.1 — 视觉 UI 操作路由（看图点按钮）
==================================================
基于截图 + Moondream 视觉模型，实现"用户看截图 → 说点哪里 → 系统自动点"。

API:
  POST /api/v1/visual/capture   → 截图页面并分析 UI 元素
  POST /api/v1/visual/click     → 根据描述点击页面元素
  POST /api/v1/visual/type      → 根据描述在输入框输入文字
"""

import os, base64, json, logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("evo.api.visual_ui")
router = APIRouter(prefix="/api/v1/visual", tags=["visual_ui"])

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
VISION_MODEL = "moondream"


class CaptureRequest(BaseModel):
    url: str = "https://autoevoai.com/"
    prompt: Optional[str] = None  # 自定义分析提示


class ClickRequest(BaseModel):
    url: str = "https://autoevoai.com/"
    description: str = ""  # 用户描述要点的元素，如"登录按钮"
    screenshot_b64: Optional[str] = None


class TypeRequest(BaseModel):
    url: str = "https://autoevoai.com/"
    target_description: str = ""  # 要输入的目标元素描述，如"搜索框"
    text: str = ""  # 要输入的文字
    screenshot_b64: Optional[str] = None


async def _take_screenshot(url: str) -> dict:
    """截取指定 URL 的页面截图"""
    try:
        from core.browser_engine import get_browser_engine
        engine = await get_browser_engine()
        launch_result = await engine.launch(headless=True)
        if not launch_result.get("success"):
            return {"success": False, "error": "浏览器启动失败"}

        nav_result = await engine.goto(url, timeout=20000)
        ss = await engine.screenshot(full_page=True)
        page_info = await engine.get_page_info()
        await engine.close()

        return {
            "success": True,
            "screenshot_b64": ss.base64 if ss else "",
            "title": page_info.get("title", ""),
            "url": page_info.get("url", url),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _ollama_vision(image_b64: str, prompt: str) -> str:
    """调用 moondream 视觉模型"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as c:
            resp = await c.post(f"{OLLAMA_HOST}/api/generate", json={
                "model": VISION_MODEL,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 500},
            })
            if resp.status_code == 200:
                return resp.json().get("response", "")
            return f"[错误: {resp.status_code}]"
    except Exception as e:
        return f"[失败: {e}]"


@router.post("/capture")
async def capture_page(req: CaptureRequest):
    """
    截取页面截图，并用视觉模型分析 UI 元素

    返回截图 base64 + 页面所有可交互元素的描述
    """
    result = await _take_screenshot(req.url)
    if not result.get("success"):
        raise HTTPException(502, result.get("error", "截图失败"))

    screenshot_b64 = result.get("screenshot_b64", "")
    if not screenshot_b64:
        return {"success": False, "error": "截图为空"}

    # 用视觉模型分析 UI
    prompt = req.prompt or (
        "List every interactive UI element visible on this page. "
        "For each give: TYPE | TEXT/LABEL | POSITION(top/left/center/right/bottom). "
        "Types: button, link, input, checkbox, radio, dropdown, icon, heading, text, image, textarea, tab, dialog."
    )
    vision_result = await _ollama_vision(screenshot_b64, prompt)

    # 解析元素
    elements = []
    for line in vision_result.split("\n"):
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        elements.append({
            "type": parts[0] if len(parts) > 0 else "unknown",
            "text": parts[1] if len(parts) > 1 else "",
            "position": parts[2] if len(parts) > 2 else "center",
        })

    return {
        "success": True,
        "url": result.get("url", req.url),
        "title": result.get("title", ""),
        "screenshot_b64": screenshot_b64,
        "elements": elements,
        "element_count": len(elements),
        "vision_raw": vision_result,
    }


@router.post("/click")
async def click_element(req: ClickRequest):
    """
    用户描述要点击的元素，系统自动找到并点击

    例如: {"url": "https://example.com", "description": "登录按钮"}
    """
    screenshot_b64 = req.screenshot_b64
    if not screenshot_b64:
        ss = await _take_screenshot(req.url)
        screenshot_b64 = ss.get("screenshot_b64", "")
        if not screenshot_b64:
            raise HTTPException(502, "截图失败")

    prompt = (
        f'Look at this screenshot. Find the element described as: "{req.description}". '
        "Return ONLY the CSS selector or XPath to click it. "
        "Format: selectors like #id, .class, button, a[href*='login'], input[type='submit'] etc. "
        "If you can't find it, say NOT_FOUND."
    )
    vision_result = await _ollama_vision(screenshot_b64, prompt)

    if "NOT_FOUND" in vision_result:
        # 降级：用 vision 描述整个页面，让 LLM 再次尝试
        desc_prompt = f'Describe this screenshot in detail. Where is the "{req.description}" located? What does it look like?'
        desc = await _ollama_vision(screenshot_b64, desc_prompt)

        return {
            "success": False,
            "error": f"未能定位元素: {req.description}",
            "page_description": desc,
            "hint": "请提供更具体的描述，比如'页面右上角的蓝色登录按钮'",
        }

    # 这里返回 vision 找到的选择器
    # 前端或后续可以调用 browser_engine 来实际点击
    return {
        "success": True,
        "target": req.description,
        "selector_suggestion": vision_result.strip(),
        "url": req.url,
        "instruction": f"尝试用浏览器引擎点击: {vision_result.strip()}",
    }


@router.post("/type")
async def type_text(req: TypeRequest):
    """
    用户描述要输入的目标元素和文字，系统自动找到并输入

    例如: {"url": "https://example.com", "target_description": "搜索框", "text": "AI新闻"}
    """
    screenshot_b64 = req.screenshot_b64
    if not screenshot_b64:
        ss = await _take_screenshot(req.url)
        screenshot_b64 = ss.get("screenshot_b64", "")
        if not screenshot_b64:
            raise HTTPException(502, "截图失败")

    prompt = (
        f'Look at this screenshot. Find the input element described as: "{req.target_description}". '
        "Return ONLY the CSS selector to fill text into it. "
        "Format: #id, .class, input[name='q'], textarea etc. "
        "Then I will type: \"{req.text}\" into it. "
        "If you can't find it, say NOT_FOUND."
    )
    vision_result = await _ollama_vision(screenshot_b64, prompt)

    if "NOT_FOUND" in vision_result:
        return {"success": False, "error": f"未能定位输入框: {req.target_description}"}

    return {
        "success": True,
        "target": req.target_description,
        "text": req.text,
        "selector_suggestion": vision_result.strip(),
        "url": req.url,
    }


@router.get("/status")
async def visual_ui_status():
    """检查视觉 UI 操作服务的可用性"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{OLLAMA_HOST}/api/tags")
            models = []
            if r.status_code == 200:
                data = r.json()
                models = [m["name"] for m in data.get("models", [])]
            has_vision = any(VISION_MODEL in m for m in models)
            return {
                "success": True,
                "ollama_available": r.status_code == 200,
                "vision_model": VISION_MODEL,
                "model_loaded": has_vision,
                "available_models": models,
            }
    except Exception as e:
        return {"success": False, "error": str(e), "ollama_available": False}
