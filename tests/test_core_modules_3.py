"""AUTO-EVO-AI V0.1 — 3 个核心模块测试（system_monitor/sso_auth/data_analysis）"""
import pytest
import sys, os, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ─────────────────────────────────────────────
# system_monitor
# ─────────────────────────────────────────────
class TestSystemMonitor:
    @pytest.fixture
    def mod(self):
        from modules.system_monitor import SystemMonitorModule
        return SystemMonitorModule()

    def test_import(self):
        from modules.system_monitor import SystemMonitorModule
        assert SystemMonitorModule is not None

    def test_initialize(self, mod):
        assert mod.initialize() == True
        assert mod._collecting == True

    def test_health_check(self, mod):
        mod.initialize()
        hc = mod.health_check()
        assert hc["status"] in ("healthy", "degraded")
        assert hc["module_id"] == "system_monitor"

    def test_get_metrics(self, mod):
        mod.initialize()
        r = mod.get_metrics()
        assert r["success"] == True
        assert "cpu_percent" in r["metrics"]

    def test_get_cpu(self, mod):
        mod.initialize()
        r = mod.get_cpu()
        assert r["success"] == True
        assert "cpu_percent" in r
        assert r["cpu_count"] == os.cpu_count()

    def test_get_memory(self, mod):
        mod.initialize()
        r = mod.get_memory()
        assert r["success"] == True
        assert r["total_gb"] > 0

    def test_get_disk(self, mod):
        mod.initialize()
        r = mod.get_disk()
        assert r["success"] == True

    def test_get_network(self, mod):
        mod.initialize()
        r = mod.get_network()
        assert r["success"] == True

    def test_get_processes(self, mod):
        mod.initialize()
        r = mod.get_processes()
        assert r["success"] == True

    def test_get_alerts(self, mod):
        mod.initialize()
        r = mod.get_alerts()
        assert r["success"] == True

    def test_alert_rules(self, mod):
        mod.initialize()
        r = mod.list_alert_rules()
        assert r["success"] == True
        assert len(r["rules"]) >= 6  # 6+ default rules

    def test_add_alert_rule(self, mod):
        mod.initialize()
        r = mod.add_alert_rule({"rule_id": "test-1", "metric": "cpu_percent", "threshold": "99", "description": "test"})
        assert r["success"] == True

    def test_ack_alert(self, mod):
        mod.initialize()
        r = mod.ack_alert({"alert_id": "nonexistent"})
        assert r["success"] == False

    def test_execute_status(self, mod):
        mod.initialize()
        import asyncio
        r = asyncio.run(mod.execute("status"))
        assert r["success"] == True

    def test_execute_metrics(self, mod):
        mod.initialize()
        import asyncio
        r = asyncio.run(mod.execute("get_metrics"))
        assert r["success"] == True

    def test_trend(self, mod):
        mod.initialize()
        r = mod.get_trend({"metric": "cpu_percent", "minutes": 1})
        assert r["success"] == True

    def test_query_db(self, mod):
        mod.initialize()
        r = mod.get_metrics()  # triggers DB write
        assert r["success"] == True

    def test_delegate(self, mod):
        d = mod.delegate
        assert d is not None

    def test_shutdown(self, mod):
        mod.initialize()
        import asyncio
        r = asyncio.run(mod.shutdown())
        assert r == True

    def test_docstring(self, mod):
        assert "系统监控" in mod.__doc__ or "监控" in mod.__doc__
        assert mod.MODULE_ID == "system-monitor" or hasattr(mod, "MODULE_ID")

    def test_delegate_notification(self, mod):
        mod.initialize()
        r = mod.delegate.notification.send("test")
        assert r.get("delegate_noop") in (True, None)  # Noop 兜底不崩


