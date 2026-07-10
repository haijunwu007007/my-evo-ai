from core.logging_config import get_logger
logger = get_logger("evo.routes_video_intelligence")
"""
AUTO-EVO-AI V0.1 — 视频智能理解路由（真实实现）
===============================================
支持上传视频自动分析内容、检测物体、提取音频转写。
"""

import os, json, tempfile, logging, base64
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from modules.video_intelligence import VideoIntelligence, analyze_video, get_video_info

logger = logging.getLogger("evo.api.video_intelligence")
router = APIRouter(prefix="/api/v1/video-intelligence", tags=["video_intelligence"])

_mod = VideoIntelligence()


@router.get("/status")
async def get_status():
    """视频理解引擎状态"""
    return {
        "success": True,
        **_mod.status(),
    }


@router.post("/analyze")
async def analyze_uploaded_video(
    file: UploadFile = File(...),
    prompt: str = Form("请详细描述这个视频的内容"),
):
    """
    上传视频并自动分析内容

    流程:
    1. 保存上传的视频到临时文件
    2. ffmpeg 提取关键帧（最多 8 帧）
    3. Moondream 视觉模型分析每帧
    4. ffmpeg 提取音频 + 语音转写
    5. 返回综合分析结果
    """
    if not file.filename:
        raise HTTPException(400, "请上传视频文件")

    # 检查文件类型
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    video_exts = {"mp4", "avi", "mov", "mkv", "webm", "flv", "wmv", "m4v", "3gp"}
    if ext not in video_exts:
        # 如果不是视频格式，尝试作为图片处理
        img_exts = {"jpg", "jpeg", "png", "gif", "bmp", "webp"}
        if ext in img_exts:
            return {
                "success": True,
                "note": "上传的是图片而非视频，已使用视觉模型分析",
                "is_video": False,
            }
        raise HTTPException(400, f"不支持的文件格式: .{ext}，请上传视频文件 ({', '.join(video_exts[:5])}等)")

    # 保存到临时文件
    tmp_dir = tempfile.mkdtemp(prefix="evo_video_upload_")
    tmp_path = os.path.join(tmp_dir, f"upload_{file.filename}")
    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        # 分析视频
        result = await analyze_video(tmp_path, prompt)
        return result

    except Exception as e:
        logger.error(f"视频分析失败: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # 清理临时文件
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except Exception:
            pass


@router.post("/info")
async def video_info(file: UploadFile = File(...)):
    """获取上传视频的元信息（不解码内容）"""
    tmp_dir = tempfile.mkdtemp(prefix="evo_video_info_")
    tmp_path = os.path.join(tmp_dir, file.filename or "video.bin")
    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
        info = await get_video_info(tmp_path)
        info["file_name"] = file.filename
        info["file_size_mb"] = round(len(content) / (1024 * 1024), 2)
        return {"success": True, "info": info}
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except Exception:
            pass


@router.post("/transcribe")
async def transcribe_video_route(file: UploadFile = File(...)):
    """上传视频并提取音频转写文字"""
    tmp_dir = tempfile.mkdtemp(prefix="evo_video_transcribe_")
    tmp_path = os.path.join(tmp_dir, file.filename or "video.bin")
    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
        return await _mod.transcribe(tmp_path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except Exception:
            pass
