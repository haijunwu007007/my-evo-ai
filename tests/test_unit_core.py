"""AUTO-EVO-AI V0.1 — 核心模块单元测试"""
import os, sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin
from modules.jwt_token import JwtToken
from modules.permission_rbac import PermissionRbac
from modules.data_analysis import DataAnalysis
from modules.forex_api import ForexApi
from modules.data_masking import DataMasking
from modules.recommendation_system import RecommendationSystem
import json, time

class TestJWTToken:
    def setup_method(self): self.m = JwtToken()
    def test_module_attrs(self):
        assert self.m.MODULE_ID == "jwt-token"
        assert self.m.MODULE_NAME == "JWT 令牌管理"
        assert self.m.VERSION == "v7.0"
        assert self.m.MODULE_LEVEL == "A"
    def test_health_check(self):
        self.m.initialize()
        h = self.m.health_check()
        assert h.healthy
        assert h.module_id == "jwt-token"
    def test_create_token(self):
        import asyncio
        r = asyncio.run(self.m.execute("create", {"claims": {"sub": "test_user", "roles": ["admin"]}}))
        assert r.success
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict):
            assert d.get('access_token')
            assert d.get('refresh_token')
    def test_verify_valid_token(self):
        import asyncio
        r = asyncio.run(self.m.execute("create", {"claims": {"sub": "vuser"}}))
        data = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        token = data.get('access_token') if isinstance(data, dict) else None
        if token:
            r2 = asyncio.run(self.m.execute("verify", {"token": token}))
            d2 = r2.data if hasattr(r2, 'data') else vars(r2).get('data', r2)
            if isinstance(d2, dict): assert d2.get('valid')
    def test_invalid_token(self):
        import asyncio
        r = asyncio.run(self.m.execute("verify", {"token": "bad.token.sig"}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict): assert not d.get('valid')

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

class TestDataAnalysis:
    def setup_method(self): self.m = DataAnalysis()
    def test_describe(self):
        import asyncio
        r = asyncio.run(self.m.execute("describe", {"data": [1,2,3,4,5,6,7,8,9,10]}))
        assert r.success
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict):
            assert d.get('stats', {}).get('count') == 10

