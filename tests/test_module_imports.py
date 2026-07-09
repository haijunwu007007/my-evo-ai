"""AUTO-EVO-AI V0.1 — 关键模块批量导入测试（80个核心+业务模块）"""
import sys, os, importlib, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_MANAGER_MODULES = [
    "access_control", "aegis_governance", "agent_apollo", "agent_athena",
    "alert_manager", "api_cache", "api_mock", "api_rate_guard", "api_tester",
    "api_versioning", "audit_log", "automation_hub", "auto_failover",
    "auto_healing", "auto_restart", "auto_scale", "autorecovery", "autoskills",
    "backup_engine", "backup_manager", "backup_redis", "backup_scheduler",
    "backup_verify", "block_device", "blue_green", "billion_group_os",
    "bloom_filter", "bot_detection", "browser_auto",
    "cache_engine", "canary_release", "capacity_planner", "cdn_invalidate",
    "cdn_manager", "chaos_engine", "chart_engine", "cicd_pipeline",
    "clickhouse_olap", "clone_database", "cloud_connector", "cluster_proxy",
    "cluster_shard", "code_generator", "code_quality", "code_sandbox",
    "command_stats", "compliance_auditor", "compress_algorithm",
    "config_center", "config_manager", "config_reloader", "config_service",
    "connection_draining", "consumer_group", "cors_manager", "cpu_profiler",
    "cron_engine", "cron_scheduler", "crypto_api", "dashboard",
    "data_archival", "data_lineage", "data_pipeline", "data_sync",
    "decision_engine", "delay_queue", "distributed_tracer", "dns_manager",
    "docker_deploy", "docker_manager", "document_automation", "email_pro",
    "encryption_service", "export_engine", "feature_flag", "flow_engine",
]
_LIGHT_MODULES = [
    "astro_site", "bookstack_kb", "browser_use", "browser_use_agent",
    "cal_scheduler", "chatwoot_support", "data_quality", "decision_tree",
    "feishu_notifier", "grafana_monitor", "home_assistant", "humanizer",
    "invoice_agent", "libre_translate", "log_aggregator", "mcp_bridge",
    "multi_agent_crew", "priority_queue",
]

ALL_MODULES = _MANAGER_MODULES + _LIGHT_MODULES

@pytest.mark.parametrize("mod_name", ALL_MODULES)
def test_module_import(mod_name):
    """验证模块可导入"""
    try:
        mod = importlib.import_module(f"modules.{mod_name}")
        assert mod is not None
    except Exception as e:
        pytest.fail(f"{mod_name}: {e}")
