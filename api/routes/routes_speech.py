"""
AUTO-EVO-AI V0.1 — 语音识别路由
主引擎：Google 免费语音识别（支持中文，免费，需联网）
备用：PocketSphinx（英文）+ Vosk（中文，模型就绪时）
"""

import os
import json
import logging
import tempfile
import subprocess
from fastapi import APIRouter, UploadFile, File

logger = logging.getLogger("routes_speech")
router = APIRouter(prefix="/api/v1/speech", tags=["speech"])

VOSK_MODEL_DIR = "/home/ubuntu/vosk_models"
_vosk_model = None

def _wav_from_webm(webm_bytes: bytes) -> tuple[bytes | None, int]:
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as fin:
            fin.write(webm_bytes)
            webm_path = fin.name
        wav_path = webm_path + ".wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", webm_path,
             "-ar", "16000", "-ac", "1", "-sample_fmt", "s16le",
             wav_path],
            capture_output=True, timeout=30
        )
        with open(wav_path, "rb") as f:
            wav_data = f.read()
        os.unlink(webm_path)
        if os.path.exists(wav_path):
            os.unlink(wav_path)
        return wav_data, 16000
    except Exception as e:
        logger.warning(f"ffmpeg 转码失败: {e}")
        return None, 0

def _google_recognize(wav_data: bytes) -> str:
    """Google 免费语音识别 — 支持中文"""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(wav_data)
            tmp.flush()
            with sr.AudioFile(tmp.name) as source:
                audio = r.record(source)
            return r.recognize_google(audio, language="zh-CN")
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        logger.warning(f"Google 识别请求失败: {e}")
        return ""
    except Exception as e:
        logger.warning(f"Google 识别错误: {e}")
        return ""

def _pocketsphinx_recognize(wav_data: bytes) -> str:
    """PocketSphinx 离线识别（英文）"""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(wav_data)
            tmp.flush()
            with sr.AudioFile(tmp.name) as source:
                audio = r.record(source)
            return r.recognize_sphinx(audio)
    except Exception as e:
        return ""

def _vosk_recognize(wav_data: bytes, sample_rate: int = 16000) -> str:
    global _vosk_model
    if _vosk_model is None:
        try:
            import vosk
            if os.path.isdir(VOSK_MODEL_DIR):
                for entry in sorted(os.listdir(VOSK_MODEL_DIR)):
                    full = os.path.join(VOSK_MODEL_DIR, entry)
                    if os.path.isdir(full):
                        _vosk_model = vosk.Model(full)
                        logger.info(f"Vosk 模型加载: {full}")
                        break
        except Exception as e:
            logger.warning(f"Vosk 加载失败: {e}")
    if _vosk_model is None:
        return ""
    try:
        import vosk, wave, io
        rec = vosk.KaldiRecognizer(_vosk_model, sample_rate)
        try:
            wf = wave.open(io.BytesIO(wav_data), 'rb')
            data = wf.readframes(wf.getnframes())
            wf.close()
        except wave.Error:
            rec.AcceptWaveform(wav_data)
            result = json.loads(rec.Result())
            return result.get("text", "").strip()
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip()
            if text:
                return text
        partial = json.loads(rec.PartialResult())
        return partial.get("partial", "").strip()
    except Exception as e:
        logger.warning(f"Vosk 识别失败: {e}")
        return ""

@router.get("/status")
def speech_status():
    vosk_ok = _vosk_model is not None or os.path.isdir(VOSK_MODEL_DIR)
    return {
        "available": True,
        "providers": {
            "google_free": True,
            "pocketsphinx": True,
            "vosk": vosk_ok,
            "vosk_model_ready": _vosk_model is not None,
        },
        "active": "google",
    }

@router.post("/recognize")
async def recognize_speech(file: UploadFile = File(...)):
    try:
        raw = await file.read()
        if not raw or len(raw) < 100:
            return {"success": False, "text": "", "error": "音频过短"}

        wav_data, sr = _wav_from_webm(raw)
        if wav_data is None:
            return {"success": False, "text": "", "error": "音频转码失败"}

        # 1) Google 中文识别（免费，首选）
        text = _google_recognize(wav_data)
        if text:
            logger.info(f"Google: {text[:50]}")
            return {"success": True, "text": text, "provider": "google"}

        # 2) Vosk 离线中文
        text = _vosk_recognize(wav_data, sr)
        if text:
            logger.info(f"Vosk: {text[:50]}")
            return {"success": True, "text": text, "provider": "vosk"}

        # 3) PocketSphinx 英文
        text = _pocketsphinx_recognize(wav_data)
        if text:
            logger.info(f"Sphinx: {text[:50]}")
            return {"success": True, "text": text, "provider": "pocketsphinx"}

        return {"success": False, "text": "", "error": "所有引擎均识别失败，请重试"}

    except Exception as e:
        logger.error(f"语音识别错误: {e}")
        return {"success": False, "text": "", "error": str(e)[:200]}
