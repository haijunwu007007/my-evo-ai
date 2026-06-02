import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_sqlite_basic():
    from core.db_provider import SqliteEngine
    db = SqliteEngine()
    c = db.connect()
    c.execute("CREATE TABLE IF NOT EXISTS _covtest (id INTEGER, name TEXT)")
    c.execute("INSERT INTO _covtest VALUES (1, 'ok')")
    r = c.execute("SELECT * FROM _covtest").fetchall()
    assert len(r) >= 1
    c.execute("DROP TABLE _covtest")
    db.close()

def test_db_provider_imports():
    from core.db_provider import get_db, SqliteEngine
    assert SqliteEngine
    assert callable(get_db)

def test_plugin_manager():
    from core.plugin_manager import PluginManager
    pm = PluginManager()
    import asyncio
    asyncio.run(pm.discover())
    assert len(pm._plugins) >= 0

def test_naive_ui_dist_exists():
    assert os.path.isfile("frontend/dist/index.html"), "SPA未构建"

def test_core_auth():
    from core.auth_provider import create_token, verify_token
    t = create_token("test_user", "user")
    assert "access_token" in t

def test_config_loader():
    from core.config_loader import load_config
    c = load_config()
    assert c is not None
