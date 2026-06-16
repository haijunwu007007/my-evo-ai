"""开源中心静态页面路由"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent

@router.get("/hub")
async def hub_page():
    hub_path = BASE_DIR / "frontend" / "hub.html"
    if hub_path.exists():
        return FileResponse(str(hub_path))
    return {"error": "hub page not found"}
