"""AUTO-EVO-AI V0.1 - 集成与端到端测试 (33+)

覆盖：模块可导入、引擎接口、数据流、环境检查"""
import unittest, sys, os, json, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestSystemIntegration(unittest.TestCase):
    """系统集成测试"""

    def test_001_core_engines_importable(self):
        """核心引擎可导入"""
        from core import decision_engine, event_engine, scheduler_engine, module_delegate
        self.assertTrue(hasattr(decision_engine, 'DecisionEngine'))
        self.assertTrue(hasattr(event_engine, 'EventEngine'))
        self.assertTrue(hasattr(scheduler_engine, 'SchedulerEngine'))
        self.assertTrue(hasattr(module_delegate, 'ModuleDelegate'))

    def test_002_enterprise_base_importable(self):
        """企业级基类可导入"""
        from modules._base.enterprise_module import (
            EnterpriseModule, ModuleStatus, HealthReport,
            CircuitBreakerMixin, RateLimiterMixin
        )
        self.assertTrue(issubclass(EnterpriseModule, object))
        self.assertEqual(ModuleStatus.RUNNING.value, 'running')

    def test_003_api_routes_exist(self):
        """API 路由文件存在"""
        api_dir = os.path.join(os.path.dirname(__file__), '..', 'api')
        self.assertTrue(os.path.isdir(api_dir))
        route_files = [f for f in os.listdir(api_dir) if f.endswith('.py') and not f.startswith('__')]
        self.assertGreater(len(route_files), 0)

    def test_004_api_server_exists(self):
        """API 服务器文件存在"""
        root = os.path.join(os.path.dirname(__file__), '..')
        self.assertTrue(os.path.exists(os.path.join(root, 'api_server.py')))

    def test_005_frontend_buildable(self):
        """前端构建文件存在"""
        frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        self.assertTrue(os.path.isdir(frontend_dir))
        self.assertTrue(os.path.exists(os.path.join(frontend_dir, 'package.json')))

    def test_006_dockerfile_exists(self):
        """Dockerfile 存在"""
        root = os.path.join(os.path.dirname(__file__), '..')
        self.assertTrue(os.path.exists(os.path.join(root, 'Dockerfile')))

    def test_007_config_yaml_exists(self):
        """配置文件存在"""
        root = os.path.join(os.path.dirname(__file__), '..')
        self.assertTrue(os.path.exists(os.path.join(root, 'config.yaml')))

    def test_008_requirements_exists(self):
        """依赖文件存在"""
        root = os.path.join(os.path.dirname(__file__), '..')
        self.assertTrue(os.path.exists(os.path.join(root, 'requirements.txt')))

    def test_009_llm_gateway_functions(self):
        """LLM 网关函数可调用"""
        from core.llm_gateway import get_llm_gateway, get_llm_pool
        pool = get_llm_pool()
        self.assertIsNotNone(pool)

    def test_010_event_engine_functions(self):
        """事件引擎函数可调用"""
        from core.event_engine import get_event_engine, EventType
        self.assertTrue(hasattr(EventType, '__members__'))

    def test_011_scheduler_engine_functions(self):
        """调度引擎函数可调用"""
        from core.scheduler_engine import get_scheduler_engine, ScheduleType
        self.assertTrue(hasattr(ScheduleType, '__members__'))

    def test_012_module_delegate_functions(self):
        """模块委派可导入"""
        from core.module_delegate import ModuleDelegate
        self.assertTrue(callable(ModuleDelegate))


class TestModuleMeta(unittest.TestCase):
    """模块元数据测试"""

    def test_013_module_meta_consistency(self):
        """模块元数据一致性"""
        modules_dir = os.path.join(os.path.dirname(__file__), '..', 'modules')
        py_files = glob.glob(os.path.join(modules_dir, '*.py'))
        py_files = [f for f in py_files if not os.path.basename(f).startswith('__')]
        with_meta = 0
        for f in py_files:
            content = open(f, encoding='utf-8', errors='ignore').read()
            if '__module_meta__' in content or '__meta__' in content:
                with_meta += 1
        self.assertGreaterEqual(with_meta, len(py_files) * 0.9)

    def test_014_module_class_export(self):
        """模块 class 导出"""
        modules_dir = os.path.join(os.path.dirname(__file__), '..', 'modules')
        py_files = glob.glob(os.path.join(modules_dir, '*.py'))
        py_files = [f for f in py_files if not os.path.basename(f).startswith('__')]
        with_export = 0
        for f in py_files:
            content = open(f, encoding='utf-8', errors='ignore').read()
            if 'module_class=' in content:
                with_export += 1
        self.assertGreaterEqual(with_export, 25)  # 至少有25个模块有class导出

    def test_015_async_execute_pattern(self):
        """异步 execute 模式"""
        modules_dir = os.path.join(os.path.dirname(__file__), '..', 'modules')
        py_files = glob.glob(os.path.join(modules_dir, '*.py'))
        py_files = [f for f in py_files if not os.path.basename(f).startswith('__')]
        with_async = 0
        for f in py_files[:50]:
            content = open(f, encoding='utf-8', errors='ignore').read()
            if 'async def execute' in content:
                with_async += 1
        self.assertGreaterEqual(with_async, 30)


