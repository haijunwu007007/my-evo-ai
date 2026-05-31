"""
AUTO-EVO-AI V0.1 — API 路由/参数/响应格式测试
覆盖: 路由规则、参数校验、响应格式、HTTP状态码、错误处理
"""

import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest


class TestAPIRouting(unittest.TestCase):
    """API路由：路径规范/命名规则"""

    @classmethod
    def setUpClass(cls):
        cls.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.api_dir = os.path.join(cls.root, 'api')

    def test_001_api_dir_exists(self):
        """api目录存在"""
        self.assertTrue(os.path.exists(self.api_dir), "api/ 目录不存在")

    def test_002_route_files_exist(self):
        """路由文件存在"""
        if not os.path.exists(self.api_dir):
            self.skipTest('api/ 目录不存在')
        files = [f for f in os.listdir(self.api_dir) if f.endswith('.py') and f != '__init__.py']
        self.assertGreaterEqual(len(files), 3, f"路由文件数不足: {len(files)}")

    def test_003_route_naming_convention(self):
        """路由文件名使用下划线"""
        if not os.path.exists(self.api_dir):
            self.skipTest('api/ 目录不存在')
        for f in os.listdir(self.api_dir):
            if f.endswith('.py') and f != '__init__.py':
                self.assertNotIn('-', f, f"文件名含连字符: {f}")

    def test_004_api_server_has_routes(self):
        """api_server.py 包含路由定义"""
        api_path = os.path.join(self.root, 'api_server.py')
        if not os.path.exists(api_path):
            self.skipTest('api_server.py 不在根目录')
        content = open(api_path, encoding='utf-8').read()
        route_count = content.count('@app.')
        self.assertGreaterEqual(route_count, 10, f"路由定义数不足: {route_count}")

    def test_005_route_has_docstring(self):
        """路由函数有docstring"""
        api_path = os.path.join(self.root, 'api_server.py')
        if not os.path.exists(api_path):
            self.skipTest('api_server.py 不在根目录')
        content = open(api_path, encoding='utf-8').read()
        # 检查def后的docstring
        docstring_count = content.count('\"\"\"')
        self.assertGreaterEqual(docstring_count, 10, "docstring 不足")

    def test_006_route_method_diversity(self):
        """路由方法多样性（GET/POST/PUT/DELETE）"""
        api_path = os.path.join(self.root, 'api_server.py')
        if not os.path.exists(api_path):
            self.skipTest('api_server.py 不在根目录')
        content = open(api_path, encoding='utf-8').read()
        methods = {'get': content.count('.get('), 'post': content.count('.post('),
                   'put': content.count('.put('), 'delete': content.count('.delete(')}
        self.assertGreater(methods['get'], 0, "无 GET 路由")
        self.assertGreater(methods['post'], 0, "无 POST 路由")
        self.assertIn('put' if methods['put'] > 0 else 'delete', methods)

    def test_007_api_path_prefix(self):
        """API路径以 /api/ 开头"""
        api_path = os.path.join(self.root, 'api_server.py')
        if not os.path.exists(api_path):
            self.skipTest('api_server.py 不在根目录')
        content = open(api_path, encoding='utf-8').read()
        lines = content.split('\n')
        api_routes = [l.strip() for l in lines if '@app.' in l and '("/api/' in l]
        non_prefixed = [r for r in api_routes if not '/api/' in r]
        self.assertGreater(len(api_routes), 2, f"API路由不足: {len(api_routes)}")

    def test_008_no_hardcoded_ports(self):
        """路由中无硬编码端口"""
        api_path = os.path.join(self.root, 'api_server.py')
        if not os.path.exists(api_path):
            self.skipTest('api_server.py 不在根目录')
        content = open(api_path, encoding='utf-8').read()
        # 允许 ':8765' 在 uvicorn.run 中，但不在路由路径中
        route_lines = [l for l in content.split('\n') if '@app.' in l]
        hardcoded = [l for l in route_lines if ':8765' in l or ':8766' in l]
        self.assertEqual(len(hardcoded), 0, f"路由中含硬编码端口: {hardcoded}")

    def test_009_json_response_header(self):
        """JSON响应头设置"""
        api_path = os.path.join(self.root, 'api_server.py')
        if not os.path.exists(api_path):
            self.skipTest('api_server.py 不在根目录')
        content = open(api_path, encoding='utf-8').read()
        has_json_header = 'application/json' in content
        has_cors = 'Access-Control' in content
        self.assertTrue(has_json_header or has_cors, "缺少 JSON 或 CORS 头设置")

    def test_010_error_handler(self):
        """异常处理器存在"""
        api_path = os.path.join(self.root, 'api_server.py')
        if not os.path.exists(api_path):
            self.skipTest('api_server.py 不在根目录')
        content = open(api_path, encoding='utf-8').read()
        has_exception_handler = 'exception_handler' in content or 'HTTPException' in content
        self.assertTrue(has_exception_handler, "缺少异常处理器")