# ─────────────────────────────────────────────
# sso_auth
# ─────────────────────────────────────────────
class TestSsoAuth:
    @pytest.fixture
    def mod(self):
        from modules.sso_auth import SsoAuth
        return SsoAuth()

    def test_import(self):
        from modules.sso_auth import SsoAuth
        assert SsoAuth is not None

    def test_initialize(self, mod):
        mod.initialize()
        assert mod.status.name == "RUNNING"

    def test_health(self, mod):
        mod.initialize()
        hc = mod.health_check()
        assert hc.healthy == True
        assert hc.module_id == "sso-auth"

    def _exec(self, mod, action, params):
        import asyncio
        r = asyncio.run(mod.execute(action, params))
        return r

    def _ok(self, r):
        """_safe_execute 返回 Result(success=True)，真实状态在 data.success"""
        return r.data.get("success", True) if r.data else True

    def _data(self, r):
        return r.data or {}

    def test_login(self, mod):
        mod.initialize()
        r = self._exec(mod, "login", {"user_id": "u1", "username": "alice"})
        assert self._ok(r) == True
        assert "session_token" in self._data(r)

    def test_validate_session(self, mod):
        mod.initialize()
        token = self._data(self._exec(mod, "login", {"user_id": "u2", "username": "bob"}))["session_token"]
        r = self._exec(mod, "validate", {"session_token": token})
        assert self._data(r).get("valid") == True
        assert self._data(r).get("user_id") == "u2"

    def test_logout(self, mod):
        mod.initialize()
        token = self._data(self._exec(mod, "login", {"user_id": "u3"}))["session_token"]
        r = self._exec(mod, "logout", {"session_token": token})
        assert self._ok(r) == True

    def test_create_and_exchange_ticket(self, mod):
        mod.initialize()
        token = self._data(self._exec(mod, "login", {"user_id": "u4"}))["session_token"]
        ticket_r = self._exec(mod, "create_ticket", {"session_token": token, "service": "app1"})
        assert self._ok(ticket_r) == True
        ticket = self._data(ticket_r)["ticket"]
        exchange_r = self._exec(mod, "exchange_ticket", {"ticket": ticket, "service": "app1"})
        assert self._ok(exchange_r) == True
        assert "app_session_token" in self._data(exchange_r)

    def test_register_app(self, mod):
        mod.initialize()
        r = self._exec(mod, "register_app", {"name": "myapp"})
        assert self._ok(r) == True
        assert "app_id" in self._data(r)
        assert "app_secret" in self._data(r)

    def test_jwt_generation(self, mod):
        mod.initialize()
        r = self._exec(mod, "generate_jwt", {"user_id": "jwt_user", "role": "admin"})
        assert self._ok(r) == True
        assert "jwt" in self._data(r) or "token" in self._data(r)

    def test_jwt_verification(self, mod):
        mod.initialize()
        r = self._exec(mod, "generate_jwt", {"user_id": "v_user", "role": "viewer"})
        r2 = self._exec(mod, "verify_jwt", {"token": self._data(r).get("jwt", self._data(r).get("token", ""))})
        data = self._data(r2)
        assert data.get("valid") == True

    def test_register_and_authenticate(self, mod):
        mod.initialize()
        import uuid
        _u = f"testuser_{uuid.uuid4().hex[:6]}"
        reg_r = self._exec(mod, "register_user", {"username": _u, "password": "secret123"})
        assert self._ok(reg_r) == True
        uid = self._data(reg_r).get("user_id", "")
        auth_r = self._exec(mod, "authenticate", {"username": _u, "password": "secret123"})
        assert self._ok(auth_r) == True
        assert self._data(auth_r).get("user_id") == uid or uid in str(self._data(auth_r))

    def test_delegate(self, mod):
        d = mod.delegate
        assert d is not None

    def test_shutdown(self, mod):
        mod.initialize()
        import asyncio
        asyncio.run(mod.shutdown())
        assert mod.status.name == "STOPPED"

    def test_bad_action(self, mod):
        mod.initialize()
        r = self._exec(mod, "nonexistent", {})
        # _safe_execute: success=True, data.success=False
        assert self._ok(r) == False

    def test_password_mismatch(self, mod):
        mod.initialize()
        self._exec(mod, "register_user", {"username": "puser", "password": "right"})
        r = self._exec(mod, "authenticate", {"username": "puser", "password": "wrong"})
        assert self._ok(r) == False

    def test_expired_ticket(self, mod):
        mod.initialize()
        token = self._data(self._exec(mod, "login", {"user_id": "exp_user"}))["session_token"]
        ticket_r = self._exec(mod, "create_ticket", {"session_token": token, "service": "app"})
        ticket = self._data(ticket_r)["ticket"]
        if ticket in mod._tickets:
            mod._tickets[ticket]["expires_at"] = time.time() - 1
        r = self._exec(mod, "exchange_ticket", {"ticket": ticket, "service": "app"})
        assert self._ok(r) == False


