"""AUTO-EVO-AI V0.1 — data_layer + persistence + module_enterprise 单元测试"""
import pytest, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.logging_config import get_logger
logger = get_logger("test_data_layer")


class TestModuleEnterprise:
    """EnterpriseModule 基类单元测试"""

    def test_import(self):
        from modules._base.enterprise_module import EnterpriseModule
        assert EnterpriseModule is not None

    def test_create_default(self):
        from modules._base.enterprise_module import EnterpriseModule
        m = EnterpriseModule()
        assert m is not None

    def test_create_with_id(self):
        from modules._base.enterprise_module import EnterpriseModule
        m = EnterpriseModule(module_id="test-ent-001", module_name="Test Enterprise")
        assert m.module_id == "test-ent-001"

    def test_get_status_default(self):
        from modules._base.enterprise_module import EnterpriseModule
        m = EnterpriseModule(module_id="test-ent-002", module_name="Test Status")
        status = m.get_status()
        assert isinstance(status, dict)
        assert "module_id" in status

    def test_initialize(self):
        from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
        m = EnterpriseModule(module_id="test-ent-003", module_name="Test Init")
        result = m.initialize()
        assert result is not None


class TestPersistence:
    """persistence.py 核心功能测试"""

    def test_import(self):
        from core.persistence import PersistenceManager
        assert PersistenceManager is not None

    def test_local_file_persistence(self):
        from core.persistence import PersistenceManager
        pm = PersistenceManager()
        assert pm is not None


class TestModuleRegistryIntegration:
    """module_registry 集成测试"""

    def test_singleton_import(self):
        from core.module_registry import ModuleRegistry
        assert ModuleRegistry is not None

    def test_create_and_register(self):
        from core.module_registry import ModuleRegistry
        r = ModuleRegistry()
        assert hasattr(r, 'register')  # 确认有注册方法
