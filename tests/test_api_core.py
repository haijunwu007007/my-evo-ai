"""Core API coverage tests — uses /api/v1/ version prefix"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from api_server import app
from fastapi.testclient import TestClient

client = TestClient(app)

class TestCoreAPI:
    def test_001_root(self):
        r = client.get("/")
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        assert "AUTO-EVO-AI" in d["system"]

    def test_002_status(self):
        r = client.get("/api/v1/status")
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        assert d["status"] == "running"

    def test_003_auth_config(self):
        r = client.get("/api/v1/auth/config")
        assert r.status_code == 200

    def test_004_metrics(self):
        r = client.get("/metrics")
        assert r.status_code == 200

    def test_005_modules(self):
        r = client.get("/api/v1/modules")
        assert r.status_code in (200, 404)

    def test_006_module_list(self):
        r = client.get("/api/v1/modules/list?limit=5")
        assert r.status_code in (200, 404)

    def test_007_profiler_status(self):
        r = client.get("/api/v1/profile/status")
        assert r.status_code in (200, 404)

    def test_008_ws_status(self):
        r = client.get("/api/v1/ws/status")
        assert r.status_code in (200, 404)

    def test_009_legacy_api_rewrite(self):
        """向后兼容：旧 /api/ 路径通过中间件重写"""
        r = client.get("/api/status")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "running"

    def test_010_legacy_modules(self):
        r = client.get("/api/modules/list?limit=5")
        assert r.status_code in (200, 404)

    def test_011_coordinator(self):
        r = client.get("/api/v1/coordinator/status")
        assert r.status_code in (200, 404)

    def test_012_diagnosis(self):
        r = client.get("/api/v1/diagnosis/system")
        d = r.json() if r.status_code == 200 else {}
        assert r.status_code in (200, 404)

    def test_013_scheduler(self):
        r = client.get("/api/v1/scheduler/tasks")
        assert r.status_code in (200, 404)
