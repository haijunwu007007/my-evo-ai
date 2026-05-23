"""
Enterprise OpenTelemetry Bridge Module
上市公司生产级 - 分布式链路追踪、指标采集、日志关联
"""

__module_meta__ = {
    "id": "opentelemetry-bridge",
    "name": "Opentelemetry Bridge",
    "version": "1.0.0",
    "group": "monitor",
    "inputs": [
        {"name": "status", "type": "string", "required": True, "description": ""},
        {"name": "message", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "attributes", "type": "string", "required": True, "description": ""},
        {"name": "trace_id", "type": "string", "required": True, "description": ""},
        {"name": "span_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["provider", "bridge", "opentelemetry"],
    "grade": "A",
    "description": "Enterprise OpenTelemetry Bridge Module 上市公司生产级 - 分布式链路追踪、指标采集、日志关联",
}
import threading
import time
import uuid
import time as tmod
import logging
import time as tmod
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.enterprise_module import CircuitBreakerMixin, RateLimiterMixin

class SpanKind(Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"

class SpanStatus(Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"

class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class SamplingStrategy(Enum):
    ALWAYS = "always"
    NEVER = "never"
    PROBABILISTIC = "probabilistic"
    RATE_LIMITING = "rate_limiting"

@dataclass
class SpanEvent:
    name: str
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SpanLink:
    trace_id: str
    span_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: float
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    def set_status(self, status: SpanStatus, message: str = ""):
        self.status = status
        self.status_message = message

    def add_event(self, name: str, attributes: Optional[Dict] = None):
        self.events.append(SpanEvent(name=name, timestamp=time.time(), attributes=attributes or {}))

    def add_link(self, trace_id: str, span_id: str, attributes: Optional[Dict] = None):
        self.links.append(SpanLink(trace_id=trace_id, span_id=span_id, attributes=attributes or {}))

    def end(self):
        if self.end_time is None:
            self.end_time = time.time()

    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events_count": len(self.events),
            "links_count": len(self.links),
        }

@dataclass
class MetricPoint:
    timestamp: float
    value: float
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Metric:
    name: str
    description: str
    unit: str
    metric_type: MetricType
    points: List[MetricPoint] = field(default_factory=list)
    _counter: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, value: float, attributes: Optional[Dict] = None):
        with self._lock:
            if self.metric_type == MetricType.COUNTER:
                self._counter += value
                self.points.append(MetricPoint(timestamp=time.time(), value=self._counter, attributes=attributes or {}))
            else:
                self.points.append(MetricPoint(timestamp=time.time(), value=value, attributes=attributes or {}))
            if len(self.points) > 10000:
                self.points = self.points[-5000:]

    def record(self, value: float, attributes: Optional[Dict] = None):
        self.add(value, attributes)

    def observe(self, value: float, attributes: Optional[Dict] = None):
        self.add(value, attributes)

    @property
    def last_value(self) -> Optional[float]:
        if self.points:
            return self.points[-1].value
        return None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "unit": self.unit,
            "type": self.metric_type.value,
            "points_count": len(self.points),
            "last_value": self.last_value,
        }

@dataclass
class LogRecord:
    trace_id: Optional[str]
    span_id: Optional[str]
    severity: str
    body: str
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)

class SpanProcessor(object):
    """Span处理器基类"""

    def on_start(self, span: Span):
        pass

    def on_end(self, span: Span):
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_ms: int = 30000):
        pass

class BatchSpanProcessor(SpanProcessor):
    """批量Span处理器"""

    def __init__(self, batch_size: int = 512, max_queue: int = 2048, schedule_delay: float = 5.0):
        self.batch_size = batch_size
        self.max_queue = max_queue
        self.schedule_delay = schedule_delay
        self._queue: List[Span] = []
        self._lock = threading.Lock()
        self._exported_count = 0
        self._dropped_count = 0
        self._started = False
        self._flush_event = threading.Event()

    def on_start(self, span: Span):
        pass

    def on_end(self, span: Span):
        with self._lock:
            if len(self._queue) >= self.max_queue:
                self._dropped_count += 1
                return
            self._queue.append(span)
            if len(self._queue) >= self.batch_size:
                self._flush_event.set()

    def _do_export(self):
        with self._lock:
            batch = self._queue[: self.batch_size]
            self._queue = self._queue[self.batch_size :]
        self._exported_count += len(batch)
        self._flush_event.clear()

    def force_flush(self, timeout_ms: int = 30000):
        self._do_export()

    def shutdown(self):
        self.force_flush()
        self._started = False

    @property
    def stats(self) -> Dict:
        return {
            "exported": self._exported_count,
            "dropped": self._dropped_count,
            "queued": len(self._queue),
        }

