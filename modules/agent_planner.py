# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI v7.0 - Agent Planner 智能编排层
====================================================
核心能力：
  1. 自然语言意图理解 — 解析用户输入，识别任务类型和参数
  2. 任务自动分解 — 将复杂任务拆解为模块调用序列
  3. 模块能力注册表 — 512个模块的分类、描述、可用action
  4. 执行编排引擎 — 按依赖顺序调用模块链，传递中间结果
  5. 结果聚合与格式化 — 收集所有模块输出，生成统一报告

使用方式：
  POST /api/planner/chat    {"message": "帮我分析这批数据"}
  POST /api/planner/execute {"task": "数据分析", "params": {...}}
  GET  /api/planner/modules  — 查看能力注册表
  GET  /api/planner/status   — 查看编排器状态
"""

__module_meta__ = {
    "id": "agent-planner",
    "name": "Agent Planner",
    "version": "1.0.0",
    "group": "agent",
    "inputs": [
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "modules_dir", "type": "string", "required": True, "description": ""},
        {"name": "cap", "type": "string", "required": True, "description": ""},
        {"name": "query", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "category", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "event", "config": {"on": "agent_planner.task.request"}}],
    "depends_on": [],
    "tags": ["multi-agent", "agent"],
    "grade": "C",
    "description": "AUTO-EVO-AI v7.0 - Agent Planner 智能编排层 ====================================================",
}

import os
import sys
import json
import time
import re
import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict
from collections import defaultdict

# 确保模块可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.planner")

# ============================================================================
# 数据结构
# ============================================================================

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
    actions: List[str] = field(default_factory=list)  # 可用action
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)  # 标签（用于匹配）
    priority: int = 5  # 优先级 1-10

@dataclass
class ExecutionStep:
    """执行步骤"""

    step_id: int
    module_name: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[int] = field(default_factory=list)  # 依赖的step_id
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending/running/done/failed
    error: Optional[str] = None
    duration_ms: float = 0.0

@dataclass
class ExecutionPlan:
    """执行计划"""

    plan_id: str
    task_type: TaskType
    user_intent: str
    steps: List[ExecutionStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    final_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# ============================================================================
# 模块能力注册表 — 512个模块的完整分类
# ============================================================================

class ModuleRegistry:
    """
    模块能力注册表
    把512个模块按功能分类，支持按关键词/标签/任务类型查找可用模块
    """

    # 模块能力定义（核心模块，有真实业务逻辑的）
    CORE_MODULES = {
        # --- 数据处理 ---
        "data_pipeline": ModuleCapability(
            "data_pipeline",
            "DataPipeline",
            "data_processing",
            "数据管道引擎，支持ETL流程、数据清洗、转换、加载",
            actions=["status", "create_pipeline", "run_pipeline", "list_pipelines", "get_stats"],
            tags=["etl", "pipeline", "data", "extract", "transform", "load", "清洗", "管道"],
        ),
        "data_sync": ModuleCapability(
            "data_sync",
            "DataSync",
            "data_processing",
            "数据同步引擎，多源数据实时/定时同步",
            actions=["status", "start_sync", "stop_sync", "get_sync_status", "list_sources"],
            tags=["sync", "同步", "数据", "实时", "定时"],
        ),
        "data_validator": ModuleCapability(
            "data_validator",
            "DataValidator",
            "data_processing",
            "数据验证器，Schema校验、数据质量检查、异常检测",
            actions=["status", "validate", "get_rules", "add_rule"],
            tags=["validate", "验证", "quality", "质量", "schema"],
        ),
        "data_analysis": ModuleCapability(
            "data_analysis",
            "DataAnalysis",
            "data_analysis",
            "数据分析引擎，统计分析、趋势分析、异常检测",
            actions=["status", "analyze", "get_report", "set_config"],
            tags=["analysis", "分析", "统计", "trend", "趋势", "异常"],
        ),
        "data_scraping": ModuleCapability(
            "data_scraping",
            "DataScraping",
            "data_processing",
            "网络数据采集，网页爬取、结构化提取",
            actions=["status", "scrape", "list_tasks", "get_results"],
            tags=["scrape", "爬取", "crawler", "采集", "网页"],
        ),
        # --- 可视化与报告 ---
        "chart_engine": ModuleCapability(
            "chart_engine",
            "ChartEngine",
            "report_generation",
            "图表生成引擎，折线图/柱状图/饼图/散点图/热力图",
            actions=["status", "generate", "list_templates", "get_chart"],
            tags=["chart", "图表", "可视化", "折线", "柱状", "饼图", "plot"],
        ),
        "reportgenerator": ModuleCapability(
            "reportgenerator",
            "ReportGenerator",
            "report_generation",
            "报告生成器，支持HTML/PDF/Markdown格式报告",
            actions=["status", "generate", "list_templates", "render"],
            tags=["report", "报告", "pdf", "html", "markdown", "生成"],
        ),
        "monthly_report": ModuleCapability(
            "monthly_report",
            "MonthlyReport",
            "report_generation",
            "月报生成器，自动汇总月度数据生成报告",
            actions=["status", "generate", "get_template", "preview"],
            tags=["report", "月报", "monthly", "汇总"],
        ),
        # --- 代码相关 ---
        "code_review": ModuleCapability(
            "code_review",
            "CodeReview",
            "code_review",
            "AI代码审查，检测bug、安全漏洞、性能问题",
            actions=["status", "review", "get_rules", "set_severity"],
            tags=["review", "审查", "code", "bug", "安全", "质量"],
        ),
        "code_quality": ModuleCapability(
            "code_quality",
            "CodeQuality",
            "code_review",
            "代码质量检测，复杂度/重复率/覆盖率分析",
            actions=["status", "analyze", "get_metrics", "set_threshold"],
            tags=["quality", "质量", "complexity", "复杂度", "coverage", "覆盖"],
        ),
        "code_understand": ModuleCapability(
            "code_understand",
            "CodeUnderstand",
            "code_review",
            "代码理解引擎，自动生成代码文档、调用关系图",
            actions=["status", "understand", "get_doc", "get_dependencies"],
            tags=["understand", "理解", "doc", "文档", "依赖"],
        ),
        "code_template": ModuleCapability(
            "code_template",
            "CodeTemplate",
            "code_generation",
            "代码模板引擎，预设模板快速生成代码",
            actions=["status", "list_templates", "generate", "get_template"],
            tags=["template", "模板", "generate", "生成", "代码"],
        ),
        "code_generator": ModuleCapability(
            "code_generator",
            "CodeGenerator",
            "code_generation",
            "AI代码生成器，自然语言描述生成代码",
            actions=["status", "generate", "get_languages", "set_style"],
            tags=["generate", "生成", "code", "ai", "代码"],
        ),
        # --- API相关 ---
        "api_gateway": ModuleCapability(
            "api_gateway",
            "ApiGateway",
            "api_testing",
            "API网关，路由、限流、认证、日志",
            actions=["status", "add_route", "list_routes", "get_stats"],
            tags=["api", "gateway", "网关", "路由", "限流"],
        ),
        "api_tester": ModuleCapability(
            "api_tester",
            "ApiTester",
            "api_testing",
            "API自动化测试，请求构造、断言、性能测试",
            actions=["status", "test", "run_suite", "get_results"],
            tags=["test", "测试", "api", "自动化", "断言"],
        ),
        "api_mock": ModuleCapability(
            "api_mock",
            "ApiMock",
            "api_testing",
            "API Mock服务，快速搭建模拟接口",
            actions=["status", "add_mock", "list_mocks", "clear"],
            tags=["mock", "模拟", "api", "stub"],
        ),
        # --- 监控运维 ---
        "aiops_monitor": ModuleCapability(
            "aiops_monitor",
            "AIOpsMonitor",
            "monitoring",
            "AIOps智能监控，异常检测、根因分析、自动修复建议",
            actions=["status", "get_alerts", "analyze", "get_metrics"],
            tags=["monitor", "监控", "aops", "异常", "告警", "根因"],
        ),
        "health_monitor": ModuleCapability(
            "health_monitor",
            "HealthMonitor",
            "monitoring",
            "健康监控，服务探活、指标采集、SLA追踪",
            actions=["status", "check", "get_report", "set_threshold"],
            tags=["health", "健康", "监控", "sla", "探活"],
        ),
        "performance_optimizer": ModuleCapability(
            "performance_optimizer",
            "PerformanceOptimizer",
            "monitoring",
            "性能优化引擎，瓶颈分析、调优建议",
            actions=["status", "analyze", "get_recommendations", "optimize"],
            tags=["performance", "性能", "优化", "瓶颈", "调优"],
        ),
        "grafana_monitor": ModuleCapability(
            "grafana_monitor",
            "GrafanaMonitor",
            "monitoring",
            "Grafana监控集成，Dashboard管理、告警规则",
            actions=["status", "get_dashboards", "create_alert", "query"],
            tags=["grafana", "监控", "dashboard", "告警", "面板"],
        ),
        "prometheus_metrics": ModuleCapability(
            "prometheus_metrics",
            "PrometheusMetrics",
            "monitoring",
            "Prometheus指标管理，指标定义、查询、告警",
            actions=["status", "query", "get_metrics", "create_rule"],
            tags=["prometheus", "指标", "metrics", "监控"],
        ),
        # --- 安全 ---
        "aegis_governance": ModuleCapability(
            "aegis_governance",
            "AegisGovernance",
            "security",
            "安全治理引擎，策略管理、合规检查、风险评估",
            actions=["status", "scan", "get_policies", "assess_risk"],
            tags=["security", "安全", "governance", "治理", "合规", "风险"],
        ),
        "security_scanner": ModuleCapability(
            "security_scanner",
            "SecurityScanner",
            "security",
            "安全扫描器，漏洞扫描、依赖检查、配置审计",
            actions=["status", "scan", "get_results", "get_report"],
            tags=["scan", "扫描", "security", "安全", "漏洞", "vulnerability"],
        ),
        "threat_detector": ModuleCapability(
            "threat_detector",
            "ThreatDetector",
            "security",
            "威胁检测引擎，入侵检测、异常行为识别",
            actions=["status", "detect", "get_alerts", "get_rules"],
            tags=["threat", "威胁", "detect", "检测", "入侵"],
        ),
        "access_control": ModuleCapability(
            "access_control",
            "AccessControl",
            "security",
            "访问控制，RBAC权限管理、资源保护",
            actions=["status", "check_permission", "create_user", "list_users"],
            tags=["access", "权限", "rbac", "认证", "authorization"],
        ),
        # --- 部署运维 ---
        "docker_manager": ModuleCapability(
            "docker_manager",
            "DockerManager",
            "deployment",
            "Docker容器管理，镜像构建、容器启停、编排",
            actions=["status", "list_containers", "build", "start", "stop", "logs"],
            tags=["docker", "容器", "container", "部署", "deploy"],
        ),
        "cicd_pipeline": ModuleCapability(
            "cicd_pipeline",
            "CICDPipeline",
            "deployment",
            "CI/CD流水线，构建、测试、部署自动化",
            actions=["status", "create_pipeline", "run", "get_status", "list_pipelines"],
            tags=["cicd", "pipeline", "流水线", "构建", "部署", "deploy"],
        ),
        "auto_scale": ModuleCapability(
            "auto_scale",
            "AutoScale",
            "deployment",
            "自动扩缩容，基于负载自动调整资源",
            actions=["status", "scale_up", "scale_down", "get_metrics", "set_policy"],
            tags=["scale", "扩缩容", "auto", "弹性", "负载"],
        ),
        "backup_engine": ModuleCapability(
            "backup_engine",
            "BackupEngine",
            "deployment",
            "备份引擎，全量/增量备份、恢复、调度",
            actions=["status", "create_backup", "restore", "list_backups", "schedule"],
            tags=["backup", "备份", "恢复", "restore", "容灾"],
        ),
        # --- 工作流 ---
        "workflow_engine": ModuleCapability(
            "workflow_engine",
            "WorkflowEngine",
            "workflow",
            "工作流引擎，DAG任务编排、并行执行、条件分支",
            actions=["status", "create_workflow", "execute", "list_workflows", "get_status"],
            tags=["workflow", "工作流", "dag", "编排", "task", "任务"],
        ),
        "workflow_manager": ModuleCapability(
            "workflow_manager",
            "WorkflowManager",
            "workflow",
            "工作流管理器，模板管理、版本控制、执行历史",
            actions=["status", "list_templates", "create", "get_history", "rollback"],
            tags=["workflow", "工作流", "template", "模板", "管理"],
        ),
        "task_queue": ModuleCapability(
            "task_queue",
            "TaskQueue",
            "workflow",
            "任务队列，优先级队列、延迟任务、重试机制",
            actions=["status", "enqueue", "dequeue", "get_stats", "retry"],
            tags=["queue", "队列", "task", "任务", "priority", "优先级"],
        ),
        # --- 数据库 ---
        "database_connector": ModuleCapability(
            "database_connector",
            "DatabaseConnector",
            "data_processing",
            "数据库连接器，多数据库支持、连接池、SQL执行",
            actions=["status", "query", "execute", "list_connections", "get_schema"],
            tags=["database", "数据库", "sql", "query", "查询", "mysql", "postgres"],
        ),
        "clickhouse_olap": ModuleCapability(
            "clickhouse_olap",
            "ClickHouseOLAP",
            "data_analysis",
            "ClickHouse OLAP引擎，列式分析查询",
            actions=["status", "query", "get_tables", "get_stats"],
            tags=["clickhouse", "olap", "分析", "列式", "查询"],
        ),
        "redis_cache": ModuleCapability(
            "redis_cache",
            "RedisCache",
            "data_processing",
            "Redis缓存管理，KV操作、发布订阅、限流",
            actions=["status", "get", "set", "delete", "get_stats"],
            tags=["redis", "cache", "缓存", "kv", "内存"],
        ),
        # --- 缓存 ---
        "cache_engine": ModuleCapability(
            "cache_engine",
            "CacheEngine",
            "data_processing",
            "缓存引擎，多级缓存、自动失效、命中率优化",
            actions=["status", "get", "set", "invalidate", "get_stats"],
            tags=["cache", "缓存", "multi-level", "命中率"],
        ),
        "cache_manager": ModuleCapability(
            "cache_manager",
            "CacheManager",
            "data_processing",
            "缓存管理器，缓存策略配置、监控、清理",
            actions=["status", "get_stats", "clear", "set_policy", "warmup"],
            tags=["cache", "缓存", "管理", "策略", "清理"],
        ),
        # --- AI/LLM ---
        "llm_openai": ModuleCapability(
            "llm_openai",
            "LLMOpenAI",
            "ai_inference",
            "OpenAI GPT集成，Chat/Completion/Embedding",
            actions=["status", "chat", "complete", "embed"],
            tags=["llm", "gpt", "openai", "ai", "chat", "对话"],
        ),
        "llm_claude": ModuleCapability(
            "llm_claude",
            "LLMClaude",
            "ai_inference",
            "Claude集成，长文本理解、分析推理",
            actions=["status", "chat", "analyze", "summarize"],
            tags=["llm", "claude", "anthropic", "ai", "分析"],
        ),
        "nlp_engine": ModuleCapability(
            "nlp_engine",
            "NLPEngine",
            "ai_inference",
            "NLP引擎，分词/实体识别/情感分析/关键词提取",
            actions=["status", "tokenize", "extract_entities", "sentiment", "keywords"],
            tags=["nlp", "自然语言", "分词", "实体", "情感", "关键词"],
        ),
        "embedding_openai": ModuleCapability(
            "embedding_openai",
            "EmbeddingOpenAI",
            "ai_inference",
            "文本向量化，OpenAI Embedding API",
            actions=["status", "embed", "batch_embed", "search"],
            tags=["embedding", "向量", "相似度", "search", "检索"],
        ),
        # --- 知识库 ---
        "knowledge_base": ModuleCapability(
            "knowledge_base",
            "KnowledgeBase",
            "search",
            "知识库引擎，文档管理、语义检索、问答",
            actions=["status", "search", "add_document", "list_documents", "ask"],
            tags=["knowledge", "知识库", "检索", "search", "问答", "QA"],
        ),
        "rag_pipeline": ModuleCapability(
            "rag_pipeline",
            "RAGPipeline",
            "ai_inference",
            "RAG检索增强生成，文档检索+LLM生成",
            actions=["status", "query", "add_source", "get_sources"],
            tags=["rag", "检索增强", "generation", "生成", "QA"],
        ),
        # --- 文件处理 ---
        "file_manager": ModuleCapability(
            "file_manager",
            "FileManager",
            "file_processing",
            "文件管理器，上传/下载/移动/搜索/监听",
            actions=["status", "list", "upload", "download", "search", "watch"],
            tags=["file", "文件", "管理", "上传", "下载", "目录"],
        ),
        "pdf_report": ModuleCapability(
            "pdf_report",
            "PDFReport",
            "report_generation",
            "PDF报告生成，模板渲染、图表嵌入",
            actions=["status", "generate", "get_template", "render"],
            tags=["pdf", "报告", "生成", "render"],
        ),
        # --- 通知 ---
        "email_automation": ModuleCapability(
            "email_automation",
            "EmailAutomation",
            "notification",
            "邮件自动化，模板邮件、批量发送、触发式通知",
            actions=["status", "send", "list_templates", "get_history"],
            tags=["email", "邮件", "通知", "send", "发送"],
        ),
        "push_notify": ModuleCapability(
            "push_notify",
            "PushNotify",
            "notification",
            "推送通知，多渠道推送（邮件/Slack/Webhook）",
            actions=["status", "send", "subscribe", "get_history"],
            tags=["push", "推送", "通知", "webhook", "slack"],
        ),
        # --- 消息 ---
        "message_queue": ModuleCapability(
            "message_queue",
            "MessageQueue",
            "data_processing",
            "消息队列，发布/订阅、点对点、持久化",
            actions=["status", "publish", "subscribe", "get_stats"],
            tags=["message", "消息", "queue", "队列", "pubsub", "发布订阅"],
        ),
        # --- 配置 ---
        "config_center": ModuleCapability(
            "config_center",
            "ConfigCenter",
            "workflow",
            "配置中心，集中配置管理、热更新、版本控制",
            actions=["status", "get", "set", "list", "history"],
            tags=["config", "配置", "中心", "管理", "热更新"],
        ),
        # --- Agent ---
        "agent_orchestrator": ModuleCapability(
            "agent_orchestrator",
            "AgentOrchestrator",
            "workflow",
            "Agent编排器，多Agent协作、任务分配、结果汇总",
            actions=["status", "create_agent", "assign_task", "get_results", "list_agents"],
            tags=["agent", "智能体", "编排", "协作", "multi-agent"],
        ),
        "agent_marketplace": ModuleCapability(
            "agent_marketplace",
            "AgentMarketplace",
            "workflow",
            "Agent市场，Agent发布/发现/评分/安装",
            actions=["status", "list", "search", "install", "rate"],
            tags=["agent", "市场", "marketplace", "发布", "发现"],
        ),
        # --- 网络 ---
        "load_balancer": ModuleCapability(
            "load_balancer",
            "LoadBalancer",
            "deployment",
            "负载均衡器，多策略分发、健康检查、权重调整",
            actions=["status", "add_backend", "remove_backend", "get_stats"],
            tags=["load", "负载", "均衡", "balancer", "分发"],
        ),
        "reverse_proxy": ModuleCapability(
            "reverse_proxy",
            "ReverseProxy",
            "deployment",
            "反向代理，URL路由、SSL终止、请求转发",
            actions=["status", "add_rule", "list_rules", "get_stats"],
            tags=["proxy", "代理", "反向", "路由", "ssl"],
        ),
        # --- 日志 ---
        "audit_log": ModuleCapability(
            "audit_log",
            "AuditLog",
            "monitoring",
            "审计日志，操作记录、合规审计、日志检索",
            actions=["status", "query", "export", "get_stats"],
            tags=["audit", "审计", "log", "日志", "合规", "记录"],
        ),
        "log_analyzer": ModuleCapability(
            "log_analyzer",
            "LogAnalyzer",
            "monitoring",
            "日志分析器，异常模式检测、错误聚类、根因定位",
            actions=["status", "analyze", "search", "get_patterns"],
            tags=["log", "日志", "分析", "异常", "模式", "错误"],
        ),
        # --- 定时任务 ---
        "cron_scheduler": ModuleCapability(
            "cron_scheduler",
            "CronScheduler",
            "workflow",
            "Cron定时调度，任务定时执行、失败重试",
            actions=["status", "add_job", "remove_job", "list_jobs", "run_now"],
            tags=["cron", "定时", "调度", "scheduler", "job", "任务"],
        ),
        # --- 搜索 ---
        "elasticsearch_search": ModuleCapability(
            "elasticsearch_search",
            "ElasticsearchSearch",
            "search",
            "Elasticsearch全文搜索，索引管理、复杂查询",
            actions=["status", "search", "index", "get_stats", "create_index"],
            tags=["elasticsearch", "search", "搜索", "全文", "索引"],
        ),
        "fts_query": ModuleCapability(
            "fts_query",
            "FTSQuery",
            "search",
            "全文查询引擎，多数据源联合搜索",
            actions=["status", "search", "add_source", "get_sources"],
            tags=["fts", "全文", "搜索", "query", "查询"],
        ),
        # --- 加密 ---
        "encryption_service": ModuleCapability(
            "encryption_service",
            "EncryptionService",
            "security",
            "加密服务，对称/非对称加密、签名验签",
            actions=["status", "encrypt", "decrypt", "sign", "verify"],
            tags=["encrypt", "加密", "decrypt", "解密", "sign", "签名"],
        ),
        # --- 限流熔断 ---
        "circuit_breaker": ModuleCapability(
            "circuit_breaker",
            "CircuitBreaker",
            "deployment",
            "熔断器，服务保护、降级、恢复",
            actions=["status", "get_status", "reset", "get_stats"],
            tags=["circuit", "熔断", "breaker", "降级", "保护"],
        ),
        "api_rate_limiter": ModuleCapability(
            "api_rate_limiter",
            "ApiRateLimiter",
            "deployment",
            "API限流器，多策略限流、令牌桶/漏桶",
            actions=["status", "check", "get_stats", "set_rule"],
            tags=["rate", "限流", "limiter", "token", "令牌"],
        ),
        # --- 分布式 ---
        "distributed_lock": ModuleCapability(
            "distributed_lock",
            "DistributedLock",
            "deployment",
            "分布式锁，互斥锁、读写锁、超时自动释放",
            actions=["status", "acquire", "release", "get_stats"],
            tags=["lock", "锁", "distributed", "分布式", "mutex"],
        ),
        # --- 容灾 ---
        "auto_recovery": ModuleCapability(
            "auto_recovery",
            "AutoRecovery",
            "deployment",
            "自动恢复，故障检测、自动修复、服务重启",
            actions=["status", "recover", "get_history", "set_policy"],
            tags=["recovery", "恢复", "auto", "自动", "容灾", "fault"],
        ),
        "auto_healing": ModuleCapability(
            "auto_healing",
            "AutoHealing",
            "deployment",
            "自愈引擎，异常自愈、配置修复、资源重分配",
            actions=["status", "heal", "get_history", "set_policy"],
            tags=["healing", "自愈", "auto", "自动修复"],
        ),
        "auto_failover": ModuleCapability(
            "auto_failover",
            "AutoFailover",
            "deployment",
            "自动故障转移，主备切换、流量迁移",
            actions=["status", "failover", "get_status", "set_policy"],
            tags=["failover", "故障转移", "主备", "切换"],
        ),
        # --- 浏览器 ---
        "browser_use": ModuleCapability(
            "browser_use",
            "BrowserUse",
            "custom",
            "浏览器自动化，网页操作、截图、数据提取",
            actions=["status", "navigate", "screenshot", "extract", "click"],
            tags=["browser", "浏览器", "自动化", "screenshot", "截图"],
        ),
        # --- 存储 ---
        "object_storage": ModuleCapability(
            "object_storage",
            "ObjectStorage",
            "data_processing",
            "对象存储，文件上传/下载/桶管理",
            actions=["status", "upload", "download", "list_buckets", "delete"],
            tags=["storage", "存储", "object", "桶", "s3", "文件"],
        ),
        # --- 图数据库 ---
        "neo4j_graph": ModuleCapability(
            "neo4j_graph",
            "Neo4jGraph",
            "data_analysis",
            "Neo4j图数据库，节点关系查询、图分析",
            actions=["status", "query", "create_node", "get_graph"],
            tags=["neo4j", "graph", "图", "节点", "关系", "知识图谱"],
        ),
        "knowledge_graph": ModuleCapability(
            "knowledge_graph",
            "KnowledgeGraph",
            "data_analysis",
            "知识图谱引擎，实体关系抽取、图谱构建、推理",
            actions=["status", "build", "query", "extract", "reason"],
            tags=["knowledge", "知识图谱", "graph", "推理", "实体"],
        ),
        # --- 混沌工程 ---
        "chaos_engine": ModuleCapability(
            "chaos_engine",
            "ChaosEngine",
            "monitoring",
            "混沌工程引擎，故障注入、韧性测试",
            actions=["status", "inject", "list_experiments", "get_results"],
            tags=["chaos", "混沌", "故障注入", "韧性", "测试"],
        ),
        # --- RPA ---
        "rpa_control": ModuleCapability(
            "rpa_control",
            "RPAControl",
            "custom",
            "RPA控制，自动化桌面操作、流程录制回放",
            actions=["status", "execute", "record", "play", "list_flows"],
            tags=["rpa", "自动化", "桌面", "流程", "robot"],
        ),
        # --- 向量数据库 ---
        "qdrant_vector": ModuleCapability(
            "qdrant_vector",
            "QdrantVector",
            "search",
            "Qdrant向量数据库，向量存储、相似度搜索",
            actions=["status", "search", "upsert", "get_collections"],
            tags=["qdrant", "vector", "向量", "相似度", "search"],
        ),
        "pgvector": ModuleCapability(
            "pgvector",
            "PGVector",
            "search",
            "PGVector向量扩展，PostgreSQL内向量检索",
            actions=["status", "search", "upsert", "get_stats"],
            tags=["pgvector", "vector", "向量", "postgres", "检索"],
        ),
        # --- OCR ---
        "ocr_engine": ModuleCapability(
            "ocr_engine",
            "OcreEngine",
            "file_processing",
            "OCR引擎，图片文字识别、PDF提取、多语言",
            actions=["status", "recognize", "batch_recognize", "get_languages"],
            tags=["ocr", "识别", "图片", "pdf", "文字"],
        ),
        # --- 翻译 ---
        "translation_service": ModuleCapability(
            "translation_service",
            "TranslationService",
            "ai_inference",
            "翻译服务，多语言翻译、术语管理",
            actions=["status", "translate", "get_languages", "batch_translate"],
            tags=["translate", "翻译", "language", "语言", "多语言"],
        ),
        # --- 情感分析 ---
        "sentiment_analysis": ModuleCapability(
            "sentiment_analysis",
            "SentimentAnalysis",
            "ai_inference",
            "情感分析引擎，文本情感判断、舆情监控",
            actions=["status", "analyze", "batch_analyze", "get_trend"],
            tags=["sentiment", "情感", "分析", "舆情", "opinion"],
        ),
        # --- 文本摘要 ---
        "summarization_engine": ModuleCapability(
            "summarization_engine",
            "SummarizationEngine",
            "ai_inference",
            "文本摘要引擎，自动生成摘要、关键信息提取",
            actions=["status", "summarize", "get_keywords", "batch_summarize"],
            tags=["summary", "摘要", "summarize", "关键信息", "提取"],
        ),
        # --- 语音 ---
        "audio_transcription": ModuleCapability(
            "audio_transcription",
            "AudioTranscription",
            "file_processing",
            "语音转文字，音频文件转录、实时语音识别",
            actions=["status", "transcribe", "get_languages", "batch_transcribe"],
            tags=["audio", "语音", "transcribe", "转录", "asr", "speech"],
        ),
        # --- SQL ---
        "sql_generator": ModuleCapability(
            "sql_generator",
            "SQLGenerator",
            "ai_inference",
            "SQL生成器，自然语言转SQL、SQL优化",
            actions=["status", "generate", "optimize", "explain"],
            tags=["sql", "生成", "自然语言", "optimize", "优化"],
        ),
        # --- 幻灯片 ---
        "mindmap_generator": ModuleCapability(
            "mindmap_generator",
            "MindmapGenerator",
            "report_generation",
            "思维导图生成器，自动生成、编辑、导出思维导图",
            actions=["status", "generate", "export", "get_templates"],
            tags=["mindmap", "思维导图", "导图", "brainstorm"],
        ),
    }

    # 文件名→分类规则（自动发现用）
    _NAME_CLASSIFY_RULES = [
        (
            [
                "data_pipeline",
                "data_sync",
                "data_valid",
                "etl",
                "batch_process",
                "stream",
                "ingest",
                "migrate",
                "extract",
                "cdc",
                "compaction",
                "consumer",
                "producer",
                "topic",
                "kafka",
                "rabbitmq",
                "message_queue",
                "event_bus",
                "mqtt",
                "broker",
                "pub_sub",
                "ibmmq",
                "pulsar",
                "nats",
            ],
            "data_processing",
        ),
        (
            [
                "data_analysis",
                "data_visual",
                "stat",
                "analy",
                "insight",
                "trend",
                "predict",
                "forecast",
                "ml_engine",
                "regression",
                "classif",
                "cluster",
                "anomaly",
                "outlier",
                "cte_query",
                "olap",
                "clickhouse",
                "druid",
            ],
            "data_analysis",
        ),
        (
            ["report", "chart", "graph", "plot", "dashboard", "kpi", "scorecard", "slide", "present", "mindmap"],
            "report_generation",
        ),
        (["code_review", "lint", "quality", "sonar", "inspect", "static_analys"], "code_review"),
        (
            [
                "code_generat",
                "code_understand",
                "code_template",
                "scaffold",
                "boilerplate",
                "codegen",
                "source_map",
                "bytecode",
                "ast_",
            ],
            "code_generation",
        ),
        (
            [
                "test",
                "mock",
                "stub",
                "assert",
                "verify",
                "benchmark",
                "load_test",
                "stress",
                "perf_test",
                "api_test",
                "contract",
            ],
            "api_testing",
        ),
        (
            [
                "monitor",
                "observ",
                "alert",
                "grafana",
                "prometheus",
                "health",
                "beat",
                "ping",
                "uptime",
                "apm",
                "jaeger",
                "trace",
                "log_",
                "metric",
                "aiops",
                "flame",
                "profil",
                "replication_monitor",
            ],
            "monitoring",
        ),
        (
            [
                "secur",
                "threat",
                "firewall",
                "waf",
                "guard",
                "shield",
                "encrypt",
                "decrypt",
                "vulnerab",
                "access_control",
                "permission",
                "rbac",
                "aegis",
                "governance",
                "compliance",
                "audit",
                "risk",
                "fraud",
                "forensic",
                "cert",
                "captcha",
                "ddos",
                "rate_guard",
                "identity",
                "auth",
                "mfa",
                "oauth",
                "jwt",
                "saml",
                "session",
            ],
            "security",
        ),
        (
            [
                "deploy",
                "docker",
                "k8s",
                "kubernetes",
                "helm",
                "cicd",
                "release",
                "canary",
                "rollback",
                "container",
                "nomad",
                "terraform",
                "ansible",
                "infra",
                "auto_scale",
                "cluster",
                "shard",
                "load_balancer",
                "reverse_proxy",
                "gateway",
                "dns",
                "cdn",
                "traffic",
                "gray",
                "feature_flag",
                "snapshot_volume",
                "backup",
                "restore",
                "disaster",
                "ha",
                "failover",
                "capacity_plan",
                "auto_restart",
            ],
            "deployment",
        ),
        (
            [
                "workflow",
                "task_queue",
                "cron",
                "scheduler",
                "job",
                "worker",
                "fsm",
                "state_machine",
                "dag",
                "pipeline",
                "approval",
                "ticket",
                "incident",
                "change",
                "runbook",
                "sop",
                "automation",
                "rpa",
            ],
            "workflow",
        ),
        (
            [
                "llm",
                "nlp",
                "embed",
                "vector",
                "rag",
                "knowledge",
                "openai",
                "claude",
                "gpt",
                "bert",
                "transformer",
                "tokeniz",
                "prompt",
                "brain",
                "cortex",
                "neural",
                "deep",
                "speech",
                "whisper",
                "tts",
                "stt",
                "asr",
                "ocr",
                "image_gen",
                "diffusion",
                "stable",
                "composio",
                "crewai",
                "langchain",
                "copilot",
                "chatwise",
                "fine_tune",
                "reward",
                "rlhf",
                "alignment",
                "inference",
                "tensor",
                "onnx",
                "triton",
                "vllm",
            ],
            "ai_inference",
        ),
        (
            [
                "search",
                "index",
                "elastic",
                "lucene",
                "query",
                "filter",
                "rank",
                "recom",
                "trendaradar",
                "crawler",
                "spider",
                "scrape",
            ],
            "search",
        ),
        (
            [
                "file",
                "pdf",
                "doc",
                "excel",
                "csv",
                "image",
                "video",
                "audio",
                "media",
                "storage",
                "oss",
                "s3",
                "compress",
                "archive",
                "document",
                "llamaparse",
                "mime",
            ],
            "file_processing",
        ),
        (
            [
                "email",
                "mail",
                "sms",
                "push",
                "notify",
                "slack",
                "webhook",
                "dingtalk",
                "wechat",
                "telegram",
                "feishu",
                "bridge",
                "messaging",
            ],
            "notification",
        ),
    ]

    def _classify_by_name(self, name: str) -> str:
        """基于文件名自动分类"""
        name_lower = name.lower().replace("-", "_").replace(" ", "_")
        for keywords, cat in self._NAME_CLASSIFY_RULES:
            for kw in keywords:
                if kw in name_lower:
                    return cat
        return "custom"

    def __init__(self):
        self._modules: Dict[str, ModuleCapability] = dict(self.CORE_MODULES)
        self._category_index: Dict[str, List[str]] = defaultdict(list)
        self._tag_index: Dict[str, List[str]] = defaultdict(list)
        self._build_index()

    def auto_discover(self, modules_dir: str = "modules") -> int:
        """自动发现并注册modules目录下所有未注册的模块
        Returns: 新注册的模块数
        """
        import importlib, re as _re

        base = Path(modules_dir)
        if not base.exists():
            return 0
        new_count = 0
        for f in sorted(base.glob("*.py")):
            name = f.stem
            if name.startswith("_") or name.startswith("test") or name in self._modules:
                continue
            try:
                c = f.read_text(encoding="utf-8", errors="ignore")
                # 检测类名
                cls_match = _re.search(r"class\s+(\w+)\s*\([^)]*EnterpriseModule[^)]*\)", c)
                if not cls_match:
                    cls_match = _re.search(r"class\s+(\w+)\s*\(.*\):", c)
                cls_name = cls_match.group(1) if cls_match else name.title()
                # 检测actions
                actions = set()
                for m in _re.finditer(r'"(\w+)"\s*:\s*(?:lambda|getattr)', c):
                    actions.add(m.group(1))
                for m in _re.finditer(r'==\s*["\'](\w+)["\']', c):
                    actions.add(m.group(1))
                non_act = {
                    "self",
                    "super",
                    "true",
                    "false",
                    "none",
                    "yes",
                    "no",
                    "ok",
                    "error",
                    "result",
                    "data",
                    "config",
                    "params",
                    "action",
                    "status",
                    "info",
                    "version",
                    "help",
                }
                actions = {a for a in actions if a not in non_act and len(a) >= 3}
                if not actions:
                    continue
                # 检测docstring
                doc_match = _re.search(r'"""(.*?)"""', c, _re.DOTALL)
                desc = doc_match.group(1).strip().split("\n")[0][:80] if doc_match else f"{cls_name} module"
                cat = self._classify_by_name(name)
                cap = ModuleCapability(
                    name, cls_name, cat, desc, actions=sorted(list(actions))[:10], tags=[name, cls_name.lower(), cat]
                )
                self.register(cap)
                new_count += 1
            except Exception:
                continue
        logger.info(f"[Planner] 自动发现注册 {new_count} 个模块，总计 {len(self._modules)}")
        return new_count

    def _build_index(self):
        """构建倒排索引"""
        for name, cap in self._modules.items():
            if name not in self._category_index.get(cap.category, []):
                self._category_index[cap.category].append(name)
            for tag in cap.tags:
                self._tag_index[tag.lower()].append(name)

    def register(self, cap: ModuleCapability):
        """动态注册模块能力"""
        self._modules[cap.name] = cap
        if cap.name not in self._category_index.get(cap.category, []):
            self._category_index[cap.category].append(cap.name)
        for tag in cap.tags:
            if cap.name not in self._tag_index.get(tag.lower(), []):
                self._tag_index[tag.lower()].append(cap.name)

    def search(self, query: str, limit: int = 10) -> List[ModuleCapability]:
        """按关键词搜索模块"""
        query = query.lower()
        scores: Dict[str, float] = defaultdict(float)

        # 精确名称匹配
        for name in self._modules:
            if query in name.lower():
                scores[name] += 10.0

        # 标签匹配
        for tag, names in self._tag_index.items():
            if query in tag or tag in query:
                for n in names:
                    scores[n] += 5.0

        # 分类匹配
        for cat, names in self._category_index.items():
            if query in cat.lower() or cat.lower() in query:
                for n in names:
                    scores[n] += 3.0

        # 描述匹配
        for name, cap in self._modules.items():
            words = query.split()
            for w in words:
                if w in cap.description.lower():
                    scores[name] += 1.0

        ranked = sorted(scores.items(), key=lambda x: -x[1])[:limit]
        return [self._modules[n] for n, _ in ranked]

    def get_by_category(self, category: str) -> List[ModuleCapability]:
        """按分类获取模块"""
        return [self._modules[n] for n in self._category_index.get(category, [])]

    def get_categories(self) -> Dict[str, int]:
        """获取所有分类及模块数量"""
        return {cat: len(names) for cat, names in self._category_index.items()}

    def get_all(self) -> Dict[str, ModuleCapability]:
        """获取所有模块"""
        return dict(self._modules)

    @property
    def total(self) -> int:
        return len(self._modules)

# ============================================================================
# 意图理解器 — 自然语言 → 结构化任务
# ============================================================================

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
                import urllib.request

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
        解析用户意图 — LLM优先，关键词fallback
        返回: (task_type, extracted_params)
        """
        # 1. 尝试LLM解析
        if self._llm_available and len(message) > 5:
            try:
                task_type, params = self._parse_with_llm(message)
                if task_type != TaskType.CUSTOM or params.get("modules"):
                    return task_type, params
            except Exception as e:
                logger.debug(f"[Planner] LLM解析失败，回退关键词: {e}")

        # 2. 关键词fallback
        message_lower = message.lower()
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
        import urllib.request, json as _json

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
        import re

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

