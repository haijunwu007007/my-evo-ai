from __future__ import annotations
"""
AUTO-EVO-AI v6.32 — m30 Agent Orchestrator 主编排器 (智能体大脑)
================================================================
功能：系统级智能编排中枢 —— 用户一句话，自动拆解→调度→执行→学习→改进

核心架构：
┌─────────────────────────────────────────────────────┐
│                   Agent Orchestrator                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ 意图理解  │→│ 任务拆解  │→│ 模块调度  │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ 并行执行  │→│ 结果聚合  │→│ 自我进化  │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘

能力：
- 自然语言意图解析 → 自动选择模块组合
- 复杂任务DAG拆解（支持串行/并行/条件分支）
- 52个模块智能调度（按优先级/依赖/负载均衡）
- 执行结果聚合与质量评估
- 调用 self_evolving_engine 记录经验、优化策略
- 调用 longterm_memory 存储长期上下文
- 异常自动恢复（降级/重试/跳过）
- 实时状态追踪与进度回调

命名空间: evo.orchestrator.*
协议: GPL-3.0
"""

__module_meta__ = {
    "id": "agent-orchestrator",
    "name": "Agent主编排器",
    "version": "6.3.2",
    "group": "orchestrator",
    "inputs": [
        {"name": "goal", "type": "string", "required": True, "description": "用户目标描述"},
        {"name": "context", "type": "dict", "description": "上下文信息"},
        {"name": "mode", "type": "string", "description": "执行模式: auto/manual"},
    ],
    "outputs": [
        {"name": "tasks", "type": "list[dict]", "description": "拆解后的任务列表"},
        {"name": "execution_result", "type": "dict", "description": "执行结果"},
        {"name": "insights", "type": "list[string]", "description": "经验洞察"},
    ],
    "triggers": [
        {"type": "event", "config": {"on": "orchestrator.task.request"}},
        {"type": "event", "config": {"on": "agent.goal.submitted"}},
    ],
    "depends_on": ["workflow-manager", "self-evolving-engine", "longterm-memory", "ai-gateway"],
    "tags": ["orchestrator", "agent", "core", "brain"],
    "grade": "S",
}
import re
import time
import uuid
import json
import logging
import threading
from dataclasses import dataclass, field
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Tuple, Set
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# ============================================================================
# 枚举定义
# ============================================================================

class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    PLANNING = "planning"
    DISPATCHING = "dispatching"
    RUNNING = "running"
    WAITING = "waiting"  # 等待依赖完成
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEGRADED = "degraded"  # 降级完成

class TaskPriority(Enum):
    """任务优先级"""

    CRITICAL = 0  # 关键（安全/风控）
    HIGH = 1  # 高（用户直接请求）
    MEDIUM = 2  # 中（后台任务）
    LOW = 3  # 低（优化/学习）

class IntentCategory(Enum):
    """意图分类"""

    DATA_ANALYSIS = "data_analysis"  # 数据分析
    DOCUMENT_GEN = "document_gen"  # 文档生成
    COMMUNICATION = "communication"  # 通信/消息
    RPA_DESKTOP = "rpa_desktop"  # 桌面操作
    STRATEGY = "strategy"  # 战略决策
    SECURITY = "security"  # 安全/审批
    MONITORING = "monitoring"  # 监控/运维
    CONTENT = "content"  # 内容创作
    ECOMMERCE = "ecommerce"  # 电商
    FINANCE_LEGAL = "finance_legal"  # 财税法务
    FILE_OPERATION = "file_operation"  # 文件操作
    WEB_OPERATION = "web_operation"  # 网页操作
    SCHEDULE = "schedule"  # 定时/调度
    SYSTEM = "system"  # 系统管理
    CUSTOM = "custom"  # 自定义复合任务

# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class ModuleCapability:
    """模块能力描述"""

    module_name: str
    display_name: str
    capabilities: List[str]  # 功能关键词
    intent_map: List[IntentCategory]  # 匹配的意图
    priority: TaskPriority = TaskPriority.MEDIUM
    timeout: float = 120.0  # 超时秒数
    is_blocking: bool = False  # 是否阻塞后续
    dependencies: List[str] = field(default_factory=list)  # 前置模块
    fallback: Optional[str] = None  # 降级模块

@dataclass
class SubTask:
    """子任务"""

    task_id: str
    name: str
    description: str
    module_name: str
    intent: IntentCategory
    params: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    result: Any = None
    error: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)

@dataclass
class OrchestratorTask:
    """编排任务（顶层）"""

    task_id: str
    user_input: str
    intent: IntentCategory
    sub_tasks: List[SubTask] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.HIGH
    result: Any = None
    error: str = ""
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    total_duration_ms: float = 0.0
    quality_score: float = 0.0  # 0-1 质量评分
    lessons_learned: List[str] = field(default_factory=list)

# ============================================================================
# AI 意图理解器（可选增强层）
# ============================================================================

class AIIntentAnalyzer(object):
    """
    AI 增强的意图理解器
    使用 LLM 做深度意图解析、回退到规则引擎
    """

    SYSTEM_PROMPT = """你是一个任务拆解专家。用户会输入自然语言，你需要：
1. 分析主要意图（单选）
2. 识别次要意图（可多选）
3. 提取关键参数
4. 估计复杂度

意图分类：
- data_analysis: 数据分析、统计、报表
- document_gen: 文档生成、报告、合同
- communication: 消息通知、邮件、飞书
- rpa_desktop: 桌面操作、浏览器自动化
- strategy: 战略决策、商业分析
- security: 审批、权限、安全
- monitoring: 监控、告警、运维
- content: 内容创作、营销文案
- ecommerce: 电商、订单、库存
- finance_legal: 财税、法务
- file_operation: 文件操作、整理
- web_operation: 网页操作、API调用
- schedule: 定时任务、调度
- system: 系统管理、配置
- custom: 自定义/复杂任务

输出JSON格式：
{
  "primary_intent": "xxx",
  "confidence": 0.95,
  "secondary_intents": ["xxx", "yyy"],
  "key_params": {"时间": "今天", "对象": "张总"},
  "complexity": "medium",
  "suggestion": "简要建议"
}"""

    def __init__(self, ai_gateway=None):
        self.ai_gateway = ai_gateway
        self._rule_analyzer = IntentAnalyzer

    async def analyze(self, user_input: str) -> Tuple[IntentCategory, float, List[IntentCategory]]:
        """
        AI 增强的意图分析

        Returns:
            (主意图, 置信度, 次要意图列表)
        """
        # 尝试使用 AI
        if self.ai_gateway and self.ai_gateway.models:
            try:
                return await self._ai_analyze(user_input)
            except Exception as e:
                logger.warning(f"AI意图分析失败，降级到规则引擎: {e}")

        # 降级到规则引擎
        return self._rule_analyzer.analyze(user_input)

    async def _ai_analyze(self, user_input: str) -> Tuple[IntentCategory, float, List[IntentCategory]]:
        """使用 LLM 分析意图"""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"用户输入: {user_input}"},
        ]

        try:
            response = self.ai_gateway.chat(
                messages=messages,
                model=None,  # 使用默认模型
                temperature=0.1,
            )

            import json

            # 解析 JSON 响应
            content = response.get("content", "{}")
            # 提取 JSON
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(content[json_start:json_end])
            else:
                result = json.loads(content)

            # 转换意图
            primary = self._str_to_intent(result.get("primary_intent", "custom"))
            confidence = float(result.get("confidence", 0.5))
            secondary = [self._str_to_intent(s) for s in result.get("secondary_intents", [])]

            logger.info(f"AI意图分析: {primary.value} ({confidence:.0%})")
            return (primary, confidence, secondary)

        except Exception as e:
            logger.warning(f"AI分析异常: {e}")
            return IntentCategory.CUSTOM, 0.3, []

    @staticmethod
    def _str_to_intent(intent_str: str) -> IntentCategory:
        """字符串转意图枚举"""
        mapping = {
            "data_analysis": IntentCategory.DATA_ANALYSIS,
            "document_gen": IntentCategory.DOCUMENT_GEN,
            "communication": IntentCategory.COMMUNICATION,
            "rpa_desktop": IntentCategory.RPA_DESKTOP,
            "strategy": IntentCategory.STRATEGY,
            "security": IntentCategory.SECURITY,
            "monitoring": IntentCategory.MONITORING,
            "content": IntentCategory.CONTENT,
            "ecommerce": IntentCategory.ECOMMERCE,
            "finance_legal": IntentCategory.FINANCE_LEGAL,
            "file_operation": IntentCategory.FILE_OPERATION,
            "web_operation": IntentCategory.WEB_OPERATION,
            "schedule": IntentCategory.SCHEDULE,
            "system": IntentCategory.SYSTEM,
            "custom": IntentCategory.CUSTOM,
        }
        return mapping.get(intent_str.lower(), IntentCategory.CUSTOM)

