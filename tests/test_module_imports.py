"""AUTO-EVO-AI V0.1 — 关键模块批量导入测试（4个轻量+前40个模块）"""
import sys, os, importlib, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

@pytest.mark.parametrize("mod_name", [
    "astro_site", "bookstack_kb", "browser_use", "browser_use_agent",
    "cal_scheduler", "chatwoot_support", "data_quality", "decision_tree",
    "feishu_notifier", "grafana_monitor", "home_assistant", "humanizer",
    "invoice_agent", "libre_translate", "log_aggregator", "mcp_bridge",
    "multi_agent_crew", "priority_queue",
    "access_control", "aegis_governance", "agent_apollo", "agent_athena",
    "alert_manager", "api_cache", "audit_log", "automation_hub",
    "backup_engine", "backup_manager", "billion_group_os", "bloom_filter",
    "bot_detection", "browser_auto",
    "cache_engine", "cdn_manager", "chaos_engine", "chart_engine",
    "cicd_pipeline", "cloud_connector", "code_generator", "code_quality",
])
def test_module_import(mod_name):
    """验证模块可导入"""
    try:
        mod = importlib.import_module(f"modules.{mod_name}")
        assert mod is not None
    except Exception as e:
        pytest.fail(f"{mod_name}: {e}")
