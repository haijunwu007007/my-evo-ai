"""
AUTO-EVO-AI V0.1 - 分布式链路追踪
==================================
基于 OpenTelemetry 标准的轻量级链路追踪实现。
每个请求生成 trace_id，贯穿所有模块调用链。

生产级特性：
  - 自动 trace_id 传播（父子关系）
  - Span 生命周期管理
  - 调用链路可视化数据输出
  - 内存轻量（无需外部依赖如Jaeger）
  - 支持后续对接 Jaeger/Zipkin

使用方式:
  tracer = get_tracer()
  with tracer.trace("operation_name", module_id="xxx") as span:
      span.set_tag("key", "value")
      # ... 业务逻辑 ...
"""

import time
import uuid
import logging
import threading
import functools
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

logger = logging.getLogger("evo.tracing")


@dataclass
class Span:
    """追踪跨度"""

    trace_id: str
    span_id: str
    parent_id: str | None
    operation_name: str
    module_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    tags: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # ok / error

    @property
    def duration_ms(self) -> float:
        if self.end_time and self.start_time:
            return round((self.end_time - self.start_time) * 1000, 2)
        return 0.0

    def set_tag(self, key: str, value: Any):
        self.tags[key] = value

    def log_kv(self, kv: dict[str, Any]):
        self.logs.append({"timestamp": datetime.now().isoformat(), **kv})

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "operation": self.operation_name,
            "module_id": self.module_id,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs_count": len(self.logs),
        }


@dataclass
class TraceContext:
    """追踪上下文 — 线程内传播"""

    trace_id: str
    span_id: str = ""
    parent_id: str = ""


class TracingContext:
    """
    线程安全的链路追踪器
    - 每次trace()生成新的span
    - 自动维护父子关系
    - 调用链存入内存队列，可导出
    """

    def __init__(self, max_traces: int = 10000):
        self._max_traces = max_traces
        self._traces: dict[str, list[Span]] = {}  # trace_id -> [spans]
        self._current: threading.local = threading.local()
        self._lock = threading.Lock()
        self._stats = {
            "total_spans": 0,
            "total_traces": 0,
            "errors": 0,
        }

    def _gen_id(self) -> str:
        return uuid.uuid4().hex[:16]

    def _get_current_context(self) -> TraceContext | None:
        return getattr(self._current, "context", None)

    def _set_current_context(self, ctx: TraceContext | None):
        self._current.context = ctx

    @contextmanager
    def trace(self, operation_name: str, module_id: str = "", parent_id: str = ""):
        """
        创建追踪span上下文管理器

        Args:
            operation_name: 操作名称
            module_id: 模块ID
            parent_id: 父span ID（不传则自动从当前上下文获取）
        """
        current = self._get_current_context()

        # 确定trace_id和parent_id
        if current:
            trace_id = current.trace_id
            parent_span_id = parent_id or current.span_id
        else:
            trace_id = self._gen_id()
            parent_span_id = parent_id

        span_id = self._gen_id()
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_id=parent_span_id,
            operation_name=operation_name,
            module_id=module_id,
            start_time=time.time(),
        )

        # 设置当前上下文
        new_ctx = TraceContext(trace_id=trace_id, span_id=span_id)
        self._set_current_context(new_ctx)

        try:
            self._stats["total_spans"] += 1
            yield span
            span.status = "ok"
        except Exception as e:
            span.status = "error"
            span.log_kv({"event": "error", "message": str(e)})
            self._stats["errors"] += 1
            raise
        finally:
            span.end_time = time.time()
            # 存储span
            with self._lock:
                if trace_id not in self._traces:
                    self._traces[trace_id] = []
                    self._stats["total_traces"] += 1
                self._traces[trace_id].append(span)
                # 清理旧trace
                if len(self._traces) > self._max_traces:
                    oldest_key = next(iter(self._traces))
                    del self._traces[oldest_key]
            # 恢复父上下文
            self._set_current_context(current)

    def get_trace(self, trace_id: str) -> list[dict[str, Any]]:
        """获取完整调用链"""
        with self._lock:
            spans = self._traces.get(trace_id, [])
            return [s.to_dict() for s in spans]

    def get_recent_traces(self, limit: int = 20) -> list[list[dict[str, Any]]]:
        """获取最近的调用链"""
        with self._lock:
            trace_ids = list(self._traces.keys())[-limit:]
            result = []
            for tid in trace_ids:
                spans = [s.to_dict() for s in self._traces[tid]]
                result.append(spans)
            return result

    def get_stats(self) -> dict[str, Any]:
        """获取追踪统计"""
        return {
            **self._stats,
            "active_traces": len(self._traces),
        }

    def clear(self):
        """清空追踪数据"""
        with self._lock:
            self._traces.clear()


# 全局单例
_tracer: TracingContext | None = None


def get_tracer() -> TracingContext:
    """获取全局追踪器实例"""
    global _tracer
    if _tracer is None:
        _tracer = TracingContext()
        logger.info("链路追踪器初始化完成")
    return _tracer


def trace_operation(operation_name: str):
    """装饰器：记录操作耗时到链路追踪（兼容接口）"""

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace(operation_name):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace(operation_name):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
