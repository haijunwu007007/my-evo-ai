"""Agent Planner - 模块注册表"""
import time, logging, json, uuid, hashlib
from modules._base.planner_types import TaskType, ModuleCapability, ExecutionStep
from collections import defaultdict, OrderedDict
from typing import Any, Dict, List, Optional, Tuple, Set
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
        self._modules: dict[str, ModuleCapability] = dict(self.CORE_MODULES)
        self._category_index: dict[str, list[str]] = defaultdict(list)
        self._tag_index: dict[str, list[str]] = defaultdict(list)
        self._build_index()

    def auto_discover(self, modules_dir: str = "modules") -> int:
        """自动发现并注册modules目录下所有未注册的模块
        Returns: 新注册的模块数
        """

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

    def search(self, query: str, limit: int = 10) -> list[ModuleCapability]:
        """按关键词搜索模块"""
        query = query.lower()
        scores: dict[str, float] = defaultdict(float)

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

    def get_by_category(self, category: str) -> list[ModuleCapability]:
        """按分类获取模块"""
        return [self._modules[n] for n in self._category_index.get(category, [])]

    def get_categories(self) -> dict[str, int]:
        """获取所有分类及模块数量"""
        return {cat: len(names) for cat, names in self._category_index.items()}

    def get_all(self) -> dict[str, ModuleCapability]:
        """获取所有模块"""
        return dict(self._modules)

    @property
    def total(self) -> int:
        return len(self._modules)

