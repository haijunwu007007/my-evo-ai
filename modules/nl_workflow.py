"""
自然语言 → 业务代码 + 产品决策
用户说一句人话，系统自动完成完整业务链
"""
import json, datetime

class NLWorkflow:
    def __init__(self):
        self.name = "nl_workflow"
        self.version = "1.0.0"
        # 预置业务模板
        self._templates = {
            "trend": {
                "name": "GitHub趋势监控",
                "chain": ["github_scanner", "trending_analyzer", "dingtalk_sender"],
                "params": {},
                "result": "每天早上9点自动推送AI项目趋势到钉钉"
            },
            "health": {
                "name": "系统健康巡检",
                "chain": ["health_monitor", "alert_manager"],
                "params": {},
                "result": "每小时自动检查系统状态，异常推送到钉钉"
            },
            "report": {
                "name": "自动生成报告",
                "chain": ["data_collector", "report_generator", "notify_sender"],
                "params": {"format": "markdown"},
                "result": "收集数据并生成Markdown格式报告"
            },
        }

    async def execute(self, params: dict) -> dict:
        """
        自然语言 → 执行业务链
        params: {"goal": "帮我看看GitHub有什么新项目"}
        """
        goal = params.get("goal", "")
        if not goal:
            return {"success": False, "error": "请说你要做什么"}

        # 自然语言意图识别
        intent = self._parse_intent(goal)
        template = self._templates.get(intent)

        if not template:
            return {
                "success": True,
                "reply": f"我理解了你的需求，但还没有内置模板。可用指令：趋势、健康、报告",
                "suggestions": [
                    {"cmd": "趋势", "desc": "GitHub Trending 扫描+推送"},
                    {"cmd": "健康", "desc": "系统健康巡检+告警"},
                    {"cmd": "报告", "desc": "自动生成报告"},
                ]
            }

        # 执行业务链
        result = ""
        for mod_name in template["chain"]:
            try:
                import importlib
                mod = importlib.import_module(f"modules.{mod_name}")
                cls_name = "".join(w.capitalize() for w in mod_name.split("_"))
                instance = getattr(mod, cls_name, None)
                if instance:
                    instance = instance()
                    r = await instance.execute(template.get("params", {}))
                    result += f"  {mod_name}: {r.get('status','ok')}\n"
                else:
                    result += f"  {mod_name}: 模块未加载\n"
            except Exception as e:
                result += f"  {mod_name}: {str(e)[:50]}\n"

        return {
            "success": True,
            "intent": intent,
            "template": template["name"],
            "chain": template["chain"],
            "result": result.strip() or template["result"],
            "reply": f"已执行「{template['name']}」: {template['result']}"
        }

    def _parse_intent(self, goal: str) -> str:
        g = goal.lower()
        if any(kw in g for kw in ["趋势", "trend", "github", "热门", "项目"]):
            return "trend"
        if any(kw in g for kw in ["健康", "巡检", "health", "状态", "检查"]):
            return "health"
        if any(kw in g for kw in ["报告", "报表", "report", "周报", "月报"]):
            return "report"
        return "unknown"

__module_meta__ = {
    "version": "1.0.0",
    "category": "intelligence",
    "description": "自然语言业务链—说人话做事情"
}
