"""AUTO-EVO-AI V0.1 — 自主Agent

接收高级目标 → LLM规划 → 逐步执行 → 记忆调整循环。
支持：定时触发、结果记忆、失败自愈。
"""
import json, time, os, traceback
from datetime import datetime
from typing import Optional, Dict, Any

try:
    from api.agent_llm import call_llm
except ImportError:
    call_llm = None

from api.workflow.planner import create_planner_prompt, parse_steps, TOOL_DEFS
from api.workflow.executor import tool_executor
from api.workflow.engine import get_engine, WorkflowEngine, StepStatus


class AutonomousAgent:
    """自主Agent：规划→执行→记忆→调整"""

    def __init__(self, agent_id: str = "default"):
        self.agent_id = agent_id
        self.memory: list = []
        self.max_plan_retries = 2

    def _call_llm(self, prompt: str) -> Optional[str]:
        if call_llm:
            try:
                text, _ = call_llm([{"role": "user", "content": prompt}])
                return text
            except Exception:
                return None
        return None

    def plan(self, goal: str, context: str = "") -> dict:
        """用LLM将目标分解为步骤"""
        prompt = create_planner_prompt(goal, context)
        for attempt in range(self.max_plan_retries + 1):
            try:
                text = self._call_llm(prompt)
                if not text:
                    continue
                result = parse_steps(text)
                if result.get("ok"):
                    return result
            except Exception:
                if attempt == self.max_plan_retries:
                    return {"ok": False, "error": f"规划失败: {traceback.format_exc()[:200]}"}
        return {"ok": False, "error": "LLM规划多次失败"}

    def execute_step(self, tool: str, args: dict) -> dict:
        """执行单步并记录记忆"""
        result = tool_executor(tool, args)
        self.memory.append({
            "tool": tool, "args": args, "result": result,
            "time": datetime.now().isoformat(),
        })
        return result

    def run(self, goal: str, max_steps: int = 10) -> dict:
        """完整自主运行循环"""
        all_results = []
        llm_context = ""

        # 阶段1: 规划
        plan = self.plan(goal)
        if not plan.get("ok"):
            # 先检查多步骤任务
            multi = self._detect_multi_step(goal)
            if multi:
                plan = {"ok": True, "steps": multi}
            else:
                # 降级：直接执行（适合单步目标）
                matched_tool = self._direct_match(goal)
                if matched_tool:
                    plan = {"ok": True, "steps": [{"id": "step_1", "tool": matched_tool,
                             "args": {"query": goal, "topic": goal, "code": goal,
                                      "message": goal, "url": goal,
                                      "test": True, "data": "[1,2,3]"},
                             "label": f"执行: {matched_tool}"}]}
                else:
                    # 最后降级：纯聊天
                    chat = self._call_llm(goal)
                    return {"ok": True, "goal": goal, "status": "chat",
                            "result": chat or "已收到你的消息（工具路由未匹配，可直接告诉我需要什么）", "steps_executed": 0}

        steps = plan["steps"]
        # 限制最大步骤
        steps = steps[:max_steps]

        # 阶段2: 逐步执行
        for i, step in enumerate(steps):
            step_result = self.execute_step(step["tool"], step.get("args", {}))
            all_results.append(step_result)
            # 把上一步结果注入后续步骤上下文
            if step_result.get("data"):
                for later in steps[i+1:]:
                    for k, v in later.get("args", {}).items():
                        if isinstance(v, str) and v.startswith("$last"):
                            later["args"][k] = str(step_result.get("data", ""))[:2000]

        return {
            "ok": True,
            "goal": goal,
            "status": "completed",
            "steps_planned": len(steps),
            "steps_executed": len(all_results),
            "plan": steps,
            "results": [r.get("data", "")[:200] for r in all_results],
        }

    def _direct_match(self, text: str) -> Optional[str]:
        """直接关键词匹配（LLM降级）"""
        text_lower = text.lower()
        matches = {"审查|review|pr": "code_review", "编辑|修改|改": "code_edit",
                   "分析": "code_analyze", "测试": "generate_test", "图表|可视化": "chart_create",
                   "搜索|查": "web_search", "研究|报告": "deep_research",
                   "爬取|爬虫": "web_scrape", "邮件|mail": "send_email",
                   "通知": "send_notification", "发票": "create_invoice",
                   "工单|ticket": "create_ticket", "监控|监视": "site_monitor",
                   "部署|deploy": "paas_deploy", "git|版本": "git_manage",
                   "日程|安排": "schedule_add", "费用|报销": "expense_record",
                   "合同": "contract_review", "密码": "password_manager",
                   "截图|screenshot": "screenshot_to_code",
                   "语音|合成|tts": "voice_synth", "视频|脚本": "video_script",
                   "ocr|识别": "ocr_image", "pdf": "extract_pdf",
                   "api|接口": "api_test", "安全|漏洞": "security_scan",
                   "审计": "code_audit", "低代码|无代码": "lowcode",
                   "项目|app|应用": "fullstack_project",
                   "survey|问卷|调查": "survey_create",
                   "crm|客户|联系人": "crm_contacts",
                   "erp|企业|资源": "erp_manage",
                   "wiki|知识|文档库": "wiki_manage",
                   "share|共享|分享": "file_share",
                   "远程|桌面": "remote_desktop",
                   "设备|家居": "smart_home",
                   "obs|可观测": "observability",
                   "ml|模型|训练": "mlops",
        }
        for pattern, tool in matches.items():
            for keyword in pattern.split("|"):
                if keyword in text_lower:
                    return tool
        return None

    def _detect_multi_step(self, text: str) -> Optional[list]:
        """检测多步骤任务"""
        tl = text.lower()
        if ("爬" in tl or "采集" in tl) and ("图表" in tl or "可视化" in tl):
            return [{"id":"s1","tool":"web_scrape","args":{"url":self._extract_url(text)},"label":"爬数据"},
                    {"id":"s2","tool":"chart_create","args":{"data":"$last"},"label":"生成图表"}]
        if ("搜索" in tl or "找" in tl) and "部署" in tl:
            return [{"id":"s1","tool":"web_search","args":{"query":text},"label":"搜索"},
                    {"id":"s2","tool":"paas_deploy","args":{"name":text},"label":"部署"}]
        if ("分析" in tl or "研究" in tl) and ("报告" in tl or "报表" in tl):
            return [{"id":"s1","tool":"deep_research","args":{"topic":text},"label":"研究"},
                    {"id":"s2","tool":"bi_report","args":{"data":"$last"},"label":"生成报告"}]
        if ("监控" in tl or "检查" in tl) and ("通知" in tl or "报警" in tl or "邮件" in tl):
            return [{"id":"s1","tool":"site_monitor","args":{"url":self._extract_url(text) or "https://example.com"},"label":"监控"},
                    {"id":"s2","tool":"send_notification","args":{"message":"$last"},"label":"通知"}]
        # 项目生成类任务
        if ("电商" in tl or "商城" in tl or "ecommerce" in tl or "shop" in tl):
            return [{"id":"s1","tool":"generate_project","args":{"project_type":"ecommerce","name":self._extract_project_name(text)},"label":"生成电商项目"},
                    {"id":"s2","tool":"code_review","args":{"code":"$last"},"label":"审查代码"},
                    {"id":"s3","tool":"paas_deploy","args":{"name":"ecommerce"},"label":"部署上线"}]
        if ("博客" in tl or "blog" in tl or "cms" in tl):
            return [{"id":"s1","tool":"generate_project","args":{"project_type":"blog","name":self._extract_project_name(text)},"label":"生成博客"},
                    {"id":"s2","tool":"paas_deploy","args":{"name":"blog"},"label":"部署上线"}]
        if ("crm" in tl or "客户" in tl):
            return [{"id":"s1","tool":"generate_project","args":{"project_type":"crm","name":self._extract_project_name(text)},"label":"生成CRM"},
                    {"id":"s2","tool":"paas_deploy","args":{"name":"crm"},"label":"部署上线"}]
        if ("网站" in tl or "全栈" in tl or "webapp" in tl):
            return [{"id":"s1","tool":"generate_project","args":{"project_type":"webapp","name":self._extract_project_name(text)},"label":"生成Web应用"},
                    {"id":"s2","tool":"paas_deploy","args":{"name":"webapp"},"label":"部署上线"}]
        return None

    def _extract_url(self, text: str) -> str:
        import re
        urls = re.findall(r'https?://[^\s,；，。]+', text)
        return urls[0] if urls else ""

    def _extract_project_name(self, text: str) -> str:
        import re
        # 尝试从"做个XXX"、叫"XXX"提取
        m = re.search(r'叫["""]?(.+?)["""]?[的的]', text)
        if m: return m.group(1).strip()
        m = re.search(r'(?:做个|创建|生成|搭建)(.{2,8}?)(?:网站|系统|项目|商城)', text)
        if m: return m.group(1).strip()
        return "my-app"

    @staticmethod
    def _extract_url(text: str) -> str:
        import re
        m = re.search(r'https?://[^\s]+', text)
        return m.group(0) if m else ""


# 全局实例
_default_agent = None

def get_agent() -> AutonomousAgent:
    global _default_agent
    if _default_agent is None:
        _default_agent = AutonomousAgent()
    return _default_agent
