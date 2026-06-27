"""语音识别路由 — 纯 Vosk 离线方案（不依赖 Google API）"""
import os, io, json, logging, wave
from fastapi import APIRouter, UploadFile, File

logger = logging.getLogger("routes_speech")
router = APIRouter(prefix="/api/v1/speech", tags=["speech"])

# ── Vosk 模型路径 ──
_is_win = os.name == "nt"
if _is_win:
    VOSK_DIR = r"C:\vosk_model"
else:
    VOSK_DIR = "/home/ubuntu/vosk_models/vosk-model-small-cn-0.22"

_vosk_model = None
_vosk_loaded = False

def _load_vosk():
    global _vosk_model, _vosk_loaded
    if _vosk_loaded:
        return _vosk_model
    _vosk_loaded = True
    if not os.path.isdir(VOSK_DIR):
        logger.error(f"[SPEECH] Vosk 模型目录不存在: {VOSK_DIR}")
        return None
    try:
        import vosk
        logger.info(f"[SPEECH] 加载 Vosk 模型: {VOSK_DIR}")
        _vosk_model = vosk.Model(VOSK_DIR)
        logger.info("[SPEECH] Vosk 模型加载成功")
    except Exception as e:
        logger.error(f"[SPEECH] Vosk 加载失败: {e}", exc_info=True)
    return _vosk_model


@router.get("/status")
def status():
    m = _load_vosk()
    return {
        "success": True,
        "ok": bool(m),
        "vosk": bool(m),
        "vosk_dir": VOSK_DIR,
        "vosk_dir_exists": os.path.isdir(VOSK_DIR),
        "platform": "win" if _is_win else "linux",
    }


@router.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    try:
        raw = await file.read()
        if not raw or len(raw) < 100:
            return {"success": False, "text": "", "error": "录音太短"}

        # ── 从 WAV 提取 PCM ──
        if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
            return {"success": False, "text": "", "error": "不是 WAV 格式"}

        pcm = None
        try:
            with wave.open(io.BytesIO(raw), "rb") as wf:
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                logger.info(f"[SPEECH] WAV: {channels}ch, {sampwidth*8}bit, {framerate}Hz, {wf.getnframes()} frames")
                if sampwidth == 2 and channels == 1:
                    pcm = wf.readframes(wf.getnframes())
                elif sampwidth == 2 and channels > 1:
                    # 多声道 → 取第一声道
                    frames = wf.readframes(wf.getnframes())
                    import array
                    data = array.array('h', frames)
                    mono = data[0::channels]
                    pcm = bytes(mono)
                elif sampwidth == 1:
                    # 8bit → 转为 16bit
                    frames = wf.readframes(wf.getnframes())
                    import array
                    data = array.array('B', frames)
                    data16 = array.array('h', ( (b - 128) << 8 for b in data ))
                    if channels > 1:
                        data16 = data16[0::channels]
                    pcm = bytes(data16)
                else:
                    return {"success": False, "text": "", "error": f"不支持的音频格式: {sampwidth*8}bit, {channels}ch"}
        except Exception as e:
            return {"success": False, "text": "", "error": f"WAV 解析失败: {str(e)[:60]}"}

        if not pcm or len(pcm) < 2000:
            return {"success": False, "text": "", "error": "PCM 数据无效或太短"}

        logger.info(f"[SPEECH] PCM 长度: {len(pcm)} bytes")

        # ── Vosk 识别（分块处理 + FinalResult）──
        m = _load_vosk()
        if not m:
            return {"success": False, "text": "", "error": f"Vosk 模型未加载（目录: {VOSK_DIR}，存在: {os.path.isdir(VOSK_DIR)}）"}

        import vosk
        rec = vosk.KaldiRecognizer(m, 16000)
        # 设置单词级别信息（非必须，但可提升短句识别）
        try:
            rec.SetWords(True)
        except Exception:
            pass

        # 分块处理，每块 4000 个采样点（约 0.25s）
        CHUNK = 8000  # bytes = 4000 samples * 2 bytes
        texts = []
        for i in range(0, len(pcm), CHUNK):
            chunk = pcm[i:i + CHUNK]
            if rec.AcceptWaveform(chunk):
                try:
                    r = json.loads(rec.Result())
                    t = r.get("text", "").strip()
                    if t:
                        texts.append(t)
                except Exception:
                    pass

        # 获取最终结果（关键！FinalResult 包含最后一段未返回的文字）
        try:
            final = json.loads(rec.FinalResult())
            t = final.get("text", "").strip()
            if t:
                texts.append(t)
        except Exception:
            pass

        # 尝试所有片段
        full_text = " ".join(texts).strip()
        if full_text:
            return {"success": True, "text": full_text, "engine": "vosk"}

        # 最后尝试：一次性处理全部 PCM（兜底）
        try:
            rec2 = vosk.KaldiRecognizer(m, 16000)
            if rec2.AcceptWaveform(pcm):
                r = json.loads(rec2.Result())
                t = r.get("text", "").strip()
                if t:
                    return {"success": True, "text": t, "engine": "vosk"}
            fr = json.loads(rec2.FinalResult())
            t = fr.get("text", "").strip()
            if t:
                return {"success": True, "text": t, "engine": "vosk"}
        except Exception:
            pass

        return {"success": False, "text": "", "error": "Vosk 未识别到文字"}
    except Exception as e:
        import traceback
        logger.error(f"[SPEECH] 识别异常: {e}\n{traceback.format_exc()}")
        return {"success": False, "text": "", "error": str(e)[:100]}
