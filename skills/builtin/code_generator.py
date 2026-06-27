"""代码生成技能 — 调用 LLM"""
from api.agent_llm import call_llm

skill_def = {
    "name": "code-generator", "version": "1.0.0",
    "description": "Python/JS/SQL/Java 代码生成与解释",
    "author": "AUTO-EVO-AI", "category": "代码", "icon": "💻",
    "tags": ["代码", "Python", "JS", "SQL", "Java"],
    "input_schema": {"type": "object", "properties": {"language": {"type": "string"}, "task": {"type": "string"}}},
    "output_schema": {"type": "object", "properties": {"code": {"type": "string"}, "explanation": {"type": "string"}}}
}

def execute(params, context=None):
    lang = params.get("language", "python")
    task = params.get("task", "")
    if not task:
        return {"code": "", "explanation": "请提供编程任务描述（task）"}
    sp = f"请用{lang}实现以下功能，仅输出代码和简要说明：\n{task}"
    try:
        text, _ = call_llm([{"role": "user", "content": sp}])
        return {"code": text or "", "explanation": f"{lang} 代码已生成"}
    except Exception as e:
        return {"code": "", "explanation": f"生成失败：{e}"}