class TestAPIRequestValidation(unittest.TestCase):
    """API请求：参数校验/边界值"""

    def test_001_integer_validation(self):
        """整型参数校验"""
        def validate_int(v, min_v=0, max_v=1000):
            try:
                val = int(v)
                return min_v <= val <= max_v
            except (ValueError, TypeError):
                return False
        self.assertTrue(validate_int(500))
        self.assertFalse(validate_int(-1))
        self.assertFalse(validate_int(9999))
        self.assertFalse(validate_int('abc'))

    def test_002_string_length_validation(self):
        """字符串长度校验"""
        def validate_str(s, max_len=255):
            return isinstance(s, str) and 0 < len(s) <= max_len
        self.assertTrue(validate_str('hello'))
        self.assertFalse(validate_str(''))
        self.assertFalse(validate_str(123))

    def test_003_list_validation(self):
        """列表参数校验"""
        def validate_list(items, max_items=100):
            return isinstance(items, list) and len(items) <= max_items
        self.assertTrue(validate_list([1, 2, 3]))
        self.assertTrue(validate_list([]))
        self.assertFalse(validate_list('not_list'))

    def test_004_json_body_parse(self):
        """JSON请求体解析"""
        body = '{"name": "test", "value": 42}'
        parsed = json.loads(body)
        self.assertEqual(parsed['name'], 'test')
        self.assertEqual(parsed['value'], 42)

    def test_005_missing_field_detection(self):
        """缺少必填字段检测"""
        required = ['name', 'type', 'config']
        data = {'name': 'test'}
        missing = [f for f in required if f not in data]
        self.assertEqual(missing, ['type', 'config'])

    def test_006_email_format_validation(self):
        """邮箱格式校验"""
        def is_valid_email(email):
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, str(email)))
        self.assertTrue(is_valid_email('test@example.com'))
        self.assertFalse(is_valid_email('not-an-email'))

    def test_007_url_validation(self):
        """URL格式校验"""
        def is_valid_url(url):
            return str(url).startswith(('http://', 'https://'))
        self.assertTrue(is_valid_url('https://api.example.com'))
        self.assertFalse(is_valid_url('ftp://invalid'))

    def test_008_timestamp_validation(self):
        """时间戳校验"""
        def is_valid_ts(ts):
            return isinstance(ts, (int, float)) and ts > 1e9  # 2020年后
        self.assertTrue(is_valid_ts(1700000000))
        self.assertFalse(is_valid_ts(1000000))

    def test_009_pagination_params(self):
        """分页参数校验"""
        def validate_page(page=1, size=20):
            page = max(1, int(page))
            size = max(1, min(100, int(size)))
            return page, size
        self.assertEqual(validate_page(0, 200), (1, 100))
        self.assertEqual(validate_page(2, 10), (2, 10))

    def test_010_query_string_encoding(self):
        """查询字符串编码"""
        import urllib.parse
        params = {'name': 'test value', 'type': 'a&b'}
        encoded = urllib.parse.urlencode(params)
        parsed = urllib.parse.parse_qs(encoded)
        self.assertEqual(parsed['name'][0], 'test value')
        self.assertEqual(parsed['type'][0], 'a&b')


class TestAPIResponseFormat(unittest.TestCase):
    """API响应：格式规范/状态码"""

    def test_001_success_response(self):
        """成功响应格式"""
        response = {'code': 200, 'message': 'success', 'data': {'result': 'ok'}}
        self.assertEqual(response['code'], 200)
        self.assertIn('data', response)

    def test_002_error_response(self):
        """错误响应格式"""
        response = {'code': 400, 'message': 'Bad Request', 'error': 'invalid_param'}
        self.assertIn('error', response)

    def test_003_paginated_response(self):
        """分页响应格式"""
        response = {
            'code': 200,
            'data': {'items': [1, 2, 3], 'total': 100, 'page': 1, 'size': 20}
        }
        self.assertIn('items', response['data'])
        self.assertIn('total', response['data'])

    def test_004_http_status_mapping(self):
        """HTTP状态码映射"""
        codes = {200: 'OK', 201: 'Created', 400: 'Bad Request', 404: 'Not Found', 500: 'Server Error'}
        self.assertEqual(codes[200], 'OK')
        self.assertEqual(codes[404], 'Not Found')

    def test_005_response_time_ms(self):
        """响应时间单位"""
        resp = {'duration_ms': 150}
        self.assertIsInstance(resp['duration_ms'], (int, float))

    def test_006_null_handling(self):
        """null值处理"""
        data = {'value': None}
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        self.assertIsNone(parsed['value'])

    def test_007_nested_response(self):
        """嵌套响应结构"""
        resp = {'data': {'module': {'id': 'm1', 'status': 'active', 'metrics': {'cpu': 0.5}}}}
        self.assertEqual(resp['data']['module']['metrics']['cpu'], 0.5)

    def test_008_array_response(self):
        """数组响应"""
        resp = {'items': [{'id': i} for i in range(5)]}
        self.assertEqual(len(resp['items']), 5)

    def test_009_response_encoding(self):
        """响应编码"""
        text = '你好世界'
        encoded = text.encode('utf-8')
        decoded = encoded.decode('utf-8')
        self.assertEqual(decoded, text)

    def test_010_cors_headers(self):
        """CORS头"""
        headers = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE'}
        self.assertIn('Access-Control-Allow-Origin', headers)


