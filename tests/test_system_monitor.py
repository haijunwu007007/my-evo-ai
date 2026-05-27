"""Test suite for system_monitor module"""
import os, sys, time, json, asyncio, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.system_monitor import SystemMonitorModule, MetricPoint

@pytest.fixture
def sm():
    m = SystemMonitorModule()
    m.initialize()
    return m

class TestSystemMonitorCore:
    def test_init(self, sm):
        assert sm._collect_thread is not None
        assert sm._collect_thread.is_alive()
        assert len(sm._alert_rules) >= 7

    def test_collect_metrics(self, sm):
        time.sleep(0.5)
        assert "cpu_percent" in sm._last_metrics
        assert "memory_percent" in sm._last_metrics

    def test_get_metrics(self, sm):
        r = sm.get_metrics()
        assert r["success"] is True
        assert "cpu_percent" in r["metrics"]

    def test_get_cpu(self, sm):
        r = sm.get_cpu()
        assert r["success"] is True
        assert r["cpu_count"] == os.cpu_count()

    def test_get_memory(self, sm):
        r = sm.get_memory()
        assert r["success"] is True
        assert r["total_gb"] > 0

    def test_get_disk(self, sm):
        r = sm.get_disk()
        assert r["success"] is True

    def test_get_network(self, sm):
        r = sm.get_network()
        assert r["success"] is True

    def test_get_alerts(self, sm):
        r = sm.get_alerts()
        assert r["success"] is True

    def test_add_alert_rule(self, sm):
        r = sm.add_alert_rule({"rule_id":"test-rule","metric":"cpu_percent","operator":"gt","threshold":99,"description":"test"})
        assert r["success"] is True
        assert "test-rule" in sm._alert_rules

    def test_get_trend(self, sm):
        for i in range(10):
            sm._metric_history.setdefault("cpu_percent", []).append(MetricPoint(timestamp=time.time()-i*10, value=50+i))
        r = sm.get_trend({"metric":"cpu_percent","minutes":5})
        assert r["success"] is True

    def test_health_check(self, sm):
        r = sm.health_check()
        assert r["status"] in ("healthy", "degraded")

    def test_query_db(self, sm):
        r = sm.query_db({"table":"sysmon_metrics","limit":5})
        assert r["success"] is True

    def test_execute_get_metrics(self, sm):
        r = asyncio.run(sm.execute("get_metrics"))
        assert r["success"] is True

    def test_execute_unknown(self, sm):
        r = asyncio.run(sm.execute("nonexistent"))
        assert r["success"] is False

    def test_shutdown(self, sm):
        sm.shutdown()
        assert sm._collecting is False

    def test_delegate_available(self, sm):
        assert sm.delegate is not None
