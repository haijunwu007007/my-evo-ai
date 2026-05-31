"""Agent Planner - 类型定义"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

class TaskType(str, Enum):
    """任务类型枚举"""

    DATA_ANALYSIS = "data_analysis"  # 数据分析
    DATA_PROCESSING = "data_processing"  # 数据处理/ETL
    REPORT_GENERATION = "report_generation"  # 报告生成
    CODE_GENERATION = "code_generation"  # 代码生成
    CODE_REVIEW = "code_review"  # 代码审查
    API_TESTING = "api_testing"  # API测试
    MONITORING = "monitoring"  # 监控运维
    SECURITY = "security"  # 安全审计
    DEPLOYMENT = "deployment"  # 部署运维
    WORKFLOW = "workflow"  # 工作流编排
    FILE_PROCESSING = "file_processing"  # 文件处理
    AI_INFERENCE = "ai_inference"  # AI推理
    SEARCH = "search"  # 搜索查询
    NOTIFICATION = "notification"  # 消息通知
    CHAT = "chat"  # 对话交互
    CUSTOM = "custom"  # 自定义任务

class PlanStatus(str, Enum):
    """计划状态"""

    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ModuleCapability:
    """模块能力描述"""

    name: str  # 模块名
    display_name: str  # 显示名
    category: str  # 分类
    description: str  # 功能描述
    actions: list[str] = field(default_factory=list)  # 可用action
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)  # 标签（用于匹配）
    priority: int = 5  # 优先级 1-10

@dataclass
class ExecutionStep:
    """执行步骤"""

    step_id: int
    module_name: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[int] = field(default_factory=list)  # 依赖的step_id
    result: dict[str, Any] | None = None
    status: str = "pending"  # pending/running/done/failed
    error: str | None = None
    duration_ms: float = 0.0

@dataclass
class ExecutionPlan:
    """执行计划"""

    plan_id: str
    task_type: TaskType
    user_intent: str
    steps: list[ExecutionStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    final_result: dict[str, Any] | None = None
    error: str | None = None

