"""Qwen3-TTS — 阿里开源语音合成（文本→语音，97ms流式延迟，情绪控制）"""
import logging
logger = logging.getLogger("evo.agent_tts")

import os, json, base64
from pathlib import Path
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def text_to_speech(text: str = "", voice: str = "default", 
                   speed: float = 1.0, emotion: str = "neutral",
                   output_dir: str = "") -> dict:
    """文本转语音
    Args:
        text: 要合成的文本
        voice: 音色 (default/female/male/child/elderly)
        speed: 语速 (0.5-2.0)
        emotion: 情绪 (neutral/happy/sad/angry/excited/calm)
        output_dir: 输出目录
    Returns:
        {"success": bool, "audio_file": str, "audio_base64": str, "duration_ms": int, "error": str}
    """
    if not text:
        return {"success": False, "error": "请提供 text"}

    try:
        # 尝试使用 qwen-tts 库（如果已安装）
        try:
            from qwen_tts import QwenTTS
            output_dir = output_dir or str(Path("output/audio"))
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            tts = QwenTTS()
            audio_data = tts.synthesize(
                text=text,
                voice=voice if voice != "default" else "female",
                speed=speed,
                emotion=emotion
            )
            audio_b64 = base64.b64encode(audio_data).decode() if isinstance(audio_data, bytes) else ""
            fn = f"tts_{int(__import__('time').time())}.wav"
            fp = str(Path(output_dir) / fn)
            if isinstance(audio_data, bytes):
                Path(fp).write_bytes(audio_data)
            else:
                Path(fp).write_text(audio_data, encoding='utf-8')

            return {
                "success": True,
                "audio_file": f"/output/audio/{fn}",
                "audio_base64": audio_b64[:200] + "..." if len(audio_b64) > 200 else audio_b64,
                "text_length": len(text),
                "parameters": {"voice": voice, "speed": speed, "emotion": emotion}
            }
        except ImportError:
            # 回退：调用在线API
            import httpx
            api_key = os.environ.get("DASHSCOPE_API_KEY", "") or os.environ.get("ZHIPU_API_KEY", "")
            if not api_key:
                return {"success": False, "error": "需要 DASHSCOPE_API_KEY（阿里通义）或 qwen-tts 库。运行: pip install qwen-tts"}

            # 阿里通义 TTS API
            output_dir = output_dir or str(Path("output/audio"))
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            resp = httpx.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-tts",
                    "input": {"text": text},
                    "parameters": {
                        "voice": voice if voice != "default" else "female",
                        "speed": speed,
                        "emotion": emotion
                    }
                },
                timeout=60
            )
            if resp.status_code == 200:
                data = resp.json()
                audio_content = data.get("output", {}).get("audio", "")
                fn = f"tts_{int(__import__('time').time())}.wav"
                fp = str(Path(output_dir) / fn)
                if audio_content:
                    audio_bytes = base64.b64decode(audio_content)
                    Path(fp).write_bytes(audio_bytes)
                return {
                    "success": True,
                    "audio_file": f"/output/audio/{fn}",
                    "text_length": len(text)
                }
            return {"success": False, "error": f"TTS API 返回: {resp.text[:200]}"}

    except Exception as e:
        return {"success": False, "error": f"语音合成失败: {e}"}