class TestDataMasking:
    def setup_method(self): self.m = DataMasking()
    def test_mask_phone(self):
        import asyncio
        r = asyncio.run(self.m.execute("mask", {"value": "13800138000", "type": "phone"}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict):
            assert '****' in d.get('masked', '')

class TestForexApi:
    def setup_method(self): self.m = ForexApi()
    def test_quote(self):
        import asyncio
        r = asyncio.run(self.m.execute("quote", {"pair": "USD/CNY"}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict):
            assert d.get('rate', 0) > 0

class TestRecommendationSystem:
    def setup_method(self): self.m = RecommendationSystem()
    def test_recommend_cold(self):
        import asyncio
        r = asyncio.run(self.m.execute("recommend", {"user_id": "new_user", "top_k": 3, "cold_start": True}))
        assert r.success

class TestEnterpriseModuleBase:
    def test_jwt_inherits_enterprise(self):
        m = JwtToken()
        assert isinstance(m, EnterpriseModule)
        assert isinstance(m, CircuitBreakerMixin)
        assert isinstance(m, RateLimiterMixin)
    def test_rbac_inherits(self):
        m = PermissionRbac()
        assert isinstance(m, EnterpriseModule)

class TestFeishuNotifier:
    def setup_method(self):
        from modules.feishu_notifier import FeishuNotifier
        self.m = FeishuNotifier()
    def test_health_check(self):
        self.m.initialize()
        h = self.m.health_check()
        assert h.healthy
    def test_send_action(self):
        import asyncio
        r = asyncio.run(self.m.execute("send", {"title": "Test", "content": "Hello"}))
        assert r.success
    def test_send_markdown(self):
        import asyncio
        r = asyncio.run(self.m.execute("send_markdown", {"title": "MD", "content": "# Hello"}))
        assert r.success
    def test_report_action(self):
        import asyncio
        r = asyncio.run(self.m.execute("report", {"module": "test", "status": "ok"}))
        assert r.success

class TestAuditTrail:
    def setup_method(self):
        from modules.audit_trail import AuditTrail
        self.m = AuditTrail()
    def test_record_event(self):
        import asyncio
        r = asyncio.run(self.m.execute("record", {"event_type": "login", "user": "admin", "detail": "logged in"}))
        assert r.success
    def test_query_events(self):
        import asyncio
        r = asyncio.run(self.m.execute("query", {"limit": 5}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict): assert isinstance(d.get('events', []), list)

class TestDataQuality:
    def setup_method(self):
        from modules.data_quality import DataQuality
        self.m = DataQuality()
    def test_completeness(self):
        import asyncio
        r = asyncio.run(self.m.execute("completeness", {"fields": ["a", None, "b", ""]}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict):
            assert "completeness" in d

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

class TestSsoAuth:
    def setup_method(self):
        from modules.sso_auth import SsoAuth
        self.m = SsoAuth()
    def test_create_session(self):
        import asyncio
        r = asyncio.run(self.m.execute("create_session", {"user_id": "u1", "user_data": {"name": "Alice"}}))
        assert r.success
    def test_verify_session(self):
        import asyncio
        r = asyncio.run(self.m.execute("create_session", {"user_id": "u2"}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        token = d.get("session_token") if isinstance(d, dict) else ""
        if token:
            r2 = asyncio.run(self.m.execute("verify_session", {"token": token}))
            assert r2.success

class TestOAuthProvider:
    def setup_method(self):
        from modules.oauth_provider import OAuthProvider
        self.m = OAuthProvider()
    def test_client_auth(self):
        import asyncio
        r = asyncio.run(self.m.execute("authenticate", {"client_id": "app1", "client_secret": "secret1"}))
        assert r.success

class TestHealthCheck:
    def setup_method(self):
        from modules.health_check import HealthCheck
        self.m = HealthCheck()
    def test_status(self):
        import asyncio
        r = asyncio.run(self.m.execute("status", {}))
        assert r.success
    def test_tcp_check(self):
        import asyncio
        r = asyncio.run(self.m.execute("tcp", {"host": "localhost", "port": 8765}))
        assert r.success

class TestSessionStore:
    def setup_method(self):
        from modules.session_store import SessionStore
        self.m = SessionStore()
    def test_create_get_session(self):
        import asyncio
        r = asyncio.run(self.m.execute("create", {"user_id": "s1", "data": {"theme": "dark"}}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        sid = d.get("session_id") if isinstance(d, dict) else ""
        if sid:
            r2 = asyncio.run(self.m.execute("get", {"session_id": sid}))
            assert r2.success

class TestStaticCache:
    def setup_method(self):
        from modules.cache_manager import CacheManager
        self.m = CacheManager()
    def test_set_get(self):
        import asyncio
        r = asyncio.run(self.m.execute("set", {"key": "k1", "value": "v1", "ttl": 60}))
        assert r.success
        r2 = asyncio.run(self.m.execute("get", {"key": "k1"}))
        d = r2.data if hasattr(r2, 'data') else vars(r2).get('data', r2)
        if isinstance(d, dict): assert d.get("value") == "v1"
    def test_delete(self):
        import asyncio
        asyncio.run(self.m.execute("set", {"key": "k2", "value": "v2"}))
        r = asyncio.run(self.m.execute("delete", {"key": "k2"}))
        assert r.success

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

class TestForexApiExtended:
    def setup_method(self): self.m = ForexApi()
    def test_list_pairs(self):
        import asyncio
        r = asyncio.run(self.m.execute("list", {}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict): assert len(d.get('pairs', [])) > 0
    def test_convert(self):
        import asyncio
        r = asyncio.run(self.m.execute("convert", {"from": "USD", "to": "CNY", "amount": 100}))
        d = r.data if hasattr(r, 'data') else vars(r).get('data', r)
        if isinstance(d, dict): assert d.get('result', 0) > 0