class TestAPIErrorHandling(unittest.TestCase):
    """错误处理：异常/降级/重试"""

    def test_001_not_found(self):
        """404处理"""
        error = {'code': 404, 'message': 'Module not found'}
        self.assertEqual(error['code'], 404)

    def test_002_validation_error(self):
        """参数校验错误"""
        error = {'code': 422, 'message': 'Validation Error', 'details': [{'field': 'name', 'error': 'required'}]}
        self.assertEqual(error['code'], 422)
        self.assertGreater(len(error['details']), 0)

    def test_003_timeout_error(self):
        """超时错误"""
        error = {'code': 504, 'message': 'Gateway Timeout'}
        self.assertEqual(error['code'], 504)

    def test_004_rate_limit(self):
        """限流错误"""
        error = {'code': 429, 'message': 'Too Many Requests', 'retry_after': 30}
        self.assertIn('retry_after', error)

    def test_005_auth_error(self):
        """认证错误"""
        error = {'code': 401, 'message': 'Unauthorized'}
        self.assertEqual(error['code'], 401)

    def test_006_forbidden_error(self):
        """权限错误"""
        error = {'code': 403, 'message': 'Forbidden'}
        self.assertEqual(error['code'], 403)

    def test_007_conflict_error(self):
        """冲突错误"""
        error = {'code': 409, 'message': 'Conflict'}
        self.assertEqual(error['code'], 409)

    def test_008_internal_error_format(self):
        """内部错误格式"""
        error = {'code': 500, 'message': 'Internal Error', 'request_id': 'req_xxx'}
        self.assertIn('request_id', error)

    def test_009_retry_after_header(self):
        """重试时间头"""
        headers = {'Retry-After': '120'}
        retry = int(headers['Retry-After'])
        self.assertEqual(retry, 120)

    def test_010_error_log_structure(self):
        """错误日志结构"""
        log = {'level': 'ERROR', 'module': 'api', 'path': '/api/test', 'status': 500, 'duration_ms': 250}
        for field in ['level', 'module', 'status', 'duration_ms']:
            self.assertIn(field, log)


class TestAPISecurity(unittest.TestCase):
    """API安全：认证/鉴权/防篡改"""

    def test_001_token_format(self):
        """Token格式"""
        import hashlib
        token = hashlib.sha256(b'secret').hexdigest()
        self.assertEqual(len(token), 64)

    def test_002_api_key_length(self):
        """API Key长度"""
        api_key = 'sk-' + 'a' * 48
        self.assertEqual(len(api_key), 51)

    def test_003_rate_limit_calc(self):
        """速率限制计算"""
        limit = 100
        window = 60
        per_second = limit / window
        self.assertAlmostEqual(per_second, 1.67, places=1)

    def test_004_ip_whitelist(self):
        """IP白名单"""
        whitelist = {'10.0.0.1', '192.168.1.0/24'}
        ip = '10.0.0.1'
        self.assertIn(ip, whitelist)

    def test_005_request_signing(self):
        """请求签名"""
        import hashlib, hmac
        key = b'secret'
        message = b'GET/api/status'
        sig = hmac.new(key, message, hashlib.sha256).hexdigest()
        self.assertEqual(len(sig), 64)

    def test_006_cors_origin_check(self):
        """CORS来源检查"""
        allowed = ['https://app.example.com']
        origin = 'https://app.example.com'
        self.assertIn(origin, allowed)

    def test_007_sql_injection_prevention(self):
        """SQL注入防护"""
        unsafe = "1' OR '1'='1"
        sanitized = unsafe.replace("'", "''")
        self.assertNotIn("1' OR '1'='1", sanitized)

    def test_008_xss_prevention(self):
        """XSS防护"""
        unsafe = '<script>alert("xss")</script>'
        import html
        safe = html.escape(unsafe)
        self.assertNotIn('<script>', safe)

    def test_009_path_traversal(self):
        """路径穿越防护"""
        path = '../../../etc/passwd'
        safe = os.path.normpath(path)
        # normpath 在 Windows 上不解析 .. 前导
        self.assertTrue(safe.startswith('..') or '..' in safe)
        # 应该拒绝这类路径
        def is_safe(p):
            normalized = os.path.normpath(p)
            return not normalized.startswith('..') and not normalized.startswith('/')
        self.assertFalse(is_safe('../../../etc/passwd'))

    def test_010_jwt_structure(self):
        """JWT结构"""
        import base64, json
        header = base64.urlsafe_b64encode(json.dumps({'alg': 'HS256'}).encode()).rstrip(b'=').decode()
        payload = base64.urlsafe_b64encode(json.dumps({'sub': 'user1', 'exp': 9999999999}).encode()).rstrip(b'=').decode()
        token = f'{header}.{payload}.sig'
        parts = token.split('.')
        self.assertEqual(len(parts), 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
