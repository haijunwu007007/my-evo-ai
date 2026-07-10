"""
AUTO-EVO-AI V0.1 — API 性能基准测试
=====================================
测试 /api/status /api/modules /dashboard 在 1/10 并发下的响应时间。
"""

import os, time, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 检查服务是否存活 ──
try:
    import httpx
    _client = httpx.Client(base_url="http://127.0.0.1:8765", timeout=3.0)
    _resp = _client.get("/")
    _SERVER_AVAILABLE = _resp.status_code == 200
except Exception:
    _SERVER_AVAILABLE = False

# ── 运行状态 ──
_bench_data: dict = {}
_bench_ok = True


def _skip_no_server():
    if not _SERVER_AVAILABLE:
        pytest.skip("API 服务未运行在 127.0.0.1:8765，跳过性能测试")


# ═══════════════════════════════════════════════════════
# 基准端点测试（1 并发）
# ═══════════════════════════════════════════════════════

@pytest.mark.benchmark
def test_root_latency():
    _skip_no_server()
    t0 = time.time()
    resp = _client.get("/")
    elapsed = (time.time() - t0) * 1000
    assert resp.status_code == 200
    assert elapsed < 500, f"根端点延迟过高: {elapsed:.0f}ms"
    _bench_data["root_ms"] = elapsed


@pytest.mark.benchmark
def test_status_latency():
    _skip_no_server()
    t0 = time.time()
    resp = _client.get("/api/status")
    elapsed = (time.time() - t0) * 1000
    assert resp.status_code == 200
    assert elapsed < 500, f"状态端点延迟过高: {elapsed:.0f}ms"
    _bench_data["status_ms"] = elapsed


@pytest.mark.benchmark
def test_modules_latency():
    _skip_no_server()
    t0 = time.time()
    resp = _client.get("/api/modules")
    elapsed = (time.time() - t0) * 1000
    assert resp.status_code == 200
    assert elapsed < 2000, f"模块列表延迟过高: {elapsed:.0f}ms"
    _bench_data["modules_ms"] = elapsed


@pytest.mark.benchmark
def test_dashboard_latency():
    _skip_no_server()
    t0 = time.time()
    resp = _client.get("/dashboard")
    elapsed = (time.time() - t0) * 1000
    assert resp.status_code == 200, f"Dashboard 返回 {resp.status_code}"
    assert elapsed < 500, f"Dashboard 延迟过高: {elapsed:.0f}ms"
    _bench_data["dashboard_ms"] = elapsed


# ═══════════════════════════════════════════════════════
# 并发测试
# ═══════════════════════════════════════════════════════

@pytest.mark.benchmark
def test_concurrent_status():
    """10 并发请求 /api/status（同步）"""
    _skip_no_server()
    t0 = time.time()
    ok = 0
    for _ in range(10):
        r = _client.get("/api/status")
        if r.status_code == 200:
            ok += 1
    elapsed = (time.time() - t0) * 1000
    assert ok == 10, f"10 并发 OK={ok}/10"
    assert elapsed < 3000, f"10 并发总耗时过高: {elapsed:.0f}ms"
    _bench_data["concurrent_10_ms"] = elapsed


@pytest.mark.benchmark
def test_concurrent_dashboard():
    """10 并发请求 /dashboard（同步）"""
    _skip_no_server()
    t0 = time.time()
    ok = 0
    for _ in range(10):
        r = _client.get("/dashboard")
        if r.status_code == 200:
            ok += 1
    elapsed = (time.time() - t0) * 1000
    assert ok == 10, f"10 Dashboard并发 OK={ok}/10"
    assert elapsed < 5000, f"10 Dashboard并发总耗时过高: {elapsed:.0f}ms"
    _bench_data["dashboard_concurrent_10_ms"] = elapsed


# ═══════════════════════════════════════════════════════
# 报告输出
# ═══════════════════════════════════════════════════════


@pytest.fixture(scope="session", autouse=True)
def _bench_report(request):
    yield
    if not _bench_data:
        return
    logger.info())
    logger.info("=" * 60))
    print("  AUTO-EVO-AI V0.1 — 性能基准报告")
    logger.info(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}"))
    logger.info("=" * 60))
    for metric, value_ms in sorted(_bench_data.items()):
        el = 2000 if "modules" in metric or "concurrent" in metric else 500
        status = "✅" if value_ms < el else "⚠️"
        logger.info(f"  {status} {metric:30s} = {value_ms:8.1f} ms"))
    avg = sum(_bench_data.values()) / len(_bench_data) if _bench_data else 0
    logger.info(f"  {'─' * 60}"))
    logger.info(f"  平均延迟: {avg:.0f} ms  |  采样数: {len(_bench_data)}"))
    logger.info("=" * 60))
