"""测试共享数据层 + 消息总线 + 认证提供者"""
import pytest, json, os, time
from pathlib import Path


class TestDataEngine:
    def test_basic_crud(self):
        from core.data_layer import DataEngine
        db = DataEngine.get("test_engine")
        db.execute("CREATE TABLE IF NOT EXISTS _test (id INTEGER PRIMARY KEY, name TEXT, value TEXT)")
        db.execute("DELETE FROM _test")

        # insert
        rid = db.insert("_test", {"name": "test1", "value": "hello"})
        assert rid > 0

        # fetch
        row = db.fetch_one("SELECT * FROM _test WHERE id=?", (rid,))
        assert row["name"] == "test1"
        assert row["value"] == "hello"

        # update
        db.update("_test", {"value": "world"}, "id=?", (rid,))
        row = db.fetch_one("SELECT * FROM _test WHERE id=?", (rid,))
        assert row["value"] == "world"

        # fetch_all
        rows = db.fetch_all("SELECT * FROM _test")
        assert len(rows) == 1

        # delete
        db.delete("_test", "id=?", (rid,))
        rows = db.fetch_all("SELECT * FROM _test")
        assert len(rows) == 0

    def test_upsert(self):
        from core.data_layer import DataEngine
        db = DataEngine.get("test_upsert")
        db.execute("CREATE TABLE IF NOT EXISTS _upsert (k TEXT PRIMARY KEY, v TEXT)")
        db.execute("DELETE FROM _upsert")

        db.upsert("_upsert", {"k": "a", "v": "1"}, "k")
        db.upsert("_upsert", {"k": "a", "v": "2"}, "k")
        row = db.fetch_one("SELECT * FROM _upsert WHERE k=?", ("a",))
        assert row["v"] == "2"

    def test_stats(self):
        from core.data_layer import DataEngine
        db = DataEngine.get("test_stats")
        s = db.stats()
        assert "tables" in s
        assert "size_bytes" in s

    def test_json_store(self):
        from core.data_layer import JSONStore
        store = JSONStore("test_json")
        store.save("key1", {"a": 1, "b": [2, 3]})
        val = store.load("key1")
        assert val["a"] == 1
        assert val["b"] == [2, 3]
        assert "key1" in store.keys()
        store.delete("key1")
        assert store.load("key1") == {}


class TestMessageBus:
    def test_sync_publish(self):
        from core.message_bus import MessageBus
        bus = MessageBus()
        received = []

        def handler(event):
            received.append(event.data)

        bus.subscribe("test.topic", handler)
        bus.publish("test.topic", "hello")
        assert received == ["hello"]

    def test_wildcard(self):
        from core.message_bus import MessageBus
        bus = MessageBus()
        received = []

        def handler(event):
            received.append(event.topic)

        bus.subscribe("module.*", handler)
        bus.publish("module.system.health", "ok")
        bus.publish("module.ai.status", "running")
        assert len(received) == 2

    def test_history(self):
        from core.message_bus import MessageBus
        bus = MessageBus()
        bus.publish("test.history", "e1")
        bus.publish("test.history", "e2")
        history = bus.get_history("test.history")
        assert len(history) >= 2

    def test_stats(self):
        from core.message_bus import MessageBus
        bus = MessageBus()
        s = bus.stats()
        assert "sync_subscriptions" in s
        assert "topics" in s


class TestAuthProvider:
    def test_create_and_verify_token(self):
        from core.auth_provider import create_token, verify_token
        token = create_token("test_user", role="admin")
        assert "access_token" in token
        assert token["role"] == "admin"

        payload = verify_token(token["access_token"])
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["role"] == "admin"

    def test_invalid_token(self):
        from core.auth_provider import verify_token
        payload = verify_token("invalid.token.here")
        assert payload is None

    def test_tampered_token(self):
        from core.auth_provider import create_token, verify_token
        token = create_token("user1")["access_token"]
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.tampered"
        payload = verify_token(tampered)
        assert payload is None

    def test_api_key(self):
        from core.auth_provider import verify_api_key
        assert verify_api_key("evo-admin-key-2026") is True
        assert verify_api_key("wrong-key") is False

    def test_role_check(self):
        from core.auth_provider import create_token, verify_token, check_role
        token = create_token("user1", role="user")["access_token"]
        payload = verify_token(token)
        assert check_role(payload, "user") is True
        assert check_role(payload, "admin") is False