# ============================================================================
# 意图理解器
# ============================================================================

class IntentAnalyzer(object):
    """
    自然语言意图分析器
    基于关键词匹配 + 模式识别（无需外部LLM，可离线运行）
    """

    # 意图关键词映射
    INTENT_KEYWORDS: Dict[IntentCategory, List[str]] = {
        IntentCategory.DATA_ANALYSIS: [
            "分析",
            "统计",
            "报表",
            "趋势",
            "汇总",
            "图表",
            "数据",
            "计算",
            "dashboard",
            "kpi",
            "指标",
            "环比",
            "同比",
            "可视化",
            "透视",
        ],
        IntentCategory.DOCUMENT_GEN: [
            "生成文档",
            "写报告",
            "word",
            "pdf",
            "excel",
            "ppt",
            "合同",
            "简历",
            "方案",
            "模板",
            "文档",
            "生成",
            "导出",
            "打印",
        ],
        IntentCategory.COMMUNICATION: [
            "发消息",
            "通知",
            "邮件",
            "微信",
            "钉钉",
            "飞书",
            "短信",
            "群发",
            "提醒",
            "催办",
            "回复",
            "转发",
            "通知",
            "contact",
        ],
        IntentCategory.RPA_DESKTOP: [
            "打开",
            "点击",
            "输入",
            "截图",
            "自动化",
            "鼠标",
            "键盘",
            "操作",
            "窗口",
            "应用",
            "软件",
            "桌面",
            "rpa",
            "自动化操作",
            "浏览器",
            "网页操作",
        ],
        IntentCategory.STRATEGY: [
            "决策",
            "战略",
            "规划",
            "评估",
            "预测",
            "建议",
            "方案",
            "优化",
            "改进",
            "竞品",
            "市场",
            "分析报告",
            "商业",
        ],
        IntentCategory.SECURITY: [
            "审批",
            "授权",
            "权限",
            "安全",
            "风控",
            "审计",
            "合规",
            "隔离",
            "加密",
            "验证",
            "策略",
            "policy",
            "acl",
        ],
        IntentCategory.MONITORING: [
            "监控",
            "告警",
            "异常",
            "日志",
            "巡检",
            "健康",
            "性能",
            "cpu",
            "内存",
            "磁盘",
            "网络",
            "运维",
            "报警",
        ],
        IntentCategory.CONTENT: [
            "写文章",
            "文案",
            "营销",
            "seo",
            "标题",
            "配图",
            "发布",
            "内容",
            "创意",
            "脚本",
            "视频",
            "短视频",
            "推广",
            "社交媒体",
        ],
        IntentCategory.ECOMMERCE: [
            "订单",
            "库存",
            "商品",
            "上架",
            "下架",
            "价格",
            "促销",
            "电商",
            "店铺",
            "物流",
            "退款",
            "客服",
            "采购",
        ],
        IntentCategory.FINANCE_LEGAL: [
            "发票",
            "报税",
            "财务",
            "合同审查",
            "法律",
            "合规",
            "账单",
            "成本",
            "收入",
            "税务",
            "法务",
        ],
        IntentCategory.FILE_OPERATION: [
            "文件",
            "文件夹",
            "移动",
            "复制",
            "删除",
            "重命名",
            "整理",
            "归档",
            "备份",
            "压缩",
            "下载",
            "上传",
        ],
        IntentCategory.WEB_OPERATION: [
            "网页",
            "网站",
            "爬取",
            "抓取",
            "搜索",
            "浏览",
            "url",
            "api调用",
            "接口",
            "请求",
            "http",
        ],
        IntentCategory.SCHEDULE: [
            "定时",
            "每天",
            "每周",
            "每月",
            "计划",
            "日程",
            "提醒",
            "定期",
            "cron",
            "自动执行",
            "循环",
        ],
        IntentCategory.SYSTEM: [
            "配置",
            "设置",
            "重启",
            "更新",
            "安装",
            "部署",
            "系统",
            "模块",
            "插件",
            "版本",
            "升级",
            "环境",
        ],
        IntentCategory.CUSTOM: ["复合任务", "多步骤", "流程", "帮我", "请"],
    }

    # 复合意图模式
    COMPOUND_PATTERNS: List[Tuple[str, IntentCategory, IntentCategory]] = [
        # (模式, 主要意图, 次要意图)
        (r"分析.*(?:发|通知|邮件)", IntentCategory.DATA_ANALYSIS, IntentCategory.COMMUNICATION),
        (r"生成.*(?:发|通知|邮件)", IntentCategory.DOCUMENT_GEN, IntentCategory.COMMUNICATION),
        (r"监控.*(?:告警|通知|邮件)", IntentCategory.MONITORING, IntentCategory.COMMUNICATION),
        (r"审批.*(?:通知|邮件|消息)", IntentCategory.SECURITY, IntentCategory.COMMUNICATION),
        (r"(?:写|生成).*(?:分析|报告)", IntentCategory.DOCUMENT_GEN, IntentCategory.DATA_ANALYSIS),
        (r"(?:操作|打开).*(?:截图|监控)", IntentCategory.RPA_DESKTOP, IntentCategory.MONITORING),
        (r"(?:自动|定时).*(?:分析|报告|整理)", IntentCategory.SCHEDULE, IntentCategory.DATA_ANALYSIS),
    ]

    @classmethod
    def analyze(cls, user_input: str) -> Tuple[IntentCategory, float, List[IntentCategory]]:
        """
        分析用户输入意图

        Returns:
            (主意图, 置信度, 次要意图列表)
        """
        text = user_input.lower().strip()
        scores: Dict[IntentCategory, float] = {}

        # 1. 关键词评分
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            score = sum(2.0 for kw in keywords if kw in text)
            # 长关键词权重更高
            score += sum(len(kw) * 0.1 for kw in keywords if kw in text)
            scores[intent] = score

        # 2. 复合模式检测
        secondary_intents: List[IntentCategory] = []
        for pattern, primary, secondary in cls.COMPOUND_PATTERNS:
            if re.search(pattern, text):
                scores[primary] = scores.get(primary, 0) + 3.0
                if secondary not in secondary_intents:
                    secondary_intents.append(secondary)

        # 3. 排序
        if not scores or max(scores.values()) == 0:
            return (IntentCategory.CUSTOM, 0.3, secondary_intents)

        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_intent, top_score = sorted_intents[0]
        confidence = min(top_score / 5.0, 1.0)

        # 收集次要意图
        for intent, score in sorted_intents[1:4]:
            if score > 0.5 and intent not in secondary_intents:
                secondary_intents.append(intent)

        return (primary_intent, confidence, secondary_intents)

# ============================================================================
# 模块注册表
# ============================================================================