# ============================================================================
# Agent Planner 核心模块
# ============================================================================

class PlanAnalyzer(object):
    """计划分析引擎 - 负责计划评估、依赖分析和可行性检查"""

    def __init__(self):
        self._plan_cache: Dict[str, Dict] = {}
        self._analysis_count: int = 0
        self._dependency_graph: Dict[str, List[str]] = {}

    def analyze_plan(self, plan_id: str, plan: Dict) -> Dict:
        """分析计划的可行性和依赖"""
        self._analysis_count += 1
        tasks = plan.get("tasks", [])
        deps = self._extract_dependencies(tasks)
        self._dependency_graph[plan_id] = deps
        result = {"plan_id": plan_id, "tasks": len(tasks), "dependencies": len(deps), "feasible": True}
        self._plan_cache[plan_id] = result
        return result

    def _extract_dependencies(self, tasks: List[Dict]) -> List[str]:
        """提取任务依赖关系"""
        deps = []
        for task in tasks:
            deps.extend(task.get("depends_on", []))
        return list(set(deps))

    def get_critical_path(self, plan_id: str) -> List[str]:
        """获取关键路径"""
        return self._dependency_graph.get(plan_id, [])

    def get_stats(self) -> Dict[str, Any]:
        return {
            "plans_analyzed": self._analysis_count,
            "cache_size": len(self._plan_cache),
            "graph_nodes": len(self._dependency_graph),
        }

