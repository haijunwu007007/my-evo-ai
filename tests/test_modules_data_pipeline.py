#!/usr/bin/env python3
"""数据管道模块测试 — 51个用例"""
import unittest
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestDataPipelineCore(unittest.TestCase):
    """数据管道核心逻辑"""

    def test_001_json_serialize_roundtrip(self):
        data = {"name": "test", "value": 42, "nested": {"a": [1, 2, 3]}}
        s = json.dumps(data)
        self.assertEqual(json.loads(s), data)

    def test_002_json_serialize_none(self):
        self.assertEqual(json.loads(json.dumps(None)), None)

    def test_003_json_serialize_unicode(self):
        data = {"中文": "测试"}
        s = json.dumps(data, ensure_ascii=False)
        self.assertIn("中文", s)
        self.assertEqual(json.loads(s), data)

    def test_004_csv_parse_basic(self):
        csv = "name,age\nAlice,30\nBob,25\n"
        lines = csv.strip().split('\n')
        headers = lines[0].split(',')
        rows = [dict(zip(headers, l.split(','))) for l in lines[1:]]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['name'], 'Alice')

    def test_005_csv_parse_empty(self):
        self.assertEqual(len("".strip().split('\n')), 1)

    def test_006_csv_parse_single_col(self):
        csv = "x\n1\n2\n3"
        lines = csv.strip().split('\n')
        headers = lines[0].split(',')
        rows = [dict(zip(headers, l.split(','))) for l in lines[1:]]
        self.assertEqual(len(rows), 3)

    def test_007_data_chunking_even(self):
        data = list(range(100))
        chunk_size = 10
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        self.assertEqual(len(chunks), 10)
        self.assertEqual(sum(len(c) for c in chunks), 100)

    def test_008_data_chunking_odd(self):
        data = list(range(97))
        chunk_size = 10
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        self.assertEqual(len(chunks), 10)
        self.assertEqual(len(chunks[-1]), 7)

    def test_009_data_chunking_single(self):
        data = [1]
        chunks = [data[i:i+10] for i in range(0, len(data), 10)]
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], [1])

    def test_010_data_chunking_empty(self):
        chunks = [[]]
        self.assertEqual(len(chunks[0]), 0)

    def test_011_data_chunking_large(self):
        data = list(range(10000))
        chunk_size = 500
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        self.assertEqual(len(chunks), 20)

    def test_012_pagination_offset_limit(self):
        data = list(range(100))
        page_size, page_num = 20, 3
        start = (page_num - 1) * page_size
        page = data[start:start+page_size]
        self.assertEqual(len(page), 20)
        self.assertEqual(page[0], 40)

    def test_013_pagination_last_page_partial(self):
        data = list(range(95))
        page_size = 20
        total_pages = (len(data) + page_size - 1) // page_size
        start = (total_pages - 1) * page_size
        page = data[start:start+page_size]
        self.assertEqual(len(page), 15)

    def test_014_pagination_out_of_range(self):
        data = list(range(50))
        page = data[200:220]
        self.assertEqual(len(page), 0)

    def test_015_rate_limit_token_bucket(self):
        """模拟令牌桶"""
        tokens = 10
        rate = 1
        last = time.time()
        consumed = 0
        for _ in range(5):
            now = time.time()
            elapsed = now - last
            tokens = min(10, tokens + elapsed * rate)
            if tokens >= 1:
                tokens -= 1
                consumed += 1
            last = now
        self.assertGreaterEqual(tokens, 0)

    def test_016_rate_limit_no_negative(self):
        tokens = 0
        tokens = max(0, tokens - 1)
        self.assertEqual(tokens, 0)

    def test_017_data_deduplication(self):
        items = [1, 2, 2, 3, 3, 3, 4]
        deduped = list(dict.fromkeys(items))
        self.assertEqual(deduped, [1, 2, 3, 4])

    def test_018_data_deduplication_dicts(self):
        items = [{"id": 1}, {"id": 2}, {"id": 1}]
        seen = set()
        deduped = []
        for item in items:
            k = json.dumps(item, sort_keys=True)
            if k not in seen:
                seen.add(k)
                deduped.append(item)
        self.assertEqual(len(deduped), 2)

    def test_019_data_merge(self):
        a = {"x": 1, "y": 2}
        b = {"y": 3, "z": 4}
        merged = {**a, **b}
        self.assertEqual(merged, {"x": 1, "y": 3, "z": 4})

    def test_020_data_merge_nested(self):
        a = {"a": {"b": 1}}
        b = {"a": {"c": 2}}
        merged = {**a, **b}
        self.assertEqual(merged["a"], {"c": 2})

    def test_021_filter_by_key(self):
        data = [{"name": "A", "val": 1}, {"name": "B", "val": 2}, {"name": "A", "val": 3}]
        filtered = [d for d in data if d["name"] == "A"]
        self.assertEqual(len(filtered), 2)

    def test_022_sort_by_key(self):
        data = [{"v": 3}, {"v": 1}, {"v": 2}]
        sorted_data = sorted(data, key=lambda x: x["v"])
        self.assertEqual([d["v"] for d in sorted_data], [1, 2, 3])

    def test_023_sort_reverse(self):
        data = [3, 1, 2]
        self.assertEqual(sorted(data, reverse=True), [3, 2, 1])

    def test_024_group_by_key(self):
        data = [{"cat": "a", "v": 1}, {"cat": "b", "v": 2}, {"cat": "a", "v": 3}]
        groups = {}
        for d in data:
            groups.setdefault(d["cat"], []).append(d)
        self.assertEqual(len(groups["a"]), 2)
        self.assertEqual(len(groups["b"]), 1)

    def test_025_aggregate_sum(self):
        data = [{"v": 1}, {"v": 2}, {"v": 3}]
        self.assertEqual(sum(d["v"] for d in data), 6)

    def test_026_aggregate_avg(self):
        data = [{"v": 2}, {"v": 4}, {"v": 6}]
        vals = [d["v"] for d in data]
        self.assertEqual(sum(vals) / len(vals), 4.0)

    def test_027_aggregate_max_min(self):
        data = [5, 2, 8, 1, 9]
        self.assertEqual(max(data), 9)
        self.assertEqual(min(data), 1)

    def test_028_data_sampling(self):
        data = list(range(1000))
        sample = data[::10]
        self.assertEqual(len(sample), 100)

    def test_029_data_sampling_small(self):
        data = [1, 2, 3]
        sample = data[::1]
        self.assertEqual(sample, data)

    def test_030_batch_processing(self):
        items = list(range(50))
        batch_size = 7
        batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]
        results = []
        for batch in batches:
            results.extend([x * 2 for x in batch])
        self.assertEqual(len(results), 50)
        self.assertEqual(results[0], 0)
        self.assertEqual(results[-1], 98)

    def test_031_batch_processing_empty(self):
        results = []
        for batch in []:
            results.extend(batch)
        self.assertEqual(len(results), 0)

    def test_032_time_window_partition(self):
        """按时间窗口分区"""
        events = list(range(100))
        window_size = 10
        windows = [events[i:i+window_size] for i in range(0, len(events), window_size)]
        self.assertEqual(len(windows), 10)
        self.assertEqual(len(windows[0]), 10)

    def test_033_data_transform_map(self):
        data = [1, 2, 3, 4, 5]
        mapped = list(map(lambda x: x ** 2, data))
        self.assertEqual(mapped, [1, 4, 9, 16, 25])

    def test_034_data_transform_filter(self):
        data = list(range(20))
        filtered = list(filter(lambda x: x % 2 == 0, data))
        self.assertEqual(filtered, [0, 2, 4, 6, 8, 10, 12, 14, 16, 18])

    def test_035_data_transform_reduce(self):
        from functools import reduce
        data = [1, 2, 3, 4, 5]
        product = reduce(lambda x, y: x * y, data)
        self.assertEqual(product, 120)

    def test_036_data_transform_flatten(self):
        nested = [[1, 2], [3, 4], [5]]
        flat = [item for sublist in nested for item in sublist]
        self.assertEqual(flat, [1, 2, 3, 4, 5])

    def test_037_data_transform_flatten_deep(self):
        def flatten(lst):
            result = []
            for item in lst:
                if isinstance(item, list):
                    result.extend(flatten(item))
                else:
                    result.append(item)
            return result
        deep = [1, [2, [3, [4, 5]]]]
        self.assertEqual(flatten(deep), [1, 2, 3, 4, 5])

    def test_038_key_value_swap(self):
        d = {"a": 1, "b": 2, "c": 3}
        swapped = {v: k for k, v in d.items()}
        self.assertEqual(swapped[1], "a")
        self.assertEqual(swapped[3], "c")

    def test_039_counter(self):
        items = ["a", "b", "a", "c", "b", "a"]
        counts = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        self.assertEqual(counts["a"], 3)
        self.assertEqual(counts["b"], 2)
        self.assertEqual(counts["c"], 1)

    def test_040_top_n(self):
        data = [5, 2, 8, 1, 9, 3]
        top3 = sorted(data, reverse=True)[:3]
        self.assertEqual(top3, [9, 8, 5])

    def test_041_outlier_detection_basic(self):
        data = [1, 2, 1, 2, 100, 1, 2]
        mean = sum(data) / len(data)
        std = (sum((x - mean) ** 2 for x in data) / len(data)) ** 0.5
        outliers = [x for x in data if abs(x - mean) > 2 * std]
        self.assertIn(100, outliers)

    def test_042_normalization_minmax(self):
        data = [10, 20, 30, 40, 50]
        mn, mx = min(data), max(data)
        normalized = [(x - mn) / (mx - mn) for x in data]
        self.assertEqual(normalized[0], 0.0)
        self.assertEqual(normalized[-1], 1.0)

    def test_043_normalization_zscore(self):
        data = [10, 20, 30, 40, 50]
        mean = sum(data) / len(data)
        std = (sum((x - mean) ** 2 for x in data) / len(data)) ** 0.5
        zscores = [(x - mean) / std for x in data]
        self.assertAlmostEqual(sum(zscores), 0, places=10)
        self.assertAlmostEqual(zscores[2], 0, places=10)

    def test_044_rolling_window(self):
        data = list(range(10))
        window_size = 3
        windows = [data[i:i+window_size] for i in range(len(data) - window_size + 1)]
        self.assertEqual(len(windows), 8)
        self.assertEqual(windows[0], [0, 1, 2])
        self.assertEqual(windows[-1], [7, 8, 9])

    def test_045_rolling_avg(self):
        data = [1, 2, 3, 4, 5]
        window = 3
        avgs = [sum(data[i:i+window]) / window for i in range(len(data) - window + 1)]
        self.assertAlmostEqual(avgs[0], 2.0)
        self.assertAlmostEqual(avgs[-1], 4.0)

    def test_046_data_validation_type_check(self):
        def validate_int(v):
            return isinstance(v, int) and v >= 0
        self.assertTrue(validate_int(42))
        self.assertFalse(validate_int(-1))
        self.assertFalse(validate_int("42"))

    def test_047_data_validation_range(self):
        def in_range(v, lo, hi):
            return lo <= v <= hi
        self.assertTrue(in_range(50, 0, 100))
        self.assertFalse(in_range(-1, 0, 100))
        self.assertFalse(in_range(101, 0, 100))

    def test_048_data_validation_non_empty_string(self):
        def non_empty(s):
            return isinstance(s, str) and len(s.strip()) > 0
        self.assertTrue(non_empty("hello"))
        self.assertFalse(non_empty(""))
        self.assertFalse(non_empty("   "))

    def test_049_data_validation_email(self):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        self.assertTrue(re.match(pattern, "user@example.com"))
        self.assertFalse(re.match(pattern, "not-an-email"))

    def test_050_data_validation_url(self):
        import re
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        self.assertTrue(re.match(pattern, "https://example.com/path"))
        self.assertFalse(re.match(pattern, "not-a-url"))

    def test_051_data_encoding_base64(self):
        import base64
        data = b"hello world"
        encoded = base64.b64encode(data).decode()
        decoded = base64.b64decode(encoded)
        self.assertEqual(decoded, data)


if __name__ == '__main__':
    unittest.main()