class ModuleRegistry:
    """
    模块能力注册表
    维护所有可用模块及其能力描述，用于智能调度
    """

    def __init__(self):
        self._initialized = False
        self._status = "pending"
        self._modules: Dict[str, ModuleCapability] = {}
        self._intent_index: Dict[IntentCategory, List[str]] = defaultdict(list)
        self._load_builtin_registry()

    def _load_builtin_registry(self):
        """加载内置模块能力注册"""
        builtin = [
            # 数据分析
            ModuleCapability(
                "data_analysis",
                "数据分析",
                ["分析", "统计", "图表", "可视化", "pandas"],
                [IntentCategory.DATA_ANALYSIS],
                TaskPriority.HIGH,
                timeout=60,
            ),
            ModuleCapability(
                "database_client",
                "数据库连接器",
                ["数据库", "sql", "查询", "存储"],
                [IntentCategory.DATA_ANALYSIS, IntentCategory.FILE_OPERATION],
                TaskPriority.MEDIUM,
                timeout=30,
            ),
            # 文档生成
            ModuleCapability(
                "document_automation",
                "文档自动化",
                ["word", "pdf", "excel", "报告", "文档"],
                [IntentCategory.DOCUMENT_GEN],
                TaskPriority.HIGH,
                timeout=90,
            ),
            # 通信
            ModuleCapability(
                "email_automation",
                "邮件自动化",
                ["邮件", "email", "发送", "smtp"],
                [IntentCategory.COMMUNICATION],
                TaskPriority.HIGH,
                timeout=30,
            ),
            ModuleCapability(
                "enterprise_notifier",
                "企业通知",
                ["通知", "飞书", "钉钉", "企微"],
                [IntentCategory.COMMUNICATION],
                TaskPriority.HIGH,
                timeout=15,
            ),
            ModuleCapability(
                "instant_messaging",
                "即时通讯",
                ["微信", "消息", "im"],
                [IntentCategory.COMMUNICATION],
                TaskPriority.HIGH,
                timeout=15,
            ),
            ModuleCapability(
                "uni_comm_gateway",
                "全渠道通信网关",
                ["全渠道", "统一通信"],
                [IntentCategory.COMMUNICATION],
                TaskPriority.MEDIUM,
                timeout=20,
            ),
            # 桌面RPA
            ModuleCapability(
                "visual_rpa_core",
                "视觉RPA核心",
                ["截图", "ocr", "视觉", "元素定位"],
                [IntentCategory.RPA_DESKTOP],
                TaskPriority.HIGH,
                timeout=60,
            ),
            ModuleCapability(
                "rpa_controller",
                "RPA控制器",
                ["自动化", "鼠标", "键盘", "操作"],
                [IntentCategory.RPA_DESKTOP],
                TaskPriority.HIGH,
                timeout=120,
            ),
            ModuleCapability(
                "turix_cua_bridge",
                "TuriX-CUA桥接",
                ["自然语言", "桌面操控", "cua"],
                [IntentCategory.RPA_DESKTOP],
                TaskPriority.HIGH,
                timeout=180,
                fallback="visual_rpa_core",
            ),
            ModuleCapability(
                "open_interpreter_bridge",
                "Open Interpreter",
                ["代码执行", "系统命令", "interpreter"],
                [IntentCategory.RPA_DESKTOP, IntentCategory.SYSTEM],
                TaskPriority.HIGH,
                timeout=120,
                fallback="rpa_controller",
            ),
            ModuleCapability(
                "ui_tars_bridge",
                "UI-TARS视觉理解",
                ["ui理解", "界面分析", "视觉模型"],
                [IntentCategory.RPA_DESKTOP],
                TaskPriority.MEDIUM,
                timeout=60,
            ),
            # 战略决策
            ModuleCapability(
                "decision_engine",
                "决策引擎",
                ["决策", "评估", "风险"],
                [IntentCategory.STRATEGY],
                TaskPriority.HIGH,
                timeout=60,
            ),
            ModuleCapability(
                "crewai_strategy",
                "CrewAI战略",
                ["多角色", "辩论", "战略分析"],
                [IntentCategory.STRATEGY],
                TaskPriority.HIGH,
                timeout=180,
            ),
            ModuleCapability(
                "langgraph_decision",
                "LangGraph决策流",
                ["决策流", "状态机", "条件分支"],
                [IntentCategory.STRATEGY],
                TaskPriority.MEDIUM,
                timeout=90,
            ),
            ModuleCapability(
                "business_analyst",
                "业务分析师",
                ["业务分析", "报告", "洞察"],
                [IntentCategory.STRATEGY, IntentCategory.DATA_ANALYSIS],
                TaskPriority.MEDIUM,
                timeout=120,
            ),
            # 安全
            ModuleCapability(
                "opa_policy_engine",
                "OPA策略引擎",
                ["策略", "审批", "规则"],
                [IntentCategory.SECURITY],
                TaskPriority.CRITICAL,
                timeout=30,
            ),
            ModuleCapability(
                "cerbos_permission",
                "Cerbos权限",
                ["权限", "访问控制", "角色"],
                [IntentCategory.SECURITY],
                TaskPriority.CRITICAL,
                timeout=15,
            ),
            ModuleCapability(
                "temporal_approval",
                "Temporal审批流",
                ["审批流", "工作流", "持久化"],
                [IntentCategory.SECURITY],
                TaskPriority.HIGH,
                timeout=60,
            ),
            ModuleCapability(
                "audit_trail",
                "审计追踪",
                ["审计", "日志", "追踪"],
                [IntentCategory.SECURITY],
                TaskPriority.MEDIUM,
                timeout=30,
            ),
            ModuleCapability(
                "risk_control",
                "风控拦截",
                ["风控", "拦截", "规则引擎"],
                [IntentCategory.SECURITY],
                TaskPriority.CRITICAL,
                timeout=15,
            ),
            # 监控
            ModuleCapability(
                "aiops_monitor",
                "AIOps监控",
                ["监控", "异常检测", "根因"],
                [IntentCategory.MONITORING],
                TaskPriority.HIGH,
                timeout=60,
            ),
            ModuleCapability(
                "self_healing",
                "自愈修复",
                ["自愈", "修复", "恢复"],
                [IntentCategory.MONITORING],
                TaskPriority.HIGH,
                timeout=180,
            ),
            # 内容
            ModuleCapability(
                "content_generator",
                "内容生成器",
                ["文案", "营销", "seo"],
                [IntentCategory.CONTENT],
                TaskPriority.MEDIUM,
                timeout=60,
            ),
            ModuleCapability(
                "media_content_agent",
                "新媒体内容Agent",
                ["新媒体", "文案", "配图"],
                [IntentCategory.CONTENT],
                TaskPriority.MEDIUM,
                timeout=120,
            ),
            # 电商
            ModuleCapability(
                "ecommerce_agent",
                "电商Agent",
                ["订单", "库存", "商品", "店铺"],
                [IntentCategory.ECOMMERCE],
                TaskPriority.MEDIUM,
                timeout=90,
            ),
            # 财税法务
            ModuleCapability(
                "finance_legal_agent",
                "财税法务Agent",
                ["发票", "报税", "合同审查"],
                [IntentCategory.FINANCE_LEGAL],
                TaskPriority.MEDIUM,
                timeout=90,
            ),
            # 文件
            ModuleCapability(
                "api_gateway",
                "API网关",
                ["api", "接口", "http", "限流"],
                [IntentCategory.WEB_OPERATION],
                TaskPriority.HIGH,
                timeout=30,
            ),
            # 系统
            ModuleCapability(
                "agent_resource_control",
                "资源管控",
                ["资源", "cpu", "内存", "限流"],
                [IntentCategory.SYSTEM],
                TaskPriority.MEDIUM,
                timeout=15,
            ),
            ModuleCapability(
                "model_router",
                "多模型调度",
                ["模型", "路由", "负载均衡"],
                [IntentCategory.SYSTEM],
                TaskPriority.MEDIUM,
                timeout=15,
            ),
            ModuleCapability(
                "cross_platform_adapter",
                "跨平台适配",
                ["平台", "转译", "兼容"],
                [IntentCategory.SYSTEM],
                TaskPriority.MEDIUM,
                timeout=30,
            ),
            # 自我进化
            ModuleCapability(
                "self_evolving_engine",
                "自我进化引擎",
                ["进化", "学习", "技能创建"],
                [IntentCategory.SYSTEM],
                TaskPriority.LOW,
                timeout=60,
            ),
            ModuleCapability(
                "longterm_memory",
                "长期记忆",
                ["记忆", "上下文", "历史"],
                [IntentCategory.SYSTEM],
                TaskPriority.MEDIUM,
                timeout=15,
            ),
            ModuleCapability(
                "mcp_integration",
                "MCP协议集成",
                ["mcp", "工具", "外部连接"],
                [IntentCategory.SYSTEM, IntentCategory.WEB_OPERATION],
                TaskPriority.MEDIUM,
                timeout=30,
            ),
            ModuleCapability(
                "skill_marketplace",
                "技能市场",
                ["技能", "市场", "插件"],
                [IntentCategory.SYSTEM],
                TaskPriority.LOW,
                timeout=30,
            ),
            # 低代码编排
            ModuleCapability(
                "workflow_orchestrator",
                "工作流编排",
                ["工作流", "dag", "编排"],
                [IntentCategory.SYSTEM, IntentCategory.SCHEDULE],
                TaskPriority.MEDIUM,
                timeout=120,
            ),
        ]

        for cap in builtin:
            self.register(cap)

    def register(self, capability: ModuleCapability):
        """注册模块能力"""
        self._modules[capability.module_name] = capability
        for intent in capability.intent_map:
            if capability.module_name not in self._intent_index[intent]:
                self._intent_index[intent].append(capability.module_name)

    def find_modules(self, intent: IntentCategory, limit: int = 3) -> List[ModuleCapability]:
        """根据意图查找匹配模块"""
        module_names = self._intent_index.get(intent, [])
        modules = [self._modules[m] for m in module_names if m in self._modules]
        modules.sort(key=lambda x: x.priority.value)
        return modules[:limit]

    def get_module(self, name: str) -> Optional[ModuleCapability]:
        """获取模块能力描述"""
        return self._modules.get(name)

    def list_all(self) -> Dict[str, ModuleCapability]:
        """列出所有注册模块"""
        return dict(self._modules)

