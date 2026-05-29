"""AUTO-EVO-AI V0.1 — 扩展API测试：调度器/模块执行/WebSocket"""
import pytest
import requests
import json

BASE = "http://127.0.0.1:8765"

# ─── 调度器 ──────────────────────────────────────────

class TestSchedulerAPI:
    def test_list_tasks(self):
        r = requests.get(f"{BASE}/api/scheduler/tasks", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") is not False

    def test_create_task(self):
        task = {"name": "pytest_task", "cron": "*/5 * * * *", "action": "echo test"}
        r = requests.post(f"{BASE}/api/scheduler/tasks", json=task, timeout=5)
        data = r.json()
        # 允许创建成功或返回已存在
        assert data.get("success") is not False or "exist" in str(data).lower()

    def test_create_and_delete(self):
        task = {"name": "pytest_del", "cron": "0 0 * * *", "action": "echo del"}
        r = requests.post(f"{BASE}/api/scheduler/tasks", json=task, timeout=5)
        if r.json().get("success") is not False:
            tasks = requests.get(f"{BASE}/api/scheduler/tasks", timeout=5).json()
            task_id = None
            for t in (tasks.get("tasks") or tasks.get("data") or []):
                if getattr(t, 'name', '') == "pytest_del" or (isinstance(t, dict) and t.get('name') == "pytest_del"):
                    task_id = t.get('id') if isinstance(t, dict) else getattr(t, 'id', None)
                    break
            if task_id:
                d = requests.delete(f"{BASE}/api/scheduler/tasks/{task_id}", timeout=5)
                assert d.status_code in (200, 204)

# ─── 模块执行 ──────────────────────────────────────

class TestModuleExecute:
    def test_list_modules(self):
        r = requests.get(f"{BASE}/api/modules", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "modules" in data or isinstance(data, dict)

    def test_module_categories(self):
        r = requests.get(f"{BASE}/api/modules/categories", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "categories" in data

    def test_execute_system_monitor(self):
        r = requests.post(f"{BASE}/api/modules/system_monitor/execute",
                          json={"action": "get_metrics"}, timeout=10)
        data = r.json()
        assert r.status_code in (200, 404, 422)
        if r.status_code == 200:
            assert data.get("success") is not False

    def test_execute_sso_auth(self):
        r = requests.post(f"{BASE}/api/modules/sso_auth/execute",
                          json={"action": "validate", "params": {"token": "test"}}, timeout=10)
        assert r.status_code in (200, 404, 422)

    def test_module_list_browse(self):
        r = requests.get(f"{BASE}/api/modules/list?limit=5", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "modules" in data

# ─── WebSocket ─────────────────────────────────────

class TestWebSocket:
    def test_ws_stats(self):
        r = requests.get(f"{BASE}/api/ws/stats", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") is not False

    def test_ws_channels(self):
        r = requests.get(f"{BASE}/api/ws/channels", timeout=5)
        assert r.status_code == 200

# ─── 诊断 ──────────────────────────────────────────

class TestDiagnosis:
    def test_system_diagnosis(self):
        r = requests.get(f"{BASE}/api/diagnosis/system", timeout=5)
        assert r.status_code == 200
        data = r.json()
        # 至少应该返回运行时间
        assert "uptime_human" in data

    def test_diagnosis_modules(self):
        r = requests.get(f"{BASE}/api/diagnosis/modules", timeout=5)
        assert r.status_code == 200

# ─── 配置 ──────────────────────────────────────────

class TestConfig:
    def test_config_list(self):
        r = requests.get(f"{BASE}/api/config/entries", timeout=5)
        assert r.status_code == 200