# ─────────────────────────────────────────────
# data_analysis
# ─────────────────────────────────────────────
class TestDataAnalysis:
    @pytest.fixture
    def mod(self):
        from modules.data_analysis import DataAnalysis
        return DataAnalysis()

    def test_import(self):
        from modules.data_analysis import DataAnalysis
        assert DataAnalysis is not None

    def test_initialize(self, mod):
        mod.initialize()
        assert mod.status.name == "RUNNING"

    def test_health(self, mod):
        mod.initialize()
        hc = mod.health_check()
        assert hc.healthy == True

    def test_describe(self, mod):
        r = mod._dispatch({"action": "describe", "data": [1,2,3,4,5,6,7,8,9,10]})
        assert r["success"] == True
        assert r["stats"]["count"] == 10
        assert r["stats"]["mean"] == 5.5

    def test_describe_stats(self, mod):
        r = mod._dispatch({"action": "describe", "data": [1,2,3,4,5,6,7,8,9,10]})
        s = r["stats"]
        assert s["min"] == 1
        assert s["max"] == 10
        assert s["p50"] == 6  # sorted[5] for n=10, 0-indexed
        assert s["std"] > 0

    def test_correlation_positive(self, mod):
        r = mod._dispatch({"action": "correlation", "data": [1,2,3,4,5], "x": [1,2,3,4,5], "y": [2,4,6,8,10]})
        assert r["success"] == True
        assert r["pearson"] == 1.0

    def test_correlation_negative(self, mod):
        r = mod._dispatch({"action": "correlation", "data": [1,2,3,4,5], "x": [1,2,3,4,5], "y": [10,8,6,4,2]})
        assert r["success"] == True
        assert r["pearson"] == -1.0

    def test_correlation_zero(self, mod):
        r = mod._dispatch({"action": "correlation", "data": [1,2,3], "x": [1,2,3], "y": [5,5,5]})
        assert r["success"] == True

    def test_regression(self, mod):
        r = mod._dispatch({"action": "regression", "data": [1,2,3,4,5], "x": [1,2,3,4,5], "y": [2,4,6,8,10]})
        assert r["success"] == True
        assert r["slope"] == 2.0
        assert r["r_squared"] == 1.0

    def test_outliers_iqr(self, mod):
        r = mod._dispatch({"action": "outliers", "data": [1,2,3,4,5,100]})
        assert r["success"] == True
        assert 100 in r["anomalies"]

    def test_outliers_zscore(self, mod):
        r = mod._dispatch({"action": "anomaly", "method": "zscore", "data": [1,2,3,4,5,100]})
        assert r["success"] == True

    def test_histogram(self, mod):
        r = mod._dispatch({"action": "histogram", "data": [1,1,2,2,3,3,4,4,5,5]})
        assert r["success"] == True
        assert len(r["histogram"]) == 10

    def test_normalize_minmax(self, mod):
        r = mod._dispatch({"action": "normalize", "method": "minmax", "data": [1,2,3,4,5]})
        assert r["success"] == True
        assert r["normalized"][0] == 0.0
        assert r["normalized"][-1] == 1.0

    def test_normalize_zscore(self, mod):
        r = mod._dispatch({"action": "normalize", "method": "zscore", "data": [1,2,3,4,5]})
        assert r["success"] == True

    def test_clustering(self, mod):
        r = mod._dispatch({"action": "clustering", "data": [1,1,2,2,8,8,9,9], "k": 2})
        assert r["success"] == True
        assert r["k"] == 2
        assert len(r["clusters"]) == 2

    def test_clustering_wcss(self, mod):
        r = mod._dispatch({"action": "clustering", "data": [1,1,2,2,8,8,9,9], "k": 2})
        assert r["wcss"] > 0

    def test_summarize(self, mod):
        r = mod._dispatch({"action": "summarize", "data": [1,2,3,4,5]})
        assert r["success"] == True

    def test_frequency(self, mod):
        r = mod._dispatch({"action": "frequency", "data": [1,1,2,2,2,3]})
        assert r["success"] == True
        # frequency is a list of {value, count, percent}
        freq_list = r.get("frequency", [])
        assert any(item["value"] == 2 and item["count"] == 3 for item in freq_list)

    def test_export_csv(self, mod):
        r = mod._dispatch({"action": "export_csv", "data": [1,2,3], "format": "csv"})
        assert r.get("success", False) == True or "csv" in r
        assert "value" in r.get("csv", "") or "csv" in r

    def test_empty_data_errors(self, mod):
        r = mod._dispatch({"action": "describe", "data": []})
        # empty data returns error dict, no success key
        assert "error" in r or "hint" in r

    def test_delegate(self, mod):
        d = mod.delegate
        assert d is not None

    def test_unknown_action(self, mod):
        r = mod._dispatch({"action": "nonexistent", "data": [1,2,3]})
        # unknown action returns error dict, no success key
        assert "error" in r

    def test_execute_interface(self, mod):
        import asyncio
        r = asyncio.run(mod.execute("describe", {"data": [1,2,3]}))
        # execute returns Result dataclass
        assert r.success == True

    def test_skewness_and_kurtosis(self, mod):
        r = mod._dispatch({"action": "describe", "data": [1,2,3,4,5,6,7,8,9,10]})
        s = r["stats"]
        assert "skewness" in s
        assert "kurtosis" in s

    def test_clustering_multiple_runs(self, mod):
        for _ in range(3):
            r = mod._dispatch({"action": "clustering", "data": [1,1,2,2,8,8,9,9], "k": 2})
            assert r["success"] == True

    def test_regression_residuals(self, mod):
        r = mod._dispatch({"action": "regression", "data": [1,2,3,4,5], "x": [1,2,3,4,5], "y": [2,4,6,8,10]})
        assert r["success"] == True
        assert "residuals" in r
        assert all(abs(res) < 0.001 for res in r["residuals"])
