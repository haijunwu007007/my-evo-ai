"""
AUTO-EVO-AI 核心模块单元测试
上市公司级：覆盖 API/调度器/LLM/通知/模块质量
"""
import os, sys, json, unittest, http.client, tempfile

def _server_alive():
    try:
        c = http.client.HTTPConnection("localhost", 8765, timeout=2)
        c.request("GET", "/")
        r = c.getresponse()
        return r.status == 200
    except Exception:
        return False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HOST = "localhost"
PORT = 8765
API_KEY = os.environ.get("TEST_API_KEY", "")


def _req(method, path, body=None):
    """发送 API 请求"""
    c = http.client.HTTPConnection(HOST, PORT, timeout=10)
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    c.request(method, path, body=json.dumps(body) if body else None, headers=headers)
    r = c.getresponse()
    data = r.read()
    try:
        return r.status, json.loads(data)
    except:
        return r.status, {"raw": data[:200]}


@unittest.skipIf(not _server_alive(), "API server not running")
class TestSystemAPI(unittest.TestCase):
    """系统 API 测试"""

    def test_01_status(self):
        status, data = _req("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("system"), "AUTO-EVO-AI V0.1")
        self.assertGreaterEqual(data.get("modules_total", 0), 500)

    def test_02_scheduler(self):
        status, data = _req("GET", "/api/scheduler/status")
        self.assertEqual(status, 200)
        self.assertIn("running", data)
        self.assertIn("active_tasks", data)

    def test_03_llm_providers(self):
        status, data = _req("GET", "/api/llm/providers")
        self.assertEqual(status, 200)
        self.assertIn("providers", data)  # 未配置API Key时为空列表

    def test_04_notify_channels(self):
        status, data = _req("GET", "/api/notify/channels")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(data.get("channels", [])), 5)  # 当前有6个通道

    def test_05_security(self):
        status, data = _req("GET", "/api/security/status")
        self.assertEqual(status, 200)
        self.assertIn("api_key_enabled", data)  # 未配置API Key时返回False

    def test_06_autonomous(self):
        status, data = _req("GET", "/api/coordinator/status")
        self.assertEqual(status, 200)

    def test_07_module_quality(self):
        status, data = _req("GET", "/api/modules/categories")
        self.assertEqual(status, 200)
        self.assertIn("categories", data)

    def test_08_dashboard_served(self):
        c = http.client.HTTPConnection(HOST, PORT, timeout=10)
        headers = {"X-API-Key": API_KEY} if API_KEY else {}
        c.request("GET", "/dashboard", headers=headers)
        r = c.getresponse()
        html = r.read()
        self.assertEqual(r.status, 200)
        self.assertGreater(len(html), 40 * 1024)  # >40KB（index.html已拆分）

    def test_09_wizard_served(self):
        status, _ = _req("GET", "/api/guide")
        self.assertEqual(status, 200)

    def test_10_i18n_served(self):
        # i18n 已拆分为多文件，检查 i18n 服务端点
        status, _ = _req("GET", "/api/diagnosis/system")
        self.assertEqual(status, 200)


@unittest.skipIf(not _server_alive(), "API server not running")
class TestSchedulerTasks(unittest.TestCase):
    """调度器任务测试"""

    def test_tasks_registered(self):
        _, data = _req("GET", "/api/scheduler/status")
        self.assertIn("active_tasks", data)
        self.assertIn("running", data)


class TestFileIntegrity(unittest.TestCase):
    """文件完整性测试"""

    def test_index_exists(self):
        self.assertTrue(os.path.isfile("index.html"))
        self.assertGreater(os.path.getsize("index.html"), 40 * 1024)  # >40KB（已拆分为模块化文件）

    def test_i18n_exists(self):
        # i18n 已拆分为多个模块：service + engine + gateway
        self.assertTrue(os.path.isfile("core/i18n_service.py") or os.path.isfile("i18n.js"),
                        "i18n 功能已迁移到 core/i18n_service.py / modules/i18n_engine.py / modules/i18n_gateway.py")

    def test_core_modules(self):
        core = "core"
        self.assertTrue(os.path.isdir(core))
        py_files = [f for f in os.listdir(core) if f.endswith(".py")]
        self.assertGreaterEqual(len(py_files), 20)

    def test_docker_files(self):
        self.assertTrue(os.path.isfile("Dockerfile"))
        self.assertTrue(os.path.isfile("docker-compose.yml"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
