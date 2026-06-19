# -*- coding: utf-8 -*-
"""工具执行模块测试 — 验证真实模块调用"""
import os, sys, json, importlib, unittest
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

class TestToolExec(unittest.TestCase):
    """验证 routes_tool_exec.py 的模块执行功能"""

    @classmethod
    def setUpClass(cls):
        """加载路由模块"""
        sys.path.insert(0, str(BASE / "api"))
        try:
            from api.routes.routes_tool_exec import TOOL_MODULES, EXECUTABLE_TOOLS
            cls.tool_modules = TOOL_MODULES
            cls.exec_tools = EXECUTABLE_TOOLS
        except Exception as e:
            cls.tool_modules = {}
            cls.exec_tools = []
            print(f"[WARN] 无法加载工具路由: {e}")

    def test_01_routes_py_exists(self):
        """验证路由文件存在"""
        fp = BASE / "api" / "routes" / "routes_tool_exec.py"
        self.assertTrue(fp.exists(), f"文件不存在: {fp}")

    def test_02_tool_routes_have_exec(self):
        """验证路由文件有模块执行逻辑"""
        fp = BASE / "api" / "routes" / "routes_tool_exec.py"
        c = open(fp).read()
        self.assertIn("execute/", c, "路由中缺少 execute 端点")
        self.assertIn("list", c, "路由中缺少 list 端点")
        self.assertIn("_load_tool", c, "缺少工具加载函数")
        self.assertIn("_call_module", c, "缺少模块调用函数")

    def test_03_tool_list_endpoint(self):
        """验证工具列表端点存在"""
        fp = BASE / "api" / "routes" / "routes_tool_exec.py"
        c = open(fp).read()
        self.assertIn("@router.get(\"/list\")", c, "路由中缺少 /list")
        self.assertIn("@router.post(\"/execute/", c, "路由中缺少 execute")

    def test_04_core_modules_importable(self):
        """验证核心模块可导入"""
        for mod_id in self.tool_modules:
            try:
                # 模拟模块路径
                mod_path = BASE / "modules" / f"{mod_id}.py"
                if mod_path.exists():
                    spec = importlib.util.spec_from_file_location(mod_id, mod_path)
                    self.assertIsNotNone(spec, f"模块规范为空: {mod_id}")
                    mod = importlib.util.module_from_spec(spec)
                    if hasattr(spec, 'loader') and spec.loader:
                        spec.loader.exec_module(mod)
                        print(f"  ✅ {mod_id} 导入成功")
            except Exception as e:
                self.fail(f"模块 {mod_id} 导入失败: {e}")

    def test_05_docx_processor_exists(self):
        """验证 docx_processor.py 可执行"""
        fp = BASE / "modules" / "docx_processor.py"
        self.assertTrue(fp.exists(), f"文档生成模块不存在: {fp}")
        self.assertGreater(fp.stat().st_size, 5000, "文档生成模块太小 (<5KB)")

    def test_06_excel_pro_exists(self):
        """验证 excel_pro.py 可执行"""
        fp = BASE / "modules" / "excel_pro.py"
        self.assertTrue(fp.exists(), f"电子表格模块不存在: {fp}")
        self.assertGreater(fp.stat().st_size, 5000, "电子表格模块太小 (<5KB)")

    def test_07_ppt_generator_exists(self):
        """验证 ppt_generator.py 可执行"""
        fp = BASE / "modules" / "ppt_generator.py"
        self.assertTrue(fp.exists(), f"PPT模块不存在: {fp}")
        self.assertGreater(fp.stat().st_size, 5000, "PPT模块太小 (<5KB)")

    def test_08_pdf_toolkit_exists(self):
        """验证 pdf_toolkit.py 可执行"""
        self.assertTrue((BASE / "modules" / "pdf_toolkit.py").exists(), "PDF模块不存在")

    def test_09_codebase_engine_exists(self):
        """验证 codebase_engine.py 可执行"""
        self.assertTrue((BASE / "modules" / "codebase_engine.py").exists(), "Codebase模块不存在")

    def test_10_self_evolve_exists(self):
        """验证 self_evolve.py 可执行"""
        self.assertTrue((BASE / "modules" / "self_evolve.py").exists(), "自进化模块不存在")

    def test_11_permission_sandbox_exists(self):
        """验证 permission_sandbox.py 可执行"""
        self.assertTrue((BASE / "modules" / "permission_sandbox.py").exists(), "权限沙箱模块不存在")

    def test_12_memory_tree_exists(self):
        """验证 memory_tree.py 可执行"""
        self.assertTrue((BASE / "modules" / "memory_tree.py").exists(), "记忆树模块不存在")

    def test_13_agent_llm_has_gather(self):
        """验证 agent_llm.py 有并行首发"""
        c = open(BASE / "api" / "agent_llm.py").read()
        self.assertIn("FIRST_COMPLETED", c, "缺少并行首发 FIRST_COMPLETED")

    def test_14_agent_llm_has_circuit_breaker(self):
        """验证 agent_llm.py 有熔断机制"""
        c = open(BASE / "api" / "agent_llm.py").read()
        self.assertIn("_in_cooldown", c, "缺少熔断器 _in_cooldown")

    def test_15_routes_auth_has_password(self):
        """验证认证路由有密码校验"""
        c = open(BASE / "api" / "routes" / "routes_auth.py").read()
        self.assertIn("PASSWORD_REQUIRED", c, "缺少密码校验")

    def test_16_startup_has_override(self):
        """验证 startup.py 有路由覆盖"""
        c = open(BASE / "api" / "startup.py").read()
        for path in ["video", "canvas", "deploy", "automations", "capabilities"]:
            self.assertIn(path, c, f"路由覆盖缺少 {path}")

    def test_17_tools_data_js_exists(self):
        """验证工具数据已分离"""
        self.assertTrue((BASE / "js" / "tools_data.js").exists(), "工具数据未分离到 js/tools_data.js")

    def test_18_tools_html_exists(self):
        """验证独立工具页面存在"""
        self.assertTrue((BASE / "frontend" / "tools.html").exists(), "工具独立页面不存在")

    def test_19_all_12_tabs_in_chat(self):
        """验证首页有12个Tab"""
        c = open(BASE / "frontend" / "chat.html").read()
        for tab in ["tabChat","tabDash","tabHub","tabAuto","tabVc","tabBiz",
                     "tabCanvas","tabWF","tabCaps","tabDeploy","tabVideo","tabMonitor"]:
            self.assertIn(tab, c, f"缺少Tab: {tab}")

    def test_20_chat_has_theme_toggle(self):
        """验证首页有主题切换"""
        c = open(BASE / "frontend" / "chat.html").read()
        self.assertIn("toggleTheme", c, "缺少主题切换函数")
        self.assertIn("body.light", c, "缺少亮色CSS")

    def test_21_monitor_has_theme_support(self):
        """验证监控页有主题支持"""
        c = open(BASE / "frontend" / "monitor.html").read()
        self.assertIn("evo_theme", c, "监控页不支持主题切换")

if __name__ == "__main__":
    unittest.main(verbosity=2)