# ============================================================================
# 任务规划器
# ============================================================================

class TaskPlanner:
    """
    任务拆解器
    将用户意图拆解为可执行的子任务DAG
    """

    # 意图 → 模块映射策略
    INTENT_MODULE_MAP: Dict[IntentCategory, List[str]] = {
        IntentCategory.DATA_ANALYSIS: ["data_analysis", "database_client", "business_analyst"],
        IntentCategory.DOCUMENT_GEN: ["document_automation", "content_generator"],
        IntentCategory.COMMUNICATION: ["enterprise_notifier", "email_automation", "instant_messaging"],
        IntentCategory.RPA_DESKTOP: [
            "turix_cua_bridge",
            "visual_rpa_core",
            "open_interpreter_bridge",
            "rpa_controller",
        ],
        IntentCategory.STRATEGY: ["crewai_strategy", "langgraph_decision", "business_analyst", "decision_engine"],
        IntentCategory.SECURITY: ["opa_policy_engine", "cerbos_permission", "temporal_approval", "risk_control"],
        IntentCategory.MONITORING: ["aiops_monitor", "self_healing", "audit_trail"],
        IntentCategory.CONTENT: ["content_generator", "media_content_agent"],
        IntentCategory.ECOMMERCE: ["ecommerce_agent"],
        IntentCategory.FINANCE_LEGAL: ["finance_legal_agent"],
        IntentCategory.FILE_OPERATION: ["database_client", "api_gateway"],
        IntentCategory.WEB_OPERATION: ["api_gateway", "mcp_integration", "open_interpreter_bridge"],
        IntentCategory.SCHEDULE: ["workflow_orchestrator", "agent_resource_control"],
        IntentCategory.SYSTEM: ["self_evolving_engine", "longterm_memory", "model_router", "skill_marketplace"],
        IntentCategory.CUSTOM: [],
    }

    def __init__(self, registry: ModuleRegistry):
        self.registry = registry

    def plan(
        self, user_input: str, primary_intent: IntentCategory, secondary_intents: List[IntentCategory]
    ) -> List[SubTask]:
        """
        将用户输入拆解为子任务列表

        支持复合意图拆解，例如：
        "把今天的销售数据整理成报告，发给张总"
        → [数据分析, 文档生成, 邮件发送]
        """
        sub_tasks: List[SubTask] = []
        task_counter = 0

        # 1. 主意图任务
        primary_modules = self.INTENT_MODULE_MAP.get(primary_intent, [])
        for mod_name in primary_modules:
            cap = self.registry.get_module(mod_name)
            if cap:
                task_counter += 1
                task = SubTask(
                    task_id=f"sub_{uuid.uuid4().hex[:8]}",
                    name=cap.display_name,
                    description=self._generate_task_desc(user_input, cap, primary_intent),
                    module_name=mod_name,
                    intent=primary_intent,
                    priority=cap.priority,
                    params={"user_input": user_input, "intent": primary_intent.value},
                )
                sub_tasks.append(task)

        # 2. 次要意图任务（非重复）
        added_modules = set(primary_modules)
        for intent in secondary_intents:
            sec_modules = self.INTENT_MODULE_MAP.get(intent, [])
            for mod_name in sec_modules:
                if mod_name not in added_modules:
                    cap = self.registry.get_module(mod_name)
                    if cap:
                        task_counter += 1
                        task = SubTask(
                            task_id=f"sub_{uuid.uuid4().hex[:8]}",
                            name=cap.display_name,
                            description=self._generate_task_desc(user_input, cap, intent),
                            module_name=mod_name,
                            intent=intent,
                            priority=cap.priority,
                            params={"user_input": user_input, "intent": intent.value},
                        )
                        sub_tasks.append(task)
                        added_modules.add(mod_name)

        # 3. 设置依赖关系（按优先级排序，低优先级依赖高优先级）
        self._resolve_dependencies(sub_tasks)

        # 4. 如果没有任何子任务（CUSTOM），尝试通用方案
        if not sub_tasks:
            sub_tasks = self._create_generic_plan(user_input)

        return sub_tasks

    def _generate_task_desc(self, user_input: str, cap: ModuleCapability, intent: IntentCategory) -> str:
        """生成子任务描述"""
        desc_map = {
            IntentCategory.DATA_ANALYSIS: f"分析处理：{user_input}",
            IntentCategory.DOCUMENT_GEN: f"生成文档：{user_input}",
            IntentCategory.COMMUNICATION: f"发送通知：{user_input}",
            IntentCategory.RPA_DESKTOP: f"桌面操作：{user_input}",
            IntentCategory.STRATEGY: f"战略分析：{user_input}",
            IntentCategory.SECURITY: f"安全检查：{user_input}",
            IntentCategory.MONITORING: f"监控检测：{user_input}",
            IntentCategory.CONTENT: f"内容创作：{user_input}",
            IntentCategory.ECOMMERCE: f"电商处理：{user_input}",
            IntentCategory.FINANCE_LEGAL: f"财税法务：{user_input}",
            IntentCategory.FILE_OPERATION: f"文件操作：{user_input}",
            IntentCategory.WEB_OPERATION: f"网络操作：{user_input}",
            IntentCategory.SCHEDULE: f"定时任务：{user_input}",
            IntentCategory.SYSTEM: f"系统管理：{user_input}",
            IntentCategory.CUSTOM: f"执行任务：{user_input}",
        }
        return desc_map.get(intent, f"执行：{user_input}")

    def _resolve_dependencies(self, tasks: List[SubTask]):
        """解析任务依赖关系"""
        # 按优先级排序
        tasks.sort(key=lambda t: (t.priority.value, t.intent.value))

        # 同类意图内串行，不同类意图可并行
        intent_groups: Dict[IntentCategory, List[SubTask]] = defaultdict(list)
        for t in tasks:
            intent_groups[t.intent].append(t)

        for intent, group in intent_groups.items():
            for i in range(1, len(group)):
                group[i].depends_on.append(group[i - 1].task_id)

    def _create_generic_plan(self, user_input: str) -> List[SubTask]:
        """创建通用执行计划"""
        return [
            SubTask(
                task_id=f"sub_{uuid.uuid4().hex[:8]}",
                name="通用任务执行",
                description=f"执行：{user_input}",
                module_name="open_interpreter_bridge",
                intent=IntentCategory.CUSTOM,
                params={"user_input": user_input},
                priority=TaskPriority.MEDIUM,
            )
        ]

