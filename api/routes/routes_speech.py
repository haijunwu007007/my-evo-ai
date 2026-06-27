"""语音识别路由 — 纯 Vosk 离线方案（子进程模式，崩溃不影响主服务）"""
import os, io, json, logging, wave, tempfile, subprocess, sys
from fastapi import APIRouter, UploadFile, File

logger = logging.getLogger("routes_speech")
router = APIRouter(prefix="/api/v1/speech", tags=["speech"])

_is_win = os.name == "nt"
if _is_win:
    VOSK_DIR = r"C:\vosk_model"
else:
    VOSK_DIR = "/home/ubuntu/vosk_models/vosk-model-small-cn-0.22"
_WORKER = os.path.join(os.path.dirname(__file__), "_vosk_worker.py")


@router.get("/status")
def status():
    vosk_ok = os.path.isdir(VOSK_DIR) and os.path.isfile(_WORKER)
    return {
        "success": True,
        "vosk": vosk_ok,
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

        # 保存 WAV 到临时文件
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(raw)
        wav_path = tmp.name
        tmp.close()

        try:
            result = subprocess.run(
                [sys.executable, _WORKER, wav_path],
                capture_output=True, timeout=60, text=True,
            )
            # 如果子进程打印了多余的日志，取最后一行
            out = (result.stdout or "").strip()
            # 找到最后一行 JSON
            lines = [l for l in out.split("\n") if l.strip().startswith("{")]
            if lines:
                data = json.loads(lines[-1])
                return data
            else:
                stderr = (result.stderr or "").strip()[:100]
                return {"success": False, "text": "", "error": f"子进程无输出: {stderr or 'unknown'}"}
        except subprocess.TimeoutExpired:
            return {"success": False, "text": "", "error": "识别超时(>60s)"}
        except Exception as e:
            return {"success": False, "text": "", "error": f"子进程异常: {str(e)[:80]}"}
        finally:
            try:
                if os.path.exists(wav_path):
                    os.unlink(wav_path)
            except Exception:
                pass

    except Exception as e:
        return {"success": False, "text": "", "error": str(e)[:100]}