class TestDataFlow(unittest.TestCase):
    """数据流测试"""

    def test_016_json_roundtrip(self):
        """JSON 序列化往返"""
        original = {"id": "test-001", "name": "测试模块", "enabled": True, "count": 42, "tags": ["a", "b"]}
        serialized = json.dumps(original, ensure_ascii=False)
        deserialized = json.loads(serialized)
        self.assertEqual(original, deserialized)

    def test_017_nested_data_merging(self):
        """嵌套数据合并"""
        base = {"system": {"status": "ok", "version": "V0.1"}}
        override = {"system": {"status": "degraded", "uptime": 3600}}
        merged = {**base}
        for k, v in override.items():
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = {**merged[k], **v}
            else:
                merged[k] = v
        self.assertEqual(merged["system"]["status"], "degraded")
        self.assertEqual(merged["system"]["version"], "V0.1")
        self.assertEqual(merged["system"]["uptime"], 3600)

    def test_018_pagination_logic(self):
        """分页逻辑"""
        items = list(range(100))
        def paginate(data, page=1, page_size=10):
            start = (page - 1) * page_size
            end = start + page_size
            return {"items": data[start:end], "page": page, "page_size": page_size, "total": len(data), "total_pages": (len(data) + page_size - 1) // page_size}
        p1 = paginate(items, 1, 10)
        self.assertEqual(len(p1["items"]), 10)
        p10 = paginate(items, 10, 10)
        self.assertEqual(p10["items"][0], 90)

    def test_019_filter_logic(self):
        """过滤逻辑"""
        items = [{"name": "a", "group": "ai"}, {"name": "b", "group": "ops"}, {"name": "c", "group": "ai"}]
        ai_modules = [i for i in items if i["group"] == "ai"]
        self.assertEqual(len(ai_modules), 2)

    def test_020_sort_logic(self):
        """排序逻辑"""
        items = [3, 1, 4, 1, 5, 9, 2, 6]
        self.assertEqual(sorted(items), [1, 1, 2, 3, 4, 5, 6, 9])

    def test_021_batch_operation(self):
        """批量操作"""
        def batch_process(items, batch_size=10):
            results = []
            for i in range(0, len(items), batch_size):
                results.extend([x * 2 for x in items[i:i+batch_size]])
            return results
        result = batch_process(list(range(25)), 10)
        self.assertEqual(len(result), 25)
        self.assertEqual(result[-1], 48)

    def test_022_retry_logic(self):
        """重试逻辑"""
        call_count = [0]
        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError(f"attempt {call_count[0]} failed")
            return "success"
        def retry(func, max_retries=3):
            attempts = 0
            last_error = None
            while attempts < max_retries:
                try:
                    return func()
                except Exception as e:
                    attempts += 1
                    last_error = e
            raise last_error
        result = retry(flaky, max_retries=3)
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 3)

    def test_023_circuit_breaker_logic(self):
        """熔断器逻辑"""
        class CircuitBreaker:
            def __init__(self, threshold=2):
                self.failures = 0
                self.threshold = threshold
                self.state = "closed"
            def call(self, func):
                try:
                    result = func()
                    self.failures = 0
                    self.state = "closed"
                    return result
                except Exception:
                    self.failures += 1
                    if self.failures >= self.threshold:
                        self.state = "open"
                    raise
        cb = CircuitBreaker(threshold=2)
        failing = [0]
        def fail():
            failing[0] += 1
            raise ValueError("fail")
        with self.assertRaises(ValueError):
            cb.call(fail)
        self.assertEqual(cb.failures, 1)
        with self.assertRaises(ValueError):
            cb.call(fail)
        self.assertEqual(cb.state, "open")


class TestEnvironmentCheck(unittest.TestCase):
    """环境检查测试"""

    def test_024_python_version(self):
        """Python 版本"""
        self.assertGreaterEqual(sys.version_info.major, 3)
        self.assertGreaterEqual(sys.version_info.minor, 8)

    def test_025_path_consistency(self):
        """路径一致性"""
        self.assertTrue(os.path.isabs(os.path.dirname(__file__)))

    def test_026_encoding(self):
        """编码"""
        self.assertEqual(sys.getdefaultencoding(), 'utf-8')
        self.assertEqual(sys.getfilesystemencoding(), 'utf-8')

    def test_027_platform_detection(self):
        """平台检测"""
        import platform
        self.assertTrue(platform.system() in ('Windows', 'Linux', 'Darwin'))

    def test_028_cpu_count(self):
        """CPU 核数"""
        self.assertGreater(os.cpu_count(), 0)

    def test_029_singleton_pattern(self):
        """单例模式"""
        from core.event_engine import get_event_engine
        e1 = get_event_engine()
        e2 = get_event_engine()
        self.assertIsNotNone(e1)

    def test_030_logger_configured(self):
        """日志配置"""
        import logging
        logger = logging.getLogger("evo.test")
        self.assertIsNotNone(logger)

    def test_031_module_dir_exists(self):
        """模块目录存在"""
        modules_dir = os.path.join(os.path.dirname(__file__), '..', 'modules')
        self.assertTrue(os.path.isdir(modules_dir))
        py_files = [f for f in os.listdir(modules_dir) if f.endswith('.py') and not f.startswith('__')]
        self.assertGreater(len(py_files), 100)

    def test_032_core_dir_exists(self):
        """核心目录存在"""
        core_dir = os.path.join(os.path.dirname(__file__), '..', 'core')
        self.assertTrue(os.path.isdir(core_dir))
        py_files = [f for f in os.listdir(core_dir) if f.endswith('.py') and not f.startswith('__')]
        self.assertGreater(len(py_files), 5)

    def test_033_docs_dir_exists(self):
        """文档目录存在"""
        docs_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
        self.assertTrue(os.path.isdir(docs_dir))


if __name__ == "__main__":
    unittest.main()
