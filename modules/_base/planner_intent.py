"""Agent Planner - 意图解析器"""
import os, time, json, logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from modules._base.planner_types import TaskType, PlanStatus, ModuleCapability, ExecutionStep, ExecutionPlan
class IntentParser:
    """
    混合意图理解器 — LLM优先 + 关键词fallback
    将自然语言输入解析为 TaskType + 参数
    """

    def __init__(self):
        self._llm_available = False
        self._llm_api_key = os.environ.get("EVO_LLM_API_KEY", "")
        self._llm_base_url = os.environ.get("EVO_LLM_BASE_URL", "https://api.openai.com/v1")
        self._llm_model = os.environ.get("EVO_LLM_MODEL", "gpt-4o-mini")
        if self._llm_api_key:
            try:

                self._llm_available = True
                logger.info(f"[Planner] LLM意图理解已启用: {self._llm_model}")
            except ImportError:
                logger.warning("[Planner] LLM库不可用，回退到关键词匹配")

    # 意图关键词映射
    INTENT_PATTERNS: List[Tuple[TaskType, List[str]]] = [
        (
            TaskType.DATA_ANALYSIS,
            [
                "分析",
                "数据分析",
                "统计",
                "趋势",
                "异常检测",
                "洞察",
                "analyze",
                "analysis",
                "statistics",
                "trend",
                "insight",
            ],
        ),
        (
            TaskType.DATA_PROCESSING,
            [
                "处理",
                "清洗",
                "转换",
                "ETL",
                "同步",
                "导入",
                "导出",
                "process",
                "clean",
                "transform",
                "etl",
                "sync",
                "import",
                "export",
            ],
        ),
        (
            TaskType.REPORT_GENERATION,
            ["报告", "报表", "月报", "周报", "日报", "生成报告", "report", "summary report", "monthly"],
        ),
        (
            TaskType.CODE_GENERATION,
            ["生成代码", "写代码", "代码生成", "创建脚本", "generate code", "write code", "create script"],
        ),
        (
            TaskType.CODE_REVIEW,
            ["代码审查", "代码检查", "code review", "代码质量", "review code", "check code", "code quality"],
        ),
        (TaskType.API_TESTING, ["API测试", "接口测试", "压测", "性能测试", "api test", "load test", "benchmark"]),
        (
            TaskType.MONITORING,
            [
                "监控",
                "告警",
                "指标",
                "巡检",
                "健康检查",
                "缓存",
                "monitor",
                "alert",
                "metrics",
                "health check",
                "cache",
            ],
        ),
        (
            TaskType.SECURITY,
            [
                "安全",
                "漏洞",
                "扫描",
                "审计",
                "权限",
                "加密",
                "解密",
                "security",
                "vulnerability",
                "scan",
                "audit",
                "permission",
                "encrypt",
                "decrypt",
                "cipher",
                "hash",
            ],
        ),
        (
            TaskType.DEPLOYMENT,
            ["部署", "发布", "上线", "回滚", "容器", "扩容", "deploy", "release", "rollback", "container", "scale"],
        ),
        (
            TaskType.WORKFLOW,
            [
                "工作流",
                "编排",
                "自动化",
                "流程",
                "调度",
                "workflow",
                "orchestrate",
                "automation",
                "pipeline",
                "schedule",
            ],
        ),
        (
            TaskType.FILE_PROCESSING,
            ["文件", "OCR", "PDF", "图片", "语音转文字", "file", "ocr", "pdf", "image", "transcribe"],
        ),
        (
            TaskType.AI_INFERENCE,
            [
                "AI",
                "LLM",
                "GPT",
                "Claude",
                "对话",
                "聊天",
                "embedding",
                "向量",
                "RAG",
                "NLP",
                "翻译",
                "摘要",
                "情感",
                "ai",
                "llm",
                "gpt",
                "claude",
                "chat",
                "embed",
                "rag",
                "nlp",
                "translate",
                "summarize",
                "sentiment",
            ],
        ),
        (
            TaskType.SEARCH,
            ["搜索", "查询", "检索", "查找", "知识库", "search", "query", "find", "lookup", "knowledge base"],
        ),
        (TaskType.NOTIFICATION, ["通知", "邮件", "推送", "消息", "发送", "notify", "email", "push", "message", "send"]),
        (TaskType.CHAT, ["你好", "hello", "hi", "帮我", "help", "是什么", "什么是", "怎么样", "如何", "怎么"]),
    ]

    # 任务模板 — 意图 → 模块调用序列
    TASK_TEMPLATES: Dict[TaskType, List[Dict[str, Any]]] = {
        TaskType.DATA_ANALYSIS: [
            {"module": "data_analysis", "action": "status", "desc": "数据分析"},
        ],
        TaskType.DATA_PROCESSING: [
            {"module": "data_pipeline", "action": "status", "desc": "数据处理引擎"},
        ],
        TaskType.REPORT_GENERATION: [
            {"module": "data_analysis", "action": "status", "desc": "分析报告"},
        ],
        TaskType.CODE_REVIEW: [
            {"module": "code_review", "action": "status", "desc": "代码审查"},
        ],
        TaskType.API_TESTING: [
            {"module": "api_tester", "action": "status", "desc": "API测试"},
        ],
        TaskType.MONITORING: [
            {"module": "health_monitor", "action": "status", "desc": "健康检查"},
            {"module": "perf_monitor", "action": "status", "desc": "性能监控"},
        ],
        TaskType.SECURITY: [
            {"module": "security_scanner", "action": "status", "desc": "安全扫描"},
        ],
        TaskType.DEPLOYMENT: [
            {"module": "cicd_pipeline", "action": "status", "desc": "CI/CD部署"},
        ],
        TaskType.WORKFLOW: [
            {"module": "workflow_engine", "action": "status", "desc": "工作流引擎"},
        ],
        TaskType.FILE_PROCESSING: [
            {"module": "file_manager", "action": "status", "desc": "文件管理"},
        ],
        TaskType.AI_INFERENCE: [
            {"module": "llm_openai", "action": "status", "desc": "LLM对话"},
        ],
        TaskType.SEARCH: [
            {"module": "search_engine", "action": "status", "desc": "搜索引擎"},
        ],
        TaskType.NOTIFICATION: [
            {"module": "notification_hub", "action": "status", "desc": "消息通知"},
        ],
    }

    def parse(self, message: str) -> Tuple[TaskType, Dict[str, Any]]:
        """
        解析用户意图 — 特化场景优先，LLM次之，关键词fallback
        返回: (task_type, extracted_params)
        """
        message_lower = message.lower()

        # 0. 高优先级特化检测 — 在LLM和关键词之前，确保不会因LLM返回错误类型而跳过
        gh_keywords = [
            "github trending", "github热门", "开源项目", "trending",
            "今日ai", "ai开源", "AI开源", "今日热门", "潜力项目",
            "热门开源", "流行项目", "开源推荐", "开源工具", "开源框架",
            "github scanner", "github scan", "趋势项目", "热门ai",
        ]
        if any(kw in message_lower for kw in gh_keywords):
            params = self._extract_params(message)
            params["preferred_module"] = "githubtrending"
            params["preferred_action"] = "trending"
            params["preferred_desc"] = "GitHub Trending 扫描"
            logger.info("[Planner] 检测到GitHub/Trending查询，直接重定向至 githubtrending.trending")
            return TaskType.CUSTOM, params

        # 1. 尝试LLM解析
        if self._llm_available and len(message) > 5:
            try:
                task_type, params = self._parse_with_llm(message)
                if task_type != TaskType.CUSTOM or params.get("modules"):
                    return task_type, params
            except Exception as e:
                logger.debug(f"[Planner] LLM解析失败，回退关键词: {e}")

        # 2. 关键词fallback
        best_type = TaskType.CUSTOM
        best_score = 0.0
        for task_type, keywords in self.INTENT_PATTERNS:
            score = 0.0
            for kw in keywords:
                if kw.lower() in message_lower:
                    score += 1.0
            if score > best_score:
                best_score = score
                best_type = task_type

        params = self._extract_params(message)

        return best_type, params

    def _parse_with_llm(self, message: str) -> Tuple[TaskType, Dict[str, Any]]:
        """使用LLM解析意图并返回结构化结果"""

        task_types = ", ".join([t.value for t in TaskType])
        prompt = f"""你是一个AI系统编排器的意图解析器。根据用户输入，分析其意图并返回JSON。

可用任务类型: {task_types}

用户输入: {message}

请返回以下JSON格式（不要markdown，只返回纯JSON）:
{{
  "task_type": "任务类型（从上述列表选择，如不确定选custom）",
  "summary": "一句话概括用户需求",
  "params": {{
    "raw_message": "{message}",
    "modules": ["推荐调用的模块名列表（可选）"],
    "actions": ["推荐的action列表（可选）"]
  }},
  "steps": [
    {{"module": "模块名", "action": "action名", "desc": "步骤描述"}}
  ]
}}"""

        body = _json.dumps(
            {
                "model": self._llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500,
            }
        ).encode()

        req = urllib.request.Request(
            f"{self._llm_base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._llm_api_key}",
            },
        )
        resp = urllib.request.urlopen(req, timeout=15)
        data = _json.loads(resp.read())
        content = data["choices"][0]["message"]["content"].strip()

        # 移除可能的markdown code block
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        result = _json.loads(content)

        # 解析task_type
        task_str = result.get("task_type", "custom")
        try:
            task_type = TaskType(task_str)
        except ValueError:
            task_type = TaskType.CUSTOM

        params = result.get("params", {"raw_message": message})
        params["llm_parsed"] = True
        params["llm_summary"] = result.get("summary", "")

        # 如果LLM推荐了steps，存储到params供后续使用
        if result.get("steps"):
            params["llm_steps"] = result["steps"]

        return task_type, params

    def _extract_params(self, message: str) -> Dict[str, Any]:
        """从消息中提取结构化参数"""
        params = {"raw_message": message}

        # 提取文件路径

        paths = re.findall(r'[\'"]?([A-Za-z]:\\[^\s\'"]+|/[\w/.-]+)[\'"]?', message)
        if paths:
            params["files"] = paths

        # 提取数字
        numbers = re.findall(r"\b(\d+)\b", message)
        if numbers:
            params["numbers"] = [int(n) for n in numbers]

        return params

    def get_plan(self, task_type: TaskType, params: Dict[str, Any], registry: ModuleRegistry) -> List[Dict[str, Any]]:
        """
        根据任务类型生成执行计划
        优先使用LLM推荐的步骤，fallback到模板
        """
        # 0. preferred_module 最高优先级 — 由 parse() 检测到特化场景时设定
        preferred = params.get("preferred_module")
        if preferred:
            action = params.get("preferred_action", "status")
            desc = params.get("preferred_desc", preferred)
            logger.info(f"[Planner] 使用preferred_module: {preferred}.{action}")
            return [{"module": preferred, "action": action, "desc": desc}]

        # 1. LLM推荐的步骤
        if params.get("llm_steps"):
            llm_steps = params["llm_steps"]
            # 验证步骤中的模块是否在注册表中
            validated = []
            for step in llm_steps:
                mod_name = step.get("module", "")
                if not mod_name:
                    continue
                # 如果模块在注册表中，直接使用
                if mod_name in registry._modules or mod_name in registry._pending_modules:
                    validated.append(step)
                else:
                    # 模糊匹配
                    matches = registry.search(mod_name, limit=1)
                    if matches:
                        m = matches[0]
                        validated.append(
                            {
                                "module": m.name,
                                "action": step.get("action", m.actions[0] if m.actions else "status"),
                                "desc": step.get("desc", m.description),
                            }
                        )
            if validated:
                logger.info(f"[Planner] 使用LLM推荐的{len(validated)}个步骤")
                return validated

        # 2. 模板fallback
        template = self.TASK_TEMPLATES.get(task_type, [])
        if not template:
            query = params.get("raw_message", "")
            found = registry.search(query, limit=1)
            if found:
                m = found[0]
                # 使用标准action确保兼容性
                template = [{"module": m.name, "action": "status", "desc": m.description}]
        return template

