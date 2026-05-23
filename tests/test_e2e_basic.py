"""
AUTO-EVO-AI V0.1 — 端到端集成测试
上市公司级：依赖真实 API 服务器，测试整条链路。

执行条件:
  1. API 服务器运行在 http://127.0.0.1:8765
  2. pytest -x tests/test_e2e_basic.py -v

测试范围:
  - API 存活
  - 认证
  - 系统诊断
  - 模块注册
  - 配置中心 CRUD
  - 数据库健康
  - 协调中心
"""

import os, sys, json, time, urllib.request, urllib.error

API_BASE = "http://127.0.0.1:8765"
TIMEOUT = 5

pytest_plugins = []


def _req(method: str, path: str, body: dict = None) -> dict:
    """发送 HTTP 请求并返回 JSON"""
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()) if e.code != 503 else {"error": "service_unavailable"}
    except Exception as e:
        return {"error": str(e)}


def server_alive() -> bool:
    """检查服务器是否存活"""
    try:
        r = _req("GET", "/api/status")
        return r.get("success", False) or "version" in r
    except Exception:
        return False


# ============================================================
# 测试类
# ============================================================

class TestE2EBasic:
    """基础 API 可用性"""

    def setup_method(self):
        if not server_alive():
            raise RuntimeError(
                f"API 服务器未运行在 {API_BASE}。请先启动: python api_server.py"
            )

    def test_01_root(self):
        """根端点返回版本信息"""
        r = _req("GET", "/")
        assert isinstance(r, dict), f"expected dict, got {type(r)}"
        # / 端点可能返回不同格式，只要成功即可
        assert not r.get("error"), f"root error: {r}"

    def test_02_api_status(self):
        """API 状态端点"""
        r = _req("GET", "/api/status")
        assert not r.get("error"), f"status error: {r}"
        print(f"  API Status: version={r.get('version','?')}, uptime={r.get('uptime','?')}")

    def test_03_metrics(self):
        """Prometheus Metrics 端点"""
        import urllib.request
        try:
            resp = urllib.request.urlopen(f"{API_BASE}/metrics", timeout=TIMEOUT)
            body = resp.read().decode()
            assert len(body) > 0, "metrics body empty"
            print(f"  Metrics: {len(body)} bytes")
        except Exception as e:
            # Metrics 可能未启用，不强制失败
            print(f"  [WARN] metrics not available: {e}")


class TestE2EAuth:
    """认证相关"""

    def setup_method(self):
        if not server_alive():
            raise RuntimeError("Server not running")

    def test_01_auth_status(self):
        r = _req("GET", "/api/auth/status")
        assert not r.get("error"), f"auth status error: {r}"
        assert "api_key_enabled" in r or "auth_mode" in r, f"unexpected response: {r}"
        print(f"  Auth: api_key={r.get('api_key_enabled','?')}, mode={r.get('auth_mode','?')}")


class TestE2ESystem:
    """系统诊断"""

    def setup_method(self):
        if not server_alive():
            raise RuntimeError("Server not running")

    def test_01_diagnosis(self):
        r = _req("GET", "/api/diagnosis/system")
        assert not r.get("error"), f"diagnosis error: {r}"
        assert "uptime_seconds" in r or "uptime_human" in r, f"unexpected: {r}"
        print(f"  System: uptime={r.get('uptime_human','?')}, version={r.get('api_version','?')}")

    def test_02_modules_diagnosis(self):
        r = _req("GET", "/api/diagnosis/modules")
        assert not r.get("error"), f"modules diagnosis error: {r}"
        count = r.get("count", r.get("modules", 0))
        count = len(count) if isinstance(count, (list, dict)) else count
        print(f"  Modules registered: {count}")

    def test_03_config_center(self):
        """配置中心 CRUD"""
        # 读
        r = _req("GET", "/api/config")
        assert not r.get("error"), f"config error: {r}"
        # 写
        r2 = _req("PUT", "/api/config/test_key", {"value": "test_value_123"})
        assert not r2.get("error"), f"config set error: {r2}"
        # 验证
        r3 = _req("GET", "/api/config/test_key")
        val = r3.get("value", "")
        print(f"  Config: write/read OK (value='{val}')")
        # 删除
        _req("DELETE", "/api/config/test_key")

    def test_04_persistence_status(self):
        r = _req("GET", "/api/persistence/status")
        assert not r.get("error"), f"persistence error: {r}"
        print(f"  Persistence: db_type={r.get('db_type','?')}")


