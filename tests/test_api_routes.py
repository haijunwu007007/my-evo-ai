"""AUTO-EVO-AI V0.1 — API 路由测试（/api/v1/ 版本前缀）"""
import pytest
import requests

BASE = "http://127.0.0.1:8765"


class TestSystemStatus:
    def test_status_returns_running(self):
        r = requests.get(f"{BASE}/api/v1/status", timeout=5)
        d = r.json()
        assert d["status"] == "running"
        assert d["modules_total"] > 0

    def test_status_has_version(self):
        r = requests.get(f"{BASE}/api/v1/status", timeout=5)
        assert "api_version" in r.json()


class TestModulesBrowse:
    def test_list_modules(self):
        r = requests.get(f"{BASE}/api/v1/modules/list?limit=10", timeout=5)
        d = r.json()
        assert d["success"]
        assert len(d["modules"]) > 0

    def test_modules_have_grades(self):
        r = requests.get(f"{BASE}/api/v1/modules/list?limit=50", timeout=5)
        for m in r.json()["modules"]:
            assert "grade" in m

    def test_modules_have_categories(self):
        r = requests.get(f"{BASE}/api/v1/modules/list?limit=50", timeout=5)
        for m in r.json()["modules"]:
            assert "category" in m

    def test_modules_have_real_logic(self):
        r = requests.get(f"{BASE}/api/v1/modules/list?limit=50", timeout=5)
        for m in r.json()["modules"]:
            assert "real_logic" in m

    def test_total_modules(self):
        r = requests.get(f"{BASE}/api/v1/modules/list?limit=1", timeout=5)
        assert r.json()["total"] >= 400


class TestDiagnosis:
    def test_system_diagnosis(self):
        r = requests.get(f"{BASE}/api/v1/diagnosis/system", timeout=5)
        d = r.json()
        assert d["success"]
        assert "status" in d

    def test_config_endpoint(self):
        r = requests.get(f"{BASE}/api/v1/config", timeout=5)
        assert "success" in r.json() or isinstance(r.json(), list)


class TestAuth:
    def test_auth_config(self):
        r = requests.get(f"{BASE}/api/v1/auth/config", timeout=5)
        assert r.status_code == 200


class TestMonitor:
    def test_realtime_metrics(self):
        r = requests.get(f"{BASE}/api/v1/monitor/realtime", timeout=5)
        d = r.json()
        assert isinstance(d, dict)

    def test_legacy_api_still_works(self):
        """向后兼容：旧 /api/ 路径应被中间件重写"""
        r = requests.get(f"{BASE}/api/status", timeout=5)
        d = r.json()
        assert d["status"] == "running"
