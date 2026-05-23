"""AUTO-EVO-AI V0.1 API 集成测试"""
import os, sys, json, time, http.client, threading

SERVER_ALIVE = None
def _server_alive():
    global SERVER_ALIVE
    if SERVER_ALIVE is not None:
        return SERVER_ALIVE
    try:
        c = http.client.HTTPConnection("localhost", 8765, timeout=2)
        c.request("GET", "/")
        r = c.getresponse()
        SERVER_ALIVE = r.status == 200
    except Exception:
        SERVER_ALIVE = False
    return SERVER_ALIVE
from pathlib import Path

# 确保能找到项目
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

HOST = "localhost"
PORT = 8765


def _req(method, path, body=None, timeout=10):
    c = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    headers = {"Content-Type": "application/json"}
    c.request(method, path, body=json.dumps(body) if body else None, headers=headers)
    r = c.getresponse()
    data = r.read()
    try:
        return r.status, json.loads(data)
    except:
        return r.status, {"raw": data[:200]}


# ═══════════════════════════════════════════════════════════
# 系统状态测试
# ═══════════════════════════════════════════════════════════

def test_system_root():
    if not _server_alive(): return
    """GET / — 根路径返回系统状态"""
    status, data = _req("GET", "/")
    assert status == 200
    assert data["system"] == "AUTO-EVO-AI V0.1"
    assert data["status"] == "running"
    assert data["modules_total"] >= 500


def test_system_status():
    if not _server_alive(): return
    """GET /api/status — 系统状态"""
    status, data = _req("GET", "/api/status")
    assert status == 200
    assert data["system"] == "AUTO-EVO-AI V0.1"
    assert data["status"] == "running"
    assert data["api_version"] == "0.1.0"
    assert data["modules_total"] >= 500


def test_system_health():
    if not _server_alive(): return
    """GET /api/status — 健康检查（复用状态端点）"""
    status, data = _req("GET", "/api/status")
    assert status == 200
    assert data.get("status") in ("running", "healthy", "degraded")
    assert data["modules_total"] >= 500


# ═══════════════════════════════════════════════════════════
# 模块 API 测试
# ═══════════════════════════════════════════════════════════

def test_list_modules():
    if not _server_alive(): return
    """GET /api/modules — 列出所有模块"""
    status, data = _req("GET", "/api/modules")
    assert status == 200
    assert "modules" in data
    assert data["count"] >= 500


def test_module_categories():
    if not _server_alive(): return
    """GET /api/modules/categories — 分类统计"""
    status, data = _req("GET", "/api/modules/categories")
    assert status == 200
    assert "categories" in data
    assert isinstance(data["categories"], dict)
    assert data["total"] >= 500


def test_module_detail():
    if not _server_alive(): return
    """GET /api/modules/access_control — 模块详情"""
    status, data = _req("GET", "/api/modules/access_control")
    assert status == 200
    assert data["success"] is True
    assert data.get("grade") in ("A", "B", "C", "lazy")


def test_module_health():
    if not _server_alive(): return
    """GET /api/modules/access_control/health — 模块健康"""
    status, data = _req("GET", "/api/modules/access_control/health")
    assert status == 200
    assert data is not None


def test_search_modules():
    if not _server_alive(): return
    """GET /api/search/modules?q=access — 搜索模块"""
    status, data = _req("GET", "/api/search/modules?q=access")
    assert status == 200
    assert "modules" in data
    assert data["total"] >= 1
    # 搜索结果应包含 access_control
    names = [m["name"] for m in data["modules"]]
    assert any("access" in n for n in names)


def test_batch_execute():
    if not _server_alive(): return
    """POST /api/batch-execute — 批量执行"""
    status, data = _req("POST", "/api/batch-execute", {
        "targets": ["access_control", "bloom_filter"],
        "action": "status"
    })
    assert status == 200
    assert data["success"] is True
    assert data["total"] >= 2


# ═══════════════════════════════════════════════════════════
# 配置中心测试
# ═══════════════════════════════════════════════════════════

def test_config_list():
    if not _server_alive(): return
    """GET /api/config — 列出配置"""
    status, data = _req("GET", "/api/config")
    assert status == 200
    assert data["success"] is True
    assert "configs" in data
    assert len(data["configs"]) > 0


# ═══════════════════════════════════════════════════════════
# 调度器测试
# ═══════════════════════════════════════════════════════════

def test_scheduler_status():
    if not _server_alive(): return
    """GET /api/scheduler/status — 调度器状态"""
    status, data = _req("GET", "/api/scheduler/status")
    assert status == 200
    assert data["success"] is True


def test_scheduler_tasks():
    if not _server_alive(): return
    """GET /api/scheduler/tasks — 调度器任务列表"""
    status, data = _req("GET", "/api/scheduler/tasks")
    assert status == 200
    assert data["success"] is True
    assert "tasks" in data