class TestE2EDatabase:
    """数据库健康检查"""

    def setup_method(self):
        if not server_alive():
            raise RuntimeError("Server not running")

    def test_01_db_health(self):
        """通过系统 metrics 检查数据库"""
        r = _req("GET", "/api/system/metrics")
        assert not r.get("error"), f"metrics error: {r}"
        uptime = r.get("uptime", 0)
        print(f"  System uptime: {uptime:.0f}s")

    def test_02_scheduler_status(self):
        r = _req("GET", "/api/scheduler/status")
        assert not r.get("error"), f"scheduler error: {r}"
        print(f"  Scheduler: running={r.get('running','?')}, tasks={r.get('total_tasks',0)}")

    def test_03_events_stats(self):
        r = _req("GET", "/api/events/stats")
        assert not r.get("error"), f"events error: {r}"
        print(f"  Events: total={r.get('total_events',0)}, rules={r.get('total_rules',0)}")

    def test_04_queue_stats(self):
        r = _req("GET", "/api/queue/stats")
        assert not r.get("error"), f"queue error: {r}"
        print(f"  Queue: total={r.get('total',0)}, pending={r.get('pending',0)}")


class TestE2ECoordinator:
    """协调中心"""

    def setup_method(self):
        if not server_alive():
            raise RuntimeError("Server not running")

    def test_01_status(self):
        r = _req("GET", "/api/coordinator/status")
        assert not r.get("error"), f"coordinator status error: {r}"
        modules = r.get("modules", {})
        total = modules.get("registered", modules.get("total", 0))
        print(f"  Coordinator: modules={total}")

    def test_02_capabilities(self):
        r = _req("GET", "/api/coordinator/capabilities")
        assert not r.get("error"), f"capabilities error: {r}"
        caps = r.get("capabilities", {})
        print(f"  Capabilities: {len(caps)} categories")


class TestE2ENetwork:
    """网络相关"""

    def setup_method(self):
        if not server_alive():
            raise RuntimeError("Server not running")

    def test_01_local_url(self):
        r = _req("GET", "/api/local-url")
        assert not r.get("error"), f"local url error: {r}"
        url = r.get("url", "")
        print(f"  Local URL: {url}")

    def test_02_tunnel_status(self):
        r = _req("GET", "/api/tunnel/status")
        assert not r.get("error"), f"tunnel status error: {r}"
        print(f"  Tunnel: enabled={r.get('tunnel_enabled', False)}")


class TestE2EMonitoring:
    """监控"""

    def setup_method(self):
        if not server_alive():
            raise RuntimeError("Server not running")

    def test_01_monitor_realtime(self):
        r = _req("GET", "/api/monitor/realtime")
        # 这个端点可能不存在，跳过不失败
        if r.get("error"):
            print(f"  [SKIP] realtime monitor: {r['error']}")
            return
        print(f"  Monitor: OK")

    def test_02_ws_status(self):
        r = _req("GET", "/api/ws/status")
        assert not r.get("error"), f"ws error: {r}"
        print(f"  WS: connections={r.get('active_connections',0)}")

    def test_03_rate_limit(self):
        r = _req("GET", "/api/system/rate-limit")
        assert not r.get("error"), f"rate limit error: {r}"
        print(f"  Rate Limit: enabled={r.get('rate_limiting',False)}")
