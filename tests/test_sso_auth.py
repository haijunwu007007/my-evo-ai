"""Test suite for sso_auth module - JWT, password hashing, session lifecycle"""
import os, sys, time, json, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.sso_auth import SsoAuth

@pytest.fixture
def sso():
    m = SsoAuth({"session_ttl": 3600, "ticket_ttl": 60})
    m.initialize()
    return m


class TestSsoAuthCore:
    def test_init(self, sso):
        """Init should set up empty stores"""
        assert len(sso._sessions) == 0
        assert len(sso._tickets) == 0

    def test_login(self, sso):
        """Login should create session"""
        r = sso._login({"user_id": "test_user", "username": "test"})
        assert r["success"] is True
        assert r["session_token"].startswith("sso_")
        assert r["user_id"] == "test_user"
        assert r["expires_in"] == 3600

    def test_login_with_username_only(self, sso):
        """Login without user_id should generate one from username"""
        r = sso._login({"username": "alice"})
        assert r["success"] is True
        assert r["user_id"].startswith("user_")

    def test_validate_session(self, sso):
        """Validate should return session info for valid tokens"""
        login = sso._login({"user_id": "vip1", "username": "vip1"})
        token = login["session_token"]
        r = sso._validate_session({"token": token})
        assert r["success"] is True
        assert r["valid"] is True
        assert r["user_id"] == "vip1"

    def test_validate_invalid_token(self, sso):
        """Invalid tokens should fail validation"""
        r = sso._validate_session({"token": "nonexistent"})
        assert r["valid"] is False

    def test_validate_expired_session(self, sso):
        """Expired sessions should fail and be cleaned up"""
        sso._sessions["expired_1"] = {
            "user_id": "ghost", "created_at": 0,
            "expires_at": time.time() - 1, "attributes": {}, "apps": []
        }
        r = sso._validate_session({"token": "expired_1"})
        assert r["valid"] is False
        assert "expired" in r["error"].lower()

    def test_logout_by_token(self, sso):
        """Logout should remove session by token"""
        login = sso._login({"user_id": "user_a"})
        token = login["session_token"]
        r = sso._logout({"session_token": token})
        assert r["success"] is True
        assert token not in sso._sessions

    def test_logout_by_user_id(self, sso):
        """Logout should remove all sessions for a user"""
        sso._login({"user_id": "user_b"})
        r = sso._logout({"user_id": "user_b"})
        assert r["success"] is True
        remaining = [k for k, v in sso._sessions.items() if v["user_id"] == "user_b"]
        assert len(remaining) == 0

    def test_ticket_create_and_exchange(self, sso):
        """Full ticket lifecycle: create -> exchange"""
        login = sso._login({"user_id": "ticket_user"})
        token = login["session_token"]
        ct = sso._create_ticket({"session_token": token, "service": "app1"})
        assert ct["success"] is True
        ticket = ct["ticket"]
        assert ticket.startswith("st-")
        ex = sso._exchange_ticket({"ticket": ticket, "service": "app1"})
        assert ex["success"] is True
        assert ex["app_session_token"].startswith("app_")
        assert ex["user_id"] == "ticket_user"

    def test_ticket_reuse_blocked(self, sso):
        """Used tickets should not be exchangeable again"""
        login = sso._login({"user_id": "single_user"})
        ct = sso._create_ticket({"session_token": login["session_token"], "service": "app_x"})
        sso._exchange_ticket({"ticket": ct["ticket"]})
        r2 = sso._exchange_ticket({"ticket": ct["ticket"]})
        assert r2["success"] is False
        assert "used" in r2["error"].lower()

    def test_ticket_expired(self, sso):
        """Expired tickets should be rejected"""
        sso._tickets["old_ticket"] = {
            "user_id": "x", "service": "app",
            "expires_at": time.time() - 10, "used": False
        }
        r = sso._exchange_ticket({"ticket": "old_ticket"})
        assert r["success"] is False

    def test_jwt_generation(self, sso):
        """_gen_jwt should return a JWT string"""
        token = sso._gen_jwt({"sub": "alice", "role": "admin"}, ttl=3600)
        assert isinstance(token, str)
        assert len(token) > 20
        assert token.count(".") == 2

    def test_jwt_verify_valid(self, sso):
        """Valid JWTs should verify correctly"""
        token = sso._gen_jwt({"sub": "bob", "role": "user"}, ttl=3600)
        r = sso._verify_jwt(token)
        assert r.get("valid") is True
        assert r["sub"] == "bob"
        assert r["role"] == "user"

    def test_jwt_verify_invalid(self, sso):
        """Invalid JWTs should fail verification"""
        r = sso._verify_jwt("not.a.jwt")
        assert r.get("valid") is False

    def test_jwt_verify_tampered(self, sso):
        """Tampered JWTs should fail signature check"""
        token = sso._gen_jwt({"sub": "alice"}, ttl=3600)
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalidsig"
        r = sso._verify_jwt(tampered)
        assert r.get("valid") is False

    def test_password_hash_and_verify(self, sso):
        """Password should hash and verify correctly"""
        pw = "MySecureP@ss123!"
        h = sso._hash_password(pw)
        assert isinstance(h, str)
        assert len(h) > 40
        assert sso._verify_password(pw, h) is True
        assert sso._verify_password("wrongpass", h) is False

    def test_register_user(self, sso):
        """register_user via dispatch should store user"""
        r = sso._dispatch({"action": "register_user", "username": "newuser", "password": "pass123"})
        assert r["success"] is True

    def test_authenticate(self, sso):
        """authenticate via dispatch should return token"""
        sso._dispatch({"action": "register_user", "username": "auth_user", "password": "secret"})
        r = sso._dispatch({"action": "authenticate", "username": "auth_user", "password": "secret"})
        assert r["success"] is True
        assert "session_token" in r

    def test_authenticate_wrong_password(self, sso):
        """authenticate should fail for wrong password"""
        sso._dispatch({"action": "register_user", "username": "locked", "password": "correct"})
        r = sso._dispatch({"action": "authenticate", "username": "locked", "password": "wrong"})
        assert r["success"] is False

    def test_get_user(self, sso):
        """get_user via dispatch should return user info"""
        reg = sso._dispatch({"action": "register_user", "username": "info_user", "password": "pw"})
        r = sso._dispatch({"action": "get_user", "user_id": reg["user_id"]})
        assert r["success"] is True

    def test_list_sessions(self, sso):
        """list_sessions should return active sessions"""
        sso._login({"user_id": "session_user"})
        r = sso._list_sessions({"limit": 10})
        assert r["success"] is True
        assert r["total_active"] >= 1

    def test_health_check(self, sso):
        """health_check should return healthy"""
        r = sso.health_check()
        assert r.status == "running"

    def test_generate_jwt_action(self, sso):
        """_generate_jwt (dispatch wrapper) should return dict with token"""
        r = sso._generate_jwt({"sub": "alice", "role": "admin"})
        assert r["success"] is True
        assert "token" in r or r.get("token")

    def test_register_app(self, sso):
        """register_app should create app entry"""
        r = sso._register_app({"name": "TestApp", "callback_urls": ["http://localhost/cb"]})
        assert r["success"] is True
        assert "app_secret" in r

    def test_delegate_available(self, sso):
        """module should have delegate"""
        assert sso.delegate is not None

    def test_execute_register_user(self, sso):
        """execute should dispatch register_user correctly"""
        import asyncio
        r = asyncio.run(sso.execute("execute", {"action": "register_user", "username": "exec_user", "password": "pw"}))
        assert r["success"] is True
