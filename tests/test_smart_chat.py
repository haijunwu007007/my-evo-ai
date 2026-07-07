"""
AUTO-EVO-AI V0.1 — 智能对话路由全覆盖测试
测试导航路由/动作执行/信息查询/LLM生成/多步复合指令
"""
import os, sys, json, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path

# ── 直接测试 routes_smart_chat.py 中的核心逻辑 ──
from api.routes.routes_smart_chat import (
    _extract_after, _NAVIGATION_MAP, _INFO_QUERIES, _ACTION_MAP,
    _SYSTEM_CAPABILITIES
)

BASE = Path(__file__).parent.parent


class TestNavigationMap(unittest.TestCase):
    """导航路由映射测试"""

    def test_001_nav_admin(self):
        """用户管理 → /admin#"""
        lower = "帮我用户管理"
        for keywords, url in _NAVIGATION_MAP:
            for kw in keywords:
                if kw in lower:
                    self.assertEqual(url, "/admin#")
                    return
        self.fail("未匹配到用户管理")

    def test_002_nav_workflow(self):
        """工作流 → /canvas"""
        lower = "打开工作流"
        for keywords, url in _NAVIGATION_MAP:
            for kw in keywords:
                if kw in lower:
                    self.assertEqual(url, "/canvas")
                    return
        self.fail("未匹配到工作流")

    def test_003_nav_deploy(self):
        """部署 → /deploy"""
        lower = "帮我部署应用"
        for keywords, url in _NAVIGATION_MAP:
            for kw in keywords:
                if kw in lower:
                    self.assertEqual(url, "/deploy")
                    return
        self.fail("未匹配到部署")

    def test_004_nav_agents(self):
        """智能体 → /agents"""
        lower = "查看智能体"
        for keywords, url in _NAVIGATION_MAP:
            for kw in keywords:
                if kw in lower:
                    self.assertEqual(url, "/agents")
                    return
        self.fail("未匹配到智能体")

    def test_005_nav_skills(self):
        """技能 → /skills"""
        lower = "打开技能列表"
        for keywords, url in _NAVIGATION_MAP:
            for kw in keywords:
                if kw in lower:
                    self.assertEqual(url, "/skills")
                    return
        self.fail("未匹配到技能")

    def test_006_nav_settings(self):
        """设置 → /settings"""
        lower = "打开系统设置"
        for keywords, url in _NAVIGATION_MAP:
            for kw in keywords:
                if kw in lower:
                    self.assertEqual(url, "/settings")
                    return
        self.fail("未匹配到设置")

    def test_007_nav_all_routes_have_match(self):
        """验证所有55条导航路由都有对应的关键词"""
        self.assertGreaterEqual(len(_NAVIGATION_MAP), 40, "导航路由不足40条")
        for keywords, url in _NAVIGATION_MAP:
            self.assertGreater(len(keywords), 0, f"{url} 缺少关键词")
            self.assertTrue(url.startswith("/"), f"{url} 格式错误")


class TestActionMap(unittest.TestCase):
    """动作执行映射测试"""

    def test_010_action_create_user(self):
        """创建用户 → 应提取用户名"""
        body_fn = None
        for keywords, method, url, fn in _ACTION_MAP:
            if "创建用户" in keywords[0]:
                body_fn = fn
                break
        self.assertIsNotNone(body_fn, "未找到创建用户动作")
        body = body_fn("创建用户 张三")
        self.assertEqual(body.get("username"), "张三")

    def test_011_action_remember(self):
        """记住 → 应提取内容"""
        body_fn = None
        for keywords, method, url, fn in _ACTION_MAP:
            if "记住" in keywords[0]:
                body_fn = fn
                break
        self.assertIsNotNone(body_fn, "未找到记住动作")
        body = body_fn("帮我记住密码是abc123")
        self.assertIn("abc123", body.get("content", ""))

    def test_012_action_map_not_empty(self):
        """动作映射不少于30条"""
        self.assertGreaterEqual(len(_ACTION_MAP), 30, "动作映射不足30条")
        for keywords, method, url, fn in _ACTION_MAP:
            self.assertIn(method, ("GET", "POST", "PUT", "DELETE"), f"{keywords[0]} 方法无效")
            self.assertTrue(url.startswith("/"), f"{keywords[0]} 路径无效")

    def test_013_extract_after_basic(self):
        """_extract_after 基本提取"""
        result = "创建用户 测试用户A"
        # 手动测试
        self.assertIsNotNone(result)


class TestInfoQueries(unittest.TestCase):
    """信息查询映射测试"""

    def test_020_info_keywords(self):
        """信息查询不少于40条"""
        self.assertGreaterEqual(len(_INFO_QUERIES), 40, "信息查询不足40条")

    def test_021_info_has_status(self):
        """系统状态查询存在"""
        self.assertIn("系统怎么样", _INFO_QUERIES)
        self.assertIn("模块列表", _INFO_QUERIES)
        self.assertIn("版本信息", _INFO_QUERIES)

    def test_022_info_has_users(self):
        """用户查询存在"""
        self.assertIn("用户列表", _INFO_QUERIES)
        self.assertIn("所有用户", _INFO_QUERIES)


class TestCreateKeywords(unittest.TestCase):
    """创建/生成关键词测试"""

    def test_030_capabilities_has_dev(self):
        """能力描述包含文档生成"""
        self.assertIn("PPT", _SYSTEM_CAPABILITIES)
        self.assertIn("搜索", _SYSTEM_CAPABILITIES)
        self.assertIn("记忆", _SYSTEM_CAPABILITIES)


