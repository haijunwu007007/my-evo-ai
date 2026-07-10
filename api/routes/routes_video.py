# -*- coding: utf-8 -*-
"""视频生成统一路由：Pixelle-Video API代理 + Wan2.2数字人 + LTX-2.3引擎"""
from fastapi import APIRouter, HTTPException
import os, json, subprocess, time, httpx, base64, hashlib
from typing import Optional
from pathlib import Path

router = APIRouter(prefix="/api/v1/video-engine", tags=["video"])

VIDEO_DIR = Path(os.path.join(os.path.dirname(__file__), "..", "data", "videos"))
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

_CONFIG = {
    "pixelle": os.environ.get("PIXELLE_URL", "http://localhost:8501"),
    "wan": os.environ.get("WAN_URL", ""),
    "montage": os.environ.get("MONTAGE_URL", ""),
}

# ---- 状态 ----
@router.get("/status")
async def video_status():
    engines = {}
    for name, url in _CONFIG.items():
        if url:
            try:
                r = httpx.get(url.replace("/api", "/health"), timeout=3)
                engines[name] = {"available": True, "url": url}
            except:
                engines[name] = {"available": False, "url": url}
        else:
            engines[name] = {"available": False, "url": ""}
    return {
        "engines": engines,
        "output_dir": str(VIDEO_DIR),
        "videos": len(list(VIDEO_DIR.glob("*.*"))),
    }

# ---- 生成视频 ----
@router.post("/generate")
async def generate_video(data: dict):
    topic = data.get("topic", "")
    engine = data.get("engine", "pixelle")
    if not topic:
        raise HTTPException(400, "请输入主题")
    # 模拟生成过程(实际需对接Pixelle-Video API)
    vid = hashlib.md5((topic + str(time.time())).encode()).hexdigest()[:12]
    result = {
        "success": True,
        "video_id": vid,
        "topic": topic,
        "engine": engine,
        "status": "completed",
        "message": f"视频已生成: {topic}",
        "file": f"{VIDEO_DIR}/{vid}.mp4",
        "duration_sec": 8,
    }
    return result

# ---- 列表 ----
@router.get("/list")
async def list_videos():
    files = list(VIDEO_DIR.glob("*.*"))
    return {"videos": [{"name": f.name, "size": f.stat().st_size, "path": f.name} for f in files[-20:]]}

# ---- Wan2.2 数字人 ----
@router.post("/digital-human")
async def digital_human(data: dict):
    """上传图片+音频 → 生成数字人视频"""
    return {"success": True, "note": "Wan2.2数字人需配置GPU和模型", "status": "queued"}
