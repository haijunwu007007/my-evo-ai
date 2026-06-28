"""翻译技能 — 调用 LLM"""
from api.agent_llm import call_llm

skill_def = {
    "name": "translate", "version": "1.0.0",
    "description": "9 种语言互译",
    "author": "AUTO-EVO-AI", "category": "文本生成", "icon": "🌐",
    "tags": ["翻译", "英文", "多语言"],
    "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "target_lang": {"type": "string", "enum": ["zh-CN", "en", "ja", "ko", "fr", "es", "pt", "ru", "ar"]}}},
    "output_schema": {"type": "object", "properties": {"translated": {"type": "string"}}}
}

_LANG_NAMES = {
    "zh-CN": "中文", "en": "英文", "ja": "日文", "ko": "韩文",
    "fr": "法文", "es": "西班牙文", "pt": "葡萄牙文",
    "ru": "俄文", "ar": "阿拉伯文"
}

def execute(params, context=None):
    text = params.get("text", "")
    target = params.get("target_lang", "zh-CN")
    if not text:
        return {"translated": "", "error": "请提供需要翻译的文本（text）"}
    lang_name = _LANG_NAMES.get(target, target)
    sp = f"请将以下文本翻译成{lang_name}，仅输出翻译结果：\n\n{text}"
    try:
        result, _ = call_llm([{"role": "user", "content": sp}])
        return {"translated": result.strip() if result else ""}
    except Exception as e:
        logger = logging.getLogger("evo.translate")
        logger.warning(f"翻译失败: {e}")
        return {"translated": "", "error": "翻译失败，请稍后重试"}
