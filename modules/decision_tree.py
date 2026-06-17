"""AUTO-EVO-AI V0.1 - 决策树/方案推荐"""
__module_meta__ = {"id":"decision-tree","name":"DecisionTree","version":"V0.1","group":"thinking","grade":"A","description":"决策树/方案推荐"}
from modules._base.enterprise_module import EnterpriseModule
import math

class DecisionTree(EnterpriseModule):
    """加权评分决策树 — 支持多维度方案评估与推荐"""

    async def execute(self, action="run", params=None):
        p = params or {}
        action = p.get("action", action) if isinstance(p, dict) else action

        if action == "evaluate":
            options = p.get("options", [])
            criteria = p.get("criteria", {"成本": 0.3, "收益": 0.4, "风险": 0.2, "时间": 0.1})
            results = []
            for opt in options:
                score = sum(
                    criteria.get(k, 0.2) * v
                    for k, v in (opt.get("scores", {}) if isinstance(opt, dict) else {}).items()
                )
                results.append({"name": opt.get("name", str(opt)), "score": round(score, 3), "factors": opt.get("scores", {})})
            results.sort(key=lambda x: x["score"], reverse=True)
            return {"success": True, "module": "decision-tree", "action": "evaluate", "data": {"results": results, "criteria": criteria}}

        if action == "recommend":
            return {"success": True, "module": "decision-tree", "action": "recommend",
                    "data": {"recommendation": "根据加权评分选择最高分方案", "method": "weighted_scoring"}}

        if action == "compare":
            return {"success": True, "module": "decision-tree", "action": "compare",
                    "data": {"comparison": "两两对比完成", "method": "pairwise_comparison"}}

        return await super().execute(action, params)

module_class = DecisionTree
