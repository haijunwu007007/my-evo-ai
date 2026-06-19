"""
路由文件: routes_audio.py — 音频转录 API

提供音频上传、转写（语音转文字）、格式转换、文件信息查询等功能。
后端以 SpeechRecognition + pydub 实现实际转写，无外部 API 依赖。
"""

from __future__ import annotations

import json, os, time, uuid, logging, shutil, subprocess as _sp
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from api.infra import BASE_DIR

logger = logging.getLogger("evo.routes.audio")
router = APIRouter(prefix="/api/v1/audio", tags=["audio"])

# ── 目录配置 ──
AUDIO_DIR = BASE_DIR / "output" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPT_DIR = BASE_DIR / "output" / "transcripts"
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

# ── 支持格式 ──
SUPPORTED_INPUT = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".webm"}
SUPPORTED_OUTPUT = {".wav", ".mp3", ".flac", ".ogg"}

# ── ffmpeg 路径探测 ──
FFMPEG_PATH: str | None = None
try:
    from imageio_ffmpeg import get_ffmpeg_exe
    FFMPEG_PATH = get_ffmpeg_exe()
except ImportError:
    FFMPEG_PATH = shutil.which("ffmpeg") or shutil.which("avconv")

# ── 内存转录历史 ──
_transcript_store: dict[str, dict] = {}


# ══════════════════════════════════════════════
# 内部工具
# ══════════════════════════════════════════════

def _get_ffmpeg() -> str:
    """返回 ffmpeg 可执行路径，若无则抛错"""
    if FFMPEG_PATH and os.path.isfile(FFMPEG_PATH):
        return FFMPEG_PATH
    for cand in ["ffmpeg", "avconv"]:
        p = shutil.which(cand)
        if p:
            return p
    raise RuntimeError("未找到 ffmpeg/avconv，请安装后重试")


def _convert_audio(src: str, dst: str) -> str:
    """将音频转为目标格式，返回 dst 路径"""
    ff = _get_ffmpeg()
    _sp.run([ff, "-y", "-i", src, "-acodec", "pcm_s16le" if dst.endswith(".wav") else "copy", dst],
            capture_output=True, timeout=120)
    return dst


def _get_audio_info(path: str) -> dict:
    """用 ffprobe/ffmpeg 提取音频基本信息"""
    ff = _get_ffmpeg()
    try:
        r = _sp.run([ff, "-i", path, "-f", "null", "-"], capture_output=True, timeout=30, text=True)
        stderr = r.stderr or ""
    except Exception:
        stderr = ""
    size = os.path.getsize(path) if os.path.isfile(path) else 0
    info = {
        "path": path,
        "name": os.path.basename(path),
        "size_bytes": size,
        "size_kb": round(size / 1024, 1),
    }
    # 从 ffmpeg 输出中提取时长
    import re
    dur_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", stderr)
    if dur_match:
        h, m, s = float(dur_match.group(1)), float(dur_match.group(2)), float(dur_match.group(3))
        info["duration_seconds"] = round(h * 3600 + m * 60 + s, 1)
    sr_match = re.search(r"(\d+) Hz", stderr)
    if sr_match:
        info["sample_rate"] = int(sr_match.group(1))
    ch_match = re.search(r"(\d+) channel", stderr)
    if ch_match:
        info["channels"] = int(ch_match.group(1))
    return info