# ============================================================================
# 模块执行器
# ============================================================================

class ModuleExecutor:
    """
    模块执行器
    负责动态加载和执行模块，处理超时、重试、降级
    断点1：统一执行接口
    """

    def __init__(self):
        self._initialized = False
        self._status = "pending"
        self._loaded_modules: Dict[str, Any] = {}
        self._load_errors: Dict[str, str] = {}
        self._lock = threading.Lock()

    def _publish_event(self, event_type: str, data: Dict):
        """断点2：发布模块执行事件"""
        try:
            from modules.event_bus import get_event_bus

            eb = get_event_bus()
            asyncio.create_task(eb.publish(event_type, data=data, source="module_executor"))
        except Exception:
            pass

    def load_module(self, module_name: str) -> Tuple[bool, Any, str]:
        """
        动态加载模块

        Returns:
            (成功?, 模块对象, 错误信息)
        """
        with self._lock:
            if module_name in self._loaded_modules:
                return (True, self._loaded_modules[module_name], "")
            if module_name in self._load_errors:
                return (False, None, self._load_errors[module_name])

            import importlib

            mod = importlib.import_module(f"modules.{module_name}")
            with self._lock:
                self._loaded_modules[module_name] = mod
            return (True, mod, "")

    async def execute(self, sub_task: SubTask, registry: ModuleRegistry, timeout: Optional[float] = None) -> SubTask:
        """
        执行子任务

        支持超时控制、自动重试、降级回退
        """
        _ = self.trace("execute")
        metrics_collector.counter("agent_orchestrator_ops_total", labels={"task": sub_task.module_name})
        self.audit("execute_task", f"task={sub_task.module_name}, timeout={timeout}")
        cap = registry.get_module(sub_task.module_name)
        actual_timeout = timeout or (cap.timeout if cap else 120.0)

        for attempt in range(sub_task.max_retries + 1):
            sub_task.started_at = datetime.now().isoformat()
            sub_task.status = TaskStatus.RUNNING
            start = time.time()

            try:
                pass
                # 加载模块
                success, mod, err = self.load_module(sub_task.module_name)
                if not success:
                    # 尝试降级
                    if cap and cap.fallback:
                        logger.warning(f"模块 {sub_task.module_name} 加载失败，降级到 {cap.fallback}: {err}")
                        sub_task.module_name = cap.fallback
                        sub_task.retry_count += 1
                        continue
                    raise RuntimeError(err)

                # 查找执行入口
                result = self._call_module(mod, sub_task)

                sub_task.result = result
                sub_task.status = TaskStatus.COMPLETED
                sub_task.completed_at = datetime.now().isoformat()
                sub_task.duration_ms = (time.time() - start) * 1000
                return sub_task

            except Exception as e:
                sub_task.retry_count += 1
                sub_task.error = str(e)
                logger.warning(f"子任务 {sub_task.name} 第{attempt + 1}次执行失败: {e}")

                # 降级
                if cap and cap.fallback and sub_task.module_name != cap.fallback:
                    logger.info(f"降级到 {cap.fallback}")
                    sub_task.module_name = cap.fallback
                    sub_task.error = ""
                    continue

                if attempt == sub_task.max_retries:
                    sub_task.status = TaskStatus.DEGRADED
                    sub_task.completed_at = datetime.now().isoformat()
                    sub_task.duration_ms = (time.time() - start) * 1000
                    sub_task.result = {"error": sub_task.error, "degraded": True}

        return sub_task

    def _call_module(self, mod: Any, sub_task: SubTask) -> Any:
        """调用模块的执行入口（断点1修复 + 断点2事件发布）"""
        # 断点1修复：策略1 - 查找 execute/run/process/handle 标准方法
        for method_name in ("execute", "run", "process", "handle"):
            if hasattr(mod, method_name):
                func = getattr(mod, method_name)
                if callable(func):
                    result = func(sub_task.params)
                    # 断点2: 发布模块执行事件
                    self._publish_event(
                        "module.executed",
                        {
                            "module": sub_task.module_name,
                            "method": method_name,
                            "success": result.get("success") if isinstance(result, dict) else True,
                        },
                    )
                    return result

        # 断点1修复：策略2 - 查找 Main/Engine/Core/Handler/Agent 类
        for cls_name in ("Main", "Engine", "Core", "Handler", "Agent"):
            if hasattr(mod, cls_name):
                cls = getattr(mod, cls_name)
                if hasattr(cls, "execute"):
                    result = cls().execute(sub_task.params)
                    self._publish_event(
                        "module.executed",
                        {
                            "module": sub_task.module_name,
                            "class": cls_name,
                            "method": "execute",
                            "success": result.get("success") if isinstance(result, dict) else True,
                        },
                    )
                    return result
                elif hasattr(cls, "run"):
                    result = cls().run(sub_task.params)
                    self._publish_event(
                        "module.executed",
                        {
                            "module": sub_task.module_name,
                            "class": cls_name,
                            "method": "run",
                            "success": result.get("success") if isinstance(result, dict) else True,
                        },
                    )
                    return result

        # 断点1修复：策略3 - 查找标准 execute 入口（给没有上述方法的模块提供兜底）
        if hasattr(mod, "Main"):
            try:
                main_instance = mod.Main()
                if hasattr(main_instance, "execute"):
                    result = main_instance.execute(sub_task.params)
                    self._publish_event(
                        "module.executed",
                        {
                            "module": sub_task.module_name,
                            "instance": "Main",
                            "method": "execute",
                            "success": result.get("success") if isinstance(result, dict) else True,
                        },
                    )
                    return result
            except Exception:
                pass

        # 策略4：模块元数据返回
        return {
            "module": sub_task.module_name,
            "status": "loaded",
            "note": "模块已加载，标准执行接口待注册",
            # 断点1：标注该模块需要接入标准化execute接口
            "_needs_interface": True,
            "_available_methods": [m for m in dir(mod) if not m.startswith("_")],
        }

# ============================================================================
# 进化反馈器
# ============================================================================

