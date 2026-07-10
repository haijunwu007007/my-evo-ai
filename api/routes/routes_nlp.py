import logging
logger = logging.getLogger("evo.routes_nlp")
# -*- coding: utf-8 -*-
"""NLP→工作流 — 真调用LLM拆解任务"""
from fastapi import APIRouter
import json, os

router = APIRouter(prefix="/api/v1/nlp", tags=["nlp"])

@router.post("/interpret")
async def nlp_interpret(data: dict):
    text = data.get("text", "")
    if not text:
        return {"success": False, "error": "需要 text"}

    # 调用 LLM 拆解任务
    try:
        from api.agent_llm import call_llm
        prompt = f"""你是一个任务拆解专家。分析用户需求: "{text}"
请拆解为最多5个可执行步骤，返回JSON数组:
[{{"step":1, "tool":"工具名", "action":"具体操作"}}]
工具选项: search/web/codegen/deploy/docgen/translate/summarize
只返回JSON，不要额外文字。"""
        content, _ = call_llm([{"role":"user","content":prompt}])
        if content:
            # 尝试解析JSON
            try:
                steps = json.loads(content)
                return {"success": True, "steps": steps, "source": "llm"}
            except:
                import re
                arr = re.search(r'\[.*?\]', content, re.DOTALL)
                if arr:
                    steps = json.loads(arr.group())
                    return {"success": True, "steps": steps, "source": "llm"}
                return {"success": True, "steps": [{"step":1,"tool":"chat","action":text}], "source": "llm_fallback"}
    except Exception as e:
        # 降级: 关键词匹配
        steps = [{"step":1,"tool":"search","action":f"搜索关于{text}的信息"},
                 {"step":2,"tool":"chat","action":f"总结并回答: {text}"}]
        return {"success": True, "steps": steps, "source": "rule"}
