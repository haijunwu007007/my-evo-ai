"""Core API coverage tests — tests/test_api_core.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from api_server import app
from fastapi.testclient import TestClient

client = TestClient(app)

class TestCoreAPI:
    """核心API端点的集成测试"""

    def test_001_root(self):
        r = client.get("/")
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        assert "AUTO-EVO-AI" in d["system"]
        assert d["modules_total"] >= 0

    def test_002_status(self):
        r = client.get("/api/status")
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        assert d["status"] == "running"
        assert d["api_version"] == "V0.1"

    def test_003_auth_config(self):
        r = client.get("/api/auth/config")
        assert r.status_code == 200
        d = r.json()
        assert "enabled" in d

    def test_004_modules(self):
        r = client.get("/api/modules")
        assert r.status_code == 200
        d = r.json()
        assert "modules" in d or "success" in d

    def test_005_coordinator_status(self):
        r = client.get("/api/coordinator/status")
        assert r.status_code == 200

    def test_006_diagnosis_system(self):
        r = client.get("/api/diagnosis/system")
        assert r.status_code == 200

    def test_007_profiler_status(self):
        r = client.get("/api/profile/status")
        assert r.status_code == 200
        d = r.json()
        assert "enabled" in d

    def test_008_metrics(self):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "# AUTO-EVO-AI" in r.text
        assert "evo_system_uptime_seconds" in r.text

    def test_009_manifest(self):
        r = client.get("/manifest.json")
        assert r.status_code == 200

    def test_010_auth_login(self):
        r = client.post("/api/auth/login", json={"username": "admin"})
        assert r.status_code == 200
        d = r.json()
        assert "access_token" in d

    def test_011_auth_verify(self):
        r = client.get("/api/auth/verify?token=")
        assert r.status_code == 200
        d = r.json()
        assert d["valid"] is False
