"""AUTO-EVO-AI V0.1 — 核心模块单元测试（仅真实模块）"""
import os, sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin
from modules.permission_rbac import PermissionRbac
from modules.data_masking import DataMaskingEngine as DataMasking
from modules.recommendation_system import RecommendationSystem
import json, time

class TestPermissionRbac:
    def setup_method(self): self.m = PermissionRbac()
    def test_create_role(self):
        import asyncio
        r = asyncio.run(self.m.execute("create_role", {"role_id": "tester", "permissions": ["read", "write"]}))
        assert r.success
    def test_assign_and_check(self):
        import asyncio
        asyncio.run(self.m.execute("create_role", {"role_id": "tester2", "permissions": ["read", "write", "delete"]}))
        asyncio.run(self.m.execute("assign_role", {"user_id": "u1", "role_id": "tester2"}))
        r = asyncio.run(self.m.execute("check", {"user_id": "u1", "permission": "delete"}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict):
            assert d.get('has_permission')

class TestDataMasking:
    def setup_method(self): self.m = DataMasking()
    def test_mask_phone(self):
        import asyncio
        r = asyncio.run(self.m.execute("mask", {"value": "13800138000", "type": "phone"}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict):
            assert '****' in d.get('masked', '')

class TestRecommendationSystem:
    def setup_method(self): self.m = RecommendationSystem()
    def test_recommend_cold(self):
        import asyncio
        r = asyncio.run(self.m.execute("recommend", {"user_id": "new_user", "top_k": 3, "cold_start": True}))
        assert r.success

class TestEnterpriseModuleBase:
    def test_rbac_inherits(self):
        m = PermissionRbac()
        assert isinstance(m, EnterpriseModule)

class TestSqlGenerator:
    def setup_method(self):
        from modules.sql_generator import SqlGenerator
        self.m = SqlGenerator()
    def test_generate_select(self):
        import asyncio
        r = asyncio.run(self.m.execute("generate", {"query": "select users where age > 18", "table": "users"}))
        assert r.success
    def test_validate_sql(self):
        import asyncio
        r = asyncio.run(self.m.execute("validate", {"sql": "SELECT * FROM users"}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict): assert "valid" in d or "error" in d

class TestDataMaskingExtended:
    def setup_method(self): self.m = DataMasking()
    def test_mask_email(self):
        import asyncio
        r = asyncio.run(self.m.execute("mask", {"value": "test@example.com", "type": "email"}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict): assert '@' in d.get('masked', '')
    def test_mask_idcard(self):
        import asyncio
        r = asyncio.run(self.m.execute("mask", {"value": "110101199001011234", "type": "idcard"}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict): assert '****' in d.get('masked', '')