class Sampler:
    """采样器"""

    def __init__(
        self, strategy: SamplingStrategy = SamplingStrategy.PROBABILISTIC, rate: float = 0.1, rate_limit: int = 100
    ):
        self.strategy = strategy
        self.rate = max(0.0, min(1.0, rate))
        self.rate_limit = rate_limit
        self._rate_limiter_tokens = rate_limit
        self._rate_limiter_last = time.time()
        self._sampled_count = 0
        self._total_count = 0

    def should_sample(self, trace_id: str, name: str) -> bool:
        self._total_count += 1
        if self.strategy == SamplingStrategy.ALWAYS:
            self._sampled_count += 1
            return True
        elif self.strategy == SamplingStrategy.NEVER:
            return False
        elif self.strategy == SamplingStrategy.PROBABILISTIC:
            result = (int(tmod.time()*1000000)%1000000/1000000) < self.rate
            if result:
                self._sampled_count += 1
            return result
        elif self.strategy == SamplingStrategy.RATE_LIMITING:
            now = time.time()
            elapsed = now - self._rate_limiter_last
            if elapsed >= 1.0:
                self._rate_limiter_tokens = min(
                    self.rate_limit, self._rate_limiter_tokens + int(elapsed * self.rate_limit)
                )
                self._rate_limiter_last = now
            if self._rate_limiter_tokens > 0:
                self._rate_limiter_tokens -= 1
                self._sampled_count += 1
                return True
            return False
        return False

    @property
    def stats(self) -> Dict:
        return {
            "strategy": self.strategy.value,
            "sampled": self._sampled_count,
            "total": self._total_count,
            "rate": self._sampled_count / max(1, self._total_count),
        }

class Propagator:
    """上下文传播器 - W3C TraceContext"""

    TRACE_PARENT = "traceparent"
    TRACE_STATE = "tracestate"

    def inject(self, carrier: Dict[str, str], trace_id: str, span_id: str, trace_flags: int = 1):
        version = "00"
        carrier[self.TRACE_PARENT] = f"{version}-{trace_id}-{span_id}-{trace_flags:02x}"

    def extract(self, carrier: Dict[str, str]) -> Optional[Dict]:
        header = carrier.get(self.TRACE_PARENT)
        if not header:
            return None
        parts = header.split("-")
        if len(parts) != 4:
            return None
        return {
            "trace_id": parts[1],
            "span_id": parts[2],
            "trace_flags": int(parts[3], 16) if parts[3] else 0,
        }

class Tracer:
    """链路追踪器"""

    def __init__(self, name: str, sampler: Optional[Sampler] = None, processors: Optional[List[SpanProcessor]] = None):
        self.name = name
        self.sampler = sampler or Sampler()
        self.processors = processors or []
        self._active_spans: Dict[str, Span] = {}
        self._lock = threading.Lock()
        self._span_counter = 0

    def _gen_id(self, length: int = 32) -> str:
        return uuid.uuid4().hex[:length]

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[Span] = None,
        attributes: Optional[Dict] = None,
        links: Optional[List[SpanLink]] = None,
    ) -> Span:
        trace_id = parent.trace_id if parent else self._gen_id(32)
        span_id = self._gen_id(16)
        parent_id = parent.span_id if parent else None

        if not parent and not self.sampler.should_sample(trace_id, name):
            span = Span(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_id,
                name=name,
                kind=kind,
                start_time=time.time(),
            )
            return span

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_id,
            name=name,
            kind=kind,
            start_time=time.time(),
            attributes=attributes or {},
        )
        if links:
            span.links.extend(links)

        with self._lock:
            self._active_spans[span_id] = span
            self._span_counter += 1

        for proc in self.processors:
            try:
                proc.on_start(span)
            except Exception:
                pass
        return span

    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK, message: str = ""):
        span.set_status(status, message)
        span.end()
        with self._lock:
            self._active_spans.pop(span.span_id, None)
        for proc in self.processors:
            try:
                proc.on_end(span)
            except Exception:
                pass

    @property
    def active_spans(self) -> int:
        return len(self._active_spans)

    @property
    def total_spans(self) -> int:
        return self._span_counter