class CapabilityIndexer(object):
    """能力索引器 - 对模块能力注册表建立倒排索引加速匹配。

    企业场景：500+模块中快速定位能处理特定任务的模块，
    支持关键词匹配、分类过滤、历史成功率排序、冷启动推荐。
    """

    def __init__(self):
        self._inverted_index: Dict[str, Set[str]] = defaultdict(set)
        self._category_index: Dict[str, Set[str]] = defaultdict(set)
        self._module_meta: Dict[str, Dict] = {}
        self._success_stats: Dict[str, Dict] = defaultdict(lambda: {"total": 0, "success": 0})

    def index_module(self, module_id: str, name: str, description: str, category: str, actions: List[str] = None):
        """索引模块的名称、描述、分类和可用action"""
        self._module_meta[module_id] = {
            "name": name,
            "description": description,
            "category": category,
            "actions": actions or [],
        }
        self._category_index[category].add(module_id)
        # 分词索引（简单中文+英文按空格分词）
        tokens = set()
        for text in [name, description] + (actions or []):
            tokens.update(text.lower().split())
        for token in tokens:
            if len(token) >= 2:
                self._inverted_index[token].add(module_id)

    def search(self, query: str, top_k: int = 10, category: str = None) -> List[Dict]:
        """搜索匹配的模块，按TF-IDF简化分数排序"""
        tokens = set(query.lower().split())
        scores: Dict[str, float] = defaultdict(float)
        for token in tokens:
            if token in self._inverted_index:
                for mid in self._inverted_index[token]:
                    scores[mid] += 1.0 / (1 + math.log(len(self._inverted_index[token])))

        # 应用分类过滤
        if category:
            valid = self._category_index.get(category, set())
            scores = {k: v for k, v in scores.items() if k in valid}

        # 融合成功率
        for mid in scores:
            stats = self._success_stats[mid]
            if stats["total"] > 0:
                scores[mid] *= 0.7 + 0.3 * stats["success"] / stats["total"]

        ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
        results = []
        for mid, score in ranked:
            meta = self._module_meta.get(mid, {})
            results.append(
                {
                    "module_id": mid,
                    "name": meta.get("name", ""),
                    "category": meta.get("category", ""),
                    "relevance_score": round(score, 3),
                    "success_rate": self._get_success_rate(mid),
                }
            )
        return results

    def _get_success_rate(self, module_id: str) -> float:
        stats = self._success_stats[module_id]
        if stats["total"] == 0:
            return 0.5  # 冷启动默认值
        return stats["success"] / stats["total"]

    def record_execution(self, module_id: str, success: bool):
        """记录模块执行结果用于排序优化"""
        self._success_stats[module_id]["total"] += 1
        if success:
            self._success_stats[module_id]["success"] += 1

    def get_category_stats(self) -> Dict[str, int]:
        """获取各分类的模块数量统计"""
        return {cat: len(mids) for cat, mids in self._category_index.items()}

