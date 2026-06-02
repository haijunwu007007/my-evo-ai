"""V0.2 最终覆盖测试 — Plugin + DB + Auth + Config"""
import pytest, os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ── Plugin 系统测试 ──
class TestPluginSystem:
    def test_plugin_base_import(self):
        from modules._base.plugin_base import PluginBase
        assert PluginBase is not None

    def test_plugin_manager_import(self):
        from modules._base.plugin_manager import PluginManager, HOOKS
        assert PluginManager is not None
        assert 'on_startup' in HOOKS

    def test_sample_plugin_load(self):
        from modules._base.plugin_manager import plugin_manager
        pm = plugin_manager
        pm.scan_directory(os.path.join(os.path.dirname(__file__), '..', 'modules'))
        all_p = pm.all
        assert 'sample-hello' in all_p, f"sample-hello not found in {list(all_p.keys())}"
        hello = all_p['sample-hello']
        hc = hello.health_check()
        assert hc.get('healthy') is True
        assert hc.get('status') == 'ok'

# ── DB Provider 测试 ──
class TestDbProvider:
    def test_sqlite_default(self):
        os.environ['EVO_DB_URL'] = 'sqlite:///:memory:'
        from core.db_provider import get_db, SqliteEngine
        db = get_db()
        assert isinstance(db, SqliteEngine)

    def test_postgres_fallback(self):
        os.environ['EVO_DB_URL'] = 'postgresql://u:p@localhost:5432/test'
        from core.db_provider import get_db, SqliteEngine
        db = get_db()
        assert isinstance(db, SqliteEngine)  # 没有asyncpg则降级

# ── Auth Provider 测试 ──
class TestAuthProvider:
    def test_create_token(self):
        from core.auth_provider import create_token
        t = create_token('test')
        assert 'access_token' in t
        assert t.get('token_type') == 'bearer'

    def test_verify_api_key(self):
        from core.auth_provider import verify_api_key
        assert verify_api_key('') == False

# ── Config 测试 ──
class TestConfigLoader:
    def test_config_load(self):
        from core.config_loader import load_config
        cfg = load_config()
        assert cfg is not None
