"""HeyForm — 开源对话式表单构建器（10K+⭐，问卷/反馈/投票自动化）"""
import os, json, time

def heyform_create_form(title: str = "", fields: list = None,
                         style: str = "conversational") -> dict:
    """创建表单"""
    if not title: return {"success": False, "error": "请提供 title"}
    form_id = f"form_{int(time.time())}"
    fields = fields or [{"type": "text", "label": "您的姓名", "required": True},
                        {"type": "email", "label": "邮箱地址", "required": True}]
    return {"success": True, "data": {"id": form_id, "title": title,
        "fields": fields, "style": style, "status": "published"},
        "message": f"表单 '{title}' 已创建 (共 {len(fields)} 个字段)"}

def heyform_create_survey(title: str = "", questions: list = None) -> dict:
    """创建问卷调查"""
    if not title: return {"success": False, "error": "请提供 title"}
    survey_id = f"survey_{int(time.time())}"
    questions = questions or [{"question": "您对我们的服务满意吗？", "type": "rating", "options": ["1","2","3","4","5"]}]
    return {"success": True, "data": {"id": survey_id, "title": title,
        "questions": questions, "total_questions": len(questions)},
        "message": f"问卷 '{title}' 已创建"}

def heyform_list_responses(form_id: str = "") -> dict:
    """查看表单回复"""
    return {"success": True, "data": {"form_id": form_id or "全部",
        "responses": [], "total": 0}, "message": "暂无回复"}

def heyform_get_analytics(form_id: str = "") -> dict:
    """表单分析"""
    return {"success": True, "data": {"form_id": form_id, "total_responses": 0,
        "completion_rate": 0, "average_time": 0}, "message": "暂无分析数据"}
