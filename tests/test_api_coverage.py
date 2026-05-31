"""
AUTO-EVO-AI V0.1 — API 覆盖测试（使用 FastAPI TestClient）
直接导入 app（从 api_server.py，那里注册了所有路由），不走 HTTP 端口
"""
import pytest, json
from httpx import AsyncClient, ASGITransport

# 从 api_server.py 导入 app —— 它在模块级别 include_router 了所有路由
import api_server
app = api_server.app

BASE = "http://test"

@pytest.fixture
def client():
    """CREATE a synchronous-style httpx client pointing at the ASGI app."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url=BASE)

@pytest.mark.asyncio
async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    d = r.json()
    assert d.get("success") is True

@pytest.mark.asyncio
async def test_api_status(client):
    r = await client.get("/api/status")
    assert r.status_code == 200
    d = r.json()
    assert d.get("success") is True

@pytest.mark.asyncio
async def test_modules_list(client):
    r = await client.get("/api/modules?limit=3")
    assert r.status_code == 200
    d = r.json()
    # 可能没有 success 字段（paginated 模式）
    assert "modules" in d or d.get("success") is True

@pytest.mark.asyncio
async def test_modules_categories(client):
    r = await client.get("/api/modules/categories")
    assert r.status_code == 200
    d = r.json()
    assert d.get("success") is True

@pytest.mark.asyncio
async def test_modules_search(client):
    r = await client.get("/api/search/modules?q=health")
    assert r.status_code == 200
    d = r.json()
    assert "success" in d

@pytest.mark.asyncio
async def test_modules_browse_list(client):
    r = await client.get("/api/modules/list?limit=3")
    assert r.status_code == 200
    d = r.json()
    assert d.get("success") is True

@pytest.mark.asyncio
async def test_modules_browse_categories(client):
    r = await client.get("/api/modules/categories")
    assert r.status_code == 200
    d = r.json()

@pytest.mark.asyncio
async def test_scheduler_status(client):
    r = await client.get("/api/scheduler/status")
    assert r.status_code == 200
    d = r.json()
    assert d.get("success") is True

@pytest.mark.asyncio
async def test_events_stats(client):
    r = await client.get("/api/events/stats")
    assert r.status_code == 200
    d = r.json()

@pytest.mark.asyncio
async def test_pipeline_status(client):
    r = await client.get("/api/pipeline/status")
    assert r.status_code == 200
    d = r.json()
    assert d.get("success") is True

@pytest.mark.asyncio
async def test_queue_stats(client):
    r = await client.get("/api/queue/stats")
    assert r.status_code == 200
    d = r.json()

@pytest.mark.asyncio
async def test_notify_channels(client):
    r = await client.get("/api/notify/channels")
    assert r.status_code == 200
    d = r.json()
    assert d.get("success") is True

@pytest.mark.asyncio
async def test_notify_stats(client):
    r = await client.get("/api/notify/stats")
    assert r.status_code == 200
    d = r.json()

@pytest.mark.asyncio
async def test_llm_providers(client):
    r = await client.get("/api/llm/providers")
    assert r.status_code == 200
    # llm 依赖池子初始化，可能失败但不应崩溃
    assert "providers" in r.json()

@pytest.mark.asyncio
async def test_llm_health(client):
    r = await client.get("/api/llm/health")
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_ai_providers(client):
    r = await client.get("/api/ai/providers")
    assert r.status_code == 200
    d = r.json()

@pytest.mark.asyncio
async def test_evo_summary(client):
    r = await client.get("/api/evo/summary")
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_evo_ranking(client):
    r = await client.get("/api/evo/ranking")
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_github_stats(client):
    r = await client.get("/api/github/stats")
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_plugins(client):
    r = await client.get("/api/plugins")
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_coordinator_status(client):
    r = await client.get("/api/coordinator/status")
    assert r.status_code == 200
    d = r.json()

@pytest.mark.asyncio
async def test_coordinator_capabilities(client):
    r = await client.get("/api/coordinator/capabilities")
    assert r.status_code == 200
    d = r.json()

@pytest.mark.asyncio
async def test_config_list(client):
    r = await client.get("/api/config/list")
    assert r.status_code == 200
    d = r.json()
    assert d.get("success") is True

@pytest.mark.asyncio
async def test_system_metrics(client):
    r = await client.get("/api/system/metrics")
    assert r.status_code == 200
    d = r.json()

@pytest.mark.asyncio
async def test_ws_status(client):
    r = await client.get("/api/ws/stats")
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_execution_log(client):
    r = await client.get("/api/execution-log")
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_persistence_status(client):
    r = await client.get("/api/persistence/status")
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_cicd_git_status(client):
    r = await client.get("/api/cicd/git/status")
    assert r.status_code == 200
