"""
AUTO-EVO-AI V0.1 — OpenTelemetry 可观测性集成
============================================
为 FastAPI 提供自动链路追踪 + 指标导出
"""

import os
import logging
from core.logging_config import get_logger

logger = get_logger("evo.telemetry")
_initialized = False


def init_telemetry(service_name: str = "auto-evo-ai", version: str = "V0.1"):
    """初始化 OpenTelemetry — 自动仪表化 FastAPI"""
    global _initialized
    if _initialized:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        resource = Resource.create({
            "service.name": service_name,
            "service.version": version,
        })

        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(_ConsoleSpanExtender()))

        trace.set_tracer_provider(provider)

        # 延迟导入 app（避免循环依赖）
        try:
            from api.infra import app
            FastAPIInstrumentor.instrument_app(app)
            logger.info("[OTEL] FastAPI 自动仪表化完成")
        except ImportError:
            logger.warning("[OTEL] app 不可用，延迟仪表化")

        _initialized = True
        logger.info(f"[OTEL] OpenTelemetry 初始化完成: {service_name} v{version}")

    except ImportError as e:
        logger.info(f"[OTEL] 不可用 (可选): {e}")
    except Exception as e:
        logger.warning(f"[OTEL] 初始化异常: {e}")


class _ConsoleSpanExtender:
    """增强的控制台 Span 导出器 — 比默认 ConsoleSpanExporter 更可读"""
    def __init__(self, delegate=None):
        if delegate is None:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            delegate = ConsoleSpanExporter()
        self._delegate = delegate

    def export(self, spans, timeout_millis=30000):
        for span in spans:
            attrs = span.attributes
            logger.info(
                f"[TRACE] {span.name} | "
                f"duration={span.end_time - span.start_time}ns | "
                f"trace_id={format(span.get_span_context().trace_id, '032x')[:16]}"
            )
        return self._delegate.export(spans, timeout_millis)

    def shutdown(self):
        self._delegate.shutdown()

    def force_flush(self, timeout_millis=30000):
        return self._delegate.force_flush(timeout_millis)
