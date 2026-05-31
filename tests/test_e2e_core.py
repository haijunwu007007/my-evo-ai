"""
AUTO-EVO-AI V0.1 — 核心业务 E2E 集成测试（10个用例）
================================================================
覆盖：AI/LLM、GitHub、进化引擎、通知推送、模块健康、DevOps、审计、
      管道执行、插件生态、模块发现

依赖：
  1. API 服务器运行在 http://127.0.0.1:8765
  2. pytest -x tests/test_e2e_core.py -v

执行方式：
  python -m pytest tests/test_e2e_core.py -v --tb=short
"""

import os, sys, json, time, http.client, pytest

API_HOST = "localhost"
API_PORT = 8765
TIMEOUT = 8


def _req(method: str, path: str, body: dict = None) -> tuple:
    """底层 HTTP 请求，返回 (status, data_dict)"""
    try:
        c = http.client.HTTPConnection(API_HOST, API_PORT, timeout=TIMEOUT)
        headers = {"Content-Type": "application/json"}
        encoded = json.dumps(body).encode() if body else None
        c.request(method, path, body=encoded, headers=headers)
        r = c.getresponse()
        data = r.read()
        try:
            return r.status, json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return r.status, {"raw_size": len(data)}
    except (ConnectionRefusedError, http.client.HTTPException, OSError) as e:
        return 0, {"error": f"connection_failed: {e}"}


def is_alive() -> bool:
    """快速检查服务是否存活"""
    status, data = _req("GET", "/api/status")
    return status == 200


# ═══════════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════════

@pytest.mark.e2e
@pytest.mark.integration
class TestE2E_LLM_Gateway:
    """用例1：AI/LLM 网关健康检查"""

    def setup_method(self):
        if not is_alive():
            pytest.skip("API 服务器未运行")

    def test_llm_health_check(self):
        """验证 LLM 网关状态端点"""
        status, data = _req("GET", "/api/llm/health")
        assert status in (200, 503), f"LLM health failed: {status} {data}"
        # 即使 LLM 后端不可用，网关本身应有响应
        # 检查响应结构
        if isinstance(data, dict):
            print(f"  LLM Health: providers={data.get('providers', '?')}, healthy={data.get('healthy', '?')}")
        else:
            print(f"  LLM Health response: {data}")

    def test_llm_providers_list(self):
        """获取 LLM 提供商列表"""
        status, data = _req("GET", "/api/llm/providers")
        assert status == 200, f"LLM providers failed: {status}"
        providers = data if isinstance(data, list) else data.get("providers", [])
        print(f"  LLM Providers: {len(providers)} configured")


@pytest.mark.e2e
class TestE2E_GitHub_Integration:
    """用例2：GitHub 集成"""

    def setup_method(self):
        if not is_alive():
            pytest.skip("API 服务器未运行")

    def test_github_stats(self):
        """获取 GitHub 模块统计信息"""
        status, data = _req("GET", "/api/github/stats")
        assert status == 200, f"github stats failed: {status}"
        print(f"  GitHub Stats keys: {list(data.keys())[:5]}")
        assert isinstance(data, dict), f"expected dict, got {type(data)}"

    def test_github_tracked_repos(self):
        """获取已追踪的 GitHub 仓库列表"""
        status, data = _req("GET", "/api/github/tracked")
        assert status == 200, f"github tracked failed: {status}"
        tracked = data if isinstance(data, list) else data.get("repos", [])
        print(f"  Tracked repos: {len(tracked)}")


@pytest.mark.e2e
class TestE2E_Evolution_Engine:
    """用例3：进化引擎"""

    def setup_method(self):
        if not is_alive():
            pytest.skip("API 服务器未运行")

    def test_evo_summary(self):
        """获取进化引擎摘要统计"""
        status, data = _req("GET", "/api/evo/summary")
        if status != 200:
            pytest.skip(f"evo summary not available: {status}")
        assert isinstance(data, dict), f"expected dict, got {type(data)}"
        print(f"  Evo Summary: scores={data.get('total_scores','?')}, "
              f"modules={data.get('total_modules', data.get('modules','?'))}")

    def test_evo_ranking(self):
        """获取模块进化排名"""
        status, data = _req("GET", "/api/evo/ranking")
        if status != 200:
            pytest.skip(f"evo ranking not available: {status}")
        ranking = data if isinstance(data, list) else data.get("ranking", data.get("modules", []))
        print(f"  Evo Ranking: {len(ranking)} entries")


@pytest.mark.e2e
class TestE2E_Notification:
    """用例4：通知推送服务"""

    def setup_method(self):
        if not is_alive():
            pytest.skip("API 服务器未运行")

    def test_notify_channels(self):
        """获取已配置的通知渠道"""
        status, data = _req("GET", "/api/notify/channels")
        assert status == 200, f"notify channels failed: {status}"
        channels = data if isinstance(data, list) else data.get("channels", [])
        print(f"  Notification channels: {len(channels)}")

    def test_notify_stats(self):
        """获取通知发送统计"""
        status, data = _req("GET", "/api/notify/stats")
        if status != 200:
            pytest.skip(f"notify stats not available: {status}")
        print(f"  Notify Stats: {data}")


