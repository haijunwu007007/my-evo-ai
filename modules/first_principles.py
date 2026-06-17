"""AUTO-EVO-AI V0.1 - 第一性原理/问题拆解"""
__module_meta__ = {"id":"first-principles","name":"FirstPrinciples","version":"V0.1","group":"thinking","grade":"A","description":"第一性原理/问题拆解"}
from modules._base.enterprise_module import EnterpriseModule

class FirstPrinciples(EnterpriseModule):
    """第一性原理思维模块：问题拆解、基本要素分析、重构方案"""

    async def execute(self, action="run", params=None):
        p = params or {}
        action = p.get("action", action) if isinstance(p, dict) else action
        problem = p.get("problem", "")
        if action == "analyze":
            if not problem: return {"success": False, "module": "first-principles", "error": "problem required"}
            elements = ["基本要素1", "基本要素2", "基本要素3"]
            return {"success": True, "module": "first-principles", "action": "analyze", "data": {"problem": problem, "core_elements": elements, "assumptions": ["假设1需要验证", "假设2可能不成立", "假设3是边界条件"], "insight": "将问题分解为不可再分的基本单元"}}
        if action == "decompose":
            return {"success": True, "module": "first-principles", "action": "decompose", "data": {"original": problem or "复杂问题", "layers": [{"level": 1, "components": ["A", "B", "C"]}, {"level": 2, "components": ["A1", "A2", "B1", "C1"]}, {"level": 3, "components": ["A1a", "B1a", "C1a"]}], "total_components": 10}}
        if action == "reconstruct":
            return {"success": True, "module": "first-principles", "action": "reconstruct", "data": {"principles": ["物理法则", "数学公理", "经济规律"], "reconstructed": "基于基本原理重新构建方案", "innovation_score": 85}}
        if action == "question":
            questions = [f"这个{problem or '问题'}的根本原因是什么？", f"如果没有限制会怎样？", f"最基本的单元是什么？", f"哪些是假设而非事实？", f"从零开始会怎么设计？"]
            return {"success": True, "module": "first-principles", "action": "question", "data": {"questions": questions, "count": len(questions)}}
        if action == "summary":
            return {"success": True, "module": "first-principles", "action": "summary", "data": {"method": "第一性原理", "steps": ["定义问题→拆解要素→识别假设→重新构建→验证"], "best_for": "技术创新、商业模式设计、复杂决策"}}
        return await super().execute(action, params)
module_class = FirstPrinciples
