# 原 system_coordinator_v3.py L1210-3043 — 跨模块编排器
"""跨模块编排器"""
import logging, time, re, os, sys, math, asyncio
import threading, importlib, inspect
from typing import Dict, Any, Optional, List, Set
from collections.abc import Callable
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector
logger = logging.getLogger("evo.coordinator.v3")

class CrossModuleOrchestrator:
    """
    跨模块编排引擎 v3.0
    自动分析任务需求，组合多个模块形成执行链
    """

    def __init__(self, coordinator, capability_graph: ModuleCapabilityGraph):
        self.coordinator = coordinator
        self.graph = capability_graph
        self._execution_chains: dict[str, list[str]] = {}  # task_pattern -> [module_ids]
        self._chain_stats: dict[str, dict] = defaultdict(lambda: {"success": 0, "fail": 0})

    def build_chain(self, task: str) -> list[dict]:
        """
        为任务构建执行链
        返回: [{"module": id, "method": str, "params": dict}, ...]
        """
        task_lower = task.lower()
        chain = []

        # 预定义的任务模式 — 选最具体的匹配（关键词最长匹配优先）
        patterns = self._get_task_patterns()
        matched_pattern = None
        best_match_name = None
        best_match_score = 0
        for pattern_name, pattern_info in patterns.items():
            matched_keywords = [kw for kw in pattern_info["keywords"] if kw in task_lower]
            if matched_keywords:
                # 评分: 匹配关键词中最长的长度 + 匹配数量
                score = max(len(kw) for kw in matched_keywords) + len(matched_keywords) * 0.1
                if score > best_match_score:
                    best_match_score = score
                    best_match_name = pattern_name
        if best_match_name:
            chain = self._build_chain_from_pattern(patterns[best_match_name], task)
            matched_pattern = best_match_name

        # 如果没有匹配模式，动态构建（仅在任务与系统领域能力相关时）
        if not chain:
            needed_steps = self._analyze_task_capabilities(task)
            if needed_steps:
                chain = self._build_chain_from_capabilities(needed_steps, task)

        return chain

    def _get_task_patterns(self) -> dict:
        """获取预定义的任务模式"""
        return {
            "financial_analysis": {
                "keywords": ["股票分析", "基金分析", "金融分析", "投资分析", "stock analysis", "fund analysis"],
                "chain": [
                    {"capability": "read", "module_hint": "stock_api", "method": "analyze", "params_from": "task"},
                    {"capability": "analyze", "module_hint": "ai_gateway", "method": "analyze", "params_from": "task"},
                ],
            },
            "data_pipeline": {
                "keywords": ["数据处理", "ETL", "数据清洗", "data pipeline", "etl"],
                "chain": [
                    {"capability": "read", "module_hint": "data_pipeline", "method": "analyze", "params_from": "task"},
                    {
                        "capability": "analyze",
                        "module_hint": "data_pipeline",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "code_generation": {
                "keywords": ["生成代码", "创建项目", "code generation", "generate code", "create project"],
                "chain": [
                    {
                        "capability": "generate",
                        "module_hint": "open_lovable",
                        "method": "generate_code",
                        "params_from": "task",
                    },
                ],
            },
            "system_monitor": {
                "keywords": ["系统监控", "健康检查", "monitor system", "health check", "system status"],
                "chain": [
                    {"capability": "health", "module_hint": "perf_monitor", "method": "status", "params": {}},
                ],
            },
            "memory_consolidation": {
                "keywords": ["整理记忆", "记忆整合", "consolidate memory", "memory cleanup"],
                "chain": [
                    {"capability": "read", "module_hint": "second_brain", "method": "analyze", "params": {}},
                ],
            },
            "github_trending": {
                "keywords": [
                    "github trending",
                    "github热门",
                    "开源项目",
                    "AI项目",
                    "trending",
                    "github scanner",
                    "github scan",
                    "趋势项目",
                    "潜力项目",
                    "热门开源",
                    "流行项目",
                    "热门ai",
                    "ai开源",
                    "AI开源",
                    "开源",
                    "github",
                    "查询开源",
                    "有潜力",
                    "今天ai",
                    "今天热门",
                    "查询ai",
                    "ai项目",
                    "开源推荐",
                    "开源工具",
                    "开源框架",
                ],
                "chain": [
                    {
                        "capability": "scan",
                        "module_hint": "github_scanner",
                        "method": "fetch_trending",
                        "params_from": "task",
                    },
                ],
            },
            "web_scrape": {
                "keywords": [
                    "网页抓取",
                    "网页采集",
                    "网页数据",
                    "web scrape",
                    "web crawl",
                    "爬取网页",
                    "采集数据",
                    "抓取数据",
                    "网页内容",
                    "页面数据",
                    "scrape",
                    "crawl",
                ],
                "chain": [
                    {
                        "capability": "scan",
                        "module_hint": "web_scraper",
                        "method": "quick_scrape",
                        "params_from": "task",
                    },
                ],
            },
            "search_info": {
                "keywords": [
                    "搜索信息",
                    "查找信息",
                    "查询信息",
                    "look up",
                    "find info",
                    "找资料",
                    "搜索信息",
                    "search info",
                ],
                "chain": [
                    {"capability": "scan", "module_hint": "ai_gateway", "method": "analyze", "params_from": "task"},
                ],
            },
            "search": {
                "keywords": ["search for", "搜索", "search", "查找", "find"],
                "chain": [
                    {"capability": "search", "module_hint": "search_engine", "method": "search", "params_from": "task"},
                ],
            },
            "trend_analysis": {
                "keywords": ["趋势分析", "趋势报告", "trend analysis", "行业趋势", "技术趋势", "市场趋势"],
                "chain": [
                    {
                        "capability": "scan",
                        "module_hint": "github_scanner",
                        "method": "fetch_trending",
                        "params_from": "task",
                    },
                ],
            },
            "notification": {
                "keywords": [
                    "notify",
                    "notification",
                    "alert",
                    "push",
                    "发送通知",
                    "推送",
                    "通知",
                    "告警推送",
                    "send notification",
                    "send alert",
                    "email notify",
                    "message send",
                    "broadcast",
                ],
                "chain": [
                    {
                        "capability": "send",
                        "module_hint": "enterprise_notifier",
                        "method": "send",
                        "params_from": "task",
                    },
                ],
            },
            "backup": {
                "keywords": [
                    "backup",
                    "restore",
                    "备份",
                    "恢复",
                    "容灾",
                    "快照",
                    "snapshot",
                    "archive",
                    "incremental backup",
                    "full backup",
                    "data backup",
                ],
                "chain": [
                    {"capability": "backup", "module_hint": "backup_engine", "method": "create", "params": {}},
                ],
            },
            "audit": {
                "keywords": [
                    "audit",
                    "compliance",
                    "合规",
                    "审计",
                    "治理",
                    "governance",
                    "log audit",
                    "security audit",
                    "access log",
                    "operation log",
                    "审计日志",
                ],
                "chain": [
                    {"capability": "audit", "module_hint": "audit_log", "method": "report", "params": {}},
                ],
            },
            "scheduling": {
                "keywords": [
                    "schedule",
                    "cron",
                    "定时",
                    "调度",
                    "周期",
                    "周期任务",
                    "定时任务",
                    "job schedule",
                    "task scheduler",
                    "periodic",
                ],
                "chain": [
                    {
                        "capability": "schedule",
                        "module_hint": "smart_scheduler",
                        "method": "get_task_list",
                        "params": {},
                    },
                ],
            },
            "rate_limiting": {
                "keywords": [
                    "rate limit",
                    "throttle",
                    "限流",
                    "熔断",
                    "降级",
                    "限速",
                    "traffic control",
                    "rate limiter",
                    "circuit breaker",
                    "throttling",
                ],
                "chain": [
                    {"capability": "limit", "module_hint": "rate_limiter", "method": "get_config", "params": {}},
                ],
            },
            "caching": {
                "keywords": [
                    "cache",
                    "缓存",
                    "caching",
                    "redis cache",
                    "memory cache",
                    "cache hit",
                    "cache performance",
                    "cache status",
                    "缓存命中",
                    "缓存预热",
                ],
                "chain": [
                    {"capability": "health", "module_hint": "cache_engine", "method": "stats", "params": {}},
                ],
            },
            "user_management": {
                "keywords": [
                    "user",
                    "role",
                    "permission",
                    "权限",
                    "用户",
                    "角色",
                    "访问控制",
                    "user management",
                    "access control",
                    "rbac",
                    "auth",
                    "authentication",
                    "authorization",
                ],
                "chain": [
                    {
                        "capability": "manage",
                        "module_hint": "access_control",
                        "method": "get_compliance_report",
                        "params": {},
                    },
                ],
            },
            "log_management": {
                "keywords": [
                    "log",
                    "日志",
                    "log clean",
                    "log rotate",
                    "清理日志",
                    "日志管理",
                    "log analysis",
                    "日志分析",
                    "日志收集",
                    "log collect",
                    "log aggregate",
                ],
                "chain": [
                    {"capability": "read", "module_hint": "log_aggregator", "method": "search", "params": {}},
                ],
            },
            "query_optimization": {
                "keywords": [
                    "query",
                    "optimize",
                    "索引",
                    "index",
                    "慢查询",
                    "slow query",
                    "sql optimize",
                    "database optimize",
                    "query performance",
                    "查询优化",
                ],
                "chain": [
                    {"capability": "health", "module_hint": "database_client", "method": "slow_queries", "params": {}},
                ],
            },
            "compress_processing": {
                "keywords": [
                    "compress",
                    "decompress",
                    "zip",
                    "unzip",
                    "rar",
                    "tar",
                    "7z",
                    "压缩",
                    "解压",
                    "打包",
                    "compress file",
                    "compress data",
                ],
                "chain": [
                    {
                        "capability": "compress",
                        "module_hint": "compress_algorithm",
                        "method": "get_stats",
                        "params": {},
                    },
                ],
            },
            "file_processing": {
                "keywords": ["file process", "file manage", "文件处理", "文件管理", "manage files"],
                "chain": [
                    {"capability": "manage", "module_hint": "file_manager", "method": "get_stats", "params": {}},
                ],
            },
            "report_generation": {
                "keywords": [
                    "report",
                    "报告",
                    "报表",
                    "生成报告",
                    "generate report",
                    "summary report",
                    "日报",
                    "周报",
                    "月报",
                    "仪表盘",
                    "dashboard",
                ],
                "chain": [
                    {"capability": "generate", "module_hint": "data_analysis", "method": "analyze", "params": {}},
                ],
            },
            "traffic_routing": {
                "keywords": [
                    "route",
                    "gateway",
                    "proxy",
                    "路由",
                    "网关",
                    "代理",
                    "流量",
                    "traffic",
                    "api gateway",
                    "load balance",
                    "负载均衡",
                ],
                "chain": [
                    {"capability": "route", "module_hint": "api_gateway", "method": "system_info", "params": {}},
                ],
            },
            "security_scanning": {
                "keywords": [
                    "security scan",
                    "vulnerability",
                    "vulnerabilities",
                    "漏洞",
                    "安全扫描",
                    "安全检测",
                    "pentest",
                    "security check",
                    "sast",
                    "dast",
                    "dependency scan",
                    "依赖检查",
                ],
                "chain": [
                    {"capability": "scan", "module_hint": "security_scanner", "method": "quick_scan", "params": {}},
                ],
            },
            "database_ops": {
                "keywords": [
                    "database",
                    "数据库",
                    "db",
                    "sql",
                    "postgres",
                    "mysql",
                    "mongodb",
                    "redis",
                    "database status",
                    "数据库状态",
                    "db connection",
                    "数据库连接",
                ],
                "chain": [
                    {"capability": "health", "module_hint": "database_client", "method": "pool_stats", "params": {}},
                ],
            },
            "security_check": {
                "keywords": [
                    "check security",
                    "security status",
                    "安全状态",
                    "安全检查",
                    "security status",
                    "security health",
                    "system security",
                ],
                "chain": [
                    {
                        "capability": "health",
                        "module_hint": "security_scanner",
                        "method": "get_compliance",
                        "params": {},
                    },
                ],
            },
            "network_check": {
                "keywords": ["network status", "check network", "网络状态", "网络检查", "bandwidth", "带宽"],
                "chain": [
                    {"capability": "health", "module_hint": "network_healer", "method": "analyze", "params": {}},
                ],
            },
            "monitoring": {
                "keywords": [
                    "monitor",
                    "health",
                    "status",
                    "系统状态",
                    "系统健康",
                    "运行状态",
                    "performance",
                    "性能",
                    "指标",
                    "metrics",
                    "cpu",
                    "memory",
                    "ram",
                    "check status",
                    "check health",
                ],
                "chain": [
                    {"capability": "health", "module_hint": "perf_monitor", "method": "status", "params": {}},
                ],
            },
            "data_analysis": {
                "keywords": [
                    "analyze data",
                    "数据分析",
                    "数据统计",
                    "statistics",
                    "data analysis",
                    "data analytics",
                    "数据处理",
                    "process data",
                ],
                "chain": [
                    {"capability": "analyze", "module_hint": "data_analysis", "method": "analyze", "params": {}},
                ],
            },
            "ai_chat": {
                "keywords": [
                    "chat",
                    "talk",
                    "ask ai",
                    "问ai",
                    "和ai",
                    "对话",
                    "conversation",
                    "discuss",
                    "explain to me",
                ],
                "chain": [
                    {"capability": "chat", "module_hint": "ai_gateway", "method": "analyze", "params_from": "task"},
                ],
            },
            "encryption_ops": {
                "keywords": [
                    "encrypt",
                    "decrypt",
                    "cipher",
                    "hash",
                    "加密",
                    "解密",
                    "哈希",
                    "密码",
                    "密钥",
                    "encryption",
                    "decryption",
                    "cryptography",
                    "aes",
                    "rsa",
                    "ssl",
                    "tls",
                    "sign",
                    "verify",
                    "签名",
                    "验签",
                ],
                "chain": [
                    {"capability": "encrypt", "module_hint": "data_encrypt", "method": "stats", "params": {}},
                ],
            },
            "validation": {
                "keywords": [
                    "validate",
                    "validation",
                    "校验",
                    "验证",
                    "schema",
                    "input validate",
                    "data validate",
                    "格式校验",
                    "input check",
                ],
                "chain": [
                    {"capability": "validate", "module_hint": "config_service", "method": "health_check", "params": {}},
                ],
            },
            # === 新增pattern (2026-05-15 批量扩展 30个) ===
            "browser_automation": {
                "keywords": [
                    "browser",
                    "浏览器",
                    "selenium",
                    "playwright",
                    "网页自动",
                    "打开网页",
                    "截图",
                    "screenshot",
                    "fill form",
                    "browser test",
                    "headless",
                ],
                "chain": [
                    {
                        "capability": "automate",
                        "module_hint": "browser_auto",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "rpa_task": {
                "keywords": [
                    "rpa",
                    "机器人",
                    "桌面自动",
                    "desktop auto",
                    "自动操作",
                    "macro",
                    "录制",
                    "自动化脚本",
                    "gui auto",
                    "界面自动",
                ],
                "chain": [
                    {
                        "capability": "automate",
                        "module_hint": "rpa_controller",
                        "method": "initialize",
                        "params_from": "task",
                    },
                ],
            },
            "kafka_ops": {
                "keywords": [
                    "kafka",
                    "消息队列",
                    "message queue",
                    "topic",
                    "consumer",
                    "producer",
                    "消息发送",
                    "消息消费",
                    "event stream",
                    "消息流",
                ],
                "chain": [
                    {"capability": "send", "module_hint": "kafka_producer", "method": "send", "params_from": "task"},
                ],
            },
            "decision_making": {
                "keywords": [
                    "决策",
                    "decision",
                    "规则引擎",
                    "rule engine",
                    "评分",
                    "scoring",
                    "ab test",
                    "ab测试",
                    "策略",
                    "policy",
                    "决策引擎",
                ],
                "chain": [
                    {
                        "capability": "analyze",
                        "module_hint": "decision_engine",
                        "method": "evaluate_rules",
                        "params_from": "task",
                    },
                ],
            },
            "schema_management": {
                "keywords": [
                    "schema",
                    "模式",
                    "数据模式",
                    "schema registry",
                    "兼容性",
                    "compatibility",
                    "avro",
                    "protobuf",
                    "schema evolution",
                ],
                "chain": [
                    {
                        "capability": "validate",
                        "module_hint": "schema_registry",
                        "method": "validate",
                        "params_from": "task",
                    },
                ],
            },
            "database_connector_ops": {
                "keywords": [
                    "数据库连接",
                    "db connector",
                    "连接池",
                    "connection pool",
                    "query",
                    "sql执行",
                    "数据库操作",
                    "db operation",
                    "batch query",
                ],
                "chain": [
                    {
                        "capability": "health",
                        "module_hint": "database_connector",
                        "method": "initialize",
                        "params_from": "task",
                    },
                ],
            },
            "email_send": {
                "keywords": [
                    "发邮件",
                    "send email",
                    "email",
                    "邮件",
                    "smtp",
                    "mail send",
                    "邮件通知",
                    "邮件发送",
                    "邮件模板",
                ],
                "chain": [
                    {"capability": "send", "module_hint": "email_automation", "method": "send", "params_from": "task"},
                ],
            },
            "telegram_notify": {
                "keywords": ["telegram", "tg通知", "tg消息", "电报", "bot消息"],
                "chain": [
                    {
                        "capability": "send",
                        "module_hint": "telegram_bridge",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "http_request": {
                "keywords": [
                    "http请求",
                    "http request",
                    "api调用",
                    "api call",
                    "rest api",
                    "发送请求",
                    "get请求",
                    "post请求",
                    "http client",
                    "接口调用",
                ],
                "chain": [
                    {"capability": "scan", "module_hint": "http_client", "method": "analyze", "params_from": "task"},
                ],
            },
            "prometheus_metrics": {
                "keywords": [
                    "prometheus",
                    "指标采集",
                    "metrics collect",
                    "监控指标",
                    "metrics",
                    "grafana",
                    "仪表盘",
                    "监控面板",
                    "prom query",
                ],
                "chain": [
                    {
                        "capability": "health",
                        "module_hint": "prometheus_metrics",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "grafana_dashboard": {
                "keywords": ["grafana", "仪表盘", "dashboard", "监控面板", "可视化监控", "监控视图"],
                "chain": [
                    {
                        "capability": "health",
                        "module_hint": "grafana_monitor",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "workflow_manage": {
                "keywords": [
                    "workflow",
                    "工作流",
                    "流程管理",
                    "审批流",
                    "bpmn",
                    "流程引擎",
                    "流程自动化",
                    "工作流引擎",
                    "business process",
                ],
                "chain": [
                    {
                        "capability": "manage",
                        "module_hint": "workflow_manager",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "code_review_auto": {
                "keywords": [
                    "code review",
                    "代码审查",
                    "代码评审",
                    "代码质量",
                    "code quality",
                    "代码检查",
                    "lint",
                    "code smell",
                ],
                "chain": [
                    {"capability": "analyze", "module_hint": "code_review", "method": "analyze", "params_from": "task"},
                ],
            },
            "image_generate": {
                "keywords": [
                    "生成图片",
                    "image generate",
                    "ai画图",
                    "ai绘图",
                    "dall-e",
                    "stable diffusion",
                    "图片生成",
                    "文生图",
                    "text to image",
                    "create image",
                ],
                "chain": [
                    {
                        "capability": "generate",
                        "module_hint": "image_generation",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "meeting_transcribe": {
                "keywords": [
                    "会议",
                    "meeting",
                    "会议记录",
                    "meeting notes",
                    "转录",
                    "transcribe",
                    "语音转文字",
                    "speech to text",
                    "会议纪要",
                ],
                "chain": [
                    {
                        "capability": "analyze",
                        "module_hint": "meeting_transcribe",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "trigger_management": {
                "keywords": [
                    "trigger",
                    "触发器",
                    "事件触发",
                    "webhook trigger",
                    "条件触发",
                    "auto trigger",
                    "自动触发",
                    "event trigger",
                ],
                "chain": [
                    {
                        "capability": "manage",
                        "module_hint": "trigger_engine",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "webhook_management": {
                "keywords": ["webhook", "回调", "callback", "webhook管理", "webhook配置", "api回调", "事件回调"],
                "chain": [
                    {
                        "capability": "manage",
                        "module_hint": "webhook_handler",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "docker_ops": {
                "keywords": [
                    "docker",
                    "容器",
                    "container",
                    "镜像",
                    "image",
                    "dockerfile",
                    "docker-compose",
                    "容器管理",
                    "container manage",
                ],
                "chain": [
                    {
                        "capability": "manage",
                        "module_hint": "docker_manager",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "cloud_deploy": {
                "keywords": [
                    "deploy",
                    "部署",
                    "发布",
                    "release",
                    "rollout",
                    "上线",
                    "argo",
                    "argocd",
                    "蓝绿部署",
                    "blue green",
                    "canary",
                ],
                "chain": [
                    {"capability": "deploy", "module_hint": "k8s_orch", "method": "analyze", "params_from": "task"},
                ],
            },
            "data_masking": {
                "keywords": [
                    "数据脱敏",
                    "data masking",
                    "隐私保护",
                    "privacy",
                    "敏感数据",
                    "数据匿名",
                    "anonymize",
                    "pseudonymize",
                ],
                "chain": [
                    {"capability": "manage", "module_hint": "data_masking", "method": "analyze", "params_from": "task"},
                ],
            },
            "compliance_check": {
                "keywords": [
                    "合规检查",
                    "compliance",
                    "合规审计",
                    "policy check",
                    "规范检查",
                    "标准合规",
                    "regulation",
                    "法规",
                ],
                "chain": [
                    {
                        "capability": "audit",
                        "module_hint": "compliance_auditor",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "alert_management": {
                "keywords": [
                    "告警",
                    "alert",
                    "告警管理",
                    "alert manage",
                    "告警规则",
                    "alert rule",
                    "告警通知",
                    "alert notify",
                    "报警",
                ],
                "chain": [
                    {
                        "capability": "manage",
                        "module_hint": "alert_manager",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "load_balance": {
                "keywords": [
                    "负载均衡",
                    "load balance",
                    "lb",
                    "流量分发",
                    "流量管理",
                    "round robin",
                    "weighted",
                    "权重",
                ],
                "chain": [
                    {"capability": "route", "module_hint": "load_balancer", "method": "analyze", "params_from": "task"},
                ],
            },
            "object_storage": {
                "keywords": [
                    "对象存储",
                    "object storage",
                    "s3",
                    "oss",
                    "minio",
                    "bucket",
                    "文件存储",
                    "云存储",
                    "blob storage",
                ],
                "chain": [
                    {
                        "capability": "manage",
                        "module_hint": "object_storage",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "longterm_memory": {
                "keywords": [
                    "长期记忆",
                    "longterm memory",
                    "持久记忆",
                    "记忆检索",
                    "memory search",
                    "知识库",
                    "knowledge base",
                    "记忆管理",
                ],
                "chain": [
                    {
                        "capability": "read",
                        "module_hint": "longterm_memory",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "auto_healing": {
                "keywords": [
                    "自愈",
                    "auto healing",
                    "自动修复",
                    "auto fix",
                    "self heal",
                    "故障恢复",
                    "fault recovery",
                    "自动恢复",
                ],
                "chain": [
                    {
                        "capability": "health",
                        "module_hint": "auto_recovery",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "template_manage": {
                "keywords": [
                    "模板",
                    "template",
                    "模板管理",
                    "模板库",
                    "模板市场",
                    "模板创建",
                    "template create",
                    "模板引擎",
                ],
                "chain": [
                    {
                        "capability": "manage",
                        "module_hint": "template_registry",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "encryption_service": {
                "keywords": [
                    "加密服务",
                    "encryption service",
                    "数据加密",
                    "data encryption",
                    "密钥管理",
                    "key management",
                    "hsm",
                    "安全加密",
                ],
                "chain": [
                    {
                        "capability": "encrypt",
                        "module_hint": "encryption_service",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "data_sync": {
                "keywords": [
                    "数据同步",
                    "data sync",
                    "数据迁移",
                    "data migration",
                    "数据复制",
                    "实时同步",
                    "realtime sync",
                    "双向同步",
                ],
                "chain": [
                    {"capability": "manage", "module_hint": "data_sync", "method": "analyze", "params_from": "task"},
                ],
            },
            "form_builder": {
                "keywords": [
                    "表单",
                    "form",
                    "表单构建",
                    "form build",
                    "表单设计",
                    "form design",
                    "动态表单",
                    "dynamic form",
                    "问卷",
                ],
                "chain": [
                    {
                        "capability": "generate",
                        "module_hint": "form_builder",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
            "capacity_planning": {
                "keywords": [
                    "容量规划",
                    "capacity",
                    "扩容",
                    "scale",
                    "资源规划",
                    "resource plan",
                    "容量评估",
                    "capacity assess",
                ],
                "chain": [
                    {
                        "capability": "health",
                        "module_hint": "capacity_planner",
                        "method": "analyze",
                        "params_from": "task",
                    },
                ],
            },
        }

    def _build_chain_from_pattern(self, pattern: dict, task: str = "") -> list[dict]:
        """从预定义模式构建执行链"""
        chain = []
        for step in pattern.get("chain", []):
            module_id = self._resolve_module(step.get("module_hint"), step.get("capability"), task)
            # Fallback: 如果 hint 解析不到，按能力查找模块
            if not module_id:
                cap = step.get("capability", "")
                candidates = self.graph.find_modules_by_capability(cap)
                if candidates:
                    module_id = candidates[0]
            if module_id:
                chain.append(
                    {
                        "module": module_id,
                        "method": step.get("method"),
                        "params": step.get("params", {}),
                        "capability": step.get("capability"),
                    }
                )
        return chain

    def _build_chain_from_capabilities(self, needed_steps: list[str], task: str) -> list[dict]:
        """根据已识别的能力序列构建执行链（仅在needed_steps非空时调用）"""
        chain = []

        for cap in needed_steps:
            # 传入 task 让 _resolve_module 做领域感知
            module_id = self._resolve_module("", cap, task)
            if not module_id:
                modules = self.graph.find_modules_by_capability(cap)
                if modules:
                    module_id = modules[0]
            if module_id:
                method = self._get_default_method(module_id, cap)
                # 跳过私有方法和 __init__
                if method and not method.startswith("_") and method != "__init__":
                    chain.append(
                        {
                            "module": module_id,
                            "method": method,
                            "params": {},
                            "capability": cap,
                        }
                    )

        return chain

    def _analyze_task_capabilities(self, task: str) -> list[str]:
        """分析任务需要的能力序列"""
        task_lower = task.lower()
        capabilities = []

        # 任务领域识别（英文+中文双匹配）
        is_github = any(
            kw in task_lower
            for kw in [
                "github",
                "开源",
                "开源项目",
                "trending",
                "repository",
                "repo",
                "git",
                "代码仓库",
                "开源软件",
                "源码",
                "open source",
            ]
        )
        is_financial = any(
            kw in task_lower
            for kw in [
                "stock",
                "股票",
                "fund",
                "基金",
                "futures",
                "期货",
                "forex",
                "crypto",
                "btc",
                "eth",
                "macro",
                "宏观",
                "finance",
                "金融",
                "指数",
                "大盘",
                "上证",
                "深证",
                "股价",
                "净值",
                "汇率",
                "价格",
                "quote",
                "price",
                "gdp",
                "cpi",
                "pmi",
                "利率",
            ]
        )
        is_data = any(kw in task_lower for kw in ["data", "数据", "database", "db", "cache", "队列", "pipeline"])
        is_code = any(
            kw in task_lower
            for kw in ["code", "代码", "script", "编程", "python", "javascript", "generate", "生成", "create", "项目"]
        )
        is_video = any(kw in task_lower for kw in ["video", "视频", "movie", "电影", "gif", "动画"])
        is_ml = any(
            kw in task_lower
            for kw in [
                "ml",
                "machine learning",
                "train",
                "训练",
                "model",
                "模型",
                "paper",
                "论文",
                "research",
                "huggingface",
                "pytorch",
                "机器学习",
                "深度学习",
            ]
        )
        is_translate = any(
            kw in task_lower for kw in ["translate", "translation", "翻译", "i18n", "语言", "english", "中文"]
        )
        is_monitor = any(
            kw in task_lower for kw in ["monitor", "监控", "health", "健康", "status", "状态", "performance"]
        )
        is_backup = any(kw in task_lower for kw in ["backup", "备份", "archive"])
        is_memory = any(kw in task_lower for kw in ["memory", "remember", "记忆", "brain", "学习", "learn"])
        is_notification = any(kw in task_lower for kw in ["notify", "notification", "通知", "send", "推送", "feishu"])
        is_security = any(
            kw in task_lower
            for kw in [
                "security",
                "安全",
                "vulnerability",
                "vulnerabilities",
                "漏洞",
                "threat",
                "威胁",
                "hack",
                "attack",
                "攻击",
                "防火墙",
                "firewall",
                "waf",
                "入侵",
                "intrusion",
                "protect",
                "防护",
                "加固",
            ]
        )
        is_encrypt = any(
            kw in task_lower
            for kw in ["encrypt", "decrypt", "加密", "解密", "cipher", "crypto", "密码", "hash", "sha", "aes", "rsa"]
        )
        is_web_scrape = any(
            kw in task_lower
            for kw in [
                "网页",
                "website",
                "scrape",
                "crawl",
                "爬取",
                "抓取",
                "采集",
                "web page",
                "html页面",
                "页面内容",
                "url",
            ]
        )

        # 检测操作能力（中文+英文双匹配）
        need_read = any(
            kw in task_lower
            for kw in [
                "获取",
                "读取",
                "查询",
                "get",
                "read",
                "fetch",
                "query",
                "check",
                "看",
                "查",
                "拉取",
                "收盘",
                "价格",
                "quote",
                "实时",
            ]
        )
        need_analyze = any(
            kw in task_lower
            for kw in ["分析", "统计", "评估", "analyze", "evaluate", "assess", "统计", "compare", "对比"]
        )
        need_create = any(kw in task_lower for kw in ["生成", "创建", "generate", "create", "build", "make"])
        need_export = any(kw in task_lower for kw in ["保存", "写入", "导出", "save", "write", "export", "output"])
        need_send = any(kw in task_lower for kw in ["发送", "推送", "通知", "send", "push", "notify", "email"])
        need_search = any(kw in task_lower for kw in ["搜索", "查找", "search", "find", "lookup", "论文", "paper"])
        need_train = any(kw in task_lower for kw in ["train", "训练", "learn", "学习", "fit"])
        need_scan = any(kw in task_lower for kw in ["扫描", "scan", "排查", "探测", "检测", "嗅探"])

        # 领域驱动 + 操作驱动的双重编排
        if is_github:
            capabilities.append("scan")
            if need_analyze:
                capabilities.append("analyze")
            if need_search:
                capabilities.append("scan")
        elif is_web_scrape:
            capabilities.append("scan")
            if need_analyze:
                capabilities.append("analyze")
            if need_export:
                capabilities.append("export")
        elif is_financial:
            capabilities.append("read")  # 金融任务先获取数据
            if need_analyze:
                capabilities.append("analyze")
            capabilities.append("chat")  # AI 总结
            if need_export:
                capabilities.append("export")
        elif is_code:
            capabilities.append("generate")
            if need_read:
                capabilities.append("read")
        elif is_video:
            capabilities.append("generate")
        elif is_ml:
            # 机器学习: 论文搜索优先，训练其次
            if any(kw in task_lower for kw in ["搜索", "找", "查", "论文", "paper", "research"]):
                capabilities.append("search")
            elif any(kw in task_lower for kw in ["训练", "train", "学习", "fit"]):
                capabilities.append("train")
            else:
                capabilities.append("search")
            capabilities.append("chat")
        elif is_translate:
            capabilities.append("translate")
            if need_export:
                capabilities.append("export")
        elif is_monitor:
            capabilities.append("health")
            capabilities.append("chat")
            if need_send:
                capabilities.append("send")
        elif is_backup:
            capabilities.append("backup")
        elif is_memory:
            capabilities.append("read")
            capabilities.append("chat")
        elif is_notification:
            capabilities.append("send")
        elif is_security:
            capabilities.append("scan")  # security_scanner handles scanning
            if need_read:
                capabilities.append("read")
        elif is_encrypt:
            capabilities.append("encrypt")  # data_encrypt handles encryption
        elif any(
            kw in task_lower
            for kw in ["compress", "decompress", "zip", "unzip", "rar", "tar", "7z", "压缩", "解压", "打包"]
        ):
            # 压缩操作 — 直接路由到compress模块
            capabilities.append("compress")
        else:
            # 通用操作驱动
            if need_scan:
                capabilities.append("scan")
            if need_read:
                capabilities.append("read")
            if need_search:
                capabilities.append("search")
            if need_analyze:
                capabilities.append("analyze")
            if need_create:
                capabilities.append("generate")
            if need_export:
                capabilities.append("export")
            if need_send:
                capabilities.append("send")
            if need_train:
                capabilities.append("train")

                # 如果没有检测到任何能力，返回空——不硬路由
                # （旧逻辑: 默认 scan 会导致无关任务被强行执行）
            capabilities.append("chat")

        return capabilities

    def _resolve_module(self, hint: str, capability: str, task: str = "") -> str | None:
        """解析模块 hint 到实际模块ID"""
        task_lower = task.lower()

        # 0. hint 直接匹配（最高优先级 — 精确指定）
        if hint and hint in self.graph.graph:
            return hint

        # 1. hint 模糊匹配
        if hint:
            for module_id in self.graph.graph:
                if hint.replace("_", "") in module_id.replace("_", "") or module_id.replace("_", "") in hint.replace(
                    "_", ""
                ):
                    return module_id

        # 2. 领域感知模块选择（英文+中文双匹配）— 仅当无 hint 时
        domain_module_map = {
            "stock": "stock_api",
            "股票": "stock_api",
            "fund": "fund_api",
            "基金": "fund_api",
            "futures": "futures_api",
            "期货": "futures_api",
            "forex": "forex_api",
            "汇率": "forex_api",
            "crypto": "crypto_api",
            "btc": "crypto_api",
            "eth": "crypto_api",
            "macro": "macro_api",
            "宏观": "macro_api",
            "gdp": "macro_api",
            "cpi": "macro_api",
            "指数": "stock_api",
            "translate": "i18n_gateway",
            "翻译": "i18n_gateway",
            "video": "pixelle_video",
            "视频": "pixelle_video",
            "代码": "atom_code",
            "网站": "open_lovable",
            "webpage": "open_lovable",
            "monitor": "perf_monitor",
            "监控": "perf_monitor",
            "性能": "perf_monitor",
            "performance": "perf_monitor",
            "network": "network_healer",
            "网络": "network_healer",
            "带宽": "network_healer",
            "backup": "backup_engine",
            "备份": "backup_engine",
            "paper": "ml_intern",
            "论文": "ml_intern",
            "model": "ml_intern",
            "模型": "ml_intern",
            "feishu": "uni_comm_gateway",
            "飞书": "uni_comm_gateway",
            "email": "email_automation",
            "邮件": "email_automation",
            "memory": "second_brain",
            "记忆": "second_brain",
            "github": "github_scanner",
            "开源": "github_scanner",
            "trending": "trendaradar_trend",
            "趋势": "trendaradar_trend",
            "encrypt": "data_encrypt",
            "decrypt": "data_encrypt",
            "加密": "data_encrypt",
            "解密": "data_encrypt",
            "cipher": "data_encrypt",
            "hash": "data_encrypt",
            "密码": "data_encrypt",
            "notify": "enterprise_notifier",
            "notification": "enterprise_notifier",
            "推送": "enterprise_notifier",
            "通知": "enterprise_notifier",
            "audit": "audit_log",
            "审计": "audit_log",
            "合规": "aegis_governance",
            "schedule": "smart_scheduler",
            "调度": "smart_scheduler",
            "定时": "smart_scheduler",
            "cron": "smart_scheduler",
            "rate limit": "rate_limiter",
            "限流": "rate_limiter",
            "熔断": "rate_limiter",
            "cache": "cache_engine",
            "缓存": "cache_engine",
            "user": "access_control",
            "权限": "access_control",
            "角色": "access_control",
            "rbac": "access_control",
            "log": "log_aggregator",
            "日志": "log_aggregator",
            "search": "search_engine",
            "搜索": "search_engine",
            "检索": "search_engine",
            "query": "search_engine",
            "查询": "search_engine",
            "file": "file_manager",
            "文件": "file_manager",
            "report": "data_analysis",
            "报告": "data_analysis",
            "报表": "data_analysis",
            "gateway": "api_gateway",
            "路由": "api_gateway",
            "网关": "api_gateway",
            "security": "security_scanner",
            "安全": "security_scanner",
            "漏洞": "security_scanner",
            "protect": "security_scanner",
            "防护": "security_scanner",
            "threat": "security_scanner",
            "database": "database_client",
            "数据库": "database_client",
            "db": "database_client",
            "deploy": "cicd_pipeline",
            "部署": "cicd_pipeline",
            "发布": "cicd_pipeline",
            "workflow": "workflow_engine",
            "工作流": "workflow_engine",
            "编排": "workflow_engine",
            "config": "config_service",
            "配置": "config_service",
            "设置": "config_service",
            "secret": "secret_vault",
            "密钥": "secret_vault",
            "validate": "config_service",
            "校验": "config_service",
            "验证": "config_service",
            "alert": "enterprise_notifier",
            "告警": "enterprise_notifier",
            "queue": "message_queue",
            "队列": "message_queue",
            "mq": "message_queue",
            "lock": "distributed_lock",
            "锁": "distributed_lock",
            "分布式锁": "distributed_lock",
            "trace": "distributed_tracer",
            "链路": "distributed_tracer",
            "incident": "incident_manager",
            "事件": "incident_manager",
            "故障": "incident_manager",
            "container": "container_manager",
            "容器": "container_manager",
            "docker": "container_manager",
            "persist": "persistence",
            "持久化": "persistence",
            "protect": "security_scanner",
            "hacker": "security_scanner",
            "threat": "security_scanner",
            "vulnerability": "security_scanner",
            "vuln": "security_scanner",
            "compress": "compress_algorithm",
            "压缩": "compress_algorithm",
            "decompress": "compress_algorithm",
            "zip": "compress_algorithm",
            "store": "cache_engine",
            "temp": "cache_engine",
            "缓存": "cache_engine",
        }

        # 使用词边界匹配，避免 "project" 匹配 "projects" 等误匹配
        # 收集所有匹配，取关键词最长的（更具体的优先）
        import re as _re

        best_match = None
        best_kw_len = 0
        for kw, module_id in domain_module_map.items():
            if module_id in self.graph.graph:
                matched = False
                if kw.isascii():
                    pattern = r"\b" + _re.escape(kw) + r"\b"
                    if _re.search(pattern, task_lower):
                        matched = True
                elif kw in task_lower:
                    matched = True
                if matched and len(kw) > best_kw_len:
                    best_match = module_id
                    best_kw_len = len(kw)
        if best_match:
            return best_match

        # 3. 能力匹配（智能优先级）
        cap_module_priority = {
            "read": [
                "stock_api",
                "fund_api",
                "futures_api",
                "forex_api",
                "crypto_api",
                "macro_api",
                "database_client",
                "cache_engine",
            ],
            "scan": ["security_scanner", "github_scanner", "web_scraper", "trendaradar_trend", "automation_hub"],
            "analyze": ["data_analysis", "business_analyst", "trendaradar_trend", "ai_gateway"],
            "generate": ["open_lovable", "atom_code", "pixelle_video"],
            "export": ["export_engine", "backup_engine"],
            "send": ["uni_comm_gateway", "email_automation", "feishu_notifier"],
            "chat": ["ai_gateway", "autonomous_agent"],
            "translate": ["i18n_gateway"],
            "search": ["ml_intern", "ai_gateway", "github_scanner"],
            "train": ["ml_intern"],
            "health": ["perf_monitor"],
            "backup": ["backup_engine"],
            "stats": ["perf_monitor", "business_analyst"],
            "compress": ["compress_algorithm"],
            "encrypt": ["data_encrypt"],
        }

        for preferred in cap_module_priority.get(capability, []):
            if preferred in self.graph.graph:
                return preferred

        # 4. 通用能力匹配
        modules = self.graph.find_modules_by_capability(capability)
        if modules:
            return modules[0]

        # 5. 向量语义 Fallback — 用ChromaDB语义搜索兜底
        if task:
            try:
                vector_results = self.graph.find_modules_vector(task, top_k=5)
                for mid, score in vector_results:
                    if score > 0.2 and mid in self.graph.graph:
                        return mid
            except Exception:
                pass

        return None

    def _get_default_method(self, module_id: str, capability: str) -> str:
        """获取模块的默认方法"""
        info = self.graph.get_module_info(module_id)
        if not info:
            return "execute"

        methods = info.get("methods", [])

        # 模块专用方法映射（精确匹配，按优先级排序）
        module_method_map = {
            "stock_api": {"read": "get_realtime_quote", "analyze": "chat"},
            "fund_api": {"read": "get_fund_list"},
            "futures_api": {"read": "get_main_contracts"},
            "forex_api": {"read": "get_exchange_rate"},
            "crypto_api": {"read": "quote"},
            "macro_api": {"read": "gdp"},
            "i18n_gateway": {"translate": "translate"},
            "open_lovable": {"generate": "generate_project"},
            "pixelle_video": {"generate": "generate_video"},
            "ml_intern": {"search": "research_paper", "train": "train_model"},
            "perf_monitor": {"health": "collect_metrics"},
            "backup_engine": {"backup": "create_backup"},
            "ai_gateway": {"chat": "chat", "analyze": "chat"},
            "uni_comm_gateway": {"send": "send_message"},
            "email_automation": {"send": "send_email"},
            "export_engine": {"export": "export_markdown"},
            "second_brain": {"read": "get_stats", "analyze": "consolidate"},
        }

        # 1. 精确模块+能力匹配
        if module_id in module_method_map:
            specific = module_method_map[module_id].get(capability)
            if specific and specific in methods:
                return specific

        # 2. 通用前缀匹配
        method_map = {
            "read": ["get_", "fetch", "query", "quote", "gdp", "cpi", "kline"],
            "write": ["set", "write", "save", "store"],
            "create": ["create_", "add", "new"],
            "delete": ["delete", "remove", "clear"],
            "send": ["send", "push", "notify", "post"],
            "scan": ["scan", "detect", "check"],
            "analyze": ["analyze", "analysis", "stats"],
            "generate": ["generate", "create", "build"],
            "chat": ["chat", "talk", "ask"],
            "translate": ["translate", "translation"],
            "search": ["search", "find", "lookup", "papers"],
            "train": ["train", "learn", "fit"],
            "health": ["health_check", "collect_metrics", "check_health"],
            "stats": ["get_stats", "stats"],
            "export": ["export", "save", "write"],
            "backup": ["create_backup", "backup", "do_auto_backup"],
        }

        prefixes = method_map.get(capability, [])
        for prefix in prefixes:
            for method in methods:
                if method.startswith(prefix) or method == prefix:
                    if not method.startswith("_"):
                        return method

        # 3. 返回第一个可用公共方法
        for method in methods:
            if not method.startswith("__"):
                return method

        return "execute"

    async def execute_chain(self, chain: list[dict], task: str, context: dict = None) -> dict:
        """执行模块链"""
        context = context or {}
        results = []
        shared_data = {}

        for i, step in enumerate(chain):
            module_id = step["module"]
            method_name = step.get("method", "status") or "status"
            params = step.get("params", {}).copy()
            # 确保method传入_execute_single_module，避免action变成task文本
            params["method"] = method_name

            # 替换模板参数
            for key, value in params.items():
                if isinstance(value, str) and "{" in value:
                    try:
                        params[key] = value.format(data=shared_data.get("last_result", ""), task=task)
                    except Exception:
                        pass

            # 执行模块方法
            try:
                result = await self.coordinator._execute_single_module(
                    module_id, task, params, {**context, "_chain_step": i, "_shared": shared_data}
                )
                # 如果模块执行失败但action不是标准action，fallback到status
                if not result.get("success") and method_name != "status":
                    fallback_params = {"action": "status", "params": {}, "method": "status"}
                    result = await self.coordinator._execute_single_module(
                        module_id, task, fallback_params, {**context, "_chain_step": i, "_shared": shared_data}
                    )
                results.append({"step": i, "module": module_id, "result": result})

                if result.get("success"):
                    shared_data["last_result"] = result.get("result", result)
                else:
                    # 记录失败但继续执行后续步骤
                    logger.warning(f"[Chain] 第 {i + 1} 步 {module_id}.{method_name} 失败: {result.get('error', '?')}")

            except Exception as e:
                results.append({"step": i, "module": module_id, "result": {"success": False, "error": str(e)}})
                logger.warning(f"[Chain] 第 {i + 1} 步 {module_id}.{method_name} 异常: {e}")

        # 汇总结果 — 至少有一个步骤成功就算部分成功
        success_count = sum(1 for r in results if r.get("result", {}).get("success"))
        if success_count > 0:
            return {
                "success": True,
                "result": shared_data.get("last_result"),
                "step_results": results,
                "chain": [s["module"] for s in chain],
                "success_rate": f"{success_count}/{len(chain)}",
            }
        else:
            return {
                "success": False,
                "error": f"执行链所有步骤均失败 ({len(chain)}步)",
                "step_results": results,
                "chain": [s["module"] for s in chain],
            }

# ============================================================================
# 系统核心协调器 v3.0
# ============================================================================