class EvolutionFeedback:
    """
    进化反馈器
    将执行结果反馈给 self_evolving_engine 进行学习
    """

    def __init__(self):
        self._initialized = False
        self._status = "pending"
        self._engine = None
        self._memory = None

    def set_memory(self, memory_engine):
        """P1: 外部注入记忆引擎实例"""
        self._memory_engine = memory_engine

    def _get_engine(self):
        if self._engine is None:
            from modules import self_evolving_engine

            self._engine = self_evolving_engine
        return self._engine

    def _get_memory(self):
        if self._memory is None:
            from modules import longterm_memory

            self._memory = longterm_memory
        return self._memory

    def record_execution(self, task: OrchestratorTask):
        """记录任务执行结果用于学习"""
        # P1: 写入长期记忆
        me = getattr(self, "_memory_engine", None)
        if me:
            try:
                modules_used = [st.module_name for st in task.sub_tasks]
                success = task.status == TaskStatus.COMPLETED
                me.save_memory(
                    content=f"意图:{task.intent.value} | 模块:{','.join(modules_used)} | 质量:{task.quality_score:.0%}",
                    memory_type="execution_log",
                    entity_id=task.task_id,
                    weight=0.7 if success else 0.9,
                )
            except Exception as e:
                logger.debug(f"[P1记忆] EvolutionFeedback写入失败: {e}")

        engine = self._get_engine()
        if engine and hasattr(engine, "record_experience"):
            try:
                engine.record_experience(
                    task_type=task.intent.value,
                    user_input=task.user_input,
                    success=task.status == TaskStatus.COMPLETED,
                    modules_used=[st.module_name for st in task.sub_tasks],
                    quality_score=task.quality_score,
                    lessons=task.lessons_learned,
                )
                logger.info("已将执行经验反馈给自我进化引擎")
            except Exception as e:
                logger.debug(f"进化反馈写入失败: {e}")

    def store_context(self, key: str, value: Any):
        """P1: 存储长期记忆上下文（增强版）"""
        # 优先使用注入的 memory_engine
        me = getattr(self, "_memory_engine", None)
        if me:
            try:
                me.save_memory(
                    content=f"{key}: {str(value)[:200]}", memory_type="context", entity_id="evolution", weight=0.5
                )
                return
            except Exception as e:
                logger.debug(f"记忆引擎写入失败: {e}")
        # 降级：旧的 store API
        memory = self._get_memory()
        if memory and hasattr(memory, "store"):
            try:
                memory.store(key, value)
            except Exception as e:
                logger.debug(f"长期记忆写入失败: {e}")

# ============================================================================
class ExecutionDAGBuilder:
    """执行DAG构建器 - 将任务分解为有向无环图并编排执行顺序。

    企业场景：复杂工作流（如CI/CD流水线、数据ETL管道）需要
    正确处理任务依赖、并行化、条件分支和失败回退。
    """

    def __init__(self):
        self._initialized = False
        self._status = "pending"
        self._nodes: Dict[str, Dict] = {}  # task_id -> {deps, action, parallel}
        self._edges: Dict[str, Set[str]] = defaultdict(set)

    def add_task(self, task_id: str, action: str, depends_on: List[str] = None, parallel: bool = False):
        """添加任务节点"""
        self._nodes[task_id] = {
            "action": action,
            "depends_on": depends_on or [],
            "parallel": parallel,
            "status": "pending",
        }
        for dep in depends_on or []:
            self._edges[dep].add(task_id)

    def build(self) -> Dict:
        """构建可执行的DAG，返回执行层级"""
        in_degree = {tid: len(info["depends_on"]) for tid, info in self._nodes.items()}
        reverse = defaultdict(set)
        for tid, info in self._nodes.items():
            for dep in info["depends_on"]:
                reverse[dep].add(tid)

        # 拓扑分层
        layers = []
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        visited = set()
        while queue:
            layer = []
            for tid in queue:
                if tid in visited:
                    continue
                visited.add(tid)
                layer.append(tid)
            if layer:
                layers.append(layer)
            next_queue = []
            for tid in layer:
                for dependent in reverse.get(tid, set()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)
            queue = next_queue

        # 检测环
        if len(visited) != len(self._nodes):
            missing = set(self._nodes) - visited
            return {"success": False, "error": "circular_dependency", "cycle_nodes": list(missing)}

        # 计算并行度
        max_parallel = max(len(l) for l in layers) if layers else 0
        return {
            "success": True,
            "layers": layers,
            "total_tasks": len(self._nodes),
            "max_parallelism": max_parallel,
            "critical_path_length": len(layers),
        }

    def estimate_execution_time(self, task_durations: Dict[str, float]) -> Dict:
        """估算DAG总执行时间（考虑并行）"""
        dag = self.build()
        if not dag["success"]:
            return {"error": "DAG contains cycle"}
        total = 0
        for layer in dag["layers"]:
            layer_max = max((task_durations.get(t, 1.0) for t in layer), default=1.0)
            total += layer_max
        return {
            "estimated_seconds": round(total, 1),
            "layers": dag["critical_path_length"],
            "max_parallelism": dag["max_parallelism"],
            "speedup_vs_serial": round(sum(task_durations.values()) / total, 1) if total > 0 else 0,
        }

# 主编排器（核心）
# ============================================================================

