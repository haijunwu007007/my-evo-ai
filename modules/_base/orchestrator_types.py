"""AUTO-EVO-AI — 编排器通用类型定义（从 agent_orchestrator.py 提取）"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = [
    "TaskStatus", "TaskPriority", "IntentCategory",
    "ModuleCapability", "SubTask", "OrchestratorTask",
]


class TaskStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    ROLLING_BACK = "rolling_back"


class TaskPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class IntentCategory(Enum):
    """意图分类"""
    INQUIRY = "inquiry"
    OPERATION = "operation"
    ANALYSIS = "analysis"
    CREATION = "creation"
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"
    WORKFLOW = "workflow"
    SYSTEM = "system"
    UNKNOWN = "unknown"
    DATA_ANALYSIS = "data_analysis"
    DOCUMENT_GEN = "document_gen"
    COMMUNICATION = "communication"
    RPA_DESKTOP = "rpa_desktop"
    STRATEGY = "strategy"
    SECURITY = "security"
    CONTENT = "content"
    ECOMMERCE = "ecommerce"
    FINANCE_LEGAL = "finance_legal"
    FILE_OPERATION = "file_operation"
    WEB_OPERATION = "web_operation"
    SCHEDULE = "schedule"
    CUSTOM = "custom"





@dataclass
class SubTask:
    id: str
    name: str
    module: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 30
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    dag_level: int = 0


@dataclass
class OrchestratorTask:
    id: str
    goal: str
    context: Dict[str, Any] = field(default_factory=dict)
    subtasks: List[SubTask] = field(default_factory=list)
    status: str = "pending"
    mode: str = "auto"
    priority: int = 1
    owner: str = "system"
    created_at: float = 0.0
    updated_at: float = 0.0
    completed_at: float = 0.0
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    tags: List[str] = field(default_factory=list)