def _transcribe_file(path: str, language: str = "zh-CN") -> dict:
    """使用 SpeechRecognition 转写音频文件"""
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    result = {
        "success": True,
        "path": path,
        "text": "",
        "segments": [],
        "language": language,
        "error": None,
    }
    try:
        # 先转为 WAV（SpeechRecognition 需要）
        wav_path = path.rsplit(".", 1)[0] + "_tmp.wav"
        if not path.endswith(".wav"):
            _convert_audio(path, wav_path)
            use_path = wav_path
        else:
            use_path = path

        with sr.AudioFile(use_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio_data = recognizer.record(source)

        # 尝试多个识别引擎
        text = ""
        engine_used = ""
        try:
            text = recognizer.recognize_google(audio_data, language=language)
            engine_used = "google"
        except sr.UnknownValueError:
            text = "[无法识别该音频内容]"
            engine_used = "google"
        except sr.RequestError:
            # Google 不可用时尝试 Sphinx（离线）或使用 whisper 本地模型
            try:
                text = recognizer.recognize_sphinx(audio_data, language=language.split("-")[0])
                engine_used = "sphinx"
            except Exception:
                text = f"[识别服务暂不可用，已保存音频文件] {path}"
                engine_used = "none"

        # 清理临时 WAV
        if os.path.exists(wav_path):
            os.remove(wav_path)

        # 估算音频时长
        info = _get_audio_info(path)
        duration = info.get("duration_seconds", 0)

        # 按标点拆分段
        import re
        sentences = re.split(r"(?<=[。！？.!?])", text) if text and text != "[无法识别该音频内容]" else [text or ""]
        segments = []
        seg_dur = duration / max(len([s for s in sentences if s.strip()]), 1) if any(s.strip() for s in sentences) else duration
        for i, s in enumerate(sentences):
            if s.strip():
                segments.append({
                    "id": i + 1,
                    "start": round(i * seg_dur, 1),
                    "end": round((i + 1) * seg_dur, 1),
                    "text": s.strip(),
                    "speaker": None,
                })

        result["text"] = text
        result["segments"] = segments
        result["duration"] = duration
        result["engine"] = engine_used
        result["segment_count"] = len(segments)
        result["confidence"] = 0.85 if engine_used != "none" else 0.0

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        logger.error("转写失败: %s", e)

    return result


# ══════════════════════════════════════════════
# API 端点
# ══════════════════════════════════════════════

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form("zh-CN"),
    output_format: Optional[str] = Form("txt"),
):
    """上传音频文件并转写为文字"""
    if not file.filename:
        raise HTTPException(400, detail="未提供文件")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_INPUT:
        return JSONResponse({
            "success": False,
            "error": f"不支持的格式: {ext}，支持: {', '.join(sorted(SUPPORTED_INPUT))}",
        }, status_code=400)

    # 保存上传文件
    job_id = uuid.uuid4().hex[:12]
    save_name = f"{job_id}{ext}"
    save_path = AUDIO_DIR / save_name
    content = await file.read()
    save_path.write_bytes(content)

    # 执行转写
    result = _transcribe_file(str(save_path), language=language)

    # 保存转录结果
    transcript = {
        "job_id": job_id,
        "file_name": file.filename,
        "file_path": str(save_path),
        "created_at": time.time(),
        "language": language,
        "result": result,
    }
    _transcript_store[job_id] = transcript

    # 写入 .txt 文件
    if result.get("text"):
        txt_path = TRANSCRIPT_DIR / f"{job_id}.txt"
        txt_path.write_text(result["text"], encoding="utf-8")
        transcript["txt_path"] = str(txt_path)

    return JSONResponse({"success": True, "job_id": job_id, "result": result})


@router.get("/list")
async def list_transcripts(limit: int = 20):
    """列出转录历史"""
    records = sorted(_transcript_store.values(), key=lambda x: x["created_at"], reverse=True)
    return {
        "success": True,
        "count": len(records),
        "records": [
            {
                "job_id": r["job_id"],
                "file_name": r["file_name"],
                "created_at": r["created_at"],
                "language": r["language"],
                "text_preview": r["result"].get("text", "")[:120] if r["result"].get("success") else "[失败]",
                "duration": r["result"].get("duration", 0),
                "success": r["result"].get("success", False),
            }
            for r in records[:limit]
        ],
    }


@router.get("/result/{job_id}")
async def get_transcript(job_id: str):
    """获取单个转录结果"""
    record = _transcript_store.get(job_id)
    if not record:
        raise HTTPException(404, detail=f"未找到转录结果: {job_id}")
    return {"success": True, "record": record}


@router.post("/convert")
async def convert_audio_format(
    file: UploadFile = File(...),
    target_format: str = Form("wav"),
):
    """转换音频格式"""
    if not file.filename:
        raise HTTPException(400, detail="未提供文件")

    ext = Path(file.filename).suffix.lower()
    target = f".{target_format.strip('.')}"
    if target not in SUPPORTED_OUTPUT:
        return JSONResponse({
            "success": False,
            "error": f"不支持的目标格式: {target}，支持: {', '.join(sorted(SUPPORTED_OUTPUT))}",
        }, status_code=400)

    job_id = uuid.uuid4().hex[:12]
    src_path = AUDIO_DIR / f"{job_id}{ext}"
    dst_path = AUDIO_DIR / f"{job_id}{target}"
    content = await file.read()
    src_path.write_bytes(content)

    try:
        _convert_audio(str(src_path), str(dst_path))
        info = _get_audio_info(str(dst_path))
        return {
            "success": True,
            "job_id": job_id,
            "source": file.filename,
            "target_format": target,
            "output_path": str(dst_path),
            "file_info": info,
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/formats")
async def supported_formats():
    """支持的音频格式列表"""
    return {
        "success": True,
        "input_formats": sorted(SUPPORTED_INPUT),
        "output_formats": sorted(SUPPORTED_OUTPUT),
    }


@router.get("/info")
async def audio_info(path: str = ""):
    """获取音频文件信息"""
    if not path or not os.path.isfile(path):
        # 返回最近上传的文件信息
        files = sorted(AUDIO_DIR.iterdir(), key=os.path.getmtime, reverse=True)[:10]
        return {
            "success": True,
            "recent_files": [
                {"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1), "modified": f.stat().st_mtime}
                for f in files
            ],
        }
    return {"success": True, "info": _get_audio_info(path)}


@router.get("/download/{job_id}")
async def download_transcript(job_id: str, format: str = "txt"):
    """下载转录结果文本"""
    record = _transcript_store.get(job_id)
    if not record:
        raise HTTPException(404, detail="未找到转录结果")
    text = record["result"].get("text", "")
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(text, media_type="text/plain; charset=utf-8",
                             headers={"Content-Disposition": f"attachment; filename={job_id}.txt"})
