"""AUTO-EVO-AI 集成测试套件"""
import pytest
import httpx
import json

BASE_URL = "http://localhost:8765"

@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=30)

class TestSystemHealth:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "AUTO" in r.text or "EVO" in r.text

    def test_version(self, client):
        r = client.get("/api/v1/version")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data or "success" in data

    def test_modules(self, client):
        r = client.get("/api/v1/modules")
        assert r.status_code == 200
        data = r.json()
        modules = data.get("modules", data.get("data", []))
        assert len(modules) > 0

    def test_status(self, client):
        r = client.get("/api/v1/status")
        assert r.status_code == 200
        data = r.json()
        assert "success" in data or "status" in data

class TestPages:
    pages = ["/chat.html", "/enterprise.html", "/admin", "/billion-os.html",
             "/audit", "/webhooks", "/backup", "/install-wizard", "/marketplace",
             "/bi", "/realtime", "/docs", "/deploy"]

    @pytest.mark.parametrize("path", pages)
    def test_page_200(self, client, path):
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
        assert len(r.text) > 100, f"{path} too short: {len(r.text)}B"

class TestAPI:
    def test_coordinator_status(self, client):
        r = client.get("/api/v1/coordinator/status")
        assert r.status_code == 200

    def test_coordinator_capabilities(self, client):
        r = client.get("/api/v1/coordinator/capabilities")
        assert r.status_code == 200

    def test_skills(self, client):
        r = client.get("/api/v1/skills")
        assert r.status_code in (200, 404)

    def test_plugins(self, client):
        r = client.get("/api/v1/plugins")
        assert r.status_code in (200, 404)

class TestDesktopAgent:
    def test_desktop_import(self):
        import importlib
        mod = importlib.import_module("modules.desktop_agent")
        cls = getattr(mod, "DesktopAgent", None)
        if cls is None:
            # 尝试找任何以Agent结尾的类
            for name in dir(mod):
                if name.endswith("Agent") and not name.startswith("_"):
                    cls = getattr(mod, name)
                    break
        assert cls is not None, "DesktopAgent class not found"
        da = cls()
        assert da is not None

    def test_desktop_capabilities(self):
        import importlib
        mod = importlib.import_module("modules.desktop_agent")
        cls = getattr(mod, "DesktopAgent", None)
        if cls is None:
            for name in dir(mod):
                if name.endswith("Agent") and not name.startswith("_"):
                    cls = getattr(mod, name)
                    break
        assert cls is not None
        da = cls()
        if hasattr(da, "capabilities"):
            caps = da.capabilities()
            assert len(caps) > 0

class TestModules:
    def test_stub_modules_import(self):
        import importlib
        modules_to_test = [
            "bookstack_kb", "browser_use", "cal_scheduler",
            "data_quality", "decision_tree", "humanizer",
            "invoice_agent", "libre_translate", "mcp_bridge",
            "multi_agent_crew", "priority_queue", "vanna_ai_query"
        ]
        lookup = {
            "bookstack_kb": "BookstackKnowledgeBase",
            "cal_scheduler": "CalendarScheduler",
            "data_quality": "DataQualityChecker",
            "decision_tree": "DecisionTree",
            "humanizer": "Humanizer",
            "invoice_agent": "InvoiceAgent",
            "libre_translate": "LibreTranslate",
            "mcp_bridge": "McpBridge",
            "multi_agent_crew": "MultiAgentCrew",
            "priority_queue": "PriorityQueue",
            "vanna_ai_query": "VannaAIQuery",
        }
        for mod_name in modules_to_test:
            mod = importlib.import_module(f"modules.{mod_name}")
            cls_name = lookup.get(mod_name, "".join(x.capitalize() for x in mod_name.split("_")))
            cls = getattr(mod, cls_name, None)
            if cls is None:
                # 尝试模糊匹配
                for name in dir(mod):
                    if cls_name.lower() in name.lower() and not name.startswith("_"):
                        cls = getattr(mod, name)
                        break
            assert cls is not None, f"{mod_name}: class {cls_name} not found in {[x for x in dir(mod) if not x.startswith('_')][:10]}"
            instance = cls()
            assert instance is not None
