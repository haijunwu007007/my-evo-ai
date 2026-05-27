"""Quick test for sso_auth method signatures"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.sso_auth import SsoAuth

sso = SsoAuth()
sso.initialize()

# Test JWT
token = sso._gen_jwt({"sub":"alice","role":"admin"}, ttl=3600)
print(f"JWT token: {token[:50]}... type={type(token).__name__}")

# Test verify
result = sso._verify_jwt(token)
print(f"Verify: valid={result.get('valid')}, sub={result.get('sub')}")

# Test password
h = sso._hash_password("MyP@ss123!")
print(f"Hash: {h[:30]}... type={type(h).__name__}")
v = sso._verify_password("MyP@ss123!", h)
print(f"Verify correct pw: {v}")
vw = sso._verify_password("wrong", h)
print(f"Verify wrong pw: {vw}")

# Test dispatch
r = sso._dispatch({"action": "generate_jwt", "sub": "alice", "role": "admin"})
print(f"Dispatch jwt: success={r.get('success')}, has_token={'token' in r}")

r2 = sso._dispatch({"action": "register_user", "username": "u1", "password": "pw1"})
print(f"Register user: success={r2.get('success')}, user_id={r2.get('user_id')}")

r3 = sso._dispatch({"action": "authenticate", "username": "u1", "password": "pw1"})
print(f"Authenticate: success={r3.get('success')}, session={r3.get('session_token','')[:20]}")
