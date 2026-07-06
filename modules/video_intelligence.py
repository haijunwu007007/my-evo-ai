"""
AUTO-EVO-AI V0.1 — 视频智能理解引擎（真实实现）
===============================================
基于 ffmpeg 抽帧 + Moondream/Ollama 视觉模型，实现视频内容理解。

流程:
  1. 接收视频文件 → 保存到临时目录
  2. ffmpeg 抽取关键帧（均匀取样，最多 8 帧）
  3. 每帧发送到 Moondream 视觉模型 → 获得描述
  4. 合并多帧描述 + 提取音频转写 → 生成综合理解报告

依赖: ffmpeg (系统级), Ollama (模型: moondream)
"""

import os, json, time, base64, subprocess, tempfile, logging, asyncio
from pathlib import Path
from typing import Optional

logger = logging.getLogger("evo.video_intelligence")

# ── Ollama 视觉模型配置 ──
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
VISION_MODEL = "moondream"  # 或 llava / qwen3-vl


def _ffmpeg_available() -> bool:
    """检查系统是否有 ffmpeg"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


async def _ollama_vision(image_base64: str, prompt: str = "请详细描述这张图片的内容") -> str:
    """调用 Ollama 视觉模型分析图片"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as c:
            resp = await c.post(f"{OLLAMA_HOST}/api/generate", json={
                "model": VISION_MODEL,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 300},
            })
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "").strip()
            return f"[视觉模型错误: {resp.status_code}]"
    except Exception as e:
        return f"[视觉模型调用失败: {e}]"


