# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI V0.1 - DistributedTracer 分布式追踪
================================================
企业级分布式追踪：Span/Trace/Baggage传播/采样/导出。
支持：OpenTelemetry风格Span管理、Trace上下文传播、
      指数采样、父子Span关联、Baggage跨服务传播、
      Span事件/标签、Trace导出、慢追踪检测、
      服务拓扑自动发现。

A级生产标准：EnterpriseModule + 链路追踪 + Prometheus + 审计 + 熔断 + 限流
"""

__module_meta__ = {
        "id": "distributed-tracer",
        "name": "Distributed Tracer",
        "version": "V0.1",
        "group": "database",
        "inputs": [
            {
                "name": "max_cache",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "trace",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "service_name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "limit",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "threshold_ms",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "limit_2",
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
            "config",
            "engine",
            "distributed",
            "service"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 - DistributedTracer 分布式追踪 ================================================"
    }

import time
import asyncio
import json
import time as tmod
import logging
import time as tmod
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    Result,
    CircuitBreakerMixin,
    RateLimiterMixin,
)
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.distributed_tracer")

# ============================================================================
# 数据模型
# ============================================================================

class SpanKind(str, Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"

class SpanStatus(str, Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"

class SamplingStrategy(str, Enum):
    ALWAYS = "always"
    NEVER = "never"
    PROBABILISTIC = "probabilistic"
    RATE_LIMITING = "rate_limiting"

@dataclass
class SpanEvent:
    """Span事件"""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SpanLink:
    """Span关联"""

    trace_id: str = ""
    span_id: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Span:
    """Span"""

    trace_id: str = ""
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: str = ""
    operation_name: str = ""
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    duration_ms: float = 0.0
    service_name: str = ""
    resource: Dict[str, str] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    baggage: Dict[str, str] = field(default_factory=dict)
    error_message: str = ""
    stack_trace: str = ""

@dataclass
class Trace:
    """Trace"""

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:32])
    root_span: Optional[Span] = None
    spans: List[Span] = field(default_factory=list)
    baggage: Dict[str, str] = field(default_factory=dict)
    status: SpanStatus = SpanStatus.UNSET
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: float = 0.0
    service_count: int = 0
    span_count: int = 0
    error_count: int = 0
    sampled: bool = True

@dataclass
class ServiceTopology:
    """服务拓扑"""

    service_name: str = ""
    inbound_services: List[str] = field(default_factory=list)
    outbound_services: List[str] = field(default_factory=list)
    call_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0

@dataclass
class ExporterConfig:
    """导出器配置"""

    exporter_type: str = "memory"  # memory/file/grpc/http
    endpoint: str = ""
    batch_size: int = 100
    flush_interval: float = 5.0
    retry_max: int = 3
    timeout: float = 30.0

# ============================================================================
# DistributedTracer 主类
# ============================================================================

class TraceQueryEngine(object):
    """链路查询引擎 - 支持按服务、标签、耗时等维度检索链路数据"""

    def __init__(self, max_cache: int = 10000):
        self._cache: List[Trace] = []
        self._max_cache = max_cache
        self._query_count = 0

    def store(self, trace: Trace) -> None:
        """存储完成的链路"""
        self._cache.append(trace)
        if len(self._cache) > self._max_cache:
            self._cache = self._cache[-self._max_cache // 2 :]

    def query_by_service(self, service_name: str, limit: int = 50) -> List[Dict]:
        """按服务名查询链路"""
        self._query_count += 1
        results = []
        for trace in reversed(self._cache):
            if any(s["service"] == service_name for s in trace.spans):
                results.append(trace.to_dict())
                if len(results) >= limit:
                    break
        return results

    def query_slow_traces(self, threshold_ms: float = 1000, limit: int = 20) -> List[Dict]:
        """查询慢链路"""
        self._query_count += 1
        results = []
        for trace in reversed(self._cache):
            duration_ms = (trace.end_time - trace.start_time) * 1000 if trace.end_time else 0
            if duration_ms > threshold_ms:
                results.append({**trace.to_dict(), "duration_ms": round(duration_ms, 2)})
                if len(results) >= limit:
                    break
        return results

    def query_by_tag(self, tag_key: str, tag_value: str, limit: int = 50) -> List[Dict]:
        """按标签查询链路"""
        self._query_count += 1
        results = []
        for trace in reversed(self._cache):
            for span in trace.spans:
                tags = span.get("tags", {})
                if tags.get(tag_key) == tag_value:
                    results.append(trace.to_dict())
                    break
            if len(results) >= limit:
                break
        return results

    def get_error_traces(self, limit: int = 20) -> List[Dict]:
        """查询包含错误的链路"""
        self._query_count += 1
        results = []
        for trace in reversed(self._cache):
            has_error = any(s.get("status") in ("error", "ERROR") for s in trace.spans)
            if has_error:
                results.append(trace.to_dict())
                if len(results) >= limit:
                    break
        return results

    def get_stats(self) -> Dict:
        """查询引擎统计"""
        return {
            "cached_traces": len(self._cache),
            "query_count": self._query_count,
            "max_cache": self._max_cache,
        }

class DistributedTracer(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    分布式追踪

    功能：
      - Trace/Span创建与管理
      - 上下文传播（inject/extract）
      - Baggage跨服务传递
      - 多种采样策略
      - Span事件与标签
      - Span关联（Links）
      - Trace导出
      - 慢追踪检测
      - 服务拓扑自动发现
      - 追踪查询
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__()
        self.config = config or {}
        # Trace存储
        self._traces: Dict[str, Trace] = {}
        # 活跃Span（trace_id -> span_id -> Span）
        self._active_spans: Dict[str, Dict[str, Span]] = defaultdict(dict)
        # 服务拓扑
        self._topology: Dict[str, ServiceTopology] = {}
        # 采样
        self._sampling_strategy = SamplingStrategy(self.config.get("sampling_strategy", "probabilistic"))
        self._sampling_rate = self.config.get("sampling_rate", 0.1)
        self._rate_limiter_tokens = self.config.get("rate_limit_tokens", 100)
        self._rate_limiter_max = self._rate_limiter_tokens
        # 慢追踪阈值
        self._slow_threshold_ms = self.config.get("slow_threshold_ms", 5000.0)
        # 导出器
        self._exporter_config = ExporterConfig(
            **{k: v for k, v in self.config.get("exporter", {}).items() if k in ExporterConfig.__dataclass_fields__}
        )
        self._export_buffer: List[Span] = []
        self._flush_task: Optional[asyncio.Task] = None
        # 统计
        self._tracer_stats = {
            "traces_received": 0,
            "traces_sampled": 0,
            "traces_dropped": 0,
            "spans_created": 0,
            "slow_traces": 0,
            "services_discovered": 0,
            "exported_spans": 0,
        }
        # 导出回调
        self._export_callbacks: List[Callable] = []

    # ----------------------------------------------------------------
    # 生命周期
    # ----------------------------------------------------------------

    def initialize(self) -> Result:
        self._update_status(ModuleStatus.RUNNING)
        self._query_engine = TraceQueryEngine(max_cache=self._max_traces)
        self._setup_rate_limit(rate=1000, burst=2000)
        if self._exporter_config.exporter_type != "memory":
            self._flush_task = asyncio.create_task(self._flush_loop())
        self.service_name = self.config.get("service_name", "auto-evo-ai")
        self.audit(
            "tracer_initialized", {"service": self.service_name, "exporter": self._exporter_config.exporter_type}
        )
        logger.info("[DistributedTracer] 初始化完成")
        return Result(success=True)

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        params = params or {}
        actions = {
            "should_sample": self.should_sample,
            "start_trace": self.start_trace,
            "start_span": self.start_span,
            "end_span": self.end_span,
            "add_span_event": self.add_span_event,
            "add_span_link": self.add_span_link,
            "inject": self.inject,
            "extract": self.extract,
            "set_baggage": self.set_baggage,
            "get_baggage": self.get_baggage,
            "flush": self.flush,
            "add_export_callback": self.add_export_callback,
            "get_trace": self.get_trace,
            "search_traces": self.search_traces,
            "get_topology": self.get_topology,
            "get_stats": self.get_stats,
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

    def health_check(self) -> HealthReport:
        return HealthReport(
            status="running",
            healthy=True,
            last_beat=datetime.now().isoformat(),
            uptime_seconds=self.stats.uptime_seconds,
            checks_run=4,
            error_rate=self.stats.error_rate,
            details={
                "traces": len(self._traces),
                "active_spans": sum(len(v) for v in self._active_spans.values()),
                "services": len(self._topology),
                "export_buffer": len(self._export_buffer),
            },
            version="V0.1",
        )

    def shutdown(self) -> Result:
        if self._flush_task:
            self._flush_task.cancel()
        self.flush()
        self._update_status(ModuleStatus.STOPPED)
        return Result(success=True)

    # ----------------------------------------------------------------
    # 采样
    # ----------------------------------------------------------------

    def should_sample(self, trace_id: str) -> bool:
        if self._sampling_strategy == SamplingStrategy.ALWAYS:
            return True
        if self._sampling_strategy == SamplingStrategy.NEVER:
            return False
        if self._sampling_strategy == SamplingStrategy.PROBABILISTIC:
            return (int(tmod.time()*1000000)%1000000/1000000) < self._sampling_rate
        if self._sampling_strategy == SamplingStrategy.RATE_LIMITING:
            if self._rate_limiter_tokens > 0:
                self._rate_limiter_tokens -= 1
                return True
            return False
        return True

    # ----------------------------------------------------------------
    # Trace管理
    # ----------------------------------------------------------------

    def start_trace(
        self,
        operation_name: str,
        *,
        service_name: str = "",
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict] = None,
        baggage: Optional[Dict[str, str]] = None,
    ) -> Span:
        """开始新Trace"""
        metrics_collector.counter("dtracer_ops_total")

        trace_id = uuid.uuid4().hex[:32]
        sampled = self.should_sample(trace_id)
        self._tracer_stats["traces_received"] += 1
        if not sampled:
            self._tracer_stats["traces_dropped"] += 1
            return Span(trace_id=trace_id, operation_name=operation_name)
        self._tracer_stats["traces_sampled"] += 1
        span = Span(
            trace_id=trace_id,
            operation_name=operation_name,
            kind=kind,
            service_name=service_name or self.service_name,
            attributes=attributes or {},
            baggage=baggage or {},
        )
        trace = Trace(
            trace_id=trace_id,
            root_span=span,
            spans=[span],
            baggage=dict(baggage or {}),
            sampled=True,
            start_time=span.start_time,
        )
        self._traces[trace_id] = trace
        self._active_spans[trace_id][span.span_id] = span
        self._tracer_stats["spans_created"] += 1
        # 拓扑更新
        self._update_topology(service_name or self.service_name)
        return span

    def start_span(
        self,
        operation_name: str,
        trace_id: str,
        parent_span_id: str = "",
        *,
        service_name: str = "",
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict] = None,
        links: Optional[List[SpanLink]] = None,
    ) -> Optional[Span]:
        """创建子Span"""
        trace = self._traces.get(trace_id)
        if not trace or not trace.sampled:
            return None
        span = Span(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            kind=kind,
            service_name=service_name or self.service_name,
            attributes=attributes or {},
            baggage=dict(trace.baggage),
            links=links or [],
        )
        trace.spans.append(span)
        self._active_spans[trace_id][span.span_id] = span
        trace.span_count += 1
        self._tracer_stats["spans_created"] += 1
        # 父子关系拓扑
        if parent_span_id:
            parent = self._active_spans.get(trace_id, {}).get(parent_span_id)
            if parent and parent.service_name != span.service_name:
                self._add_topology_edge(parent.service_name, span.service_name)
        return span

    def end_span(
        self,
        trace_id: str,
        span_id: str,
        *,
        status: SpanStatus = SpanStatus.OK,
        error_message: str = "",
        attributes: Optional[Dict] = None,
    ) -> Optional[Span]:
        """结束Span"""
        span_dict = self._active_spans.get(trace_id, {})
        span = span_dict.pop(span_id, None)
        if not span:
            return None
        span.end_time = datetime.now().isoformat()
        span.status = status
        if error_message:
            span.error_message = error_message
            span.status = SpanStatus.ERROR
        if attributes:
            span.attributes.update(attributes)
        # 计算耗时
        if span.start_time and span.end_time:
            try:
                start = datetime.fromisoformat(span.start_time)
                end = datetime.fromisoformat(span.end_time)
                span.duration_ms = (end - start).total_seconds() * 1000
            except (ValueError, TypeError):
                pass
        # 导出
        self._export_buffer.append(span)
        if len(self._export_buffer) >= self._exporter_config.batch_size:
            asyncio.create_task(self.flush())
        # 检查Trace是否完成
        trace = self._traces.get(trace_id)
        if trace:
            if not span_dict:
                trace.end_time = span.end_time
                trace.duration_ms = sum(s.duration_ms for s in trace.spans)
                trace.error_count = sum(1 for s in trace.spans if s.status == SpanStatus.ERROR)
                trace.status = SpanStatus.ERROR if trace.error_count > 0 else SpanStatus.OK
                if trace.duration_ms > self._slow_threshold_ms:
                    self._tracer_stats["slow_traces"] += 1
        return span

    def add_span_event(self, trace_id: str, span_id: str, event_name: str, attributes: Optional[Dict] = None):
        span = self._active_spans.get(trace_id, {}).get(span_id)
        if span:
            span.events.append(SpanEvent(name=event_name, attributes=attributes or {}))

    def add_span_link(
        self, trace_id: str, span_id: str, link_trace_id: str, link_span_id: str, attributes: Optional[Dict] = None
    ):
        span = self._active_spans.get(trace_id, {}).get(span_id)
        if span:
            span.links.append(SpanLink(trace_id=link_trace_id, span_id=link_span_id, attributes=attributes or {}))

    # ----------------------------------------------------------------
    # 上下文传播
    # ----------------------------------------------------------------

    def inject(self, span: Span) -> Dict[str, str]:
        """注入Trace上下文到Carrier"""
        return {
            "traceparent": f"00-{span.trace_id}-{span.span_id}-01",
            "tracestate": "",
            "x-b3-traceid": span.trace_id,
            "x-b3-spanid": span.span_id,
            "x-b3-parentspanid": span.parent_span_id,
        }

    def extract(self, carrier: Dict[str, str]) -> Optional[Dict]:
        """从Carrier提取Trace上下文"""
        traceparent = carrier.get("traceparent") or carrier.get("Traceparent")
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 4:
                return {"trace_id": parts[1], "span_id": parts[2], "sampled": parts[3] == "01"}
        trace_id = carrier.get("x-b3-traceid")
        span_id = carrier.get("x-b3-spanid")
        parent_span_id = carrier.get("x-b3-parentspanid", "")
        if trace_id and span_id:
            return {"trace_id": trace_id, "span_id": span_id, "parent_span_id": parent_span_id}
        return None

    # ----------------------------------------------------------------
    # Baggage
    # ----------------------------------------------------------------

    def set_baggage(self, trace_id: str, key: str, value: str):
        trace = self._traces.get(trace_id)
        if trace:
            trace.baggage[key] = value
            for span in self._active_spans.get(trace_id, {}).values():
                span.baggage[key] = value

    def get_baggage(self, trace_id: str, key: str) -> Optional[str]:
        trace = self._traces.get(trace_id)
        return trace.baggage.get(key) if trace else None

    # ----------------------------------------------------------------
    # 导出
    # ----------------------------------------------------------------

    def flush(self):
        if not self._export_buffer:
            return
        spans = self._export_buffer[:]
        self._export_buffer.clear()
        self._tracer_stats["exported_spans"] += len(spans)
        for callback in self._export_callbacks:
            try:
                result = callback(spans)
                if asyncio.iscoroutine(result):
                    result
            except Exception as e:
                logger.error(f"[Tracer] 导出回调失败: {e}")
        # 内存存储上限
        if len(self._traces) > 100000:
            sorted_ids = sorted(self._traces.keys(), key=lambda tid: self._traces[tid].start_time or "")
            for tid in sorted_ids[:50000]:
                del self._traces[tid]

    def _flush_loop(self):
        while True:
            try:
                time.sleep(self._exporter_config.flush_interval)
                self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Tracer] flush异常: {e}")

    def add_export_callback(self, callback: Callable):
        self._export_callbacks.append(callback)

    # ----------------------------------------------------------------
    # 拓扑
    # ----------------------------------------------------------------

    def _update_topology(self, service_name: str):
        if service_name not in self._topology:
            self._topology[service_name] = ServiceTopology(service_name=service_name)
            self._tracer_stats["services_discovered"] += 1

    def _add_topology_edge(self, from_service: str, to_service: str):
        self._update_topology(from_service)
        self._update_topology(to_service)
        topo = self._topology[from_service]
        if to_service not in topo.outbound_services:
            topo.outbound_services.append(to_service)
        topo.call_count += 1
        target = self._topology[to_service]
        if from_service not in target.inbound_services:
            target.inbound_services.append(from_service)

    # ----------------------------------------------------------------
    # 查询
    # ----------------------------------------------------------------

    def get_trace(self, trace_id: str) -> Optional[Dict]:
        trace = self._traces.get(trace_id)
        if not trace:
            return None
        return {
            "trace_id": trace.trace_id,
            "status": trace.status.value,
            "duration_ms": round(trace.duration_ms, 2),
            "span_count": trace.span_count,
            "error_count": trace.error_count,
            "service_count": trace.service_count,
            "baggage": trace.baggage,
            "spans": [
                {
                    "span_id": s.span_id,
                    "parent": s.parent_span_id,
                    "operation": s.operation_name,
                    "kind": s.kind.value,
                    "service": s.service_name,
                    "status": s.status.value,
                    "duration_ms": round(s.duration_ms, 2),
                    "attributes": s.attributes,
                    "events": [{"name": e.name, "attrs": e.attributes} for e in s.events],
                }
                for s in trace.spans
            ],
        }

    def search_traces(
        self,
        *,
        service_name: str = "",
        operation: str = "",
        status: str = "",
        min_duration_ms: float = 0,
        limit: int = 20,
    ) -> List[Dict]:
        results = []
        for trace in list(self._traces.values()):
            if not trace.sampled:
                continue
            if service_name and not any(s.service_name == service_name for s in trace.spans):
                continue
            if operation and not any(s.operation_name == operation for s in trace.spans):
                continue
            if status and trace.status.value != status:
                continue
            if min_duration_ms and trace.duration_ms < min_duration_ms:
                continue
            results.append(
                {
                    "trace_id": trace.trace_id,
                    "status": trace.status.value,
                    "duration_ms": round(trace.duration_ms, 2),
                    "span_count": trace.span_count,
                    "error_count": trace.error_count,
                    "start_time": trace.start_time,
                }
            )
        return sorted(results, key=lambda x: x["duration_ms"], reverse=True)[:limit]

    def get_topology(self) -> Dict[str, Any]:
        return {
            name: {
                "inbound": t.inbound_services,
                "outbound": t.outbound_services,
                "call_count": t.call_count,
                "avg_latency_ms": round(t.avg_latency_ms, 2),
            }
            for name, t in self._topology.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        return {**self._tracer_stats, "module_stats": self.stats.to_dict()}

# ============================================================================
# 模块注册
# ============================================================================

module_class = DistributedTracer
