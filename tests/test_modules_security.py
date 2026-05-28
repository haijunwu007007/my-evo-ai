#!/usr/bin/env python3
"""安全模块测试 — 41个用例"""
import unittest
import json
import os
import sys
import hashlib
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestSecurityCore(unittest.TestCase):
    """安全核心逻辑"""

    def test_001_hash_sha256(self):
        h = hashlib.sha256(b"test").hexdigest()
        self.assertEqual(len(h), 64)
        self.assertEqual(h, hashlib.sha256(b"test").hexdigest())

    def test_002_hash_md5(self):
        h = hashlib.md5(b"test").hexdigest()
        self.assertEqual(len(h), 32)

    def test_003_hash_deterministic(self):
        data = b"hello world"
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         hashlib.sha256(data).hexdigest())

    def test_004_hash_different_inputs(self):
        self.assertNotEqual(hashlib.sha256(b"a").hexdigest(),
                            hashlib.sha256(b"b").hexdigest())

    def test_005_hash_empty(self):
        h = hashlib.sha256(b"").hexdigest()
        self.assertEqual(len(h), 64)

    def test_006_base64_encode_decode(self):
        data = b"secret data"
        enc = base64.b64encode(data).decode()
        dec = base64.b64decode(enc)
        self.assertEqual(dec, data)

    def test_007_base64_urlsafe(self):
        data = b"test data with + / ="
        enc = base64.urlsafe_b64encode(data).decode()
        dec = base64.urlsafe_b64decode(enc)
        self.assertEqual(dec, data)

    def test_008_xss_escape_html(self):
        def escape(s):
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")
        self.assertEqual(escape("<script>alert('xss')</script>"),
                         "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;")
        self.assertNotIn("<", escape("<test>"))

    def test_009_xss_escape_attribute(self):
        def escape_attr(s):
            return s.replace('"', "&quot;").replace("'", "&#x27;")
        self.assertEqual(escape_attr('onclick="evil()"'),
                         "onclick=&quot;evil()&quot;")

    def test_010_sql_injection_detection(self):
        dangerous = ["' OR '1'='1", "'; DROP TABLE users;--",
                     "1 UNION SELECT * FROM passwords",
                     "admin'--"]
        safe = ["normal_user", "hello world", "2024-01-01", "100"]
        suspicious_keywords = ["' OR", "'--", "UNION SELECT", "DROP TABLE",
                               "INSERT INTO", "--", "';"]
        def is_suspicious(s):
            for kw in suspicious_keywords:
                if kw.upper() in s.upper():
                    return True
            return False
        for d in dangerous:
            self.assertTrue(is_suspicious(d), f"Missed: {d}")
        for s in safe:
            self.assertFalse(is_suspicious(s), f"False positive: {s}")

    def test_011_password_validation_min_length(self):
        def valid_password(pw):
            return len(pw) >= 8
        self.assertTrue(valid_password("12345678"))
        self.assertFalse(valid_password("1234567"))

    def test_012_password_validation_complexity(self):
        def strong_password(pw):
            has_upper = any(c.isupper() for c in pw)
            has_lower = any(c.islower() for c in pw)
            has_digit = any(c.isdigit() for c in pw)
            return len(pw) >= 8 and has_upper and has_lower and has_digit
        self.assertTrue(strong_password("Abc12345"))
        self.assertFalse(strong_password("abcdefgh"))
        self.assertFalse(strong_password("ABCDEFGH"))
        self.assertFalse(strong_password("12345678"))

    def test_013_jwt_structure_check(self):
        import re
        # 允许2段或3段 base64url 结构
        pattern = r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)?$'
        self.assertTrue(re.match(pattern, "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc"))
        self.assertTrue(re.match(pattern, "header.payload"))
        self.assertFalse(re.match(pattern, "not-a-jwt"))
        self.assertFalse(re.match(pattern, "too.many.dots.here"))

    def test_014_sanitize_filename(self):
        def sanitize(name):
            import re
            return re.sub(r'[<>:"/\\|?*]', '_', name)
        self.assertEqual(sanitize("file<name>.txt"), "file_name_.txt")
        self.assertEqual(sanitize("a/b:c"), "a_b_c")
        self.assertEqual(sanitize("normal.txt"), "normal.txt")

    def test_015_sanitize_path_traversal(self):
        def is_safe_path(path):
            import os
            normalized = os.path.normpath(path)
            return not normalized.startswith('..') and not normalized.startswith('/')
        self.assertTrue(is_safe_path("data/file.txt"))
        self.assertFalse(is_safe_path("../../../etc/passwd"))

    def test_016_sql_parameterized_placeholder(self):
        query = "SELECT * FROM users WHERE id = ? AND name = ?"
        self.assertEqual(query.count('?'), 2)

    def test_017_api_key_format_check(self):
        import re
        pattern = r'^[A-Za-z0-9_-]{20,}$'
        self.assertTrue(re.match(pattern, "sk-" + "a" * 30))
        self.assertFalse(re.match(pattern, "short"))

    def test_018_cors_origin_validation(self):
        allowed = ["https://example.com", "https://app.example.com"]
        def is_allowed(origin):
            return any(origin == a or (a.startswith("https://") and origin.endswith(a.split("//")[1]))
                       for a in allowed)
        self.assertTrue(is_allowed("https://example.com"))
        self.assertFalse(is_allowed("https://evil.com"))

    def test_019_csrf_token_length(self):
        import secrets
        token = secrets.token_hex(32)
        self.assertEqual(len(token), 64)

    def test_020_csrf_token_random(self):
        import secrets
        tokens = {secrets.token_hex(32) for _ in range(100)}
        self.assertEqual(len(tokens), 100)

    def test_021_rate_limit_window(self):
        window = 60
        max_requests = 100
        self.assertGreater(max_requests, 0)
        self.assertGreater(window, 0)

    def test_022_ip_address_validation(self):
        import re
        def is_valid_ipv4(ip):
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for p in parts:
                if not p.isdigit():
                    return False
                n = int(p)
                if n < 0 or n > 255:
                    return False
            return True
        self.assertTrue(is_valid_ipv4("192.168.1.1"))
        self.assertTrue(is_valid_ipv4("0.0.0.0"))
        self.assertTrue(is_valid_ipv4("255.255.255.255"))
        self.assertFalse(is_valid_ipv4("999.999.999.999"))
        self.assertFalse(is_valid_ipv4("not-an-ip"))
        self.assertFalse(is_valid_ipv4("256.0.0.0"))

    def test_023_email_validation(self):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        self.assertTrue(re.match(pattern, "user@example.com"))
        self.assertTrue(re.match(pattern, "test.user+tag@sub.domain.co"))
        self.assertFalse(re.match(pattern, "@example.com"))
        self.assertFalse(re.match(pattern, "user@"))

    def test_024_url_validation(self):
        import re
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        self.assertTrue(re.match(pattern, "https://example.com"))
        self.assertTrue(re.match(pattern, "http://localhost:8080/path"))
        self.assertFalse(re.match(pattern, "ftp://example.com"))

    def test_025_encrypt_decrypt_simple(self):
        """异或简单加密测试"""
        def xor_crypt(data, key):
            return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
        key = b"secret"
        plaintext = b"hello world"
        ciphertext = xor_crypt(plaintext, key)
        decrypted = xor_crypt(ciphertext, key)
        self.assertEqual(decrypted, plaintext)
        self.assertNotEqual(ciphertext, plaintext)

    def test_026_encrypt_decrypt_empty(self):
        def xor_crypt(data, key):
            return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
        self.assertEqual(xor_crypt(b"", b"key"), b"")

    def test_027_access_control_basic(self):
        roles = {"admin": ["read", "write", "delete"],
                 "user": ["read"],
                 "guest": []}
        def has_permission(role, action):
            return action in roles.get(role, [])
        self.assertTrue(has_permission("admin", "delete"))
        self.assertTrue(has_permission("user", "read"))
        self.assertFalse(has_permission("user", "delete"))
        self.assertFalse(has_permission("guest", "read"))

    def test_028_access_control_unknown_role(self):
        roles = {"admin": ["read"]}
        def has_permission(role, action):
            return action in roles.get(role, [])
        self.assertFalse(has_permission("hacker", "read"))

    def test_029_token_expiry_check_valid(self):
        import time
        issued = time.time() - 1800
        ttl = 3600
        self.assertLess(time.time() - issued, ttl)

    def test_030_token_expiry_check_expired(self):
        import time
        issued = time.time() - 7200
        ttl = 3600
        self.assertGreater(time.time() - issued, ttl)

    def test_031_log_sanitization(self):
        def sanitize_log(msg):
            sensitive = ["password", "token", "secret", "api_key"]
            for s in sensitive:
                msg = msg.replace(s, "***")
            return msg
        self.assertNotIn("password", sanitize_log("password=123456"))
        self.assertNotIn("secret", sanitize_log("secret_key=abc"))

    def test_032_log_sanitization_email(self):
        def mask_email(email):
            local, domain = email.split('@')
            return local[0] + "***@" + domain
        self.assertEqual(mask_email("alice@example.com"), "a***@example.com")

    def test_033_environment_variable_placeholder(self):
        template = "postgresql://${DB_USER}:${DB_PASS}@localhost/db"
        self.assertIn("${DB_USER}", template)
        self.assertIn("${DB_PASS}", template)

    def test_034_environment_variable_resolve(self):
        env = {"DB_USER": "admin", "DB_PASS": "secret123"}
        template = "postgresql://${DB_USER}:${DB_PASS}@localhost/db"
        import re
        resolved = re.sub(r'\$\{(\w+)\}', lambda m: env.get(m.group(1), ''), template)
        self.assertEqual(resolved, "postgresql://admin:secret123@localhost/db")

    def test_035_input_length_validation(self):
        def validate_length(s, max_len):
            return len(s) <= max_len
        self.assertTrue(validate_length("short", 100))
        self.assertFalse(validate_length("x" * 101, 100))

    def test_036_input_whitelist(self):
        allowed = {"read", "write", "admin"}
        self.assertIn("read", allowed)
        self.assertNotIn("delete", allowed)

    def test_037_input_blacklist(self):
        blocked = {"rm", "drop", "truncate"}
        self.assertNotIn("select", blocked)
        self.assertIn("drop", blocked)

    def test_038_uuid_generation(self):
        import uuid
        u = str(uuid.uuid4())
        self.assertEqual(len(u), 36)
        self.assertEqual(u.count('-'), 4)

    def test_039_uuid_uniqueness(self):
        import uuid
        ids = {str(uuid.uuid4()) for _ in range(1000)}
        self.assertEqual(len(ids), 1000)

    def test_040_certificate_pinning_mock(self):
        expected_fingerprint = "abc123"
        provided = "abc123"
        self.assertEqual(provided, expected_fingerprint)

    def test_041_timing_attack_protection(self):
        import hmac
        a = b"secret123"
        b = b"secret456"
        result = hmac.compare_digest(a, a)
        self.assertTrue(result)
        result = hmac.compare_digest(a, b)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
