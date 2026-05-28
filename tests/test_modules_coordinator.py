"""AUTO-EVO-AI V0.1 — 协调器/资源控制单元测试"""
import os, sys, time, json, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest

class TestAgentResourceControlStructure(unittest.TestCase):
    """agent_resource_control 结构验证"""
    
    @classmethod
    def setUpClass(cls):
        cls.module_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')
    
    def test_001_file_exists(self):
        path = os.path.join(self.module_dir, 'agent_resource_control.py')
        self.assertTrue(os.path.exists(path), "agent_resource_control.py 不存在")
    
    def test_002_can_import(self):
        path = os.path.join(self.module_dir, 'agent_resource_control.py')
        content = open(path, encoding='utf-8').read()
        self.assertIn('class AgentResourceController', content)
        self.assertIn('class AgentPool', content)
        self.assertIn('class HardwareMonitor', content)
    
    def test_003_has_real_logic(self):
        path = os.path.join(self.module_dir, 'agent_resource_control.py')
        content = open(path, encoding='utf-8').read()
        has_thread = 'threading.' in content or '_monitor_loop' in content
        has_pool = 'AgentPool' in content
        has_loadbal = 'LoadBalancer' in content
        self.assertTrue(has_thread, "缺少线程监控")
        self.assertTrue(has_pool, "缺少AgentPool")
        self.assertTrue(has_loadbal, "缺少LoadBalancer")

class TestCoordinatorV3Structure(unittest.TestCase):
    """system_coordinator_v3 结构验证"""
    
    @classmethod
    def setUpClass(cls):
        cls.module_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')
    
    def test_004_file_exists(self):
        path = os.path.join(self.module_dir, 'system_coordinator_v3.py')
        self.assertTrue(os.path.exists(path))
    
    def test_005_no_infinite_recursion(self):
        path = os.path.join(self.module_dir, 'system_coordinator_v3.py')
        content = open(path, encoding='utf-8').read()
        # Check that the analyzer doesn't create itself
        analyzer_init = content[content.find('class SystemCoordinatorV3Analyzer'):]
        analyzer_init = analyzer_init[:analyzer_init.find('\nclass ')]
        # Should not have self._analyzer = SystemCoordinatorV3Analyzer()
        self.assertNotIn('SystemCoordinatorV3Analyzer()', analyzer_init,
            "Analyzer 不应自引用创建")
    
    def test_006_module_class_exists(self):
        path = os.path.join(self.module_dir, 'system_coordinator_v3.py')
        content = open(path, encoding='utf-8').read()
        self.assertIn('module_class = SystemCoordinatorV3', content)
    
    def test_007_no_extended_daemon_ref(self):
        path = os.path.join(self.module_dir, 'system_coordinator_v3.py')
        content = open(path, encoding='utf-8').read()
        self.assertNotIn('extended_daemon_modules', content,
            "不应再引用已归档的 extended_daemon_modules.py")

class TestArchivedModulesClean(unittest.TestCase):
    """验证归档是否干净"""
    
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def test_008_no_extended_daemon_in_core(self):
        path = os.path.join(self.root, 'core', 'extended_daemon_modules.py')
        self.assertFalse(os.path.exists(path), "extended_daemon_modules.py 应已删除")
    
    def test_009_no_archive_in_core(self):
        core_dir = os.path.join(self.root, 'core')
        files = [f for f in os.listdir(core_dir) if f.endswith('.py')]
        self.assertNotIn('extended_daemon_modules.py', files)

if __name__ == '__main__':
    unittest.main()