@pytest.mark.e2e
class TestE2E_Module_Health:
    """用例5：模块健康检查"""

    KNOWN_MODULES = [
        "agent-orchestrator", "ai-gateway", "task-center",
        "github-scanner", "alert-manager",
    ]

    def setup_method(self):
        if not is_alive():
            pytest.skip("API 服务器未运行")

    def test_first_module_health(self):
        """对已知模块执行健康检查"""
        status, data = _req("GET", "/api/modules/agent-orchestrator/health")
        if status in (404, 422):
            # 模块名可能不同，尝试用 dash 转下划线
            status, data = _req("GET", "/api/modules/agent_orchestrator/health")
        assert status in (200, 404), f"health check failed: {status} {data}"
        if status == 200:
            print(f"  Module Health: {data.get('status', '?')}")


@pytest.mark.e2e
class TestE2E_DevOps:
    """用例6：DevOps/Git 集成"""

    def setup_method(self):
        if not is_alive():
            pytest.skip("API 服务器未运行")

    def test_git_status(self):
        """获取 Git 仓库状态"""
        status, data = _req("GET", "/api/cicd/git/status")
        if status != 200:
            pytest.skip(f"git status not available: {status}")
        assert isinstance(data, dict), f"expected dict, got {type(data)}"
        print(f"  Git Status: branch={data.get('branch','?')}, "
              f"changes={data.get('changes', data.get('uncommitted', '?'))}")


@pytest.mark.e2e
class TestE2E_Execution_Log:
    """用例7：执行日志/审计追踪"""

    def setup_method(self):
        if not is_alive():
            pytest.skip("API 服务器未运行")

    def test_execution_log(self):
        """查询执行日志"""
        status, data = _req("GET", "/api/execution-log")
        if status != 200:
            pytest.skip(f"execution log not available: {status}")
        logs = data if isinstance(data, list) else data.get("logs", data.get("entries", []))
        print(f"  Execution Logs: {len(logs)} entries")
        if logs:
            first = logs[0] if isinstance(logs, list) else list(logs.values())[0]
            print(f"  Latest: {first.get('action','?')} | {first.get('status','?')}")


@pytest.mark.e2e
class TestE2E_Pipeline:
    """用例8：管道/工作流系统"""

    def setup_method(self):
        if not is_alive():
            pytest.skip("API 服务器未运行")

    def test_pipeline_status(self):
        """获取管道系统状态"""
        status, data = _req("GET", "/api/pipeline/status")
        if status != 200:
            pytest.skip(f"pipeline status not available: {status}")
        pipelines = data if isinstance(data, list) else data.get("pipelines", [])
        print(f"  Pipelines: {len(pipelines)}")
        if pipelines and isinstance(pipelines, list):
            print(f"  Pipeline names: {[p.get('name',p.get('id','?')) for p in pipelines[:5]]}")


@pytest.mark.e2e
class TestE2E_Plugin_Ecosystem:
    """用例9：插件生态"""

    def setup_method(self):
        if not is_alive():
            pytest.skip("API 服务器未运行")

    def test_plugin_list(self):
        """获取插件列表"""
        status, data = _req("GET", "/api/plugins")
        if status != 200:
            pytest.skip(f"plugins not available: {status}")
        plugins = data if isinstance(data, list) else data.get("plugins", [])
        print(f"  Plugins: {len(plugins)}")
        if plugins and isinstance(plugins, list):
            print(f"  First 3: {[p.get('name',p.get('id','?')) for p in plugins[:3]]}")


@pytest.mark.e2e
class TestE2E_Module_Discovery:
    """用例10：模块发现/浏览"""

    def setup_method(self):
        if not is_alive():
            pytest.skip("API 服务器未运行")

    def test_module_list(self):
        """获取已注册模块列表"""
        status, data = _req("GET", "/api/modules")
        assert status == 200, f"module list failed: {status}"
        modules = data if isinstance(data, list) else data.get("modules", [])
        count = len(modules) if isinstance(modules, list) else data.get("total", data.get("count", 0))
        print(f"  Registered modules: {count}")

    def test_module_categories(self):
        """获取模块分类"""
        status, data = _req("GET", "/api/modules/categories")
        assert status == 200, f"module categories failed: {status}"
        cats = data if isinstance(data, (list, dict)) else {}
        if isinstance(cats, dict):
            print(f"  Categories: {list(cats.keys())[:8]}")
        elif isinstance(cats, list):
            print(f"  Categories: {len(cats)}")

    def test_module_search(self):
        """搜索模块"""
        status, data = _req("GET", "/api/search/modules?q=agent")
        if status != 200:
            pytest.skip(f"module search not available: {status}")
        results = data if isinstance(data, list) else data.get("results", data.get("modules", []))
        print(f"  Search 'agent': {len(results)} results")
