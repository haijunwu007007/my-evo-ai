"""测试：外部工具集成路由"""
import pytest
from fastapi.testclient import TestClient

try:
    from api_server import app
    HAS_SERVER = True
except ImportError:
    HAS_SERVER = False

pytestmark = pytest.mark.skipif(not HAS_SERVER, reason="api_server.py not importable")

client = TestClient(app)

TOOL_ENDPOINTS = [
    ("/api/tools/langfuse", "Langfuse 状态"),
    ("/api/tools/langfuse/health", "Langfuse 健康"),
    ("/api/tools/langfuse/traces", "Langfuse 追踪"),
    ("/api/tools/superset", "Superset 状态"),
    ("/api/tools/superset/health", "Superset 健康"),
    ("/api/tools/activepieces", "ActivePieces 状态"),
    ("/api/tools/activepieces/health", "ActivePieces 健康"),
    ("/api/tools/meili", "Meilisearch 状态"),
    ("/api/tools/pdf", "Stirling-PDF 状态"),
    ("/api/tools/uptime", "Uptime-Kuma 状态"),
    ("/api/tools/nextchat", "NextChat 状态"),
    ("/api/tools/browser-use", "Browser-Use 状态"),
    ("/api/tools/filebrowser", "FileBrowser 状态"),
    ("/api/tools/openclaw", "OpenClaw 状态"),
    ("/api/tools/dify", "Dify 状态"),
    ("/api/tools/chroma", "ChromaDB 状态"),
    ("/api/agent-s/status", "Agent-S 状态"),
    ("/api/litellm/health", "LiteLLM 健康"),
]

class TestToolRoutes:
    """外部工具集成路由 — 验证所有桥接端点 200"""

    @pytest.mark.parametrize("path,desc", TOOL_ENDPOINTS)
    def test_tool_route_returns_json(self, path: str, desc: str):
        resp = client.get(path)
        assert resp.status_code == 200, f"{desc} ({path}) → {resp.status_code}"
        data = resp.json()
        assert isinstance(data, dict), f"{desc} 返回非 JSON"
        # Langfuse traces 端点返回 traces+note
        # 每个工具响应至少包含描述性字段
        if "traces" in path:
            assert "traces" in data or "note" in data, f"{desc} 缺少 traces/note"
        else:
            assert any(k in data for k in ("available", "name", "healthy", "status", "success")), \
                f"{desc} 缺少关键字段: {list(data.keys())[:5]}"



    def test_agent_s_check(self):
        """Agent-S 环境检测端点"""
        resp = client.get("/api/agent-s/check")
        assert resp.status_code == 200
        data = resp.json()
        # 应返回环境检测信息
        assert isinstance(data, dict)

    def test_litellm_providers(self):
        """LiteLLM 提供商列表"""
        resp = client.get("/api/litellm/providers")
        assert resp.status_code == 200
        data = resp.json() if resp.text else {}
        assert isinstance(data, (dict, list))
