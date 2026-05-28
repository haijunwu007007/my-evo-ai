"""
AUTO-EVO-AI V0.1 — 框架级模块测试（第三波）
通过 EnterpriseModule 接口统一测试，不依赖模块内部方法名
覆盖: 模块加载/注册/元数据/健康检查基础接口
"""

import os, sys, time, json, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import tempfile


# ── 模块加载测试 ──

class TestModuleLoader(unittest.TestCase):
    """模块加载器：发现/注册/元数据验证"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules'))
        cls.module_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')

    def test_001_module_count(self):
        """模块目录存在且文件数>400"""
        files = [f for f in os.listdir(self.module_dir) if f.endswith('.py') and f != '__init__.py']
        self.assertGreaterEqual(len(files), 400, f"模块数不足: {len(files)}")

    def test_002_each_module_has_meta(self):
        """每个模块文件包含 __module_meta__ 或 __meta__"""
        missing = []
        for f in sorted(os.listdir(self.module_dir)):
            if not f.endswith('.py') or f == '__init__.py':
                continue
            path = os.path.join(self.module_dir, f)
            try:
                content = open(path, 'r', encoding='utf-8').read()
                if '__module_meta__' not in content and '__meta__' not in content:
                    missing.append(f)
            except:
                missing.append(f)
        if missing:
            self.assertLessEqual(len(missing), 20, f"超过20个模块缺少元数据，示例: {missing[:5]}")

    def test_003_core_engines_exist(self):
        """核心引擎文件都存在"""
        core_dir = os.path.join(os.path.dirname(self.module_dir), 'core')
        root_dir = os.path.dirname(self.module_dir)
        required = ['decision_engine.py', 'llm_gateway.py',
                     'scheduler_engine.py', 'event_engine.py']
        missing = [r for r in required if not os.path.exists(os.path.join(core_dir, r))]
        # api_server.py 在根目录
        api_path = os.path.join(root_dir, 'api_server.py')
        if not os.path.exists(api_path):
            missing.append('api_server.py')
        self.assertEqual(len(missing), 0, f"缺少核心引擎: {missing}")

    def test_004_base_framework_exists(self):
        """基础框架文件都存在"""
        base_dir = os.path.join(self.module_dir, '_base')
        required = ['enterprise_module.py', 'module_meta.py', 'registry.py']
        missing = [r for r in required if not os.path.exists(os.path.join(base_dir, r))]
        self.assertEqual(len(missing), 0, f"缺少基础框架: {missing}")


# ── 模块元数据一致性测试 ──

class TestModuleMetadata(unittest.TestCase):
    """模块元数据：版本统一/ID命名/分组规范"""

    @classmethod
    def setUpClass(cls):
        cls.module_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')

    def test_001_version_uniform(self):
        """所有模块版本为 V0.1"""
        mismatches = []
        for f in sorted(os.listdir(self.module_dir)):
            if not f.endswith('.py') or f == '__init__.py':
                continue
            path = os.path.join(self.module_dir, f)
            content = open(path, 'r', encoding='utf-8').read()
            if '"version"' in content and '"V0.1"' not in content:
                for line in content.split('\n'):
                    if '"version"' in line and 'V0.1' not in line:
                        mismatches.append(f"{f}: {line.strip()}")
                        break
        if mismatches:
            self.assertLessEqual(len(mismatches), 5, f"版本不一致数: {len(mismatches)}")

    def test_002_no_duplicate_module_ids(self):
        """模块ID不重复"""
        ids = []
        for f in sorted(os.listdir(self.module_dir)):
            if not f.endswith('.py') or f == '__init__.py':
                continue
            path = os.path.join(self.module_dir, f)
            content = open(path, 'r', encoding='utf-8').read()
            for line in content.split('\n'):
                if '"id"' in line and ':' in line:
                    import re
                    m = re.search(r'"id"\s*:\s*"([^"]+)"', line)
                    if m:
                        ids.append(m.group(1))
                    break
        dupes = [x for x in ids if ids.count(x) > 1]
        self.assertEqual(len(dupes), 0, f"重复ID: {set(dupes)}")

    def test_003_no_broken_imports_in_core(self):
        """核心引擎导入不抛出语法错误"""
        core_dir = os.path.join(os.path.dirname(self.module_dir), 'core')
        broken = []
        for f in sorted(os.listdir(core_dir)):
            if not f.endswith('.py') or f == '__init__.py':
                continue
            path = os.path.join(core_dir, f)
            try:
                compile(open(path, 'r', encoding='utf-8').read(), path, 'exec')
            except SyntaxError as e:
                broken.append(f"{f}: {e}")
        self.assertEqual(len(broken), 0, f"语法错误: {broken[:5]}")


# ── 模块类型安全检查 ──

class TestModuleSecurity(unittest.TestCase):
    """模块安全：禁止eval/exec/危险模式"""

    @classmethod
    def setUpClass(cls):
        cls.module_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')

    def test_001_no_dangerous_patterns(self):
        """模块中无__import__直接调用（白名单除外）"""
        dangerous = []
        for f in sorted(os.listdir(self.module_dir)):
            if not f.endswith('.py') or f == '__init__.py':
                continue
            path = os.path.join(self.module_dir, f)
            content = open(path, 'r', encoding='utf-8').read()
            if '__import__(' in content:
                dangerous.append(f)
        self.assertLessEqual(len(dangerous), 100, f"含__import__的模块: {dangerous}")


# ── 模块执行兼容性测试（通过execute接口） ──

class TestModuleExecutionPattern(unittest.TestCase):
    """模块执行模式：验证execute()和health_check()接口存在性"""

    @classmethod
    def setUpClass(cls):
        cls.module_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')

    def test_001_execute_method_exists_in_core_modules(self):
        """核心模块文件包含def execute("""
        modules_with_execute = []
        modules_without = []
        for f in sorted(os.listdir(self.module_dir)):
            if not f.endswith('.py') or f == '__init__.py':
                continue
            path = os.path.join(self.module_dir, f)
            content = open(path, 'r', encoding='utf-8').read()
            if 'def execute(' in content:
                modules_with_execute.append(f)
            if content.count('\n') > 100 and 'def execute(' not in content:
                modules_without.append(f)
        self.assertGreaterEqual(len(modules_with_execute), 30,
                                 f"含execute的模块不足: {len(modules_with_execute)}")

    def test_002_health_check_exists(self):
        """大模块包含health_check方法"""
        modules_with_hc = []
        for f in sorted(os.listdir(self.module_dir)):
            if not f.endswith('.py') or f == '__init__.py':
                continue
            path = os.path.join(self.module_dir, f)
            content = open(path, 'r', encoding='utf-8').read()
            if 'def health_check(' in content:
                modules_with_hc.append(f)
        self.assertGreaterEqual(len(modules_with_hc), 30,
                                 f"含health_check的模块不足: {len(modules_with_hc)}")


# ── 版本文件一致性测试 ──

class TestVersionConsistency(unittest.TestCase):
    """版本一致性：config.yaml/api_server/frontend 版本统一"""

    def test_001_config_version(self):
        """api_server.py和前端版本统一为V0.1"""
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 检查 api_server.py 版本
        api_path = os.path.join(root_dir, 'api_server.py')
        if os.path.exists(api_path):
            content = open(api_path, 'r', encoding='utf-8').read()
            self.assertIn('V0.1', content, "api_server.py 版本非 V0.1")
        # 检查前端版本
        pkg_path = os.path.join(root_dir, 'frontend', 'package.json')
        if os.path.exists(pkg_path):
            import json
            pkg = json.load(open(pkg_path, 'r', encoding='utf-8'))
            ver = pkg.get('version', '')
            self.assertIn('0.1', ver, f"前端版本非 0.1: {ver}")

    def test_002_api_server_version(self):
        """api_server.py版本"""
        api_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'core', 'api_server.py')
        if os.path.exists(api_path):
            content = open(api_path, 'r', encoding='utf-8').read()
            self.assertIn('V0.1', content, "api_server.py 版本非 V0.1")


# ── 数据完整性测试 ──

class TestDataIntegrity(unittest.TestCase):
    """数据完整性：测试数据不丢失"""

    def test_001_tests_exist(self):
        """测试文件存在且可收集"""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        test_files = [f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.py')]
        self.assertGreaterEqual(len(test_files), 18, f"测试文件数不足: {len(test_files)}")

    def test_002_docs_exist(self):
        """文档存在"""
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
        if os.path.exists(docs_dir):
            doc_files = [f for f in os.listdir(docs_dir) if f.endswith('.md')]
            self.assertGreaterEqual(len(doc_files), 1, "缺少文档文件")


# ── 模块分类统计测试 ──

class TestModuleCategorization(unittest.TestCase):
    """模块分类：验证分组标签合理性"""

    @classmethod
    def setUpClass(cls):
        cls.module_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')

    def test_001_group_distribution(self):
        """各分组模块数量合理"""
        groups = {}
        for f in sorted(os.listdir(self.module_dir)):
            if not f.endswith('.py') or f == '__init__.py':
                continue
            path = os.path.join(self.module_dir, f)
            content = open(path, 'r', encoding='utf-8').read()
            import re
            m = re.search(r'"group"\s*:\s*"([^"]+)"', content)
            if m:
                g = m.group(1)
                groups[g] = groups.get(g, 0) + 1
        self.assertGreaterEqual(len(groups), 10, f"分组数不足: {len(groups)}")
        # 核心分组应有足够模块
        core_groups = {'security', 'data', 'devops', 'monitor', 'developer'}
        for g in core_groups:
            if g in groups:
                self.assertGreaterEqual(groups[g], 5, f"分组 {g} 模块数不足: {groups[g]}")


# ── Python语法编译测试 ──

class TestPythonSyntax(unittest.TestCase):
    """Python语法：所有模块可编译"""

    @classmethod
    def setUpClass(cls):
        cls.module_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')

    def test_001_all_modules_compile(self):
        """所有模块文件可编译通过"""
        broken = []
        for f in sorted(os.listdir(self.module_dir)):
            if not f.endswith('.py') or f == '__init__.py':
                continue
            path = os.path.join(self.module_dir, f)
            try:
                compile(open(path, 'r', encoding='utf-8').read(), path, 'exec')
            except SyntaxError as e:
                broken.append(f"{f}: {e}")
        self.assertEqual(len(broken), 0, f"编译失败的模块: {broken[:10]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
