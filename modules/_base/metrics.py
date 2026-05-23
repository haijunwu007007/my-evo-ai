# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 - Prometheus 指标采集
=======================================
轻量级 Prometheus 兼容指标系统。
自动采集每个模块的：请求量、延迟、错误率、活跃连接数。

生产级特性：
  - Counter（计数器）: request_count, error_count
  - Histogram（直方图）: latency_ms 分布
  - Gauge（仪表盘）: active_connections, queue_size
  - 按module_id / action / status 自动打标签
  - 支持 /metrics 端点输出 Prometheus 文本格式
  - 内存安全，自动清理过期指标

使用方式:
  metrics = get_metrics()
  metrics.record("request_count", 1, {"module": "xxx", "action": "execute"})
  metrics.observe("latency_ms", 42.5, {"module": "xxx"})
"""

import time
import logging
import threading
import functools
import asyncio
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("evo.metrics")


class MetricPoint:
    """单个指标数据点"""

    def __init__(
        self, name: str, value: float = 0.0, labels: Optional[Dict[str, str]] = None, metric_type: str = "counter"
    ):
        self.name = name
        self.value = value
        self.labels = labels or {}
        self.metric_type = metric_type
        self.timestamp = time.time()
        # Histogram专用
        self.buckets: List[float] = [5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
        self.observations: List[float] = []

    def inc(self, value: float = 1.0):
        self.value += value
        self.timestamp = time.time()

    def set(self, value: float):
        self.value = value
        self.timestamp = time.time()

    def observe(self, value: float):
        self.observations.append(value)
        self.value += value
        self.timestamp = time.time()
        # 保留最近10000条
        if len(self.observations) > 10000:
            self.observations = self.observations[-5000:]

    def get_percentile(self, p: float) -> float:
        if not self.observations:
            return 0.0
        sorted_obs = sorted(self.observations)
        idx = max(0, int(len(sorted_obs) * p) - 1)
        return round(sorted_obs[idx], 3)


class MetricsCollector:
    """
    Prometheus兼容指标采集器

    指标类型:
      - counter: 递增计数（请求量、错误量）
      - gauge: 可增可减（活跃连接、队列大小）
      - histogram: 分布统计（延迟、大小）
    """

    def __init__(self, max_series: int = 50000):
        self._series: Dict[str, MetricPoint] = {}
        self._lock = threading.Lock()
        self._max_series = max_series

    def _label_key(self, name: str, labels: Dict[str, str]) -> str:
        """生成指标唯一键"""
        sorted_labels = sorted(labels.items())
        label_str = ",".join(f"{k}={v}" for k, v in sorted_labels)
        return f"{name}{{{label_str}}}" if label_str else name

    def record(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None, module_id: str = ""):
        """
        记录计数器指标
        Example: metrics.record("request_count", 1, {"action": "execute"}, "health-check")
        """
        labels = dict(tags or {})
        if module_id:
            labels.setdefault("module", module_id)
        key = self._label_key(name, labels)
        with self._lock:
            if key not in self._series:
                if len(self._series) >= self._max_series:
                    # 淘汰最老的
                    oldest_key = min(self._series, key=lambda k: self._series[k].timestamp)
                    del self._series[oldest_key]
                self._series[key] = MetricPoint(name, 0.0, labels, "counter")
            self._series[key].inc(value)

    def observe(self, name: str, value: float, tags: Optional[Dict[str, str]] = None, module_id: str = ""):
        """
        记录直方图指标（延迟分布）
        Example: metrics.observe("latency_ms", 42.5, {"action": "execute"}, "health-check")
        """
        labels = dict(tags or {})
        if module_id:
            labels.setdefault("module", module_id)
        key = self._label_key(name, labels)
        with self._lock:
            if key not in self._series:
                self._series[key] = MetricPoint(name, 0.0, labels, "histogram")
            self._series[key].observe(value)

    def counter(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        module_id: str = "",
    ):
        """记录计数器指标（record的别名，兼容旧调用方式）"""
        self.record(name, value, tags or labels, module_id)

    def histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        module_id: str = "",
    ):
        """记录直方图指标（observe的别名，兼容旧调用方式）"""
        self.observe(name, value, tags or labels, module_id)

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None, module_id: str = ""):
        """
        设置仪表盘指标
        Example: metrics.gauge("active_connections", 5, {}, "database-client")
        """
        labels = dict(tags or {})
        if module_id:
            labels.setdefault("module", module_id)
        key = self._label_key(name, labels)
        with self._lock:
            if key not in self._series:
                self._series[key] = MetricPoint(name, value, labels, "gauge")
            else:
                self._series[key].set(value)

    def get_metric(self, name: str, tags: Optional[Dict[str, str]] = None) -> Optional[float]:
        """获取单个指标值"""
        labels = tags or {}
        key = self._label_key(name, labels)
        with self._lock:
            point = self._series.get(key)
            return point.value if point else None

    def get_module_metrics(self, module_id: str) -> Dict[str, Any]:
        """获取指定模块的所有指标"""
        result = {
            "module_id": module_id,
            "counters": {},
            "gauges": {},
            "histograms": {},
        }
        with self._lock:
            for key, point in self._series.items():
                if point.labels.get("module") == module_id:
                    if point.metric_type == "counter":
                        result["counters"][point.name] = {
                            "value": point.value,
                            "labels": point.labels,
                        }
                    elif point.metric_type == "gauge":
                        result["gauges"][point.name] = {
                            "value": point.value,
                            "labels": point.labels,
                        }
                    elif point.metric_type == "histogram":
                        result["histograms"][point.name] = {
                            "count": len(point.observations),
                            "avg": point.get_percentile(0.5),
                            "p95": point.get_percentile(0.95),
                            "p99": point.get_percentile(0.99),
                            "labels": point.labels,
                        }
        return result

    def to_prometheus(self) -> str:
        """导出 Prometheus 文本格式"""
        lines = []
        with self._lock:
            for key, point in self._series.items():
                labels_str = ""
                if point.labels:
                    labels_str = "{" + ",".join(f'{k}="{v}"' for k, v in sorted(point.labels.items())) + "}"

                if point.metric_type == "counter":
                    lines.append(f"# TYPE {point.name} counter")
                    lines.append(f"{point.name}_total{labels_str} {point.value}")
                elif point.metric_type == "gauge":
                    lines.append(f"# TYPE {point.name} gauge")
                    lines.append(f"{point.name}{labels_str} {point.value}")
                elif point.metric_type == "histogram":
                    lines.append(f"# TYPE {point.name} histogram")
                    lines.append(f"{point.name}_count{labels_str} {len(point.observations)}")
                    lines.append(f"{point.name}_sum{labels_str} {point.value}")
                    for bucket in point.buckets:
                        count = sum(1 for o in point.observations if o <= bucket)
                        bucket_labels = (
                            labels_str.replace("{", f'{{le="{bucket}",').replace("}", "}")
                            if labels_str
                            else f'{{le="{bucket}"}}'
                        )
                        lines.append(f"{point.name}_bucket{bucket_labels} {count}")
                lines.append("")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """获取指标采集器统计"""
        with self._lock:
            counters = sum(1 for p in self._series.values() if p.metric_type == "counter")
            gauges = sum(1 for p in self._series.values() if p.metric_type == "gauge")
            histograms = sum(1 for p in self._series.values() if p.metric_type == "histogram")
            return {
                "total_series": len(self._series),
                "counters": counters,
                "gauges": gauges,
                "histograms": histograms,
            }

    def clear(self):
        with self._lock:
            self._series.clear()


# 全局单例
_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """获取全局指标采集器"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
        logger.info("Prometheus指标采集器初始化完成")
    return _metrics


# 兼容导出：供模块使用 from modules._base.metrics import prometheus_timer, metrics_collector
metrics_collector = get_metrics()


def prometheus_timer(metric_name: str):
    """装饰器：记录函数执行时间（兼容接口）"""

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            import time as _t

            start = _t.time()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = _t.time() - start
                metrics_collector.observe(metric_name, elapsed)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time as _t

            start = _t.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = _t.time() - start
                metrics_collector.observe(metric_name, elapsed)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
