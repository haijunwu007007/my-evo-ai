"""测试 SQLite 数据库层"""
import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("EVO_AUTH_ENABLED", "false")
from api.database import db


def test_save_and_get():
    """保存并读取键值数据"""
    db.save("test", {"key": "color", "value": "blue"})
    r = db.get("test", "color")
    assert r is not None
    assert r.get("value") == "blue"


def test_query():
    """查询命名空间下数据"""
    db.save("test", {"key": "a", "group": "x"})
    db.save("test", {"key": "b", "group": "x"})
    results = db.query("test", {"group": "x"})
    assert len(results) >= 2


def test_delete():
    """删除数据"""
    db.save("test_del", {"key": "temp"})
    db.delete("test_del", "temp")
    r = db.get("test_del", "temp")
    assert r is None


def test_audit_log():
    """审计日志写入"""
    db.log_audit("test_action", actor="pytest", target="test", detail="单元测试")
    # 不崩溃即可
    assert True