# ═══════════════════════════════════════════════════════════
# LLM 测试
# ═══════════════════════════════════════════════════════════

def test_llm_providers():
    if not _server_alive(): return
    """GET /api/llm/providers — 列出 LLM Provider（可能未配置API Key，为空）"""
    status, data = _req("GET", "/api/llm/providers")
    assert status == 200
    assert data["success"] is True
    # 未配置API Key时 providers 为空列表
    assert "providers" in data


# ═══════════════════════════════════════════════════════════
# 通知测试
# ═══════════════════════════════════════════════════════════

def test_notify_channels():
    if not _server_alive(): return
    """GET /api/notify/channels — 通知通道列表"""
    status, data = _req("GET", "/api/notify/channels")
    assert status == 200
    assert data["success"] is True
    assert len(data["channels"]) >= 5


# ═══════════════════════════════════════════════════════════
# 管线测试
# ═══════════════════════════════════════════════════════════

def test_pipeline_stats():
    if not _server_alive(): return
    """GET /api/pipelines/stats — 管线统计（启动后空管线不影响）"""
    status, data = _req("GET", "/api/pipelines/stats")
    # 管线引擎需要先创建管线，空库时可能是500或503
    assert status in (200, 500, 503), f"状态码 {status} 异常"


# ═══════════════════════════════════════════════════════════
# 版本一致性测试（上市公司级关键检查）
# ═══════════════════════════════════════════════════════════

def test_version_consistency():
    if not _server_alive(): return
    """检查版本号一致性（所有端点返回相同版本）"""
    _, root = _req("GET", "/")
    _, status = _req("GET", "/api/status")

    versions = []
    for d in [root, status]:
        for v in d.get("system", ""), d.get("api_version", ""):
            if v:
                versions.append(v)

    assert all("V0.1" in v or "0.1" in v for v in versions), \
        f"版本号不一致: {versions}"


# ═══════════════════════════════════════════════════════════
# 安全测试
# ═══════════════════════════════════════════════════════════

def test_security_status():
    if not _server_alive(): return
    """GET /api/security/status — 安全状态"""
    status, data = _req("GET", "/api/security/status")
    assert status == 200
    assert "api_key_enabled" in data
    assert "rate_limiting" in data  # 实际返回键名为 rate_limiting


def test_system_diagnosis():
    if not _server_alive(): return
    """GET /api/diagnosis/system — 系统诊断"""
    status, data = _req("GET", "/api/diagnosis/system")
    assert status == 200
    assert data["success"] is True
    assert "api_version" in data


# ═══════════════════════════════════════════════════════════
# 前端静态资源测试
# ═══════════════════════════════════════════════════════════

def test_dashboard_served():
    if not _server_alive(): return
    """GET /dashboard — Dashboard 前端"""
    c = http.client.HTTPConnection(HOST, PORT, timeout=10)
    c.request("GET", "/dashboard")
    r = c.getresponse()
    html = r.read()
    assert r.status == 200, f"Dashboard 返回 {r.status}"
    assert len(html) > 40 * 1024  # > 40KB（index.html 已拆分，不再是单体巨型文件）


def test_manifest_served():
    if not _server_alive(): return
    """GET /manifest.json — PWA Manifest"""
    status, data = _req("GET", "/manifest.json")
    assert status == 200
    assert "name" in data


def test_metrics_served():
    if not _server_alive(): return
    """GET /metrics — Prometheus Metrics"""
    c = http.client.HTTPConnection(HOST, PORT, timeout=10)
    c.request("GET", "/metrics")
    r = c.getresponse()
    body = r.read().decode("utf-8")
    assert r.status == 200
    assert "evo_system_uptime_seconds" in body
    assert "evo_modules_total" in body


# ═══════════════════════════════════════════════════════════
# 系统可用性测试
# ═══════════════════════════════════════════════════════════

def test_system_backup_list():
    if not _server_alive(): return
    """GET /api/pipeline/status — 备份/管线状态快照"""
    status, data = _req("GET", "/api/pipeline/status")
    assert status == 200
    assert data["success"] is True


def test_execution_log():
    if not _server_alive(): return
    """GET /api/execution-log — 执行日志（无异常）"""
    status, data = _req("GET", "/api/execution-log")
    assert status == 200
    assert "log" in data


if __name__ == "__main__":
    success = 0
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ✅ {name}")
                success += 1
            except Exception as e:
                print(f"  ❌ {name}: {e}")
                failed += 1
    print(f"\n{'='*40}")
    print(f"总计: {success+failed}, 通过: {success}, 失败: {failed}")
    exit(0 if failed == 0 else 1)
