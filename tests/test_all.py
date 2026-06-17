"""AUTO-EVO-AI — 全量测试套件"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from agent_tools import exec_tool, list_tools

class TestTools:
    def test_tools_count(self):
        t = list_tools()
        assert len(t) >= 87, f"工具数不足: {len(t)}"

    def test_chart_create(self):
        r = exec_tool("chart_create", {"data": "[1,2,3]"})
        assert r["ok"]

    def test_code_review(self):
        r = exec_tool("code_review", {"code": "def add(a,b): return a+b"})
        assert r["ok"]

    def test_password_manager(self):
        r = exec_tool("password_manager", {})
        assert r["ok"]
        assert len(r.get("data", "")) > 10

    def test_site_monitor(self):
        r = exec_tool("site_monitor", {"url": "https://example.com"})
        assert r["ok"]

    def test_api_test(self):
        r = exec_tool("api_test", {"url": "https://example.com"})
        assert r["ok"]

    def test_unknown_tool(self):
        r = exec_tool("not_exist", {})
        assert not r["ok"]


class TestModuleRegistry:
    def test_import(self):
        from api.module_registry import scan_modules, load_all_async
        m = scan_modules()
        assert len(m) > 0

    def test_load(self):
        from api.module_registry import load_all_async
        r = load_all_async(max_workers=4)
        assert r["loaded"] > 0


class TestInfra:
    def test_rbac(self):
        from api._rbac import check_permission
        assert check_permission("admin", "tool_execute")
        assert not check_permission("viewer", "admin_settings")

    def test_response(self):
        from api._response import StandardAPIResponse
        r = StandardAPIResponse.ok("test")
        assert r["success"]

    def test_config_loader(self):
        from api._config_loader import reload_config, get_config
        c = get_config()
        assert c is not None

    def test_multi_worker(self):
        from api._multi_worker import get_circuit_breaker, get_worker_count
        cb = get_circuit_breaker("test")
        assert cb.state == "closed"
        assert get_worker_count() >= 1

    def test_plugins(self):
        import api.plugins
        assert hasattr(api.plugins, "register_all")


class TestWorkflow:
    def test_engine(self):
        from api.workflow.engine import get_engine
        e = get_engine()
        assert e is not None

    def test_autonomous(self):
        from api.workflow.autonomous import AutonomousAgent
        a = AutonomousAgent()
        r = a.run("测试")
        assert r["status"] in ("completed", "chat")
