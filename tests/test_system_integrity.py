"""AUTO-EVO-AI V0.1 — 系统完整性测试"""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest, glob, importlib.util

class TestSystemIntegrity(unittest.TestCase):
    """系统完整性 - 文件结构、导入、依赖检查"""
    
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.modules_dir = os.path.join(cls.root, 'modules')
    
    def test_001_core_files_exist(self):
        core_dir = os.path.join(self.root, 'core')
        required = ['decision_engine.py', 'llm_gateway.py', 'scheduler_engine.py',
                     'event_engine.py', 'module_delegate.py']
        for f in required:
            self.assertTrue(os.path.exists(os.path.join(core_dir, f)),
                f"核心文件缺失: core/{f}")
    
    def test_002_api_server_exists(self):
        self.assertTrue(os.path.exists(os.path.join(self.root, 'api_server.py')))
    
    def test_003_api_routes_exist(self):
        api_dir = os.path.join(self.root, 'api')
        self.assertTrue(os.path.isdir(api_dir), "api/ 目录不存在")
        py_files = glob.glob(os.path.join(api_dir, '*.py'))
        self.assertGreater(len(py_files), 5, "api/ 路由文件不足")
    
    def test_004_config_exists(self):
        self.assertTrue(os.path.exists(os.path.join(self.root, 'config.yaml')))
    
    def test_005_dockerfile_exists(self):
        self.assertTrue(os.path.exists(os.path.join(self.root, 'Dockerfile')))
    
    def test_006_frontend_dist(self):
        dist = os.path.join(self.root, 'frontend', 'dist')
        if os.path.isdir(dist):
            files = glob.glob(os.path.join(dist, '**', '*'), recursive=True)
            self.assertGreater(len(files), 10, "前端 dist 文件不足")
    
    def test_007_tests_directory(self):
        tests_dir = os.path.join(self.root, 'tests')
        py_files = glob.glob(os.path.join(tests_dir, 'test_*.py'))
        self.assertGreater(len(py_files), 20, "测试文件不足20个")
    
    def test_008_no_i18n_files(self):
        """禁止 i18n 多语言文件"""
        for root, dirs, files in os.walk(self.root):
            for f in files:
                if 'i18n' in f.lower() or 'locale' in root.lower():
                    self.fail(f"发现 i18n 文件: {os.path.join(root, f)}")
    
    def test_009_no_bak_files_in_modules(self):
        """modules/ 下无 .bak 备份文件"""
        baks = glob.glob(os.path.join(self.modules_dir, '*.bak'))
        self.assertEqual(len(baks), 0, f"发现 {len(baks)} 个 .bak 文件")
    
    def test_010_modules_count_range(self):
        py_files = glob.glob(os.path.join(self.modules_dir, '*.py'))
        count = len([f for f in py_files if not f.endswith('__init__.py')])
        self.assertGreaterEqual(count, 400, f"模块数不足: {count}")
        self.assertLessEqual(count, 550, f"模块数过多: {count}")

class TestConfigIntegrity(unittest.TestCase):
    """配置完整性检查"""
    
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def test_011_config_yaml_exists(self):
        path = os.path.join(self.root, 'config.yaml')
        self.assertTrue(os.path.exists(path))
        content = open(path, encoding='utf-8').read()
        self.assertIn('version', content)
        self.assertIn('modules', content)
    
    def test_012_gitignore_exists(self):
        path = os.path.join(self.root, '.gitignore')
        self.assertTrue(os.path.exists(path))
        content = open(path, encoding='utf-8').read()
        self.assertIn('node_modules', content)
    
    def test_013_requirements_exists(self):
        path = os.path.join(self.root, 'requirements.txt')
        self.assertTrue(os.path.exists(path))

class TestFrontendIntegrity(unittest.TestCase):
    """前端完整性检查"""
    
    @classmethod
    def setUpClass(cls):
        cls.frontend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
    
    def test_014_vue_config_exists(self):
        for f in ['vite.config.js', 'vite.config.ts', 'vue.config.js']:
            if os.path.exists(os.path.join(self.frontend, f)):
                return
        self.fail("前端构建配置文件不存在")
    
    def test_015_package_json(self):
        path = os.path.join(self.frontend, 'package.json')
        self.assertTrue(os.path.exists(path))
        content = json.loads(open(path, encoding='utf-8').read())
        self.assertIn('dependencies', content)
    
    def test_016_src_directory(self):
        src = os.path.join(self.frontend, 'src')
        self.assertTrue(os.path.isdir(src))
        vue_files = glob.glob(os.path.join(src, '**', '*.vue'), recursive=True)
        self.assertGreater(len(vue_files), 3, "Vue 组件不足")

class TestModuleConsistency(unittest.TestCase):
    """模块一致性检查"""
    
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def test_017_no_duplicate_module_classes(self):
        modules_dir = os.path.join(cls.root, 'modules')
        module_ids = {}
        for f in glob.glob(os.path.join(modules_dir, '*.py')):
            if f.endswith('__init__.py') or os.path.basename(f).startswith('_'):
                continue
            content = open(f, encoding='utf-8').read()
            for mid in ['MODULE_ID', 'module_class']:
                if mid in content:
                    for line in content.splitlines():
                        if line.startswith(mid + ' =') or line.startswith('    ' + mid + '='):
                            module_ids.setdefault(line.strip(), []).append(os.path.basename(f))
        duplicates = {k: v for k, v in module_ids.items() if len(v) > 1}
        self.assertEqual(len(duplicates), 0, f"发现重复模块ID: {duplicates}")

if __name__ == '__main__':
    unittest.main()