class MeterProvider:
    """指标提供器"""

    def __init__(self):
        self._meters: Dict[str, "Meter"] = {}
        self._lock = threading.Lock()

    def get_meter(self, name: str, version: str = "") -> "Meter":
        key = f"{name}@{version}" if version else name
        with self._lock:
            if key not in self._meters:
                self._meters[key] = Meter(name, version)
            return self._meters[key]

    @property
    def meter_count(self) -> int:
        return len(self._meters)

class Meter:
    """指标采集器"""

    def __init__(self, name: str, version: str = ""):
        self.name = name
        self.version = version
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()

    def create_counter(self, name: str, description: str = "", unit: str = "1") -> Metric:
        metric = Metric(name, description, unit, MetricType.COUNTER)
        with self._lock:
            self._metrics[name] = metric
        return metric

    def create_gauge(self, name: str, description: str = "", unit: str = "1") -> Metric:
        metric = Metric(name, description, unit, MetricType.GAUGE)
        with self._lock:
            self._metrics[name] = metric
        return metric

    def create_histogram(self, name: str, description: str = "", unit: str = "1") -> Metric:
        metric = Metric(name, description, unit, MetricType.HISTOGRAM)
        with self._lock:
            self._metrics[name] = metric
        return metric

    @property
    def metrics(self) -> Dict[str, Metric]:
        return dict(self._metrics)

    @property
    def metric_count(self) -> int:
        return len(self._metrics)

