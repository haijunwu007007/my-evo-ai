"""文字转语音技能 — edge-tts 或 gTTS"""
from pathlib import Path

skill_def = {
    "name": "voice-tts", "version": "1.0.0",
    "description": "文本转语音 mp3",
    "author": "AUTO-EVO-AI", "category": "多模态", "icon": "🔊",
    "tags": ["语音", "朗读", "TTS"],
    "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "lang": {"type": "string"}}},
    "output_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}}
}

OUT = Path(__file__).resolve().parent.parent.parent / "output" / "tts"
OUT.mkdir(parents=True, exist_ok=True)

def execute(params, context=None):
    text = params.get("text", "")
    lang = params.get("lang", "zh-CN")
    if not text:
        return {"file_path": "", "error": "请提供需要转语音的文本（text）"}
    import hashlib
    name = hashlib.md5(text.encode()).hexdigest()[:12]
    fp = str(OUT / f"{name}.mp3")

    try:
        import edge_tts
        import asyncio
        voice = "zh-CN-XiaoxiaoNeural" if lang.startswith("zh") else "en-US-JennyNeural"
        asyncio.run(edge_tts.Communicate(text, voice).save(fp))
        return {"file_path": fp}
    except ImportError:
        pass

    try:
        from gtts import gTTS
        gTTS(text=text[:500], lang=lang[:2], slow=False).save(fp)
        return {"file_path": fp}
    except ImportError:
        return {"file_path": "", "error": "edge-tts 和 gTTS 均未安装，请执行 pip install edge-tts"}
    except Exception as e:
        return {"file_path": "", "error": f"TTS 生成失败：{e}"}
