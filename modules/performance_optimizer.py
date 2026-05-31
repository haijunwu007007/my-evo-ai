from modules._base.circuit_breaker import CircuitBreakerMixin

"""
AUTO-EVO-AI V0.1 — 性能优化引擎
Grade: A (生产级) | Category: 工具链
职责：性能监控、瓶颈分析、优化建议、资源管理、基准测试
"""

__module_meta__ = {
        "id": "performance-optimizer",
        "name": "Performance Optimizer",
        "version": "V0.1",
        "group": "developer",
        "inputs": [
            {
                "name": "metrics",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "window",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "metrics_map",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "optimizations",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "metric_name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "severity",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "performance"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — 性能优化引擎 Grade: A (生产级) | Category: 工具链"
    }

import asyncio
import time
import uuid
import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque

try:
    from modules._base.enterprise_module import EnterpriseModule, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
    from _base.circuit_breaker import CircuitBreakerMixin
    from _base.rate_limiter import RateLimiterMixin

logger = logging.getLogger("performance_optimizer")

class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

class SeverityLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class PerformanceMetric:
    """性能指标"""

    metric_id: str
    name: str
    metric_type: MetricType
    value: float
    unit: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class Bottleneck:
    """性能瓶颈"""

    bottleneck_id: str
    name: str
    severity: SeverityLevel
    description: str
    metric_name: str
    current_value: float
    threshold: float
    impact: str = "medium"
    suggestions: List[str] = field(default_factory=list)
    detected_at: float = field(default_factory=time.time)

@dataclass
class BenchmarkResult:
    """基准测试结果"""

    benchmark_id: str
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    throughput_ops: float
    memory_delta_bytes: int = 0

@dataclass
class OptimizationRule:
    """优化规则"""

    rule_id: str
    name: str
    category: str
    condition_metric: str
    threshold: float
    severity: SeverityLevel
    suggestions: List[str]
    auto_fixable: bool = False

class PerformanceAnalyzer(object):
    """性能分析引擎 — 趋势分析、瓶颈根因定位、优化建议优先级排序、资源饱和度评估"""

    def analyze_trend(self, metrics: List[Dict[str, Any]], window: int = 60) -> Dict[str, Any]:
        """分析性能指标趋势：移动平均、变化率、异常检测"""
        if not metrics:
            return {"error": "no metrics data"}
        values = [m.get("value", 0) for m in metrics[-window:]]
        timestamps = [m.get("timestamp", 0) for m in metrics[-window:]]
        if len(values) < 2:
            return {"trend": "insufficient_data", "values": values}
        avg = sum(values) / len(values)
        first_half = values[: len(values) // 2]
        second_half = values[len(values) // 2 :]
        avg_first = sum(first_half) / max(len(first_half), 1)
        avg_second = sum(second_half) / max(len(second_half), 1)
        change_rate = (avg_second - avg_first) / max(abs(avg_first), 0.001)
        std_dev = (sum((v - avg) ** 2 for v in values) / len(values)) ** 0.5
        anomalies = [v for v in values if abs(v - avg) > 3 * std_dev]
        if change_rate > 0.1:
            direction = "degrading"
        elif change_rate < -0.1:
            direction = "improving"
        else:
            direction = "stable"
        return {
            "direction": direction,
            "change_rate": round(change_rate, 4),
            "current_avg": round(avg, 4),
            "std_dev": round(std_dev, 4),
            "anomaly_count": len(anomalies),
            "data_points": len(values),
        }

    def diagnose_bottleneck(self, metrics_map: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """综合诊断瓶颈根因：跨指标关联分析，定位最可能的瓶颈源"""
        findings = []
        for metric_name, data_points in metrics_map.items():
            if not data_points:
                continue
            recent = data_points[-30:]
            values = [d.get("value", 0) for d in recent]
            if not values:
                continue
            avg = sum(values) / len(values)
            max_val = max(values)
            p95 = sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0]
            severity = "low"
            if p95 > avg * 5:
                severity = "critical"
            elif p95 > avg * 3:
                severity = "high"
            elif p95 > avg * 2:
                severity = "medium"
            if severity in ("high", "critical"):
                findings.append(
                    {
                        "metric": metric_name,
                        "severity": severity,
                        "avg": round(avg, 2),
                        "p95": round(p95, 2),
                        "max": round(max_val, 2),
                        "p95_to_avg_ratio": round(p95 / max(avg, 0.001), 1),
                        "recommendation": self._suggest_fix(metric_name, severity),
                    }
                )
        findings.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4))
        return findings

    def rank_optimizations(self, optimizations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对优化建议按影响/成本比排序"""
        scored = []
        for opt in optimizations:
            impact = opt.get("expected_improvement", 0)
            effort = opt.get("implementation_effort", 1)
            risk = opt.get("risk_level", "low")
            risk_factor = {"low": 1.0, "medium": 0.7, "high": 0.4}.get(risk, 0.5)
            score = (impact * risk_factor) / max(effort, 0.1)
            scored.append({**opt, "priority_score": round(score, 2)})
        scored.sort(key=lambda x: x["priority_score"], reverse=True)
        return scored

    def _suggest_fix(self, metric_name: str, severity: str) -> str:
        suggestions = {
            "cpu_usage": "检查是否存在死循环或计算密集型操作，考虑分片或异步处理",
            "memory_usage": "排查内存泄漏，检查大对象缓存策略，考虑使用LRU或TTL淘汰",
            "response_time": "分析慢查询和N+1问题，检查外部依赖超时配置",
            "error_rate": "检查上游服务健康状态，审查错误处理和重试策略",
            "queue_depth": "增加消费者数量或优化消费速率，检查背压机制",
        }
        for key, suggestion in suggestions.items():
            if key in metric_name.lower():
                return suggestion
        return "建议深入分析该指标的调用链路和历史变化趋势"

class PerformanceOptimizer(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """性能优化引擎"""

    def __init__(self):

        super().__init__()
        self._metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._current_metrics: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._counters: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._bottlenecks: List[Bottleneck] = []
        self._benchmarks: List[BenchmarkResult] = []
        self._rules: List[OptimizationRule] = []
        self._baseline: Dict[str, float] = {}
        self._alerts_sent: List[Dict] = []

    def initialize(self) -> None:
        self._register_rules()
        self.audit("initialized", "性能优化引擎初始化完成")
        # 启动系统资源监控
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"性能优化引擎初始化完成，{len(self._rules)} 条规则")

    def _register_rules(self) -> None:
        """注册优化规则"""
        self._rules = [
            OptimizationRule(
                "cpu_high",
                "CPU使用率过高",
                "resource",
                "cpu_usage",
                80.0,
                SeverityLevel.WARNING,
                ["检查CPU密集型任务", "考虑水平扩展", "启用缓存减少计算"],
                False,
            ),
            OptimizationRule(
                "mem_high",
                "内存使用率过高",
                "resource",
                "memory_usage",
                85.0,
                SeverityLevel.WARNING,
                ["检查内存泄漏", "优化数据结构", "增加分页/流式处理"],
            ),
            OptimizationRule(
                "disk_high",
                "磁盘使用率过高",
                "resource",
                "disk_usage",
                90.0,
                SeverityLevel.CRITICAL,
                ["清理临时文件", "压缩归档旧数据", "扩展存储"],
                False,
            ),
            OptimizationRule(
                "response_slow",
                "响应时间过长",
                "latency",
                "avg_response_time_ms",
                1000.0,
                SeverityLevel.WARNING,
                ["优化数据库查询", "增加缓存层", "异步化IO操作"],
            ),
            OptimizationRule(
                "error_rate_high",
                "错误率过高",
                "reliability",
                "error_rate",
                5.0,
                SeverityLevel.CRITICAL,
                ["检查错误日志", "修复高频错误", "启用熔断器保护"],
            ),
            OptimizationRule(
                "queue_backlog",
                "消息队列积压",
                "throughput",
                "queue_depth",
                10000.0,
                SeverityLevel.WARNING,
                ["增加消费者数量", "优化处理速度", "启用批量处理"],
            ),
            OptimizationRule(
                "conn_pool_exhausted",
                "连接池耗尽",
                "resource",
                "connection_pool_usage",
                0.9,
                SeverityLevel.CRITICAL,
                ["增加连接池大小", "检查连接泄漏", "优化连接复用"],
            ),
            OptimizationRule(
                "gc_pressure",
                "GC压力大",
                "memory",
                "gc_pause_ms",
                100.0,
                SeverityLevel.WARNING,
                ["减少临时对象创建", "优化内存分配", "调整GC参数"],
            ),
            OptimizationRule(
                "thread_contention",
                "线程竞争",
                "concurrency",
                "thread_contention_rate",
                0.3,
                SeverityLevel.WARNING,
                ["减少锁粒度", "使用无锁数据结构", "优化并发策略"],
            ),
            OptimizationRule(
                "cache_miss_rate",
                "缓存命中率低",
                "caching",
                "cache_miss_rate",
                0.5,
                SeverityLevel.WARNING,
                ["调整缓存策略", "增加缓存容量", "预热关键缓存"],
            ),
        ]

    def _monitor_loop(self) -> None:
        """系统资源监控循环"""
        try:
            while True:
                self._collect_system_metrics()
                time.sleep(30)  # 每30秒采集一次
        except asyncio.CancelledError:
            pass

    def _collect_system_metrics(self) -> None:
        """采集系统指标"""
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            self.record_metric("cpu_usage", cpu, MetricType.GAUGE, "%")
            self.record_metric("memory_usage", mem.percent, MetricType.GAUGE, "%")
            self.record_metric("disk_usage", round(disk.used / disk.total * 100, 1), MetricType.GAUGE, "%")
            self.record_metric("memory_available_gb", round(mem.available / 1073741824, 2), MetricType.GAUGE, "GB")
        except ImportError:
            # 模拟数据
            self.record_metric("cpu_usage", 45 + 0.5 * 30, MetricType.GAUGE, "%")
            self.record_metric("memory_usage", 60 + 0.5 * 20, MetricType.GAUGE, "%")
        except Exception as e:
            logger.warning(f"系统指标采集失败: {e}")

    @trace_operation("record_metric")
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        unit: str = "",
        labels: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """记录性能指标"""
        metric_id = f"met_{uuid.uuid4().hex[:8]}"
        metric = PerformanceMetric(
            metric_id=metric_id, name=name, metric_type=metric_type, value=value, unit=unit, labels=labels or {}
        )

        self._current_metrics[name] = value
        self._metrics_history[name].append(
            {"value": value, "timestamp": time.time(), "unit": unit, "labels": labels or {}}
        )

        if metric_type == MetricType.COUNTER:
            self._counters[name] += value
        elif metric_type == MetricType.GAUGE:
            self._gauges[name] = value
        elif metric_type in (MetricType.HISTOGRAM, MetricType.TIMER):
            self._histograms[name].append(value)
            if len(self._histograms[name]) > 10000:
                self._histograms[name] = self._histograms[name][-5000:]

        self.stats["metrics_recorded"] += 1
        return {"metric_id": metric_id, "name": name, "value": value}

    @trace_operation("analyze_bottlenecks")
    def analyze_bottlenecks(self) -> Dict[str, Any]:
        """分析性能瓶颈"""
        self._bottlenecks.clear()

        for rule in self._rules:
            current = self._current_metrics.get(rule.condition_metric)
            if current is None:
                continue

            if current >= rule.threshold:
                bottleneck = Bottleneck(
                    bottleneck_id=f"bn_{uuid.uuid4().hex[:8]}",
                    name=rule.name,
                    severity=rule.severity,
                    description=rule.name,
                    metric_name=rule.condition_metric,
                    current_value=current,
                    threshold=rule.threshold,
                    suggestions=rule.suggestions,
                )
                self._bottlenecks.append(bottleneck)

        self._bottlenecks.sort(key=lambda b: b.severity.value, reverse=True)

        return {
            "total_bottlenecks": len(self._bottlenecks),
            "by_severity": defaultdict(int, {b.severity.value: b.severity.value for b in self._bottlenecks}),
            "details": [
                {
                    "id": b.bottleneck_id,
                    "name": b.name,
                    "severity": b.severity.value,
                    "metric": b.metric_name,
                    "current": round(b.current_value, 2),
                    "threshold": b.threshold,
                    "suggestions": b.suggestions,
                }
                for b in self._bottlenecks
            ],
        }

    @trace_operation("run_benchmark")
    def run_benchmark(self, name: str, target_fn, iterations: int = 1000, warmup: int = 100) -> Dict[str, Any]:
        """执行基准测试"""
        import gc

        gc.collect()

        # 预热
        for _ in range(min(warmup, iterations // 10)):
            try:
                target_fn() if asyncio.iscoroutinefunction(target_fn) else target_fn()
            except Exception:
                pass

        # 正式测试
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                target_fn() if asyncio.iscoroutinefunction(target_fn) else target_fn()
            except Exception:
                pass
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        if not times:
            return {"error": "no valid iterations"}

        times.sort()
        total = sum(times)
        avg = total / len(times)
        throughput = iterations / (total / 1000)

        result = BenchmarkResult(
            benchmark_id=f"bench_{uuid.uuid4().hex[:8]}",
            name=name,
            iterations=iterations,
            total_time_ms=round(total, 2),
            avg_time_ms=round(avg, 4),
            min_time_ms=round(times[0], 4),
            max_time_ms=round(times[-1], 4),
            p50_ms=round(times[len(times) // 2], 4),
            p95_ms=round(times[int(len(times) * 0.95)], 4),
            p99_ms=round(times[int(len(times) * 0.99)], 4),
            throughput_ops=round(throughput, 2),
        )
        self._benchmarks.append(result)

        return {
            "benchmark_id": result.benchmark_id,
            "name": name,
            "iterations": iterations,
            "avg_ms": result.avg_time_ms,
            "p50_ms": result.p50_ms,
            "p95_ms": result.p95_ms,
            "p99_ms": result.p99_ms,
            "min_ms": result.min_time_ms,
            "max_ms": result.max_time_ms,
            "throughput_ops": result.throughput_ops,
        }

    @trace_operation("get_optimization_report")
    def get_optimization_report(self) -> Dict[str, Any]:
        """生成优化报告"""
        bottlenecks = self.analyze_bottlenecks()

        # 指标摘要
        summary = {}
        for name, value in self._current_metrics.items():
            history = list(self._metrics_history.get(name, []))
            if history:
                values = [h["value"] for h in history]
                summary[name] = {
                    "current": round(value, 2),
                    "avg": round(sum(values) / len(values), 2),
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "samples": len(values),
                }

        # 优化建议优先级排序
        suggestions = []
        critical = [b for b in self._bottlenecks if b.severity == SeverityLevel.CRITICAL]
        warnings = [b for b in self._bottlenecks if b.severity == SeverityLevel.WARNING]

        for bn in critical + warnings:
            for sug in bn.suggestions:
                suggestions.append(
                    {
                        "priority": "critical" if bn.severity == SeverityLevel.CRITICAL else "medium",
                        "related_to": bn.metric_name,
                        "suggestion": sug,
                    }
                )

        # 基准测试对比
        bench_summary = []
        for b in self._benchmarks[-5:]:
            bench_summary.append(
                {"name": b.name, "avg_ms": b.avg_time_ms, "p95_ms": b.p95_ms, "throughput": b.throughput_ops}
            )

        overall_score = self._calculate_health_score()

        return {
            "health_score": overall_score,
            "bottlenecks_count": len(self._bottlenecks),
            "critical_issues": len(critical),
            "warnings": len(warnings),
            "metrics_summary": summary,
            "bottleneck_details": bottlenecks.get("details", []),
            "optimization_suggestions": suggestions[:10],
            "recent_benchmarks": bench_summary,
            "monitored_metrics": len(self._current_metrics),
            "data_points": sum(len(h) for h in self._metrics_history.values()),
        }

    def _calculate_health_score(self) -> float:
        """计算系统健康评分"""
        if not self._current_metrics:
            return 100.0

        score = 100.0
        for rule in self._rules:
            current = self._current_metrics.get(rule.condition_metric)
            if current is None:
                continue
            if current >= rule.threshold:
                ratio = current / rule.threshold
                deduction = (ratio - 1) * 20
                if rule.severity == SeverityLevel.CRITICAL:
                    deduction *= 3
                score -= deduction

        return max(0, min(100, round(score, 1)))

    @trace_operation("get_metrics_history")
    def get_metrics_history(self, metric_name: str, limit: int = 100) -> Dict[str, Any]:
        """获取指标历史数据"""
        history = list(self._metrics_history.get(metric_name, []))
        return {
            "metric": metric_name,
            "samples": len(history),
            "data": [
                {"value": h["value"], "timestamp": datetime.fromtimestamp(h["timestamp"]).isoformat()}
                for h in history[-limit:]
            ],
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表盘数据"""
        gauges = {}
        for name, value in self._current_metrics.items():
            unit = ""
            if name.endswith("_usage"):
                unit = "%"
            gauges[name] = {"value": round(value, 1), "unit": unit}

        return {
            "health_score": self._calculate_health_score(),
            "gauges": gauges,
            "active_bottlenecks": len(self._bottlenecks),
            "monitored_metrics": len(self._current_metrics),
            "total_data_points": sum(len(h) for h in self._metrics_history.values()),
            "benchmarks_run": len(self._benchmarks),
        }

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        metrics_collector.counter("perf_optimizer_ops_total", labels={"action": action})
        params = params or {}
        actions = {
            "record_metric": self.record_metric,
            "analyze_bottlenecks": self.analyze_bottlenecks,
            "run_benchmark": self.run_benchmark,
            "get_optimization_report": self.get_optimization_report,
            "get_metrics_history": self.get_metrics_history,
            "get_dashboard_data": self.get_dashboard_data,
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }

        if action not in actions:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}

        handler = actions[action]
        if callable(handler) and not isinstance(handler, list):
            import inspect

            if inspect.iscoroutinefunction(handler):
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            else:
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            if isinstance(result, dict):
                return {"status": "success", **result}
            return {"status": "success", "data": result}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        base.update(
            {
                "monitored_metrics": len(self._current_metrics),
                "data_points": sum(len(h) for h in self._metrics_history.values()),
                "bottlenecks": len(self._bottlenecks),
                "health_score": self._calculate_health_score(),
                "benchmarks": len(self._benchmarks),
                "rules": len(self._rules),
            }
        )
        return base

    def shutdown(self) -> None:
        if hasattr(self, "_monitoring_task"):
            self._monitoring_task.cancel()
        audit_logger.log(
            action="module_shutdown",
            resource="performance_optimizer",
            details=f"关闭，{len(self._current_metrics)} 个监控指标",
        )

module_class = PerformanceOptimizer
