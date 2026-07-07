"""运行系统测试并打印结果"""
import os, sys, unittest

# Add project root to path
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
os.chdir(root)

# Test files
from tests.test_system_integrity import (
    TestSystemIntegrity, TestConfigIntegrity, TestModuleConsistency
)
from tests.test_smart_chat import (
    TestNavigationMap, TestActionMap, TestInfoQueries,
    TestCreateKeywords, TestSystemCapabilities,
    TestModulesFolders, TestApiRoutes, TestApiServer,
    TestFrontendFiles, TestConfigFiles, TestCoreFiles
)

loader = unittest.TestLoader()
suite = unittest.TestSuite()
test_classes = [
    TestSystemIntegrity, TestConfigIntegrity, TestModuleConsistency,
    TestNavigationMap, TestActionMap, TestInfoQueries,
    TestCreateKeywords, TestSystemCapabilities,
    TestModulesFolders, TestApiRoutes, TestApiServer,
    TestFrontendFiles, TestConfigFiles, TestCoreFiles
]

for tc in test_classes:
    suite.addTests(loader.loadTestsFromTestCase(tc))

runner = unittest.TextTestRunner(verbosity=0)
result = runner.run(suite)
print(f"\n{'='*50}")
print(f"总计: {result.testsRun}  |  通过: {result.testsRun - len(result.failures) - len(result.errors)}  |  失败: {len(result.failures)}  |  错误: {len(result.errors)}")
if result.failures:
    print(f"\n失败项:")
    for t, tb in result.failures:
        print(f"  [FAIL] {t.id()}")
if result.errors:
    print(f"\n错误项:")
    for t, tb in result.errors:
        print(f"  [ERROR] {t.id()}")
exit(0 if result.wasSuccessful() else 1)