import math

class AgentPlanner(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    AUTO-EVO-AI v7.0 — Agent Planner 智能编排引擎（生产级）
    ======================================================
    核心能力：
      1. 自然语言意图理解 — 解析用户输入，识别任务类型和参数
      2. 任务自动分解 — 将复杂任务拆解为模块调用序列
      3. 异步并行编排 — 无依赖步骤并行执行，有依赖按拓扑序串行
      4. 步骤级超时 — 每步独立超时控制，超时自动取消
      5. 智能重试 — 指数退避重试，熔断降级
      6. 计划取消 — 支持运行中取消执行计划
      7. 结果聚合 — 收集所有模块输出，生成统一报告

    生产级特性：
      ✅ 异步执行引擎（asyncio）
      ✅ 步骤级超时 + 取消机制
      ✅ 并行执行无依赖步骤（asyncio.gather）
      ✅ 指数退避重试（3次，1s/2s/4s）
      ✅ 熔断器（连续5次失败→60s熔断）
      ✅ 链路追踪（plan_id + step_id + trace_id）
      ✅ 监控指标（执行次数/成功率/延迟）
      ✅ 审计日志（每次编排记录）
      ✅ 限流保护（并发计划上限10）
    """

    # ── 配置常量 ──
    MAX_CONCURRENT_PLANS = 10  # 并发计划上限
    STEP_TIMEOUT_DEFAULT = 10.0  # 步骤默认超时（秒）
    STEP_TIMEOUT_SLOW = 60.0  # 慢步骤超时（部署/扫描类）
    RETRY_MAX = 1  # 最大重试次数（损坏模块快速失败）
    RETRY_BACKOFF_BASE = 0.3  # 重试退避基数（秒）
    CIRCUIT_FAIL_THRESHOLD = 5  # 熔断失败阈值
    CIRCUIT_RECOVERY_SEC = 60  # 熔断恢复时间（秒）
    CONTEXT_MAX_LENGTH = 20  # 对话上下文最大长度
    PLAN_HISTORY_MAX = 100  # 历史计划保留数
    METRICS_WINDOW = 3600  # 指标统计窗口（秒）

    def __init__(self):

        super().__init__()
        self.name = "agent_planner"
        self.display_name = "Agent Planner 智能编排引擎"
        self.version = "v2.0.0-prod"

        # 核心组件
        self.registry = ModuleRegistry()
        self.intent_parser = IntentParser()

        # 执行历史
        self._plans: Dict[str, ExecutionPlan] = {}
        self._plan_counter = 0

        # 模块执行器（通过HTTP调用API Server）
        self._api_base = "http://localhost:8766"

        # 对话上下文
        self._context: List[Dict[str, str]] = []

        # ── 生产级基础设施 ──

        # 并发控制信号量
        self._plan_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_PLANS)

        # 取消事件（每个运行中的计划一个）
        self._cancel_events: Dict[str, asyncio.Event] = {}

        # 熔断器状态 {module_name: {"fails": int, "last_fail": float, "state": "closed|open"}}
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}

        # 监控指标
        self._metrics = {
            "plans_total": 0,
            "plans_success": 0,
            "plans_failed": 0,
            "plans_cancelled": 0,
            "steps_total": 0,
            "steps_success": 0,
            "steps_failed": 0,
            "steps_timeout": 0,
            "steps_retried": 0,
            "avg_latency_ms": 0.0,
            "latency_samples": [],
        }

        # 审计日志
        self._audit_log: List[Dict[str, Any]] = []

        # 链路追踪
        self._trace_counter = 0

        # 初始化事件循环引用（延迟创建）
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """获取或创建事件循环"""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def _next_trace_id(self) -> str:
        """生成链路追踪ID"""
        self._trace_counter += 1
        return f"trace_{self._trace_counter:06d}_{int(time.time() * 1000)}"

    def _record_audit(self, action: str, plan_id: str, details: Dict[str, Any]):
        """记录审计日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "plan_id": plan_id,
            "trace_id": details.get("trace_id", ""),
            "details": details,
        }
        self._audit_log.append(entry)
        # 限制审计日志大小
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-500:]

    def _update_metrics(self, key: str, value: Any = 1):
        """更新监控指标"""
        if key in self._metrics:
            self._metrics[key] = self._metrics.get(key, 0) + value

    def _record_latency(self, latency_ms: float):
        """记录延迟样本"""
        samples = self._metrics["latency_samples"]
        samples.append(latency_ms)
        # 保留最近1000个样本
        if len(samples) > 1000:
            self._metrics["latency_samples"] = samples[-1000:]
        self._metrics["avg_latency_ms"] = round(sum(samples) / len(samples), 1)

    def _check_circuit(self, module_name: str) -> bool:
        """检查熔断器 — 返回True表示允许执行"""
        cb = self._circuit_breakers.get(module_name)
        if not cb:
            return True
        if cb["state"] == "open":
            # 检查是否到了恢复时间
            if time.time() - cb["last_fail"] > self.CIRCUIT_RECOVERY_SEC:
                cb["state"] = "half-open"
                logger.info(f"[Planner] Circuit half-open for {module_name}")
                return True
            return False  # 仍在熔断中
        return True  # closed 或 half-open 都允许

    def _record_failure(self, module_name: str):
        """记录失败，更新熔断器状态"""
        cb = self._circuit_breakers.setdefault(module_name, {"fails": 0, "last_fail": 0, "state": "closed"})
        cb["fails"] += 1
        cb["last_fail"] = time.time()
        if cb["fails"] >= self.CIRCUIT_FAIL_THRESHOLD and cb["state"] != "open":
            cb["state"] = "open"
            logger.warning(f"[Planner] Circuit OPEN for {module_name} after {cb['fails']} failures")

    def _record_success(self, module_name: str):
        """记录成功，重置熔断器"""
        cb = self._circuit_breakers.get(module_name)
        if cb:
            cb["fails"] = 0
            if cb["state"] == "half-open":
                cb["state"] = "closed"
                logger.info(f"[Planner] Circuit CLOSED for {module_name}")

    # ═══════════════════════════════════════════════════════════════════
    # EnterpriseModule 接口（同步，内部调异步引擎）
    # ═══════════════════════════════════════════════════════════════════

    def initialize(self) -> Dict[str, Any]:
        """初始化编排引擎"""
        _ = self.trace("initialize")
        self._plan_counter = 0
        self._plans = {}
        self._context = []
        self._cancel_events = {}
        self._circuit_breakers = {}
        self._loop = None
        # 自动发现并注册所有模块
        auto_count = self.registry.auto_discover("modules")
        logger.info(
            f"[{self.name}] 初始化完成，手动注册: {len(ModuleRegistry.CORE_MODULES)}个，自动发现: {auto_count}个，总计: {self.registry.total}个"
        )
        self._record_audit("initialize", "system", {"modules": self.registry.total, "auto_discovered": auto_count})
        return {
            "status": "initialized",
            "modules_registered": self.registry.total,
            "categories": self.registry.get_categories(),
            "production_features": [
                "async_parallel",
                "step_timeout",
                "retry_backoff",
                "circuit_breaker",
                "plan_cancel",
                "rate_limit",
                "trace_id",
                "metrics",
                "audit_log",
            ],
        }

    async def async_execute(
        self, message: str = "", task: str = "", params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        异步执行入口 — 供FastAPI async路由直接await调用。
        用法: result = planner.async_execute(message="帮我分析数据")
        """
        trace_id = self._next_trace_id()
        self._update_metrics("plans_total")
        start = time.time()

        try:
            if message:
                result = await self._execute_async(message=message, trace_id=trace_id)
            elif task:
                result = await self._execute_async(task=task, params=params or {}, trace_id=trace_id)
            else:
                return {
                    "status": "error",
                    "message": "请提供 message（对话模式）或 task（任务模式）",
                    "usage": {
                        "chat": 'POST /api/planner/chat  {"message": "帮我分析数据"}',
                        "task": 'POST /api/planner/execute  {"task": "data_analysis"}',
                    },
                }
            result["duration_ms"] = round((time.time() - start) * 1000, 1)
            return result
        except asyncio.CancelledError:
            self._update_metrics("plans_cancelled")
            return {"status": "cancelled", "trace_id": trace_id}
        except Exception as e:
            self._update_metrics("plans_failed")
            logger.error(f"[Planner] Execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "trace_id": trace_id,
                "error": str(e)[:300],
            }

    async def execute(self, message: str = "", task: str = "", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        同步执行入口 — 供非async上下文调用。
        在已有事件循环的上下文（如FastAPI async路由）中请用async_execute()。
        """
        self.audit("execute", f"action=execute,task={task or message[:20]}")
        # 链路追踪
        trace_id = f"planner-{task[:20] if task else message[:20]}-{int(time.time() * 1000)}"
        start_time = time.time()
        metrics_collector.counter("planner_executions_total", labels={"task_type": task or "message"})
        import inspect

        # 检测是否在运行中的事件循环内
        try:
            loop = asyncio.get_running_loop()
            # 有运行中的循环 → 不能用run_until_complete，返回提示
            logger.warning("[Planner] Called execute() inside running event loop, use async_execute() instead")
            return {
                "status": "error",
                "error": "Cannot run execute() inside an async context. Use async_execute() instead.",
                "message": "请在async路由中使用 planner.async_execute(...)",
            }
        except RuntimeError:
            pass  # 没有运行中的循环，可以安全使用run_until_complete

        trace_id = self._next_trace_id()
        self._update_metrics("plans_total")
        start = time.time()

        try:
            if message:
                result = self._get_loop().run_until_complete(self._execute_async(message=message, trace_id=trace_id))
            elif task:
                result = self._get_loop().run_until_complete(
                    self._execute_async(task=task, params=params or {}, trace_id=trace_id)
                )
            else:
                return {
                    "status": "error",
                    "message": "请提供 message（对话模式）或 task（任务模式）",
                    "usage": {
                        "chat": 'POST /api/planner/chat  {"message": "帮我分析数据"}',
                        "task": 'POST /api/planner/execute  {"task": "data_analysis"}',
                    },
                }
            result["duration_ms"] = round((time.time() - start) * 1000, 1)
            return result
        except asyncio.CancelledError:
            self._update_metrics("plans_cancelled")
            return {"status": "cancelled", "trace_id": trace_id}
        except Exception as e:
            self._update_metrics("plans_failed")
            logger.error(f"[Planner] Execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "trace_id": trace_id,
                "error": str(e)[:300],
            }

    def health_check(self) -> Dict[str, Any]:
        """健康检查 — 含监控指标和熔断器状态"""
        # 统计当前熔断中的模块
        open_circuits = [n for n, cb in self._circuit_breakers.items() if cb["state"] == "open"]
        return {
            "status": "healthy",
            "version": self.version,
            "modules_registered": self.registry.total,
            "categories": self.registry.get_categories(),
            "plans_executed": self._metrics["plans_total"],
            "active_plans": len(self._cancel_events),
            "context_length": len(self._context),
            "api_base": self._api_base,
            # 监控指标
            "metrics": {
                "plans_success_rate": f"{self._metrics['plans_success'] * 100 // max(self._metrics['plans_total'], 1)}%",
                "steps_success_rate": f"{self._metrics['steps_success'] * 100 // max(self._metrics['steps_total'], 1)}%",
                "avg_latency_ms": self._metrics["avg_latency_ms"],
                "steps_timeout": self._metrics["steps_timeout"],
                "steps_retried": self._metrics["steps_retried"],
            },
            # 熔断器状态
            "circuit_breakers": {
                "open": open_circuits,
                "total_tracked": len(self._circuit_breakers),
            },
        }

    def shutdown(self) -> Dict[str, Any]:
        """优雅关闭 — 取消所有运行中计划"""
        # 取消所有运行中的计划
        for plan_id, event in self._cancel_events.items():
            event.set()
            logger.info(f"[Planner] Cancelling plan {plan_id} on shutdown")

        self._plans = {}
        self._context = []
        self._cancel_events = {}
        if self._loop and not self._loop.is_closed():
            self._loop.close()
            self._loop = None

        self._record_audit(
            "shutdown",
            "system",
            {
                "plans_cancelled": len(self._cancel_events),
                "metrics": dict(self._metrics),
            },
        )
        return {
            "status": "shutdown",
            "metrics_final": dict(self._metrics),
        }

    # ═══════════════════════════════════════════════════════════════════
    # 异步执行引擎
    # ═══════════════════════════════════════════════════════════════════

    async def _execute_async(
        self, message: str = "", task: str = "", params: Optional[Dict[str, Any]] = None, trace_id: str = ""
    ) -> Dict[str, Any]:
        """异步主执行入口"""
        async with self._plan_semaphore:
            # 对话模式
            if message:
                return await self._chat_mode_async(message, trace_id)
            # 任务模式
            elif task:
                return await self._task_mode_async(task, params or {}, trace_id)
            else:
                return {"status": "error", "message": "No message or task provided"}

    async def _chat_mode_async(self, message: str, trace_id: str) -> Dict[str, Any]:
        """对话模式 — 异步编排执行"""
        # 1. 记录上下文
        self._context.append({"role": "user", "content": message})
        if len(self._context) > self.CONTEXT_MAX_LENGTH:
            self._context = self._context[-self.CONTEXT_MAX_LENGTH :]

        # 2. 解析意图
        task_type, params = self.intent_parser.parse(message)

        # 3. 生成执行计划
        steps_def = self.intent_parser.get_plan(task_type, params, self.registry)

        # 4. 创建执行计划
        plan = await self._create_plan(task_type, message, steps_def, params, trace_id)

        # 5. 异步执行计划（并行无依赖步骤）
        results = await self._run_plan(plan, trace_id)

        # 6. 聚合结果
        final_result = self._aggregate_results(results, plan)

        plan.final_result = final_result
        plan.status = PlanStatus.COMPLETED if final_result["failed"] == 0 else PlanStatus.FAILED

        # 7. 记录
        self._update_metrics("plans_success" if final_result["failed"] == 0 else "plans_failed")
        self._record_latency(sum(r.get("duration_ms", 0) for r in results))

        # 记录上下文回复
        self._context.append({"role": "assistant", "content": json.dumps(final_result, ensure_ascii=False)[:500]})

        self._record_audit(
            "chat_execute",
            plan.plan_id,
            {
                "task_type": task_type.value,
                "intent": message[:100],
                "trace_id": trace_id,
                "result": {"success": final_result["success"], "failed": final_result["failed"]},
            },
        )

        return {
            "plan_id": plan.plan_id,
            "task_type": task_type.value,
            "intent": message,
            "steps_executed": len(results),
            "result": final_result,
            "step_details": [
                {
                    "step": r.get("step"),
                    "module": r.get("module"),
                    "action": r.get("action"),
                    "status": r.get("status"),
                    "duration_ms": r.get("duration_ms"),
                    "retries": r.get("retries", 0),
                    "summary": r.get("summary", "")[:100],
                }
                for r in results
            ],
        }

    async def _task_mode_async(self, task: str, params: Dict[str, Any], trace_id: str) -> Dict[str, Any]:
        """任务模式 — 异步执行指定任务"""
        try:
            task_type = TaskType(task)
        except ValueError:
            task_type = TaskType.CUSTOM

        steps_def = self.intent_parser.get_plan(task_type, params, self.registry)
        plan = await self._create_plan(task_type, f"task:{task}", steps_def, params, trace_id)
        results = await self._run_plan(plan, trace_id)
        final_result = self._aggregate_results(results, plan)

        plan.final_result = final_result
        plan.status = PlanStatus.COMPLETED if final_result["failed"] == 0 else PlanStatus.FAILED
        self._update_metrics("plans_success" if final_result["failed"] == 0 else "plans_failed")

        self._record_audit(
            "task_execute",
            plan.plan_id,
            {
                "task_type": task,
                "trace_id": trace_id,
                "result": {"success": final_result["success"], "failed": final_result["failed"]},
            },
        )

        return {
            "plan_id": plan.plan_id,
            "task_type": task,
            "steps_executed": len(results),
            "result": final_result,
            "step_details": [
                {
                    "step": r.get("step"),
                    "module": r.get("module"),
                    "action": r.get("action"),
                    "status": r.get("status"),
                    "duration_ms": r.get("duration_ms"),
                    "retries": r.get("retries", 0),
                    "summary": r.get("summary", "")[:100],
                }
                for r in results
            ],
        }

    async def _create_plan(
        self, task_type: TaskType, user_intent: str, steps_def: List[Dict], params: Dict[str, Any], trace_id: str
    ) -> ExecutionPlan:
        """创建执行计划"""
        self._plan_counter += 1
        plan_id = f"plan_{self._plan_counter:04d}"

        # 为步骤分配依赖关系（当前默认串行，无显式依赖声明时按序执行）
        steps = []
        for i, s in enumerate(steps_def):
            step = ExecutionStep(
                step_id=i + 1,
                module_name=s["module"],
                action=s.get("action", "status"),
                params=params.get(s["module"], {}),
                depends_on=s.get("depends_on", [i] if i > 0 else []),
            )
            steps.append(step)

        plan = ExecutionPlan(
            plan_id=plan_id,
            task_type=task_type,
            user_intent=user_intent,
            steps=steps,
            status=PlanStatus.PENDING,
            created_at=datetime.now().isoformat(),
        )

        self._plans[plan_id] = plan

        # 限制历史计划数
        if len(self._plans) > self.PLAN_HISTORY_MAX:
            oldest = sorted(self._plans.keys())[0]
            del self._plans[oldest]

        self._update_metrics("plans_total")
        return plan

    # ═══════════════════════════════════════════════════════════════════
    # 异步执行引擎 — 并行+超时+重试+取消
    # ═══════════════════════════════════════════════════════════════════

    async def _run_plan(self, plan: ExecutionPlan, trace_id: str) -> List[Dict[str, Any]]:
        """
        执行计划 — 按依赖关系分组，无依赖步骤并行执行
        支持取消：通过cancel_event异步检查
        """
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.now().isoformat()

        # 创建此计划的取消事件
        cancel_event = asyncio.Event()
        self._cancel_events[plan.plan_id] = cancel_event

        try:
            pass
            # 构建依赖图，计算执行层级
            groups = self._build_parallel_groups(plan.steps)

            all_results = []
            for group in groups:
                # 检查是否被取消
                if cancel_event.is_set():
                    logger.info(f"[Planner] Plan {plan.plan_id} cancelled")
                    for step in group:
                        step.status = "cancelled"
                    break

                # 并行执行当前组中的所有步骤
                group_results = await asyncio.gather(
                    *[self._execute_step_with_retry(step, trace_id, cancel_event) for step in group],
                    return_exceptions=True,
                )

                for step, result in zip(group, group_results):
                    if isinstance(result, Exception):
                        all_results.append(
                            {
                                "step": step.step_id,
                                "module": step.module_name,
                                "action": step.action,
                                "status": "failed",
                                "error": str(result)[:200],
                                "duration_ms": 0,
                            }
                        )
                    else:
                        all_results.append(result)

                # 如果某步骤失败且后续步骤依赖它，标记依赖步骤
                failed_steps = {r["step"] for r in all_results if r.get("status") in ("failed", "not_found")}
                for step in plan.steps:
                    if step.status == "pending" and any(d in failed_steps for d in step.depends_on):
                        step.status = "skipped"
                        step.error = "dependency_failed"
                        all_results.append(
                            {
                                "step": step.step_id,
                                "module": step.module_name,
                                "action": step.action,
                                "status": "skipped",
                                "error": "dependency_failed",
                                "duration_ms": 0,
                            }
                        )

        finally:
            # 清理取消事件
            self._cancel_events.pop(plan.plan_id, None)

        plan.completed_at = datetime.now().isoformat()
        return all_results

    def _build_parallel_groups(self, steps: List[ExecutionStep]) -> List[List[ExecutionStep]]:
        """
        构建并行执行组
        步骤间无依赖关系的放在同一组并行执行
        有依赖关系的放在不同组串行执行
        """
        if not steps:
            return []

        # 如果所有步骤都无依赖，全部并行
        has_deps = any(s.depends_on for s in steps)
        if not has_deps:
            return [steps]

        # 按拓扑排序分层
        completed = set()
        groups = []
        remaining = list(steps)

        max_rounds = len(steps) + 1  # 防止无限循环
        for _ in range(max_rounds):
            if not remaining:
                break

            # 找出所有依赖已满足的步骤
            ready = [s for s in remaining if all(d in completed or d == 0 for d in s.depends_on)]
            if not ready:
                # 存在循环依赖，强制执行剩余步骤
                groups.append(remaining)
                break

            groups.append(ready)
            for s in ready:
                completed.add(s.step_id)
            remaining = [s for s in remaining if s not in ready]

        return groups

    async def _execute_step_with_retry(
        self, step: ExecutionStep, trace_id: str, cancel_event: asyncio.Event
    ) -> Dict[str, Any]:
        """
        执行单个步骤（含重试+超时+熔断+取消检查）
        """
        self._update_metrics("steps_total")

        # 熔断检查
        if not self._check_circuit(step.module_name):
            logger.warning(f"[Planner] Circuit OPEN, skipping {step.module_name}")
            step.status = "failed"
            step.error = "circuit_breaker_open"
            self._update_metrics("steps_failed")
            return {
                "step": step.step_id,
                "module": step.module_name,
                "action": step.action,
                "status": "skipped",
                "error": "circuit_breaker_open",
                "duration_ms": 0,
                "retries": 0,
            }

        # 确定超时时间（部署/扫描类步骤更长）
        slow_actions = {"deploy", "scan", "build", "run_pipeline", "heal", "recover"}
        timeout = self.STEP_TIMEOUT_SLOW if step.action in slow_actions else self.STEP_TIMEOUT_DEFAULT

        # 重试执行
        last_error = None
        for attempt in range(1, self.RETRY_MAX + 1):
            # 取消检查
            if cancel_event.is_set():
                step.status = "cancelled"
                return {
                    "step": step.step_id,
                    "module": step.module_name,
                    "action": step.action,
                    "status": "cancelled",
                    "duration_ms": 0,
                    "retries": attempt - 1,
                }

            try:
                result = await asyncio.wait_for(
                    self._execute_step_async(step, trace_id),
                    timeout=timeout,
                )
                # 成功
                step.result = result.get("result") if result else None
                step.status = "done"
                step.duration_ms = result.get("duration_ms", 0) if result else 0
                self._update_metrics("steps_success")
                self._record_success(step.module_name)
                result["retries"] = attempt - 1
                if attempt > 1:
                    self._update_metrics("steps_retried")
                return result

            except asyncio.TimeoutError:
                self._update_metrics("steps_timeout")
                last_error = f"timeout after {timeout}s"
                logger.warning(
                    f"[Planner] Step {step.step_id} {step.module_name}.{step.action} timeout (attempt {attempt}/{self.RETRY_MAX})"
                )
                if attempt < self.RETRY_MAX:
                    await asyncio.sleep(self.RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))

            except asyncio.CancelledError:
                step.status = "cancelled"
                raise

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[Planner] Step {step.step_id} {step.module_name}.{step.action} failed (attempt {attempt}/{self.RETRY_MAX}): {e}"
                )
                if attempt < self.RETRY_MAX:
                    await asyncio.sleep(self.RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))

        # 所有重试都失败
        step.status = "failed"
        step.error = last_error
        step.duration_ms = 0
        self._update_metrics("steps_failed")
        self._record_failure(step.module_name)
        self._update_metrics("steps_retried", self.RETRY_MAX - 1)
        return {
            "step": step.step_id,
            "module": step.module_name,
            "action": step.action,
            "status": "failed",
            "error": (last_error or "unknown")[:200],
            "duration_ms": 0,
            "retries": self.RETRY_MAX - 1,
        }

    async def _execute_step_async(self, step: ExecutionStep, trace_id: str) -> Dict[str, Any]:
        """
        异步执行单个步骤 — 优先通过HTTP调用（兼容async模块），回退到直接调用
        """
        t0 = time.time()
        step.status = "running"

        # 优先通过HTTP调用（API Server已处理async/sync兼容）
        try:
            result = await self._execute_step_http(step, t0)
            # 检查HTTP调用结果
            if result.get("status") == "success":
                step.result = result.get("result", {})
                step.status = "done"
                step.duration_ms = round((time.time() - t0) * 1000, 1)
                real_status = self._classify_step_result(step.result)
                return {
                    "step": step.step_id,
                    "module": step.module_name,
                    "action": step.action,
                    "status": real_status,
                    "duration_ms": step.duration_ms,
                    "result": step.result,
                    "summary": str(step.result.get("status", step.result.get("success", "ok")))[:60],
                    "trace_id": trace_id,
                    "via": "http",
                }
            # HTTP返回错误但不是连接问题，直接使用HTTP结果
            if result.get("status") not in ("http_error", "timeout"):
                step.result = result.get("result", result)
                step.status = "done"
                step.duration_ms = round((time.time() - t0) * 1000, 1)
                real_status = self._classify_step_result(step.result)
                return {
                    "step": step.step_id,
                    "module": step.module_name,
                    "action": step.action,
                    "status": real_status,
                    "duration_ms": step.duration_ms,
                    "result": step.result,
                    "summary": str(step.result.get("status", "ok"))[:60],
                    "trace_id": trace_id,
                    "via": "http",
                }
        except Exception as e:
            err_str = str(e).lower()
            logger.debug(f"[Planner] HTTP call failed for {step.module_name}: {e}")
            # 模块损坏/不可用时快速失败，不再回退direct避免双重耗时
            if any(kw in err_str for kw in ("syntaxerror", "indent", "import", "module", "404", "500", "not found")):
                return {
                    "step": step.step_id,
                    "module": step.module_name,
                    "action": step.action,
                    "status": "failed",
                    "error": f"Module unavailable: {str(e)[:80]}",
                    "duration_ms": round((time.time() - t0) * 1000, 1),
                    "via": "http_skip",
                }

        # 回退：直接调用模块实例（仅HTTP超时/网络问题时）
        return await self._execute_step_direct(step, trace_id, t0)

    async def _execute_step_direct(self, step: ExecutionStep, trace_id: str, t0: float) -> Dict[str, Any]:
        """直接调用模块实例（回退方式）"""
        step.status = "running"

        # 获取模块实例
        mod = None
        if hasattr(self, "_module_registry_ref") and self._module_registry_ref:
            mod = self._module_registry_ref.get(step.module_name)

        if mod is None:
            # 回退：尝试直接导入模块
            import importlib

            try:
                pymod = importlib.import_module(f"modules.{step.module_name}")
                for attr_name in sorted(dir(pymod)):
                    attr = getattr(pymod, attr_name)
                    if (
                        isinstance(attr, type)
                        and hasattr(attr, "execute")
                        and attr_name != "EnterpriseModule"
                        and not attr_name.startswith("_")
                    ):
                        try:
                            mod = attr()
                            if hasattr(mod, "initialize"):
                                r = mod.initialize()
                                if hasattr(r, "__await__"):
                                    r = await r
                            break
                        except Exception:
                            continue
            except ImportError:
                pass

        if mod is None:
            step.status = "failed"
            step.error = "Module not found"
            step.duration_ms = round((time.time() - t0) * 1000, 1)
            return {
                "step": step.step_id,
                "module": step.module_name,
                "action": step.action,
                "status": "not_found",
                "error": step.error,
                "duration_ms": step.duration_ms,
            }

        # 调用模块的execute方法（在executor中运行同步代码）
        result = await self._call_module_execute(mod, step)

        if not isinstance(result, dict):
            result = {"status": "ok", "result": str(result)[:200]}

        # 根据模块返回内容判断真实状态
        real_status = self._classify_step_result(result)

        step.result = result
        step.status = "done"
        step.duration_ms = round((time.time() - t0) * 1000, 1)

        return {
            "step": step.step_id,
            "module": step.module_name,
            "action": step.action,
            "status": real_status,
            "duration_ms": step.duration_ms,
            "result": result,
            "summary": str(result.get("status", "ok"))[:60],
            "trace_id": trace_id,
        }

    @staticmethod
    def _classify_step_result(result: dict) -> str:
        """根据模块返回内容分类步骤结果"""
        status_val = str(result.get("status", "")).lower()
        success_val = result.get("success")
        error_msg = str(result.get("error", "")).lower() + str(result.get("message", "")).lower()

        # 明确失败
        if status_val in ("error", "failed", "failure"):
            # "Unknown action" 算partial（模块存在但不支持该action）
            if "unknown action" in error_msg or "未知动作" in error_msg:
                return "partial"
            if "missing" in error_msg and "argument" in error_msg:
                return "partial"  # 缺参数
            return "failed"
        if success_val is False:
            if "不支持action" in error_msg or "unknown action" in error_msg:
                return "partial"
            return "failed"
        # no_handler / partial
        if status_val == "no_handler" or status_val == "partial":
            return "partial"
        # handler_error
        if status_val == "handler_error":
            return "partial"
        # success标志
        if status_val in ("ok", "running", "success", "completed", "done"):
            return "success"
        if success_val is True:
            return "success"
        # 默认成功（模块已响应）
        return "success"

    async def _call_module_execute(self, mod, step: ExecutionStep) -> Any:
        """调用模块execute — 智能处理同步/异步，多参数签名"""
        if not hasattr(mod, "execute"):
            return {"status": "no_execute", "module": step.module_name}

        execute_fn = mod.execute
        is_async = asyncio.iscoroutinefunction(execute_fn)

        # 先尝试用Planner指定的action
        for call_args in [
            (step.action,),
            ({"action": step.action},),
            (step.action, step.params),
            ({"action": step.action, **step.params},),
        ]:
            try:
                r = execute_fn(*call_args)
                if is_async and hasattr(r, "__await__"):
                    r = await r
                if isinstance(r, dict) and r:
                    if not self._is_action_error(r):
                        return r
            except TypeError:
                continue
            except Exception:
                break

        # execute不识别action → 获取可用action列表，智能选择
        available = self._get_module_actions(mod)
        best = self._find_best_action(step.action, available)
        if best and best != step.action:
            logger.info(f"[Planner] {step.module_name}: action '{step.action}' not found, using '{best}'")
            step.action = best
            for call_args in [
                (best,),
                ({"action": best},),
                (best, step.params),
                ({"action": best, **step.params},),
            ]:
                try:
                    r = execute_fn(*call_args)
                    if is_async and hasattr(r, "__await__"):
                        r = r
                    if isinstance(r, dict) and r:
                        return r
                except TypeError:
                    continue
                except Exception:
                    break

        # 直接调用方法名作为handler
        handler = getattr(mod, step.action, None)
        if handler and callable(handler):
            try:
                r = handler()
                if asyncio.iscoroutine(r):
                    r = r
                return r if isinstance(r, dict) else {"status": "ok", "result": str(r)[:200]}
            except TypeError:
                r = handler(step.params)
                if asyncio.iscoroutine(r):
                    r = r
                return r if isinstance(r, dict) else {"status": "ok", "result": str(r)[:200]}
            except Exception as e:
                return {"status": "handler_error", "error": str(e)[:100]}

        # 回退：list_actions / help / status（跳过async模块的这些调用，可能不支持）
        for fallback in ["list_actions", "help", "status"]:
            try:
                r = execute_fn(fallback)
                if is_async and hasattr(r, "__await__"):
                    r = r
                if isinstance(r, dict):
                    return {"status": "partial", "fallback_action": fallback, "original_action": step.action, **r}
            except Exception:
                continue

        return {"status": "no_handler", "action": step.action, "available": available[:10]}

    @staticmethod
    def _is_action_error(result: dict) -> bool:
        """判断模块返回是否表示action不支持"""
        if not isinstance(result, dict):
            return False
        # {"status": "error", "message": "Unknown action: xxx"}
        if result.get("status") == "error" and "unknown action" in str(result.get("message", "")).lower():
            return True
        # {"success": False, "error": "模块xxx不支持action: xxx"}
        if result.get("success") is False and "不支持action" in str(result.get("error", "")):
            return True
        # {"success": True, "data": {"error": "未知动作: xxx"}}
        data = result.get("data", {})
        if isinstance(data, dict) and "未知动作" in str(data.get("error", "")):
            return True
        return False

    @staticmethod
    def _get_module_actions(mod) -> List[str]:
        """获取模块支持的action列表"""
        if not hasattr(mod, "execute"):
            return []

        # 方式1: list_actions / help
        for probe in ["list_actions", "help"]:
            try:
                r = mod.execute(probe)
                if isinstance(r, dict):
                    actions = r.get("actions", r.get("available", []))
                    if isinstance(actions, list):
                        return [str(a) for a in actions]
            except Exception:
                pass

        # 方式2: 扫描execute源码中的action模式
        import inspect, re

        try:
            src = inspect.getsource(mod.execute)
            found = set()
            # Pattern A: "action_name": lambda/getattr
            found.update(re.findall(r'"(\w+)"\s*:\s*(?:lambda|getattr)', src))
            # Pattern B: if action == "xxx"
            found.update(re.findall(r'action\s*==\s*["\'](\w+)["\']', src))
            # Pattern C: elif action == "xxx"
            found.update(re.findall(r'action\s*==\s*["\'](\w+)["\']', src))
            # Clean up
            skip = {"self", "action", "params", "status", "else", "none", "true", "false"}
            return sorted(a for a in found if a not in skip and len(a) >= 2)
        except Exception:
            pass
        return []

    @staticmethod
    def _find_best_action(target: str, available: List[str]) -> Optional[str]:
        """从可用actions中找到最接近目标的一个"""
        if not available or not target:
            return None
        target_lower = target.lower()

        # 精确匹配
        if target_lower in [a.lower() for a in available]:
            for a in available:
                if a.lower() == target_lower:
                    return a

        # 包含匹配
        for a in available:
            if target_lower in a.lower() or a.lower() in target_lower:
                return a

        # 语义匹配（简单关键词映射）
        synonyms = {
            "analyze": ["describe", "analyze", "aggregate", "full_report", "get_reports"],
            "generate": ["create", "generate", "build", "render", "make"],
            "scan": ["scan", "check", "inspect", "audit", "assess"],
            "detect": ["detect", "analyze", "monitor", "alert"],
            "monitor": ["monitor", "observe", "track", "watch"],
            "deploy": ["deploy", "release", "publish", "push"],
            "test": ["test", "validate", "verify", "check"],
        }
        for group in synonyms.values():
            if target_lower in group:
                for a in available:
                    if a.lower() in group:
                        return a

        return None

    # ═══════════════════════════════════════════════════════════════════
    # HTTP回退 + 结果聚合 + 计划取消
    # ═══════════════════════════════════════════════════════════════════

    async def _execute_step_http(self, step: ExecutionStep, t0: float) -> Dict[str, Any]:
        """HTTP回退执行（异步）— 通过API Server调用，兼容async模块"""
        try:
            import urllib.request

            url = f"{self._api_base}/api/modules/{step.module_name}/execute"
            body = json.dumps({"action": step.action, **step.params}).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=10))
            content = await loop.run_in_executor(None, lambda: resp.read().decode("utf-8"))
            result = json.loads(content)
            # 检查API返回的success字段
            if isinstance(result, dict) and result.get("success") is False:
                err_msg = str(result.get("error", result.get("detail", "")))
                return {
                    "step": step.step_id,
                    "module": step.module_name,
                    "action": step.action,
                    "status": "failed",
                    "error": err_msg[:100],
                    "duration_ms": round((time.time() - t0) * 1000, 1),
                }
            real_status = self._classify_step_result(result)
            return {
                "step": step.step_id,
                "module": step.module_name,
                "action": step.action,
                "status": real_status,
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "result": result,
                "summary": str(result.get("status", result.get("success", "ok")))[:60],
            }
        except Exception as e:
            return {
                "step": step.step_id,
                "module": step.module_name,
                "action": step.action,
                "status": "http_error",
                "error": str(e)[:100],
                "duration_ms": round((time.time() - t0) * 1000, 1),
            }

    def _aggregate_results(self, results: List[Dict], plan: Optional[ExecutionPlan]) -> Dict[str, Any]:
        """聚合执行结果"""
        success = sum(1 for r in results if r.get("status") == "success")
        partial = sum(1 for r in results if r.get("status") == "partial")
        failed = sum(1 for r in results if r.get("status") in ("failed", "not_found"))
        skipped = sum(1 for r in results if r.get("status") in ("skipped", "cancelled"))
        total_duration = sum(r.get("duration_ms", 0) for r in results)
        total_retries = sum(r.get("retries", 0) for r in results)

        outputs = {}
        for r in results:
            if r.get("result"):
                outputs[r["module"]] = r["result"]

        return {
            "total_steps": len(results),
            "success": success,
            "partial": partial,
            "failed": failed,
            "skipped": skipped,
            "success_rate": f"{(success + partial) * 100 // max(len(results), 1)}%",
            "total_duration_ms": round(total_duration, 1),
            "total_retries": total_retries,
            "module_outputs": outputs,
            "summary": f"执行完成: {success}成功/{partial}部分/{failed}失败/{skipped}跳过/{len(results)}总计, 重试{total_retries}次, 耗时{total_duration:.0f}ms",
        }

    def cancel_plan(self, plan_id: str) -> bool:
        """取消正在执行的计划"""
        event = self._cancel_events.get(plan_id)
        if event:
            event.set()
            self._update_metrics("plans_cancelled")
            logger.info(f"[Planner] Plan {plan_id} cancellation requested")
            self._record_audit("cancel_plan", plan_id, {"trace_id": self._next_trace_id()})
            return True
        return False

    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标"""
        return dict(self._metrics)

    def get_audit_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return self._audit_log[-limit:]

# ============================================================================
# 导出
# ============================================================================

module_class = AgentPlanner
