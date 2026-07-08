"""AUTO-EVO-AI V0.1 — 系统完整性测试"""
import os, sys, time, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest, glob, importlib.util

class TestSystemIntegrity(unittest.TestCase):
    """系统完整性 - 文件结构、导入、依赖检查"""
    
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.modules_dir = os.path.join(cls.root, 'modules')
    
    def test_001_core_files_exist(self):
        """核心文件存在（支持拆分后的子目录结构）"""
        core_dir = os.path.join(self.root, 'core')
        required = ['scheduler_engine.py', 'event_engine.py', 'module_delegate.py',
                     'decision', 'llm']  # decision_engine→decision/, llm_gateway→llm/
        for f in required:
            target = os.path.join(core_dir, f)
            exists = os.path.isfile(target) or (os.path.isdir(target) and os.path.isfile(os.path.join(target, 'core.py')))
            self.assertTrue(exists, f"核心文件/目录缺失: core/{f}")
    
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
        self.assertGreaterEqual(len(py_files), 3, "测试文件不足3个")
    
    def test_008_i18n_files_valid(self):
        """i18n 多语言文件完整性检查"""
        i18n_dir = os.path.join(self.root, 'i18n')
        if os.path.isdir(i18n_dir):
            lang_files = glob.glob(os.path.join(i18n_dir, '*.json'))
            self.assertGreaterEqual(len(lang_files), 4, "语言文件不足4个")
            for lf in lang_files:
                with open(lf, encoding='utf-8') as f:
                    data = json.loads(f.read())
                    self.assertIsInstance(data, dict, f"{lf} 格式错误")
                    self.assertGreaterEqual(len(data), 40, f"{lf} 键值不足40个")
    
    def test_009_backup_files_managed(self):
        """备份文件已妥善管理（.bak 允许存在，有同名的子目录即视为已拆分）"""
        baks = glob.glob(os.path.join(self.modules_dir, '*.bak'))
        for b in baks:
            base_name = os.path.splitext(os.path.basename(b))[0]
            # 检查是否有对应的子目录（表示已拆分）
            candidates = [
                base_name,  # 原名
                base_name.replace('agent_', ''),  # agent_xxx → xxx
                base_name.replace('_', ''),  # 去下划线
                base_name.replace('m53_', ''),  # m53_xxx → xxx
            ]
            has_subdir = any(os.path.isdir(os.path.join(self.modules_dir, c)) for c in candidates)
            if not has_subdir:
                self.fail(f"无对应拆分目录的bak文件: {b}")
    
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
        path = os.path.join(self.root, 'config', 'defaults.yaml')
        if not os.path.exists(path):
            path = os.path.join(self.root, 'config.yaml')
        self.assertTrue(os.path.exists(path), f"配置文件不存在: {path}")
        content = open(path, encoding='utf-8').read()
        self.assertIn('server', content, "配置文件中应包含 server")
        self.assertIn('port', content, "配置文件中应包含 port")
    
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
        cls.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.frontend = os.path.join(cls.root, 'frontend')
        cls.vue_app = os.path.join(cls.root, 'vue-app')
    
    def test_014_chat_html_exists(self):
        path = os.path.join(self.frontend, 'chat.html')
        self.assertTrue(os.path.exists(path), "chat.html 缺失")
        size = os.path.getsize(path)
        self.assertGreater(size, 30000, f"chat.html 过小: {size}B")
    
    def test_015_vue_app_config(self):
        """vue-app 目录存在且含构建配置（可选）"""
        if os.path.isdir(self.vue_app):
            for f in ['vite.config.js', 'vite.config.ts', 'vue.config.js', 'package.json']:
                if os.path.exists(os.path.join(self.vue_app, f)):
                    return
        # 如果没有 vue-app，chat.html 存在即可
        self.assertTrue(os.path.exists(os.path.join(self.frontend, 'chat.html')))
    
    def test_016_frontend_files_valid(self):
        """前端核心文件存在"""
        required = ['chat.html', 'chat_engine.js', 'share.css']
        for f in required:
            path = os.path.join(self.frontend, f)
            self.assertTrue(os.path.exists(path), f"前端文件缺失: {f}")
            self.assertGreater(os.path.getsize(path), 500, f"{f} 过小")

class TestModuleConsistency(unittest.TestCase):
    """模块一致性检查"""
    
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def test_017_no_duplicate_module_classes(self):
        modules_dir = os.path.join(self.root, 'modules')
        module_ids = {}
        for f in glob.glob(os.path.join(modules_dir, '*.py')):
            if f.endswith('__init__.py') or os.path.basename(f).startswith('_'):
                continue
            content = open(f, encoding='utf-8').read()
            fname = os.path.basename(f)
            # 跳过 mXX_ 前缀的别名文件
            if re.match(r'^m\d+_', fname):
                continue
            seen_in_file = set()
            for mid in ['MODULE_ID', 'module_class']:
                if mid in content:
                    for line in content.splitlines():
                        if line.startswith(mid + ' =') or line.startswith('    ' + mid + '='):
                            key = line.strip()
                            if key not in seen_in_file:
                                module_ids.setdefault(key, []).append(fname)
                                seen_in_file.add(key)
        duplicates = {k: v for k, v in module_ids.items() if len(v) > 1}
        self.assertEqual(len(duplicates), 0, f"发现重复模块ID: {duplicates}")

if __name__ == '__main__':
    unittest.main()
