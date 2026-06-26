"""
AUTO-EVO-AI V0.1 — 语音识别路由 (Whisper 本地引擎版)
引擎顺序：Whisper(本地) > 百度ASR > Vosk > Google > PocketSphinx
"""
import os, io, json, logging, tempfile, base64, uuid, atexit, threading
from fastapi import APIRouter, UploadFile, File
import subprocess

logger = logging.getLogger("routes_speech")
router = APIRouter(prefix="/api/v1/speech", tags=["speech"])

VOSK_MODEL_DIR = "/home/ubuntu/vosk_models"
_vosk_model = None

# ---------- Whisper 本地引擎 ----------
_whisper_model = None
_WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL", "tiny")

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    # 首次：后台加载不阻塞，立即返回 False
    _whisper_model = False
    def _load():
        global _whisper_model
        try:
            from faster_whisper import WhisperModel
            logger.info("后台加载 Whisper %s 模型...", _WHISPER_MODEL_SIZE)
            m = WhisperModel(_WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
            _whisper_model = m
            logger.info("Whisper %s 模型加载完成", _WHISPER_MODEL_SIZE)
        except Exception as e:
            logger.warning("Whisper 后台加载失败: %s，降级到云端引擎", e)
    threading.Thread(target=_load, daemon=True).start()
    return _whisper_model

def _whisper_recognize(wav_path: str) -> str:
    model = _get_whisper_model()
    if not model:
        return ""
    try:
        segments, info = model.transcribe(wav_path, language="zh", beam_size=5)
        text = "".join(seg.text for seg in segments).strip()
        return text
    except Exception as e:
        logger.warning("Whisper 转写失败: %s", e)
        return ""

def _preload_whisper():
    try:
        _get_whisper_model()
    except Exception:
        pass
threading.Thread(target=_preload_whisper, daemon=True).start()

# ---------- ffmpeg 转码 ----------
def _wav_from_webm(webm_bytes):
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as fin:
            fin.write(webm_bytes)
            webm_path = fin.name
        wav_path = webm_path + ".wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", webm_path,
             "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le",
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
        logger.warning("转码失败: %s", e)
        return None, 0

# ---------- 百度ASR (兜底) ----------
def _baidu_recognize(wav_data):
    try:
        import requests
        ak, sk = "4E1BG9lTnlSeIf1NQFlrSUeG", "rB28R1UdbK6NsEzAVw2sVVrEbTNZIHp2"
        r = requests.post(
            "https://openapi.baidu.com/oauth/2.0/token",
            params={"grant_type": "client_credentials", "client_id": ak, "client_secret": sk},
            timeout=5
        )
        token = r.json().get("access_token", "")
        if not token:
            return ""
        b64 = base64.b64encode(wav_data).decode()
        body = {
            "format": "wav", "rate": 16000, "channel": 1,
            "cuid": "autoevoai", "token": token,
            "speech": b64, "len": len(wav_data),
            "dev_pid": 1537
        }
        r = requests.post("https://vop.baidu.com/server_api", json=body, timeout=15)
        ret = r.json()
        if ret.get("err_no") == 0:
            return ret.get("result", [""])[0]
        return ""
    except Exception:
        return ""

# ---------- Google ----------
def _google_recognize(wav_data):
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(wav_data); tmp.flush()
            with sr.AudioFile(tmp.name) as src:
                audio = r.record(src)
            return r.recognize_google(audio, language="zh-CN")
    except Exception:
        return ""

# ---------- PocketSphinx ----------
def _sphinx_recognize(wav_data):
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(wav_data); tmp.flush()
            with sr.AudioFile(tmp.name) as src:
                audio = r.record(src)
            return r.recognize_sphinx(audio)
    except Exception:
        return ""

# ---------- Vosk ----------
def _vosk_recognize(wav_data, sr=16000):
    global _vosk_model
    if _vosk_model is None:
        try:
            import vosk
            if os.path.isdir(VOSK_MODEL_DIR):
                for e in sorted(os.listdir(VOSK_MODEL_DIR)):
                    p = os.path.join(VOSK_MODEL_DIR, e)
                    if os.path.isdir(p):
                        _vosk_model = vosk.Model(p); break
        except Exception:
            pass
    if not _vosk_model:
        return ""
    try:
        import vosk, wave
        rec = vosk.KaldiRecognizer(_vosk_model, sr)
        wf = wave.open(io.BytesIO(wav_data), 'rb')
        data = wf.readframes(wf.getnframes()); wf.close()
        if rec.AcceptWaveform(data):
            return json.loads(rec.Result()).get("text","").strip()
        return json.loads(rec.PartialResult()).get("partial","").strip()
    except Exception:
        return ""

# ---------- API Endpoints ----------

@router.get("/status")
def speech_status():
    m = _get_whisper_model()
    providers = {"whisper": bool(m)}
    providers["baidu"] = True
    try:
        import speech_recognition; providers["google"] = True
    except ImportError: pass
    try:
        import vosk; providers["vosk"] = os.path.isdir(VOSK_MODEL_DIR)
    except ImportError: pass
    return {
        "available": bool(m),
        "providers": providers,
        "active": "whisper" if m else "baidu"
    }

@router.post("/recognize")
async def recognize_speech(file: UploadFile = File(...)):
    try:
        raw = await file.read()
        if not raw or len(raw) < 100:
            return {"success": False, "text": "", "error": "音频过短"}

        wav_data, sample_rate = _wav_from_webm(raw)
        if wav_data is None:
            return {"success": False, "text": "", "error": "转码失败"}

        # 1) Whisper 本地引擎
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_data)
                wav_path = tmp.name
            text = _whisper_recognize(wav_path)
            os.unlink(wav_path)
            if text:
                return {"success": True, "text": text, "provider": "whisper"}
        except Exception as e:
            logger.warning("Whisper 失败: %s", e)

        # 2) Google（中国可能超时，但比百度免费版可靠）
        text = _google_recognize(wav_data)
        if text:
            return {"success": True, "text": text, "provider": "google"}

        # 3) Vosk
        text = _vosk_recognize(wav_data, sample_rate)
        if text:
            return {"success": True, "text": text, "provider": "vosk"}

        # 4) Google
        text = _google_recognize(wav_data)
        if text:
            return {"success": True, "text": text, "provider": "google"}

        # 4) Sphinx
        text = _sphinx_recognize(wav_data)
        if text:
            return {"success": True, "text": text, "provider": "pocketsphinx"}

        return {"success": False, "text": "", "error": "识别失败，请重试"}

    except Exception as e:
        return {"success": False, "text": "", "error": str(e)[:200]}
