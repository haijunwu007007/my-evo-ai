"""AUTO-EVO-AI V0.1 — ChatGPT-Next-Web 桥接路由"""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()
B = "/api/v1/tools/nextchat"

NEXTCHAT_URL = "http://127.0.0.1:3099"

@router.get(B)
async def nextchat_status():
    import urllib.request
    try:
        r = urllib.request.urlopen(f"{NEXTCHAT_URL}", timeout=5)
        return {"success": True, "available": True, "url": NEXTCHAT_URL}
    except Exception as e:
        return {"success": True, "available": False, "url": NEXTCHAT_URL, "error": str(e)[:100]}

@router.get("/nextchat", include_in_schema=False)
async def nextchat_redirect():
    return RedirectResponse(url=NEXTCHAT_URL)