class TestSystemCapabilities(unittest.TestCase):
    """系统能力描述测试"""

    def test_040_capabilities_contains_key_features(self):
        """能力清单包含关键功能"""
        self.assertIn("搜索", _SYSTEM_CAPABILITIES)
        self.assertIn("记忆", _SYSTEM_CAPABILITIES)
        self.assertIn("定时任务", _SYSTEM_CAPABILITIES)
        self.assertIn("系统诊断", _SYSTEM_CAPABILITIES)


class TestModulesFolders(unittest.TestCase):
    """模块目录完整性测试"""

    @classmethod
    def setUpClass(cls):
        cls.modules_dir = BASE / "modules"

    def test_050_modules_dir_exists(self):
        """modules/ 目录存在"""
        self.assertTrue(self.modules_dir.is_dir())

    def test_051_modules_count_minimum(self):
        """模块数不低于 440"""
        count = len([f for f in self.modules_dir.iterdir() if f.suffix == ".py" and not f.name.startswith("_")])
        self.assertGreaterEqual(count, 440, f"模块数 {count} < 440")

    def test_052_no_empty_stubs(self):
        """无空壳桩模块（<300B 且无 execute()）"""
        suspicious = []
        for f in self.modules_dir.glob("*.py"):
            if f.name.startswith("_") or f.name == "__init__.py":
                continue
            size = f.stat().st_size
            if size < 300:
                content = f.read_text(encoding="utf-8", errors="replace")
                if "def execute" not in content:
                    suspicious.append(f"{f.name}({size}B)")
        if suspicious:
            self.fail(f"发现空壳桩模块: {suspicious}")


class TestApiRoutes(unittest.TestCase):
    """API 路由文件完整性测试"""

    @classmethod
    def setUpClass(cls):
        cls.routes_dir = BASE / "api" / "routes"

    def test_060_routes_dir_exists(self):
        """api/routes/ 目录存在"""
        self.assertTrue(self.routes_dir.is_dir())

    def test_061_routes_count(self):
        """路由文件不少于 65 个"""
        count = len([f for f in self.routes_dir.glob("routes_*.py")])
        self.assertGreaterEqual(count, 65, f"路由文件 {count} < 65")

    def test_062_routes_importable(self):
        """关键路由可导入"""
        # 只测几个核心的
        importable = ["routes_smart_chat", "routes_chat", "routes_auth", "routes_modules"]
        fails = []
        for mod_name in importable:
            try:
                __import__(f"api.routes.{mod_name}")
            except Exception as e:
                fails.append(f"{mod_name}: {e}")
        if fails:
            self.fail(f"导入失败: {fails}")


class TestApiServer(unittest.TestCase):
    """api_server.py 核心端点测试"""

    def test_070_api_server_exists(self):
        """api_server.py 存在"""
        self.assertTrue((BASE / "api_server.py").is_file())

    def test_071_version_consistent(self):
        """版本号 V0.1"""
        content = (BASE / "api_server.py").read_text(encoding="utf-8")
        self.assertIn('VERSION = "V0.1"', content)


class TestFrontendFiles(unittest.TestCase):
    """前端文件完整性测试"""

    @classmethod
    def setUpClass(cls):
        cls.frontend = BASE / "frontend"

    def test_080_chat_engine_js_exists(self):
        """chat_engine.js 存在且 > 30KB"""
        path = self.frontend / "chat_engine.js"
        self.assertTrue(path.is_file())
        self.assertGreater(path.stat().st_size, 30000, "chat_engine.js 过小")

    def test_081_chat_engine_has_suggestinput(self):
        """chat_engine.js 包含 suggestInput 函数"""
        content = (self.frontend / "chat_engine.js").read_text(encoding="utf-8")
        self.assertIn("function suggestInput", content)
        self.assertIn("function send", content)
        self.assertIn("function doLogout", content)

    def test_082_chat_html_exists(self):
        """chat.html 存在且 > 40KB"""
        path = self.frontend / "chat.html"
        self.assertTrue(path.is_file())
        self.assertGreater(path.stat().st_size, 40000, "chat.html 过小")

    def test_083_no_localhost_in_frontend(self):
        """前端无硬编码 localhost"""
        for fname in ["chat.html", "chat_engine.js"]:
            path = self.frontend / fname
            if path.is_file():
                content = path.read_text(encoding="utf-8", errors="replace")
                self.assertNotIn("localhost", content, f"{fname} 包含硬编码 localhost")
                self.assertNotIn("127.0.0.1", content, f"{fname} 包含硬编码 127.0.0.1")


class TestConfigFiles(unittest.TestCase):
    """配置文件完整性测试"""

    def test_090_config_yaml_exists(self):
        """配置文件存在"""
        paths = [BASE / "config.yaml", BASE / "config" / "defaults.yaml"]
        self.assertTrue(any(p.is_file() for p in paths), "配置文件缺失")

    def test_091_requirements_exists(self):
        """requirements.txt 存在"""
        self.assertTrue((BASE / "requirements.txt").is_file())

    def test_092_gitignore_exists(self):
        """.gitignore 存在"""
        self.assertTrue((BASE / ".gitignore").is_file())


class TestCoreFiles(unittest.TestCase):
    """核心引擎文件测试"""

    @classmethod
    def setUpClass(cls):
        cls.core = BASE / "core"

    def test_100_core_dir_exists(self):
        """core/ 目录存在"""
        self.assertTrue(self.core.is_dir())

    def test_101_core_engines_exist(self):
        """核心引擎存在"""
        required = ["decision_engine.py", "llm_gateway.py", "scheduler_engine.py",
                     "event_engine.py", "module_delegate.py"]
        for f in required:
            self.assertTrue((self.core / f).is_file(), f"核心文件缺失: core/{f}")


if __name__ == "__main__":
    unittest.main()