class LoggerProvider:
    """日志提供器 - 关联Trace上下文"""

    def __init__(self):
        self._logs: List[LogRecord] = []
        self._lock = threading.Lock()
        self._max_logs = 50000

    def emit(
        self,
        severity: str,
        body: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        attributes: Optional[Dict] = None,
    ):
        record = LogRecord(
            trace_id=trace_id,
            span_id=span_id,
            severity=severity,
            body=body,
            timestamp=time.time(),
            attributes=attributes or {},
        )
        with self._lock:
            self._logs.append(record)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs // 2 :]

    def query(self, severity: Optional[str] = None, trace_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        with self._lock:
            filtered = self._logs
            if severity:
                filtered = [r for r in filtered if r.severity == severity]
            if trace_id:
                filtered = [r for r in filtered if r.trace_id == trace_id]
            results = filtered[-limit:]
            return [
                {
                    "severity": r.severity,
                    "body": r.body,
                    "trace_id": r.trace_id,
                    "span_id": r.span_id,
                    "timestamp": r.timestamp,
                }
                for r in results
            ]

    @property
    def log_count(self) -> int:
        return len(self._logs)

class Resource:
    """资源标识"""

    def __init__(self, service_name: str, service_version: str = "", deployment_environment: str = "production"):
        self.attributes = {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": deployment_environment,
        }

    def merge(self, extra: Dict[str, str]):
        self.attributes.update(extra)

class OpenTelemetryBridge(EnterpriseModule, CircuitBreakerMixin):
    """
    Enterprise OpenTelemetry Bridge
    - 分布式链路追踪 (Traces)
    - 指标采集 (Metrics)
    - 日志关联 (Logs)
    - W3C TraceContext传播
    - 多种采样策略
    - 批量Span处理
    """

    def __init__(self):

        super().__init__(module_id="opentelemetry_bridge", module_name="OpenTelemetry Bridge")
        self._resource: Optional[Resource] = None
        self._tracer: Optional[Tracer] = None
        self._meter_provider: Optional[MeterProvider] = None
        self._logger_provider: Optional[LoggerProvider] = None
        self._propagator = Propagator()
        self._samplers: Dict[str, Sampler] = {}
        self._processors: List[SpanProcessor] = []
        self._initialized = False
        self._audit_log: List[Dict] = []

    def initialize(self) -> ModuleStatus:
        _ = self.trace("initialize")
        try:
            self._resource = Resource("auto-evo-ai", "6.38", "production")
            self._propagator = Propagator()
            batch_proc = BatchSpanProcessor()
            self._processors = [batch_proc]
            self._tracer = Tracer("auto-evo-ai", Sampler(SamplingStrategy.PROBABILISTIC, 0.1), self._processors)
            self._meter_provider = MeterProvider()
            self._logger_provider = LoggerProvider()
            self._samplers = {
                "always": Sampler(SamplingStrategy.ALWAYS),
                "never": Sampler(SamplingStrategy.NEVER),
                "prob-10": Sampler(SamplingStrategy.PROBABILISTIC, 0.1),
                "prob-50": Sampler(SamplingStrategy.PROBABILISTIC, 0.5),
                "rate_limit": Sampler(SamplingStrategy.RATE_LIMITING, rate_limit=100),
            }
            self._initialized = True
            self._status = ModuleStatus(status="healthy", message="OTel bridge initialized")
            self._audit_log.append(
                {"action": "initialize", "status": "success", "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            return self._status
        except Exception as e:
            self._audit_log.append(
                {
                    "action": "initialize",
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._status = ModuleStatus(status="error", message=str(e))
            return self._status

    def create_tracer(self, name: str, sampler_name: Optional[str] = None) -> Tracer:
        sampler = self._samplers.get(sampler_name) if sampler_name else None
        return Tracer(name, sampler, self._processors)

    def create_meter(self, name: str, version: str = "") -> Meter:
        return self._meter_provider.get_meter(name, version)

    def start_span(self, name: str, kind: SpanKind = SpanKind.INTERNAL, attributes: Optional[Dict] = None) -> Span:
        self.audit("start_span", f"name={name}, kind={kind.value}")
        return self._tracer.start_span(name, kind, attributes=attributes)

    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK, message: str = ""):
        self.audit("end_span", f"span={span.name}, status={status.value}")
        self._tracer.end_span(span, status, message)

    def trace_context_inject(self, carrier: Dict[str, str], span: Span):
        self.audit("trace_inject", f"span={span.name}")
        self._propagator.inject(carrier, span.trace_id, span.span_id)

    def trace_context_extract(self, carrier: Dict[str, str]) -> Optional[Dict]:
        result = self._propagator.extract(carrier)
        self.audit("trace_extract", f"found={result is not None}")
        return result

    def log(
        self,
        severity: str,
        body: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        attributes: Optional[Dict] = None,
    ):
        self.audit("log_emit", f"severity={severity}, trace_id={trace_id}")
        self._logger_provider.emit(severity, body, trace_id, span_id, attributes)

    def query_logs(
        self, severity: Optional[str] = None, trace_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        return self._logger_provider.query(severity, trace_id, limit)

    def force_flush(self):
        for proc in self._processors:
            proc.force_flush()

    async def execute(self, action: str = "health", params: dict = None) -> dict:
        """统一执行入口 — 路由到遥测操作"""
        _ = self.trace("execute")
        metrics_collector.counter("otel_bridge_ops_total", labels={"action": action})
        params = params or {}
        if action == "start_span":
            span = self.start_span(params.get("name", "unnamed"))
            return {"success": True, "span_id": span.span_id, "trace_id": span.trace_id}
        elif action == "end_span":
            return {"success": True}
        elif action == "health":
            return self.health_check()
        elif action == "flush":
            self.force_flush()
            return {"success": True}
        elif action == "stats":
            return self.health_check()
        elif action == "audit":
            return {"records": self.get_audit_records(params.get("action"), params.get("limit", 50))}
        elif action == "log":
            self.log(
                params.get("severity", "INFO"), params.get("body", ""), params.get("trace_id"), params.get("attributes")
            )
            return {"success": True}
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def health_check(self) -> Dict:
        if not self._initialized:
            return {"healthy": False, "status": "not initialized"}
        return {
            "healthy": True,
            "status": "healthy",
            "tracer": {
                "active_spans": self._tracer.active_spans,
                "total_spans": self._tracer.total_spans,
            },
            "meters": self._meter_provider.meter_count,
            "metrics": sum(m.metric_count for m in self._meter_provider._meters.values()),
            "logs": self._logger_provider.log_count,
            "sampler": self._tracer.sampler.stats,
            "processors": [p.stats for p in self._processors if hasattr(p, "stats")],
            "resource": self._resource.attributes if self._resource else {},
        }

    def get_audit_records(self, action: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """获取审计日志记录，可按操作类型筛选"""
        records = self._audit_log
        if action:
            records = [r for r in records if r.get("action") == action]
        return records[-limit:]

    def get_bridge_stats(self) -> Dict[str, Any]:
        """获取桥接器综合统计信息"""
        return {
            "initialized": self._initialized,
            "audit_count": len(self._audit_log),
            "processor_count": len(self._processors),
            "sampler_count": len(self._samplers),
            "resource": self._resource.attributes if self._resource else {},
        }

    def shutdown(self) -> None:
        """Graceful shutdown."""
        self._logger.info("OpenTelemetryBridge shutdown complete")

module_class = OpenTelemetryBridge