def _extract_frames(video_path: str, max_frames: int = 8) -> list[str]:
    """
    从视频中提取关键帧，返回 base64 编码的 PNG 列表
    使用 ffmpeg 的 scene detection 选取内容变化最大的帧
    """
    if not _ffmpeg_available():
        logger.warning("ffmpeg 不可用，无法提取视频帧")
        return []

    frames = []
    tmp_dir = tempfile.mkdtemp(prefix="evo_video_")
    try:
        # 先获取视频时长
        dur_cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        dur_result = subprocess.run(dur_cmd, capture_output=True, text=True, timeout=30)
        duration = float(dur_result.stdout.strip() or 30)

        # 均匀取帧：每隔 duration/max_frames 秒取一帧
        interval = max(duration / max_frames, 0.5)
        for i in range(max_frames):
            time_pos = i * interval
            if time_pos >= duration:
                break
            out_path = os.path.join(tmp_dir, f"frame_{i:03d}.png")
            cmd = [
                "ffmpeg", "-ss", str(time_pos), "-i", video_path,
                "-vframes", "1", "-q:v", "2",
                "-vf", "scale=800:-1",  # 缩放宽度 800，保持比例
                "-y", out_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
                with open(out_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                    frames.append(b64)
        return frames
    except Exception as e:
        logger.error(f"抽帧失败: {e}")
        return []
    finally:
        # 清理临时文件
        try:
            for f in os.listdir(tmp_dir):
                os.remove(os.path.join(tmp_dir, f))
            os.rmdir(tmp_dir)
        except Exception:
            pass


async def _extract_audio_transcript(video_path: str) -> str:
    """从视频中提取音频并尝试转写（使用 ffmpeg + Vosk/Whisper）"""
    if not _ffmpeg_available():
        return ""

    tmp_audio = tempfile.mktemp(suffix=".wav")
    try:
        # 提取音频为 WAV 16kHz mono
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-y", tmp_audio,
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)

        if not os.path.exists(tmp_audio) or os.path.getsize(tmp_audio) < 1000:
            return ""

        # 尝试调本地的语音识别 API
        try:
            import httpx
            async with httpx.AsyncClient(timeout=120) as c:
                with open(tmp_audio, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode()
                resp = await c.post(
                    "http://127.0.0.1:8765/api/v1/speech/recognize",
                    json={"audio_base64": audio_b64},
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("text", "") or data.get("result", "") or ""
        except Exception:
            pass
        return ""
    except Exception as e:
        logger.warning(f"音频提取失败: {e}")
        return ""
    finally:
        try:
            if os.path.exists(tmp_audio):
                os.remove(tmp_audio)
        except Exception:
            pass


async def analyze_video(video_path: str, prompt: str = "请详细描述这个视频的内容") -> dict:
    """
    分析视频内容

    Args:
        video_path: 视频文件路径
        prompt: 分析提示词

    Returns:
        {"success": bool, "description": str, "frames_count": int,
         "transcript": str, "duration": float, "model": str}
    """
    start_time = time.time()

    # 1. 获取视频信息
    info = await get_video_info(video_path)

    # 2. 提取关键帧
    frames = _extract_frames(video_path, max_frames=8)

    # 3. 分析每帧
    frame_descriptions = []
    for i, frame_b64 in enumerate(frames):
        desc = await _ollama_vision(frame_b64, prompt)
        frame_descriptions.append(f"【帧 {i+1}/{len(frames)}】{desc}")

    # 4. 提取音频转写（后台并行）
    transcript_task = asyncio.create_task(_extract_audio_transcript(video_path))

    # 5. 合并结果
    result_parts = []
    if frame_descriptions:
        result_parts.append("📹 画面分析：")
        result_parts.extend(frame_descriptions)

    transcript = await transcript_task
    if transcript:
        result_parts.append(f"\n🎤 音频转写：{transcript[:1000]}")

    if not frame_descriptions and not transcript:
        result_parts.append(f"📁 视频文件信息：{json.dumps(info, ensure_ascii=False)}")

    description = "\n".join(result_parts)
    elapsed = round(time.time() - start_time, 1)

    return {
        "success": True,
        "description": description or "视频分析完成，但未能提取到视觉内容",
        "frames_count": len(frames),
        "has_transcript": bool(transcript),
        "duration": info.get("duration", 0),
        "file_size": info.get("size", 0),
        "model": VISION_MODEL,
        "elapsed_seconds": elapsed,
    }


async def get_video_info(video_path: str) -> dict:
    """获取视频文件元信息"""
    info = {
        "path": video_path,
        "name": os.path.basename(video_path),
        "size": os.path.getsize(video_path) if os.path.exists(video_path) else 0,
        "duration": 0,
        "width": 0,
        "height": 0,
        "codec": "",
        "fps": 0,
    }
    if not _ffmpeg_available():
        return info

    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            fmt = data.get("format", {})
            info["duration"] = round(float(fmt.get("duration", 0)), 1)
            info["size"] = int(fmt.get("size", 0))

            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    info["width"] = stream.get("width", 0)
                    info["height"] = stream.get("height", 0)
                    info["codec"] = stream.get("codec_name", "")
                    fps_str = stream.get("r_frame_rate", "0/1")
                    if "/" in fps_str:
                        try:
                            n, d = fps_str.split("/")
                            info["fps"] = round(float(n) / float(d), 1)
                        except Exception:
                            info["fps"] = 0
                    break
    except Exception as e:
        logger.warning(f"获取视频信息失败: {e}")
    return info


async def detect_objects(video_path: str) -> dict:
    """检测视频中的物体（通过关键帧分析）"""
    frames = _extract_frames(video_path, max_frames=6)
    all_objects = []
    for i, frame_b64 in enumerate(frames):
        desc = await _ollama_vision(frame_b64, "请列出这个画面中看到的所有物体，用逗号分隔")
        if desc and not desc.startswith("["):
            all_objects.extend([o.strip() for o in desc.split("，") if o.strip()])
    # 去重
    unique = list(dict.fromkeys(all_objects))
    return {"success": True, "objects": unique[:30], "frames_analyzed": len(frames)}


async def transcribe_video(video_path: str) -> dict:
    """提取视频音频并转写文字"""
    transcript = await _extract_audio_transcript(video_path)
    return {
        "success": bool(transcript),
        "text": transcript or "未能提取到音频内容",
    }


class VideoIntelligence:
    """视频智能理解引擎"""

    def __init__(self, config=None):
        self.config = config or {}
        logger.info("VideoIntelligence 引擎就绪")
        logger.info(f"  ffmpeg: {'可用' if _ffmpeg_available() else '不可用'}")
        logger.info(f"  视觉模型: {VISION_MODEL} @ {OLLAMA_HOST}")

    async def analyze(self, video_path: str, prompt: str = "") -> dict:
        return await analyze_video(video_path, prompt or "请详细描述这个视频的内容")

    async def detect_objects(self, video_path: str) -> dict:
        return await detect_objects(video_path)

    async def transcribe(self, video_path: str) -> dict:
        return await transcribe_video(video_path)

    async def get_info(self, video_path: str) -> dict:
        return await get_video_info(video_path)

    def status(self) -> dict:
        return {
            "available": True,
            "ffmpeg": _ffmpeg_available(),
            "model": VISION_MODEL,
            "ollama_host": OLLAMA_HOST,
        }
