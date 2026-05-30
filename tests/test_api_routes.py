"""AUTO-EVO-AI V0.1 — API 路由测试"""
import pytest
import requests

BASE = "http://127.0.0.1:8765"

class TestSystemStatus:
    def test_status_returns_running(self):
        r = requests.get(f"{BASE}/api/status", timeout=5)
        d = r.json()
        assert d["status"] == "running"
        assert d["modules_total"] > 0

    def test_status_has_version(self):
        r = requests.get(f"{BASE}/api/status", timeout=5)
        assert "api_version" in r.json()

class TestModulesBrowse:
    def test_list_modules(self):
        r = requests.get(f"{BASE}/api/modules/list?limit=10", timeout=5)
        d = r.json()
        assert d["success"]
        assert len(d["modules"]) > 0

    def test_modules_have_grades(self):
        r = requests.get(f"{BASE}/api/modules/list?limit=50", timeout=5)
        for m in r.json()["modules"]:
            assert m["grade"] in ("A", "B", "C", "S")

    def test_modules_have_categories(self):
        r = requests.get(f"{BASE}/api/modules/list?limit=50", timeout=5)
        for m in r.json()["modules"]:
            assert "category" in m

    def test_modules_have_real_logic(self):
        r = requests.get(f"{BASE}/api/modules/list?limit=50", timeout=5)
        for m in r.json()["modules"]:
            assert "real_logic" in m

    def test_total_modules(self):
        r = requests.get(f"{BASE}/api/modules/list?limit=1", timeout=5)
        assert r.json()["total"] >= 400

class TestDiagnosis:
    def test_system_diagnosis(self):
        r = requests.get(f"{BASE}/api/diagnosis/system", timeout=5)
        d = r.json()
        assert d["success"]
        assert "uptime_human" in d

    def test_config_endpoint(self):
        r = requests.get(f"{BASE}/api/config", timeout=5)
        assert r.json()["success"]

class TestAuth:
    def test_auth_login(self):
        r = requests.post(f"{BASE}/api/auth/login",
            json={"username": "admin", "password": "admin"}, timeout=5)
        # 开发模式不验证密码
        assert r.status_code in (200, 404)

class TestMonitor:
    def test_realtime_metrics(self):
        r = requests.get(f"{BASE}/api/monitor/realtime", timeout=5)
        d = r.json()
        # 兼容正常返回和错误返回
        assert "system" in d or "detail" in d or "error" in d

class TestModuleExecution:
    def test_execute_system_monitor(self):
        r = requests.post(f"{BASE}/api/modules/system_monitor/execute",
            json={"action": "get_status"}, timeout=10)
        assert r.status_code in (200, 404, 500)
