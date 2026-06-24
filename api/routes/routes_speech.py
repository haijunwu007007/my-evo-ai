"""
AUTO-EVO-AI V0.1 — 语音识别路由
引擎顺序：百度ASR(中国可用) > Google > PocketSphinx(英文)
"""
import os, json, logging, tempfile, base64, struct
from fastapi import APIRouter, UploadFile, File
import subprocess

logger = logging.getLogger("routes_speech")
router = APIRouter(prefix="/api/v1/speech", tags=["speech"])

VOSK_MODEL_DIR = "/home/ubuntu/vosk_models"
_vosk_model = None

def _wav_from_webm(webm_bytes):
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
        logger.warning(f"转码失败: {e}")
        return None, 0

def _baidu_recognize(wav_data):
    """百度ASR — 国内免费可用"""
    try:
        import requests
        # 获取token
        ak, sk = "4E1BG9lTnlSeIf1NQFlrSUeG", "rB28R1UdbK6NsEzAVw2sVVrEbTNZIHp2"
        r = requests.post(
            "https://openapi.baidu.com/oauth/2.0/token",
            params={"grant_type": "client_credentials", "client_id": ak, "client_secret": sk},
            timeout=5
        )
        token = r.json().get("access_token", "")
        if not token:
            return ""
        # 语音识别
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
        import vosk, wave, io
        rec = vosk.KaldiRecognizer(_vosk_model, sr)
        wf = wave.open(io.BytesIO(wav_data), 'rb')
        data = wf.readframes(wf.getnframes()); wf.close()
        if rec.AcceptWaveform(data):
            return json.loads(rec.Result()).get("text","").strip()
        return json.loads(rec.PartialResult()).get("partial","").strip()
    except Exception:
        return ""

@router.get("/status")
def speech_status():
    return {
        "available": True,
        "providers": {"baidu_free": True, "google_free": True, "pocketsphinx": True},
        "active": "baidu"
    }

@router.post("/recognize")
async def recognize_speech(file: UploadFile = File(...)):
    try:
        raw = await file.read()
        if not raw or len(raw) < 100:
            return {"success": False, "text": "", "error": "音频过短"}

        wav_data, sr = _wav_from_webm(raw)
        if wav_data is None:
            return {"success": False, "text": "", "error": "转码失败"}

        # 1) 百度ASR（中国，首选）
        text = _baidu_recognize(wav_data)
        if text:
            return {"success": True, "text": text, "provider": "baidu"}

        # 2) Vosk
        text = _vosk_recognize(wav_data, sr)
        if text:
            return {"success": True, "text": text, "provider": "vosk"}

        # 3) Google
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
