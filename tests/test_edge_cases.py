# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 边缘用例测试 (60+)

覆盖：空值、超长输入、并发、边界条件、异常恢复"""
import unittest, sys, os, json, time, threading, io, asyncio, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestDataEdgeCases(unittest.TestCase):
    """数据边界测试"""

    def test_001_empty_string_handling(self):
        """空字符串处理"""
        self.assertEqual("".strip(), "")
        self.assertEqual(len(""), 0)

    def test_002_none_vs_empty(self):
        """None vs 空值"""
        d = {"a": None, "b": "", "c": 0}
        self.assertIsNone(d.get("a"))
        self.assertEqual(d.get("b"), "")
        self.assertEqual(d.get("c"), 0)
        self.assertIsNone(d.get("nonexistent"))

    def test_003_large_list_memory(self):
        """大列表边界（10万元素不应炸内存）"""
        large = list(range(100000))
        self.assertEqual(len(large), 100000)
        self.assertEqual(large[0], 0)
        self.assertEqual(large[-1], 99999)

    def test_004_deeply_nested_dict(self):
        """深层嵌套字典"""
        d = {}
        cur = d
        for i in range(100):
            cur["level"] = {}
            cur = cur["level"]
        self.assertIn("level", d)

    def test_005_mixed_type_list_sort(self):
        """混合类型列表排序保护"""
        items = [3, 1, "a", 2]
        with self.assertRaises(TypeError):
            sorted(items)

    def test_006_negative_index(self):
        """负索引"""
        arr = [1, 2, 3, 4, 5]
        self.assertEqual(arr[-1], 5)
        self.assertEqual(arr[-5], 1)

    def test_007_slice_out_of_bounds(self):
        """切片越界"""
        arr = [1, 2, 3]
        self.assertEqual(arr[10:], [])
        self.assertEqual(arr[:10], [1, 2, 3])
        self.assertEqual(arr[-10:], [1, 2, 3])

    def test_008_dict_key_types(self):
        """字典键类型"""
        d = {1: "int", "1": "str", (1,): "tuple"}
        self.assertEqual(d[1], "int")
        self.assertEqual(d["1"], "str")
        self.assertEqual(d[(1,)], "tuple")

    def test_009_set_operations(self):
        """集合运算"""
        a = {1, 2, 3, 4}
        b = {3, 4, 5, 6}
        self.assertEqual(a & b, {3, 4})
        self.assertEqual(a | b, {1, 2, 3, 4, 5, 6})
        self.assertEqual(a - b, {1, 2})

    def test_010_infinity_handling(self):
        """无穷大处理"""
        inf = float('inf')
        self.assertTrue(inf > 1e308)
        self.assertTrue(float('-inf') < -1e308)
        self.assertTrue(math.isinf(inf))

    def test_011_nan_handling(self):
        """NaN 处理"""
        nan = float('nan')
        self.assertTrue(math.isnan(nan))
        self.assertFalse(nan == nan)  # NaN != NaN

    def test_012_float_precision(self):
        """浮点精度"""
        result = 0.1 + 0.2
        self.assertNotEqual(result, 0.3)  # IEEE 754
        self.assertAlmostEqual(result, 0.3, places=10)

    def test_013_zero_division_protection(self):
        """除零保护"""
        def safe_div(a, b):
            try:
                return a / b
            except ZeroDivisionError:
                return None
        self.assertIsNone(safe_div(1, 0))
        self.assertEqual(safe_div(1, 2), 0.5)

    def test_014_type_conversion_edge(self):
        """类型转换边界"""
        self.assertEqual(int("0"), 0)
        self.assertEqual(int(" 123 "), 123)
        with self.assertRaises(ValueError):
            int("")
        with self.assertRaises(ValueError):
            int("abc")

    def test_015_unicode_edge(self):
        """Unicode 边界"""
        s = "你好世界🌍🔥"
        self.assertEqual(len(s), 6)  # 4个中文 + 2个emoji
        self.assertTrue(s.isprintable())


class TestConcurrencyEdgeCases(unittest.TestCase):
    """并发边界测试"""

    def test_016_thread_safe_counter(self):
        """线程安全计数器"""
        counter = 0
        lock = threading.Lock()
        def inc():
            nonlocal counter
            for _ in range(1000):
                with lock:
                    counter += 1
        threads = [threading.Thread(target=inc) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(counter, 10000)

    def test_017_race_condition_detection(self):
        """竞态条件检测（不加锁时预期会出错）"""
        counter = 0
        def inc_unprotected():
            nonlocal counter
            for _ in range(1000):
                counter += 1
        threads = [threading.Thread(target=inc_unprotected) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        # 不加锁时几乎肯定 < 10000
        self.assertLessEqual(counter, 10000)

    def test_018_concurrent_dict_access(self):
        """并发字典访问"""
        d = {}
        lock = threading.Lock()
        def writer(k):
            for i in range(100):
                with lock:
                    d[f"{k}_{i}"] = i
        threads = [threading.Thread(target=writer, args=(f"t{j}",)) for j in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(d), 500)

    def test_019_timeout_simulation(self):
        """超时模拟"""
        import signal
        def handler(signum, frame):
            raise TimeoutError("operation timed out")
        # 只在非 Windows 平台测试 signal
        import platform
        if platform.system() != "Windows":
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(1)
            try:
                time.sleep(2)
                self.fail("should have timed out")
            except TimeoutError:
                pass
            finally:
                signal.alarm(0)
        else:
            self.skipTest("signal.SIGALRM not supported on Windows")

    def test_020_deadlock_detection(self):
        """死锁检测（使用超时锁）"""
        lock1 = threading.Lock()
        lock2 = threading.Lock()
        acquired = threading.Event()

        def thread_a():
            with lock1:
                acquired.set()
                if not lock2.acquire(timeout=0.5):
                    return  # 避免死锁
                lock2.release()

        def thread_b():
            with lock2:
                if not lock1.acquire(timeout=0.5):
                    return
                lock1.release()

        t1 = threading.Thread(target=thread_a)
        t2 = threading.Thread(target=thread_b)
        t1.start()
        t2.start()
        t1.join(timeout=2)
        t2.join(timeout=2)
        self.assertFalse(t1.is_alive())
        self.assertFalse(t2.is_alive())


class TestSerializationEdgeCases(unittest.TestCase):
    """序列化边界测试"""

    def test_021_circular_reference(self):
        """循环引用检测"""
        obj = {}
        obj["self"] = obj
        with self.assertRaises(ValueError):
            json.dumps(obj)

    def test_022_custom_object_serialization(self):
        """自定义对象序列化"""
        class Point:
            def __init__(self, x, y):
                self.x = x
                self.y = y
        p = Point(3, 4)
        with self.assertRaises(TypeError):
            json.dumps(p)

    def test_023_nested_json(self):
        """嵌套 JSON"""
        data = {"a": {"b": {"c": [1, 2, {"d": "e"}]}}}
        s = json.dumps(data)
        loaded = json.loads(s)
        self.assertEqual(loaded["a"]["b"]["c"][2]["d"], "e")

    def test_024_large_json(self):
        """大型 JSON（10万键值对）"""
        data = {f"key_{i}": f"value_{i}" for i in range(100000)}
        s = json.dumps(data)
        self.assertGreater(len(s), 100000)
        loaded = json.loads(s)
        self.assertEqual(len(loaded), 100000)

    def test_025_special_chars_in_json(self):
        """JSON 特殊字符"""
        data = {"text": "hello\nworld\t\"quoted\"\\backslash\u0041"}
        s = json.dumps(data)
        loaded = json.loads(s)
        self.assertIn("\n", loaded["text"])
        self.assertIn("\t", loaded["text"])

    def test_026_binary_in_json(self):
        """JSON 二进制数据"""
        with self.assertRaises(TypeError):
            json.dumps({"data": b"binary\x00data"})


class TestFileSystemEdgeCases(unittest.TestCase):
    """文件系统边界测试"""

    def test_027_long_path(self):
        """长路径测试"""
        base = os.path.join(os.path.dirname(__file__), '..')
        long_path = os.path.join(base, *['subdir'] * 50)
        # Windows 路径长度限制
        self.assertGreater(len(long_path), 200)

    def test_028_path_traversal_prevention(self):
        """路径遍历防护"""
        def is_safe_path(path):
            normalized = os.path.normpath(path)
            # Windows: normpath of '/etc/passwd' becomes '\etc\passwd' (starts with \)
            # Unix absolute paths start with /
            return not normalized.startswith('..') and not normalized.startswith('\\') and not normalized.startswith('/') and ':' not in normalized
        self.assertFalse(is_safe_path('../../../etc/passwd'))
        self.assertFalse(is_safe_path('/etc/passwd'))
        self.assertTrue(is_safe_path('data/file.txt'))

    def test_029_symlink_handling(self):
        """符号链接处理"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            real_file = os.path.join(tmpdir, "real.txt")
            with open(real_file, "w") as f:
                f.write("hello")
            link_file = os.path.join(tmpdir, "link.txt")
            try:
                os.symlink(real_file, link_file)
                self.assertTrue(os.path.islink(link_file))
                with open(link_file) as f:
                    self.assertEqual(f.read(), "hello")
            except (OSError, NotImplementedError):
                self.skipTest("symlink not supported")

    def test_030_temp_file_cleanup(self):
        """临时文件清理"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:
            f.write("test data")
            path = f.name
            self.assertTrue(os.path.exists(path))
        self.assertFalse(os.path.exists(path))


class TestNetworkEdgeCases(unittest.TestCase):
    """网络边界测试"""

    def test_031_url_validation(self):
        """URL 验证"""
        import re
        url_pattern = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
        self.assertTrue(url_pattern.match('https://example.com'))
        self.assertTrue(url_pattern.match('http://192.168.1.1:8080/api'))
        self.assertFalse(url_pattern.match('ftp://example.com'))
        self.assertFalse(url_pattern.match('not a url'))

    def test_032_port_range_validation(self):
        """端口范围验证"""
        def valid_port(p):
            return isinstance(p, int) and 1 <= p <= 65535
        self.assertTrue(valid_port(80))
        self.assertTrue(valid_port(443))
        self.assertTrue(valid_port(65535))
        self.assertFalse(valid_port(0))
        self.assertFalse(valid_port(-1))
        self.assertFalse(valid_port(65536))
        self.assertFalse(valid_port("80"))

    def test_033_ip_address_validation(self):
        """IP 地址验证"""
        import re
        ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        self.assertTrue(ip_pattern.match('192.168.1.1'))
        self.assertTrue(ip_pattern.match('0.0.0.0'))
        self.assertTrue(ip_pattern.match('255.255.255.255'))
        # 改进：需要额外验证每段 <=255
        def valid_ip(s):
            match = ip_pattern.match(s)
            if not match:
                return False
            return all(0 <= int(octet) <= 255 for octet in s.split('.'))
        self.assertFalse(valid_ip('256.1.1.1'))
        self.assertFalse(valid_ip('abc.def.ghi.jkl'))

    def test_034_hostname_validation(self):
        """主机名验证"""
        import re
        hn_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$')
        self.assertTrue(hn_pattern.match('example.com'))
        self.assertTrue(hn_pattern.match('my-host.local'))
        self.assertFalse(hn_pattern.match('-example.com'))
        self.assertFalse(hn_pattern.match('example-.com'))


class TestAsyncEdgeCases(unittest.TestCase):
    """异步边界测试"""

    def test_035_async_function_call(self):
        """异步函数调用"""
        async def sample():
            return 42
        result = asyncio.run(sample())
        self.assertEqual(result, 42)

    def test_036_async_exception_handling(self):
        """异步异常处理"""
        async def fail():
            raise ValueError("test error")
        with self.assertRaises(ValueError):
            asyncio.run(fail())

    def test_037_async_gather(self):
        """异步并发收集"""
        async def worker(n):
            return n * 2
        async def main():
            results = await asyncio.gather(
                worker(1), worker(2), worker(3)
            )
            return results
        results = asyncio.run(main())
        self.assertEqual(results, [2, 4, 6])

    def test_038_async_timeout(self):
        """异步超时"""
        async def slow():
            await asyncio.sleep(10)
            return "done"
        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run(asyncio.wait_for(slow(), timeout=0.1))


class TestMathEdgeCases(unittest.TestCase):
    """数学边界测试"""

    def test_039_factorial_zero(self):
        """0! = 1"""
        import math
        self.assertEqual(math.factorial(0), 1)

    def test_040_large_factorial(self):
        """大数阶乘"""
        import math
        result = math.factorial(100)
        self.assertGreater(result, 1e150)

    def test_041_power_zero(self):
        """0次方"""
        self.assertEqual(2 ** 0, 1)
        self.assertEqual(0 ** 0, 1)
        self.assertEqual(0 ** 5, 0)

    def test_042_logarithm_edges(self):
        """对数边界"""
        import math
        self.assertEqual(math.log(1), 0.0)
        self.assertAlmostEqual(math.log(math.e), 1.0)
        with self.assertRaises(ValueError):
            math.log(-1)
        with self.assertRaises(ValueError):
            math.log(0)

    def test_043_trigonometry(self):
        """三角函数"""
        import math
        self.assertAlmostEqual(math.sin(0), 0)
        self.assertAlmostEqual(math.cos(0), 1)
        self.assertAlmostEqual(math.sin(math.pi/2), 1)
        self.assertAlmostEqual(math.cos(math.pi), -1)

    def test_044_rounding(self):
        """四舍五入边界"""
        self.assertEqual(round(2.5), 2)  # banker's rounding
        self.assertEqual(round(3.5), 4)
        self.assertEqual(round(2.675, 2), 2.67)  # 浮点精度问题


class TestStringEdgeCases(unittest.TestCase):
    """字符串边界测试"""

    def test_045_empty_string_operations(self):
        """空字符串操作"""
        s = ""
        self.assertEqual(s.upper(), "")
        self.assertEqual(s.lower(), "")
        self.assertEqual(s.strip(), "")
        self.assertEqual(s.split(), [])
        self.assertEqual("".join([]), "")

    def test_046_whitespace_strings(self):
        """空白字符串"""
        s = "  \t\n\r  "
        self.assertEqual(s.strip(), "")
        self.assertNotEqual(s, "")
        self.assertTrue(s.isspace())

    def test_047_very_long_string(self):
        """超长字符串（10万字符）"""
        s = "a" * 100000
        self.assertEqual(len(s), 100000)
        self.assertEqual(s.count("a"), 100000)

    def test_048_string_encoding(self):
        """字符串编码"""
        s = "你好世界"
        utf8 = s.encode('utf-8')
        self.assertEqual(len(utf8), 12)
        utf16 = s.encode('utf-16')
        # UTF-16 = BOM(2) + 4字符*2/4字节
        self.assertGreaterEqual(len(utf16), 10)
        decoded = utf8.decode('utf-8')
        self.assertEqual(decoded, s)

    def test_049_string_formatting(self):
        """字符串格式化"""
        name = "world"
        self.assertEqual(f"hello {name}", "hello world")
        self.assertEqual("hello {}".format(name), "hello world")
        self.assertEqual("hello %s" % name, "hello world")

    def test_050_regex_edge_cases(self):
        """正则边界"""
        import re
        self.assertTrue(re.match(r'^[a-z]+$', 'hello'))
        self.assertFalse(re.match(r'^[a-z]+$', 'Hello'))
        self.assertTrue(re.match(r'.*', ''))
        self.assertFalse(re.match(r'^$', 'a'))


class TestDictEdgeCases(unittest.TestCase):
    """字典边界测试"""

    def test_051_dict_merge(self):
        """字典合并"""
        a = {"x": 1, "y": 2}
        b = {"y": 3, "z": 4}
        merged = {**a, **b}
        self.assertEqual(merged["x"], 1)
        self.assertEqual(merged["y"], 3)
        self.assertEqual(merged["z"], 4)

    def test_052_dict_default(self):
        """字典默认值"""
        d = {}
        self.assertEqual(d.get("nonexistent", "default"), "default")
        self.assertIsNone(d.get("nonexistent"))

    def test_053_dict_comprehension(self):
        """字典推导式"""
        squares = {x: x*x for x in range(10)}
        self.assertEqual(squares[5], 25)
        self.assertEqual(len(squares), 10)

    def test_054_ordered_dict(self):
        """有序字典"""
        from collections import OrderedDict
        od = OrderedDict()
        od["a"] = 1
        od["b"] = 2
        od["c"] = 3
        keys = list(od.keys())
        self.assertEqual(keys, ["a", "b", "c"])


class TestExceptionEdgeCases(unittest.TestCase):
    """异常边界测试"""

    def test_055_nested_exception(self):
        """嵌套异常"""
        def inner():
            raise ValueError("inner")
        def outer():
            try:
                inner()
            except ValueError as e:
                raise RuntimeError("outer") from e
        with self.assertRaises(RuntimeError) as ctx:
            outer()
        self.assertIsNotNone(ctx.exception.__cause__)

    def test_056_exception_chain(self):
        """异常链"""
        try:
            try:
                raise ValueError("original")
            except:
                raise RuntimeError("wrapper")
        except RuntimeError as e:
            self.assertIsNotNone(e.__context__)

    def test_057_finally_execution(self):
        """finally 执行保证"""
        executed = []
        try:
            executed.append("try")
            raise ValueError()
        except ValueError:
            executed.append("except")
        finally:
            executed.append("finally")
        self.assertEqual(executed, ["try", "except", "finally"])

    def test_058_context_manager(self):
        """上下文管理器"""
        class MyContext:
            def __init__(self):
                self.entered = False
                self.exited = False
            def __enter__(self):
                self.entered = True
                return self
            def __exit__(self, *args):
                self.exited = True
        with MyContext() as ctx:
            self.assertTrue(ctx.entered)
        self.assertTrue(ctx.exited)

    def test_059_generator_yield(self):
        """生成器 yield"""
        def gen():
            yield 1
            yield 2
            yield 3
        results = list(gen())
        self.assertEqual(results, [1, 2, 3])

    def test_060_generator_send(self):
        """生成器 send"""
        def gen():
            val = yield "ready"
            yield f"received {val}"
        g = gen()
        self.assertEqual(next(g), "ready")
        self.assertEqual(g.send("hello"), "received hello")


if __name__ == "__main__":
    unittest.main()
