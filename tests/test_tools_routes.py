"""AUTO-EVO-AI V0.1 — 外部工具路由测试 (TestClient)
验证所有 /api/tools/* 端点可正常返回
"""
import pytest
from fastapi.testclient import TestClient
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 延迟导入 — 需要在 uvicorn 环境外创建 app
pytestmark = pytest.mark.skipif(
    not os.environ.get("EVO_TEST_MODE"),
    reason="需要设置 EVO_TEST_MODE=true 以启动完整 app",
)


@pytest.fixture(scope="module")
def client():
    """创建一个 TestClient，模块级共享"""
    from api_server import app
    return TestClient(app)


TOOL_ENDPOINTS = [
    "/api/tools/minio",
    "/api/tools/portainer",
    "/api/tools/grafana",
    "/api/tools/outline",
    "/api/tools/appsmith",
    "/api/tools/code-server",
    "/api/tools/dashy",
    "/api/tools/ntfy",
    "/api/tools/nocodb",
    "/api/tools/changedetection",
    "/api/tools/hoppscotch",
    "/api/tools/tabby",
    "/api/tools/firecrawl",
    "/api/tools/mcp",
    "/api/tools/langfuse",
    "/api/tools/superset",
    "/api/tools/activepieces",
    "/api/tools/dify",
    "/api/tools/flowise",
    "/api/tools/n8n",
    "/api/tools/litellm",
    "/api/tools/llm-one-api",
    "/api/tools/agent-s",
    "/api/tools/meili",
    "/api/tools/stirling-pdf",
    "/api/tools/uptime",
    "/api/tools/nextchat",
    "/api/tools/browser-use",
    "/api/tools/filebrowser",
    "/api/tools/openclaw",
    "/api/tools/chroma",
]


class TestToolsRoutes:
    """30 个工具路由全部可响应"""

    @pytest.mark.parametrize("endpoint", TOOL_ENDPOINTS)
    def test_tool_endpoint_responds(self, client, endpoint):
        """每个工具端点返回 200 或预期错误"""
        resp = client.get(endpoint, timeout=5)
        assert resp.status_code in (200, 503), f"{endpoint} 返回 {resp.status_code}"
        data = resp.json()
        assert isinstance(data, dict)

    def test_core_endpoints(self, client):
        """核心端点验证"""
        for path in ["/", "/api/status", "/api/modules"]:
            resp = client.get(path, timeout=5)
            assert resp.status_code == 200, f"{path} 返回 {resp.status_code}"

    def test_tool_health_checks(self, client):
        """健康检查端点"""
        for ep in ["/api/tools/ntfy/health", "/api/tools/uptime/health",
                    "/api/tools/minio/health", "/api/tools/uptime/monitors"]:
            resp = client.get(ep, timeout=5)
            assert resp.status_code in (200, 404, 503), f"{ep}: {resp.status_code}"

    def test_i18n_content(self, client):
        """i18n 文件可访问"""
        resp = client.get("/api/i18n/zh-CN", timeout=5)
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert "app.name" in data

    def test_litellm_endpoints(self, client):
        """LiteLLM 路由"""
        resp = client.get("/api/tools/litellm", timeout=5)
        assert resp.status_code in (200, 503)

    def test_dashy_config(self, client):
        """Dashy 配置"""
        resp = client.get("/api/tools/dashy", timeout=5)
        assert resp.status_code == 200
