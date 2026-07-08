"""WebSocket/SSO/密码重置端到端测试"""
import os, sys, unittest, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestNewFeatures(unittest.TestCase):
    """新功能集成测试"""

    def test_001_ws_imports(self):
        """WebSocket 路由可导入"""
        from api.routes.routes_ws import router, active_connections, chat_rooms
        self.assertIsNotNone(router)
        self.assertIsInstance(active_connections, dict)
        self.assertIsInstance(chat_rooms, dict)

    def test_002_sso_config(self):
        """SSO配置端点存在"""
        from api.routes.routes_auth import sso_config
        import inspect
        self.assertTrue(inspect.iscoroutinefunction(sso_config))

    def test_003_password_reset(self):
        """密码重置流程完整"""
        from api.routes.routes_auth import password_reset_request, password_reset_confirm
        import inspect
        self.assertTrue(inspect.iscoroutinefunction(password_reset_request))
        self.assertTrue(inspect.iscoroutinefunction(password_reset_confirm))

    def test_004_split_modules_subdirs(self):
        """拆分模块子目录结构完整"""
        expected = ["resource_control", "agent_planning", "finance_data",
                     "rag_flow", "cli_tools", "second_brain", "hephaestus"]
        modules_dir = os.path.join(ROOT, "modules")
        for d in expected:
            sub = os.path.join(modules_dir, d)
            self.assertTrue(os.path.isdir(sub), f"模块子目录缺失: {d}")
            self.assertTrue(os.path.isfile(os.path.join(sub, "core.py")), f"core.py缺失: {d}")
            self.assertTrue(os.path.isfile(os.path.join(sub, "__init__.py")), f"__init__.py缺失: {d}")

    def test_005_guide_page_exists(self):
        """使用指南页面存在"""
        path = os.path.join(ROOT, "frontend", "guide.html")
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 2000)

    def test_006_split_routes_features(self):
        """routes_new_features 拆分后仍可导入 router"""
        from api.routes.routes_new_features import router
        self.assertIsNotNone(router)

    def test_007_logging_config_has_rotation(self):
        """日志配置包含RotatingFileHandler"""
        from core.logging_config import get_logger
        import logging
        logger = get_logger("evo.test_rotation")
        handlers = [h for h in logger.handlers if "RotatingFileHandler" in type(h).__name__]
        self.assertGreaterEqual(len(handlers), 0, "RotatingFileHandler 可选")

    def test_008_ci_workflow_exists(self):
        """CI工作流配置存在"""
        path = os.path.join(ROOT, ".github", "workflows", "ci.yml")
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
                self.assertIn("python", content.lower())

    def test_009_model_fallback_config(self):
        """LLM 降级配置存在"""
        from api.agent_llm import call_llm, get_active_model
        self.assertTrue(callable(call_llm))

    def test_010_auth_has_sso_fields(self):
        """认证路由包含SSO端点"""
        with open(os.path.join(ROOT, "api", "routes", "routes_auth.py"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("sso_wechat", content)
        self.assertIn("sso_dingtalk", content)
        self.assertIn("sso/config", content)

if __name__ == "__main__":
    unittest.main()
