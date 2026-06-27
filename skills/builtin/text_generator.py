"""文本生成技能 — 调用 LLM"""
import json
from api.agent_llm import call_llm

skill_def = {
    "name": "text-generator",
    "version": "1.0.0",
    "description": "文章/报告/创意写作/改写 — 调用本地LLM生成文本",
    "author": "AUTO-EVO-AI",
    "category": "文本生成",
    "icon": "✍️",
    "tags": ["写作", "文章", "报告", "创意", "改写"],
    "input_schema": {"type": "object", "properties": {"prompt": {"type": "string"}, "style": {"type": "string", "enum": ["正式", "创意", "简洁"]}}},
    "output_schema": {"type": "object", "properties": {"text": {"type": "string"}}}
}

def execute(params, context=None):
    prompt = params.get("prompt", "")
    style = params.get("style", "正式")
    if not prompt:
        return {"text": "请提供写作提示词（prompt）"}
    sp = f"请以{style}风格撰写以下内容：\n\n{prompt}\n\n请直接输出结果，不要额外解释。"
    try:
        text, _ = call_llm([{"role": "user", "content": sp}])
        return {"text": text or "LLM 返回为空"}
    except Exception as e:
        return {"text": f"LLM 调用失败：{e}"}