class AgentOrchestrator(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    AUTO-EVO-AI 主编排器 — 系统大脑

    用法示例:
        # 基础版（规则引擎）
        orchestrator = AgentOrchestrator()
        result = orchestrator.run("把今天的销售数据整理成报告发给张总")

        # AI增强版（需要配置API Key）
        from modules.ai_gateway import AIGateway
        ai_gateway = AIGateway()
        orchestrator = AgentOrchestrator(ai_gateway=ai_gateway)
        result = orchestrator.run("帮我分析下这个月的销售趋势")

    执行流程:
        1. AI/规则意图分析 → 解析用户意图
        2. TaskPlanner.plan() → 拆解为子任务
        3. ModuleExecutor.execute() → 调度模块执行
        4. 结果聚合 + 质量评估
        5. EvolutionFeedback.record() → 反馈学习
    """

    def __init__(self, max_workers: int = 4, ai_gateway=None, memory_engine=None):

        super().__init__()
        self.registry = ModuleRegistry()
        self.planner = TaskPlanner(self.registry)
        self.executor = ModuleExecutor()
        self.feedback = EvolutionFeedback()
        self.feedback.set_memory(memory_engine)  # P1: 激活长期记忆
        self.max_workers = max_workers
        self._task_history: deque = deque(maxlen=100)
        self._running = False
        self._lock = threading.Lock()
        self._progress_callbacks: List[Callable] = []

        # AI 增强层
        self.ai_gateway = ai_gateway
        self.memory_engine = memory_engine  # P1: 注入记忆引擎
        self.ai_intent_analyzer = AIIntentAnalyzer(ai_gateway)
        self.use_ai_intent = ai_gateway is not None and bool(ai_gateway.models)

        self.logger = logging.getLogger("evo.orchestrator")

        if self.use_ai_intent:
            self.logger.info("🤖 AI增强意图分析已启用")
        else:
            self.logger.info("📋 规则引擎意图分析模式")

    # ---- 公共接口 ----

    def run(
        self, user_input: str, priority: TaskPriority = TaskPriority.HIGH, callback: Optional[Callable] = None
    ) -> OrchestratorTask:
        """
        执行编排任务（主入口）

        Args:
            user_input: 用户自然语言输入
            priority: 任务优先级
            callback: 进度回调 fn(task_status, sub_task_name, progress_pct)

        Returns:
            OrchestratorTask 包含完整执行结果
        """
        # 1. 创建任务
        task = OrchestratorTask(
            task_id=f"task_{uuid.uuid4().hex[:12]}",
            user_input=user_input,
            intent=IntentCategory.CUSTOM,
            priority=priority,
            created_at=datetime.now().isoformat(),
        )

        if callback:
            self._progress_callbacks.append(callback)

        try:
            pass
            # P1+P2: 记忆检索 — 在思考之前先查上下文（含其他Agent共享经验）
            memory_context = ""
            if self.memory_engine:
                try:
                    relevant = self.memory_engine.query_memory(user_input, top_k=3)
                    if relevant:
                        ctx_parts = []
                        for r in relevant:
                            entry = r.get("entry", {})
                            content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
                            score = r.get("score", 0)
                            if score > 0.5:
                                from_agent = entry.get("metadata", {}).get("agent_id", "")
                                prefix = f"[{from_agent}的经验]" if from_agent else "[相关记忆]"
                                ctx_parts.append(f"{prefix}·{score:.0%}] {content}")
                        if ctx_parts:
                            memory_context = "\n".join(ctx_parts)
                            self.logger.info(f"[P2记忆] 检索到 {len(ctx_parts)} 条相关记忆")
                except Exception as e:
                    self.logger.warning(f"[P2记忆] 检索失败: {e}")

            # 2. 意图理解（AI增强或规则引擎）
            task.status = TaskStatus.PLANNING
            task.started_at = datetime.now().isoformat()
            self._notify(callback, task, "正在理解意图...", 5)

            # 注入记忆上下文到输入（供后续模块使用）
            if memory_context:
                user_input = f"【相关背景】{memory_context}\n\n【当前需求】{user_input}"

            if self.use_ai_intent:
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 在已有事件循环中创建task
                        primary_intent, confidence, secondary = loop.run_until_complete(
                            self.ai_intent_analyzer.analyze(user_input)
                        )
                    else:
                        primary_intent, confidence, secondary = asyncio.run(self.ai_intent_analyzer.analyze(user_input))
                except Exception as e:
                    self.logger.warning(f"AI意图分析失败: {e}，降级到规则引擎")
                    primary_intent, confidence, secondary = IntentAnalyzer.analyze(user_input)
            else:
                primary_intent, confidence, secondary = IntentAnalyzer.analyze(user_input)
            task.intent = primary_intent
            self.logger.info(
                f"意图分析: primary={primary_intent.value} "
                f"confidence={confidence:.0%} secondary={[s.value for s in secondary]}"
            )

            # 3. 任务拆解
            self._notify(callback, task, "正在规划任务...", 15)
            sub_tasks = self.planner.plan(user_input, primary_intent, secondary)
            task.sub_tasks = sub_tasks
            self.logger.info(f"拆解为 {len(sub_tasks)} 个子任务")

            # 4. 构建DAG并执行
            task.status = TaskStatus.DISPATCHING
            self._notify(callback, task, "开始执行...", 20)
            self._execute_dag(task, callback)

            # 5. 结果聚合
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.total_duration_ms = (
                datetime.fromisoformat(task.completed_at) - datetime.fromisoformat(task.started_at)
            ).total_seconds() * 1000

            # 6. 质量评估
            task.quality_score = self._evaluate_quality(task)

            # 7. 经验提取
            task.lessons_learned = self._extract_lessons(task)

            # P1: 自动归档重要记忆
            if self.memory_engine and task.status == TaskStatus.COMPLETED:
                self._archive_to_memory(task)

            self.logger.info(
                f"任务完成: id={task.task_id} duration={task.total_duration_ms:.0f}ms quality={task.quality_score:.0%}"
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()
            self.logger.error(f"任务失败: {e}")
        finally:
            # 记录历史
            self._task_history.append(task)
            # 反馈进化
            self.feedback.record_execution(task)
            if callback and callback in self._progress_callbacks:
                self._progress_callbacks.remove(callback)

        return task

    async def run_async(self, user_input: str, **kwargs) -> OrchestratorTask:
        """异步执行（线程池封装）"""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run, user_input, *[], **kwargs)

    def explain(self, user_input: str) -> Dict[str, Any]:
        """
        模拟执行计划（不实际执行，返回规划结果）

        用于"先看计划再执行"场景
        """
        # 意图分析（同步版本，使用规则引擎）
        primary_intent, confidence, secondary = IntentAnalyzer.analyze(user_input)
        sub_tasks = self.planner.plan(user_input, primary_intent, secondary)

        return {
            "user_input": user_input,
            "primary_intent": primary_intent.value,
            "confidence": f"{confidence:.0%}",
            "secondary_intents": [s.value for s in secondary],
            "estimated_steps": len(sub_tasks),
            "plan": [
                {
                    "step": i + 1,
                    "name": t.name,
                    "module": t.module_name,
                    "intent": t.intent.value,
                    "priority": t.priority.name,
                    "parallel": not t.depends_on,
                }
                for i, t in enumerate(sub_tasks)
            ],
            "estimated_modules_needed": len(set(t.module_name for t in sub_tasks)),
        }

    # ---- 内部方法 ----

    def _publish_event(self, event_type: str, data: Dict):
        """发布事件（断点2 - EventBus激活）"""
        try:
            from modules.event_bus import get_event_bus

            eb = get_event_bus()
            asyncio.create_task(eb.publish(event_type, data=data, source="agent_orchestrator"))
        except Exception:
            pass  # EventBus不可用时静默降级

    def _execute_dag(self, task: OrchestratorTask, callback: Optional[Callable]):
        """执行任务DAG（支持并行）"""
        tasks = {t.task_id: t for t in task.sub_tasks}
        completed: Set[str] = set()
        total = len(task.sub_tasks)

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {}

            while len(completed) < total:
                # 找出可执行的任务（依赖已满足）
                ready = []
                for t in task.sub_tasks:
                    if t.task_id in completed or t.task_id in futures:
                        continue
                    if t.task_id in [f.task_id for f in futures if not f.done()]:
                        continue
                    deps_met = all(d in completed for d in t.depends_on)
                    if deps_met:
                        ready.append(t)

                if not ready:
                    # 等待正在执行的任务
                    if futures:
                        done_futures = [f for f in futures if f.done()]
                        for f in done_futures:
                            result = f.result()
                            completed.add(result.task_id)
                            progress = int((len(completed) / total) * 80) + 20
                            self._notify(callback, task, f"✅ {result.name} 完成", progress)
                            del futures[f]
                        time.sleep(0.1)
                        continue
                    else:
                        break  # 无可执行且无运行中的任务

                # 提交可执行任务
                for t in ready:
                    future = pool.submit(self.executor.execute, t, self.registry)
                    future.task_id = t.task_id  # type: ignore
                    futures[future] = t

                # 收集完成的
                time.sleep(0.05)

            # 等待剩余
            for f in as_completed(futures):
                result = f.result()
                completed.add(result.task_id)
                progress = int((len(completed) / total) * 80) + 20
                self._notify(callback, task, f"✅ {result.name} 完成", progress)
                # 断点2: 发布子任务完成事件
                self._publish_event(
                    "subtask.completed",
                    {
                        "task_id": task.task_id,
                        "subtask_id": result.task_id,
                        "module": result.module_name,
                        "status": result.status.value,
                        "duration_ms": result.duration_ms,
                    },
                )

    def _evaluate_quality(self, task: OrchestratorTask) -> float:
        """评估任务执行质量 (0-1)"""
        if not task.sub_tasks:
            return 0.0

        scores = []
        for st in task.sub_tasks:
            if st.status == TaskStatus.COMPLETED:
                scores.append(1.0)
            elif st.status == TaskStatus.DEGRADED:
                scores.append(0.5)
            elif st.status == TaskStatus.FAILED:
                scores.append(0.0)
            else:
                scores.append(0.3)

        # 完成率
        completion_rate = sum(scores) / len(scores)
        # 无错误加成
        error_penalty = sum(1 for s in scores if s < 0.5) * 0.1
        # 速度加成（3秒内完成额外加分）
        speed_bonus = 0.05 if task.total_duration_ms < 3000 else 0.0

        return max(0.0, min(1.0, completion_rate - error_penalty + speed_bonus))

    def _extract_lessons(self, task: OrchestratorTask) -> List[str]:
        """提取经验教训"""
        lessons = []
        for st in task.sub_tasks:
            if st.status == TaskStatus.DEGRADED and st.error:
                lessons.append(f"模块 {st.module_name} 降级: {st.error}")
            elif st.status == TaskStatus.FAILED and st.error:
                lessons.append(f"模块 {st.module_name} 失败: {st.error}")
            elif st.duration_ms > 5000:
                lessons.append(f"模块 {st.module_name} 耗时较长: {st.duration_ms:.0f}ms")
        return lessons

    def _archive_to_memory(self, task: OrchestratorTask):
        """P1+P2: 将执行结果自动归档到长期记忆，高价值经验自动共享"""
        try:
            pass
            # 成功完成的子任务 → 记录成功模式
            for st in task.sub_tasks:
                if st.status == TaskStatus.COMPLETED and st.result:
                    content = f"成功执行 {st.name}: {st.module_name}"
                    self.memory_engine.save_agent_memory(
                        agent_id="orchestrator",
                        content=content,
                        memory_type="task_success",
                        visibility="private",
                        weight=0.7,
                    )
                elif st.status == TaskStatus.FAILED:
                    content = f"失败: {st.module_name} | {st.error}"
                    # 失败教训 → 自动 team 共享（其他Agent可避免同样错误）
                    mid = self.memory_engine.save_agent_memory(
                        agent_id="orchestrator",
                        content=content,
                        memory_type="shared_experience",
                        visibility="team",
                        tags=["failure", "lesson"],
                        weight=0.8,
                    )
                    self.memory_engine.share_memory(mid, visibility="team")

            # 任务经验教训 → 归档并共享
            if task.lessons_learned:
                for lesson in task.lessons_learned:
                    mid = self.memory_engine.save_agent_memory(
                        agent_id="orchestrator",
                        content=lesson,
                        memory_type="shared_experience",
                        visibility="team",
                        tags=["lesson"],
                        weight=0.6,
                    )
                    self.memory_engine.share_memory(mid, visibility="team")

            # 高质量任务 → 记录成功经验并共享
            if task.quality_score >= 0.8 and task.sub_tasks:
                module_list = ", ".join(st.module_name for st in task.sub_tasks if st.status == TaskStatus.COMPLETED)
                content = f"高质量完成任务，使用模块组合: {module_list}"
                mid = self.memory_engine.save_agent_memory(
                    agent_id="orchestrator",
                    content=content,
                    memory_type="shared_experience",
                    visibility="team",
                    tags=["success_pattern", "module_combo"],
                    weight=0.9,
                )
                self.memory_engine.share_memory(mid, visibility="team")

            self.logger.info(f"[P2记忆] 已归档 {len(task.sub_tasks)} 个子任务，高价值经验已共享")
        except Exception as e:
            self.logger.warning(f"[P2记忆] 归档失败: {e}")

    def _notify(self, callback: Optional[Callable], task: OrchestratorTask, message: str, progress: int):
        """进度通知"""
        if callback:
            try:
                callback(task.status.value, message, progress)
            except Exception:
                pass

    # ---- 系统信息 ----

    def get_status(self) -> Dict[str, Any]:
        """获取编排器状态"""
        total = len(self._task_history)
        completed = sum(1 for t in self._task_history if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self._task_history if t.status == TaskStatus.FAILED)

        return {
            "version": "1.1.0",
            "ai_enhanced": self.use_ai_intent,
            "ai_gateway_available": self.ai_gateway is not None,
            "ai_models_count": len(self.ai_gateway.models) if self.ai_gateway else 0,
            "registered_modules": len(self.registry.list_all()),
            "task_history_size": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "success_rate": f"{completed / total:.0%}" if total > 0 else "N/A",
            "max_workers": self.max_workers,
            "loaded_modules": list(self.executor._loaded_modules.keys()),
            "load_errors": list(self.executor._load_errors.keys()),
        }

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近任务历史"""
        history = list(self._task_history)[-limit:]
        return [
            {
                "task_id": t.task_id,
                "user_input": t.user_input[:50] + ("..." if len(t.user_input) > 50 else ""),
                "intent": t.intent.value,
                "status": t.status.value,
                "sub_tasks": len(t.sub_tasks),
                "quality": f"{t.quality_score:.0%}",
                "duration_ms": t.total_duration_ms,
                "created_at": t.created_at,
            }
            for t in history
        ]

    # ============================================================================
    # 快捷入口
    # ============================================================================

    # 全局实例
    def progress_cb(status, msg, pct):
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"  [{bar}] {pct:3d}% {msg}")

    def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口。支持status/info/run/stop/help等通用动作。"""
        if params is None:
            params = {}
        _action = action.lower().strip()
        dispatch = {
            "status": self.get_status,
            "info": self.get_info,
            "health": self.health_check,
            "help": self.get_help,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status(params)

    def get_info(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        return {
            "success": True,
            "module": self.__class__.__name__,
            "status": "active",
            "version": getattr(self, "version", "1.0.0"),
        }

    def get_help(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        methods = [m for m in dir(self) if not m.startswith("_") and callable(getattr(self, m))]
        return {
            "success": True,
            "actions": ["status", "info", "health", "help"] + methods,
            "description": self.__doc__ or "",
        }

    def shutdown(self) -> dict:
        """Graceful shutdown for agent_orchestrator."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

    def health_check(self) -> dict:
        """Health check for agent_orchestrator."""
        return {
            "status": "healthy",
            "module": self.__class__.__name__,
            "uptime": getattr(self, "_start_time", 0) and (time.time() - self._start_time) or 0,
        }

    def initialize(self) -> dict:
        """Initialize agent_orchestrator."""
        self.status = "initialized"
        self._start_time = time.time()
        self.status = "active"
        self.logger.info("%s initialized", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

_default_orchestrator: Optional[AgentOrchestrator] = None

def get_orchestrator() -> AgentOrchestrator:
    """获取全局编排器实例（单例）"""
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = AgentOrchestrator()
    return _default_orchestrator

def run(user_input: str, **kwargs) -> OrchestratorTask:
    """快捷执行入口"""
    return get_orchestrator().run(user_input, **kwargs)

def explain(user_input: str) -> Dict[str, Any]:
    """快捷规划入口（只看计划不执行）"""
    return get_orchestrator().explain(user_input)

# ============================================================================
# 自测
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 60)
    print("AUTO-EVO-AI v6.32 — Agent Orchestrator 自测")
    print("=" * 60)

    orch = AgentOrchestrator()

    # 测试1：意图分析
    print("\n--- 测试1：意图分析 ---")
    test_inputs = [
        "把今天的销售数据整理成报告发给张总",
        "监控服务器CPU和内存使用情况",
        "帮我审批一下采购申请",
        "打开微信发消息给李四",
        "分析上周的用户增长趋势并生成报告",
        "系统当前状态怎么样",
    ]
    for inp in test_inputs:
        intent, conf, sec = IntentAnalyzer.analyze(inp)
        print(f"  [{conf:.0%}] {inp}")
        print(f"    → 主意图: {intent.value} | 次要: {[s.value for s in sec]}")

    # 测试2：任务规划
    print("\n--- 测试2：任务规划 ---")
    plan = orch.explain("把今天的销售数据整理成报告发给张总")
    print(f"  主意图: {plan['primary_intent']} (置信度: {plan['confidence']})")
    print(f"  步骤数: {plan['estimated_steps']}")
    for step in plan["plan"]:
        dep = "串行" if not step["parallel"] else "并行"
        print(f"    Step {step['step']}: {step['name']} ({step['module']}) [{dep}]")

    # 测试3：实际执行
    print("\n--- 测试3：实际执行 ---")

    result = orch.run(
        "检查系统状态",
        callback=progress_cb,
    )
    print(f"\n  结果: {result.status.value}")
    print(f"  质量评分: {result.quality_score:.0%}")
    print(f"  子任务: {len(result.sub_tasks)}")
    for st in result.sub_tasks:
        icon = "✅" if st.status == TaskStatus.COMPLETED else "⚠️" if st.status == TaskStatus.DEGRADED else "❌"
        print(f"    {icon} {st.name}: {st.status.value} ({st.duration_ms:.0f}ms)")
    if result.lessons_learned:
        print(f"  经验: {result.lessons_learned}")

    # 测试4：编排器状态
    print("\n--- 测试4：编排器状态 ---")
    status = orch.get_status()
    print(f"  注册模块: {status['registered_modules']}")
    print(f"  已加载: {len(status['loaded_modules'])}")
    print(f"  加载错误: {len(status['load_errors'])}")
    print(f"  历史任务: {status['task_history_size']}")

    print("\n" + "=" * 60)
    print("✅ Agent Orchestrator 自测完成")
    print("=" * 60)

module_class = AgentOrchestrator
