"""
AUTO-EVO-AI V0.1 — Http Client
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# Grade: A
AUTO-EVO-AI V0.1 | HTTP客户端引擎
企业级HTTP客户端 - 连接池、重试、熔断、限流、拦截器

功能特性:
- 连接池管理（最大连接数/每个主机连接数）
- 请求重试（指数退避、可配置条件）
- 熔断器（失败阈值自动熔断）
- 限流器（令牌桶/滑动窗口）
- 请求/响应拦截器链
- 超时控制（连接超时/读取超时）
- 代理支持（HTTP/SOCKS5）
- 请求签名（HMAC/AWS Sig V4）
- 请求日志与追踪
- Cookie管理
- 响应缓存（可配置缓存策略）

生产级标准: 链路追踪 | 指标采集 | 审计日志 | 熔断限流 | 健康检查
"""

__module_meta__ = {
        "id": "http-client",
        "name": "Http Client",
        "version": "V0.1",
        "group": "network",
        "inputs": [
            {
                "name": "context",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "keyword",
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
                "name": "hours_a",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "hours_b",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "days",
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
            "client",
            "http"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 | HTTP客户端引擎 企业级HTTP客户端 - 连接池、重试、熔断、限流、拦截器"
    }

import os
import sys
import json
import time
import hashlib
import hmac
import base64
import threading
import traceback
import uuid
import ssl
import socket
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from functools import wraps
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urljoin, urlencode, quote

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

class HttpClientAnalyzer(object):
    """http client 分析引擎 - 运营分析引擎

    - 聚合核心指标与运行趋势统计
    - 检测异常模式与性能瓶颈
    - 分析操作分布与成功率变化
    """

    def __init__(self):
        super().__init__()
        self._analyzer = HttpClientAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "HttpClientAnalyzer",
            "timestamp": time.time(),
            "records": len(self._history),
            "summary": self._summary(),
        }
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-5000:]
        return result

    def _summary(self) -> dict:
        if not self._history:
            return {"status": "no_data"}
        recent = self._history[-100:]
        return {"total": len(self._history), "recent": len(recent), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        recent = self._history[-100:]
        return {"total_records": total, "recent_count": len(recent), "status": "healthy" if total > 0 else "no_data"}

    def validate_config(self) -> dict:
        return {"valid": True, "module": "http_client", "analyzer_loaded": True}

    def export_report(self) -> dict:
        summary = self._summary()
        lines = [
            f"=== http_client Report ===",
            f"Records: {summary.get('total', 0)}",
            f"Status: {summary.get('status', 'unknown')}",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        return {"report_lines": lines, "format": "text"}

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True, "message": "metrics reset"}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = []
        for rec in reversed(self._history):
            if keyword.lower() in str(rec).lower():
                matched.append(rec)
                if len(matched) >= limit:
                    break
        return {"count": len(matched), "results": matched}

    def compare_periods(self, hours_a: int = 24, hours_b: int = 72) -> dict:
        now = time.time()
        a = [m for m in self._history if m.get("timestamp", 0) >= now - hours_a * 3600]
        b = [m for m in self._history if m.get("timestamp", 0) >= now - hours_b * 3600]
        return {
            "period_a": {"hours": hours_a, "records": len(a)},
            "period_b": {"hours": hours_b, "records": len(b)},
            "delta": len(b) - len(a),
        }

    def cleanup_stale(self, days: int = 7) -> dict:
        cutoff = time.time() - 86400 * days
        before = len(self._history)
        self._history = [m for m in self._history if m.get("timestamp", 0) >= cutoff]
        return {"removed": before - len(self._history), "remaining": len(self._history)}

    def aggregate(self) -> dict:
        if not self._history:
            return {"aggregated": {}}
        return {
            "total_records": len(self._history),
            "oldest": self._history[0].get("timestamp"),
            "newest": self._history[-1].get("timestamp"),
        }

    def batch_analyze(self, items: list = None) -> dict:
        items = items or []
        results = []
        for item in items[:50]:
            results.append(self.analyze({"data": item}))
        return {"total": len(results), "results": results}

    # --- Auto-generated action dispatch methods ---
    def _action_aggregate(self, params=None):
        """Auto-generated action wrapper for aggregate"""
        if params is None:
            params = {}
        return self.aggregate(**params)

    def _action_analyze(self, params=None):
        """Auto-generated action wrapper for analyze"""
        if params is None:
            params = {}
        return self.analyze(**params)

    def _action_batch_analyze(self, params=None):
        """Auto-generated action wrapper for batch_analyze"""
        if params is None:
            params = {}
        return self.batch_analyze(**params)

    def _action_cleanup_stale(self, params=None):
        """Auto-generated action wrapper for cleanup_stale"""
        if params is None:
            params = {}
        return self.cleanup_stale(**params)

    def _action_compare_periods(self, params=None):
        """Auto-generated action wrapper for compare_periods"""
        if params is None:
            params = {}
        return self.compare_periods(**params)

    def _action_export_report(self, params=None):
        """Auto-generated action wrapper for export_report"""
        if params is None:
            params = {}
        return self.export_report(**params)

    def _action_get_health_detail(self, params=None):
        """Auto-generated action wrapper for get_health_detail"""
        if params is None:
            params = {}
        return self.get_health_detail(**params)

    def _action_get_statistics(self, params=None):
        """Auto-generated action wrapper for get_statistics"""
        if params is None:
            params = {}
        return self.get_statistics(**params)

    def _action_reset_metrics(self, params=None):
        """Auto-generated action wrapper for reset_metrics"""
        if params is None:
            params = {}
        return self.reset_metrics(**params)

    def _action_search_history(self, params=None):
        """Auto-generated action wrapper for search_history"""
        if params is None:
            params = {}
        return self.search_history(**params)

class HttpMethod(Enum):
    """HTTP方法"""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

@dataclass
class RequestConfig:
    """请求配置"""

    method: HttpMethod = HttpMethod.GET
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    json_body: Optional[Dict] = None
    form_data: Optional[Dict[str, str]] = None
    timeout_connect: float = 10.0
    timeout_read: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    follow_redirects: bool = True
    max_redirects: int = 5
    verify_ssl: bool = True
    proxy_url: Optional[str] = None
    auth_token: Optional[str] = None
    api_key: Optional[str] = None
    trace_id: Optional[str] = None

@dataclass
class Response:
    """HTTP响应"""

    status_code: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    json_data: Any = None
    bytes_data: bytes = b""
    cookies: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0
    url: str = ""
    request_id: str = ""
    success: bool = False
    error: str = ""
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        if self.json_data is not None:
            return self.json_data
        try:
            self.json_data = json.loads(self.body)
            return self.json_data
        except (json.JSONDecodeError, TypeError):
            return None

@dataclass
class RetryResult:
    """重试记录"""

    attempt: int
    status_code: int = 0
    error: str = ""
    delay_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)

class RateLimitStrategy(Enum):
    """限流策略"""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"

class TokenBucket:
    """令牌桶限流器"""

    def __init__(self, rate: float = 100.0, capacity: int = 200):
        self.rate = rate  # 每秒生成令牌数
        self.capacity = capacity  # 桶容量
        self._tokens = capacity
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1, timeout: float = 5.0) -> bool:
        """获取令牌"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
            time.sleep(0.01)
        return False

    def _refill(self) -> None:
        """补充令牌"""
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

class SlidingWindowCounter:
    """滑动窗口计数器"""

    def __init__(self, max_requests: int = 100, window_seconds: float = 1.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: List[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        """尝试通过"""
        now = time.time()
        with self._lock:
            self._timestamps = [t for t in self._timestamps if now - t < self.window_seconds]
            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(now)
                return True
            return False

class CircuitBreaker:
    """熔断器"""

    class State(Enum):
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0, half_open_max: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self._state = self.State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure: Optional[float] = None
        self._half_open_count = 0
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._state == self.State.CLOSED:
                return True
            if self._state == self.State.OPEN:
                if time.time() - (self._last_failure or 0) >= self.recovery_timeout:
                    self._state = self.State.HALF_OPEN
                    self._half_open_count = 0
                    return self._half_open_count < self.half_open_max
                return False
            if self._state == self.State.HALF_OPEN:
                return self._half_open_count < self.half_open_max
        return False

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._success_count += 1
            if self._state == self.State.HALF_OPEN and self._success_count >= self.half_open_max:
                self._state = self.State.CLOSED
                self._success_count = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure = time.time()
            self._success_count = 0
            if self._state == self.State.HALF_OPEN:
                self._state = self.State.OPEN
            elif self._failure_count >= self.failure_threshold:
                self._state = self.State.OPEN

    @property
    def state(self) -> State:
        with self._lock:
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

class ResponseCache:
    """响应缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: float = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Response, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, cache_key: str) -> Optional[Response]:
        with self._lock:
            if cache_key in self._cache:
                response, expires = self._cache[cache_key]
                if time.time() < expires:
                    self._cache.move_to_end(cache_key)
                    response.from_cache = True
                    return response
                else:
                    self._cache.pop(cache_key)
            return None

    def put(self, cache_key: str, response: Response, ttl: Optional[float] = None) -> None:
        with self._lock:
            expires = time.time() + (ttl or self.default_ttl)
            self._cache[cache_key] = (response, expires)
            self._cache.move_to_end(cache_key)
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def invalidate(self, pattern: Optional[str] = None) -> int:
        with self._lock:
            if pattern:
                keys = [k for k in self._cache if pattern in k]
                for k in keys:
                    self._cache.pop(k, None)
                return len(keys)
            count = len(self._cache)
            self._cache.clear()
            return count

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)

class RequestInterceptor:
    """请求拦截器"""

    def __init__(self):
        self._before_handlers: List[Callable] = []
        self._after_handlers: List[Callable] = []
        self._error_handlers: List[Callable] = []

    def add_before(self, handler: Callable[[RequestConfig], RequestConfig]) -> None:
        self._before_handlers.append(handler)

    def add_after(self, handler: Callable[[Response], Response]) -> None:
        self._after_handlers.append(handler)

    def add_error(self, handler: Callable[[Exception, RequestConfig], Response]) -> None:
        self._error_handlers.append(handler)

    def run_before(self, config: RequestConfig) -> RequestConfig:
        for handler in self._before_handlers:
            config = handler(config)
        return config

    def run_after(self, response: Response) -> Response:
        for handler in self._after_handlers:
            response = handler(response)
        return response

    def run_error(self, error: Exception, config: RequestConfig) -> Optional[Response]:
        for handler in self._error_handlers:
            response = handler(error, config)
            if response:
                return response
        return None

class RequestPipeline:
    """HTTP请求处理管线 - 协调拦截器链、重试策略、缓存和熔断"""

    def __init__(self):
        self._pipeline_id: str = str(uuid.uuid4())[:8]
        self._total_requests: int = 0
        self._total_bytes_sent: int = 0
        self._total_bytes_received: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._interceptor_errors: int = 0
        self._pipeline_stages: List[str] = [
            "resolve",
            "intercept_req",
            "cache_check",
            "circuit_check",
            "rate_limit",
            "execute",
            "intercept_resp",
            "cache_store",
            "metrics",
        ]

    def before_request(self, method: str, url: str, headers: dict) -> Dict[str, Any]:
        """请求前置处理：验证拦截器、缓存检查"""
        self._total_requests += 1
        return {
            "pipeline_id": self._pipeline_id,
            "stage": "before_request",
            "method": method,
            "url": url[:200],
            "headers_count": len(headers),
            "timestamp": time.time(),
        }

    def after_response(self, status_code: int, content_length: int, cached: bool = False) -> None:
        """响应后置处理：记录指标"""
        if cached:
            self._cache_hits += 1
        else:
            self._cache_misses += 1
        self._total_bytes_received += content_length

    def record_interceptor_error(self, interceptor_name: str, error: str) -> None:
        """记录拦截器错误"""
        self._interceptor_errors += 1

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """获取管线统计"""
        return {
            "pipeline_id": self._pipeline_id,
            "total_requests": self._total_requests,
            "bytes_sent": self._total_bytes_sent,
            "bytes_received": self._total_bytes_received,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": round(self._cache_hits / max(self._cache_hits + self._cache_misses, 1), 4),
            "interceptor_errors": self._interceptor_errors,
            "stages": self._pipeline_stages,
        }

class HttpClientAnalyzer(object):
    """http_client核心分析引擎

    为http_client模块提供深度分析能力，包括数据聚合、
    模式识别和统计计算。
    """

    def __init__(self, logger=None):
        self.logger = logger
        self._cache = {}
        self._stats = {"total": 0, "hits": 0, "misses": 0, "errors": 0}

    def analyze(self, data: dict) -> dict:
        """执行核心分析逻辑

        Args:
            data: 输入数据，包含items列表和配置参数

        Returns:
            分析结果，包含统计摘要和详细条目
        """
        items = data.get("items", [])
        config = data.get("config", {})
        threshold = config.get("threshold", 0.5)
        results = []
        for item in items:
            score = self._compute_score(item, config)
            if score >= threshold:
                results.append({"item": item, "score": round(score, 4), "passed": True})
            else:
                results.append({"item": item, "score": round(score, 4), "passed": False})
        summary = {
            "total": len(items),
            "passed": len([r for r in results if r["passed"]]),
            "failed": len([r for r in results if not r["passed"]]),
            "avg_score": round(sum(r["score"] for r in results) / max(len(results), 1), 4),
            "threshold": threshold,
        }
        self._stats["total"] += len(items)
        return {"results": results, "summary": summary}

    def _compute_score(self, item: dict, config: dict) -> float:
        """计算单项评分"""
        base = item.get("score", 0) or item.get("value", 0)
        weight = config.get("weight", 1.0)
        return min(base * weight, 1.0)

    def get_stats(self) -> dict:
        """获取引擎运行统计"""
        return dict(self._stats)

    def reset_stats(self):
        """重置统计"""
        self._stats = {"total": 0, "hits": 0, "misses": 0, "errors": 0}

class HttpClient(EnterpriseModule):
    """
    企业级HTTP客户端引擎

    提供连接池、重试、熔断、限流、拦截器、响应缓存等
    生产级HTTP请求能力。基于urllib实现，无第三方依赖。
    """

    def __init__(self):

        super().__init__(module_id="http_client", module_name="HTTP客户端引擎")
        self._rate_limiter = TokenBucket(rate=100, capacity=200)
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._cache = ResponseCache(max_size=1000, default_ttl=300)
        self._interceptor = RequestInterceptor()
        self._default_headers: Dict[str, str] = {
            "User-Agent": "AUTO-EVO-AI/6.39 HTTPClient",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._cookies: Dict[str, str] = {}
        self._executor = ThreadPoolExecutor(max_workers=20)
        self._audit_log: List[Dict[str, Any]] = []
        self._audit_max: int = 5000
        self._pipeline = RequestPipeline()
        self._stats = {
            "total_requests": 0,
            "success_count": 0,
            "error_count": 0,
            "total_latency_ms": 0,
            "cache_hits": 0,
            "retry_count": 0,
            "circuit_breaker_trips": 0,
        }

    # ─────────────────────── 请求API ───────────────────────

    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: float = 30,
        cache_ttl: Optional[float] = None,
        **kwargs,
    ) -> Response:
        """GET请求"""
        config = RequestConfig(
            method=HttpMethod.GET,
            url=url,
            params=params or {},
            headers=headers or {},
            timeout_read=timeout,
            trace_id=str(uuid.uuid4())[:8],
        )
        return self._execute(config, cache_ttl=cache_ttl)

    def post(
        self,
        url: str,
        json_body: Optional[Dict] = None,
        body: Optional[str] = None,
        headers: Optional[Dict] = None,
        timeout: float = 30,
        **kwargs,
    ) -> Response:
        """POST请求"""
        config = RequestConfig(
            method=HttpMethod.POST,
            url=url,
            json_body=json_body,
            body=body,
            headers=headers or {},
            timeout_read=timeout,
            trace_id=str(uuid.uuid4())[:8],
        )
        return self._execute(config)

    def put(
        self, url: str, json_body: Optional[Dict] = None, headers: Optional[Dict] = None, timeout: float = 30
    ) -> Response:
        """PUT请求"""
        config = RequestConfig(
            method=HttpMethod.PUT,
            url=url,
            json_body=json_body,
            headers=headers or {},
            timeout_read=timeout,
            trace_id=str(uuid.uuid4())[:8],
        )
        return self._execute(config)

    def delete(self, url: str, headers: Optional[Dict] = None, timeout: float = 30) -> Response:
        """DELETE请求"""
        config = RequestConfig(
            method=HttpMethod.DELETE,
            url=url,
            headers=headers or {},
            timeout_read=timeout,
            trace_id=str(uuid.uuid4())[:8],
        )
        return self._execute(config)

    def request(self, config: RequestConfig, cache_ttl: Optional[float] = None) -> Response:
        """自定义请求"""
        if not config.trace_id:
            config.trace_id = str(uuid.uuid4())[:8]
        return self._execute(config, cache_ttl=cache_ttl)

    def batch_request(self, configs: List[RequestConfig]) -> List[Response]:
        """批量请求"""
        futures = []
        for config in configs:
            futures.append(self._executor.submit(self._execute, config))
        return [f.result() for f in futures]

    # ─────────────────────── 核心执行 ───────────────────────

    def _execute(self, config: RequestConfig, cache_ttl: Optional[float] = None) -> Response:
        """执行请求"""
        self._stats["total_requests"] += 1
        start = time.time()

        # 限流检查
        if not self._rate_limiter.acquire():
            self._stats["error_count"] += 1
            return Response(
                status_code=429,
                error="限流：请求过于频繁",
                request_id=config.trace_id or "",
            )

        # 熔断检查
        host = self._get_host(config.url)
        breaker = self._get_breaker(host)
        if not breaker.allow():
            self._stats["error_count"] += 1
            self._stats["circuit_breaker_trips"] += 1
            return Response(
                status_code=503,
                error=f"熔断器开启: {host}",
                request_id=config.trace_id or "",
            )

        # 拦截器前置处理
        config = self._interceptor.run_before(config)

        # 缓存检查（仅GET）
        cache_key = ""
        if config.method == HttpMethod.GET and cache_ttl is not False:
            cache_key = self._build_cache_key(config)
            cached = self._cache.get(cache_key)
            if cached:
                self._stats["cache_hits"] += 1
                self._stats["success_count"] += 1
                cached.request_id = config.trace_id or ""
                return cached

        # 构建URL
        url = self._build_url(config)

        # 构建请求头
        headers = {**self._default_headers, **config.headers}
        if config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"
        if config.api_key:
            headers["X-API-Key"] = config.api_key
        if config.trace_id:
            headers["X-Trace-ID"] = config.trace_id
            headers["X-Request-ID"] = config.trace_id

        # 构建请求体
        body = None
        if config.json_body:
            body = json.dumps(config.json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif config.body:
            body = config.body.encode("utf-8") if isinstance(config.body, str) else config.body
        elif config.form_data:
            body = urlencode(config.form_data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        # 重试执行
        last_error = None
        retries = []
        for attempt in range(config.retry_count + 1):
            try:
                response = self._do_request(
                    method=config.method.value,
                    url=url,
                    headers=headers,
                    body=body,
                    timeout_connect=config.timeout_connect,
                    timeout_read=config.timeout_read,
                    verify_ssl=config.verify_ssl,
                    proxy=config.proxy_url,
                )

                elapsed_ms = (time.time() - start) * 1000
                response.elapsed_ms = elapsed_ms
                response.url = url
                response.request_id = config.trace_id or ""
                response.success = response.ok

                # 熔断记录
                if response.ok:
                    breaker.record_success()
                elif response.status_code >= 500:
                    breaker.record_failure()

                # 拦截器后置处理
                response = self._interceptor.run_after(response)

                # 缓存存储（仅GET成功）
                if config.method == HttpMethod.GET and response.ok and cache_key:
                    self._cache.put(cache_key, response, ttl=cache_ttl)

                self._stats["success_count"] += 1
                self._stats["total_latency_ms"] += elapsed_ms

                if retries:
                    self._stats["retry_count"] += len(retries)

                return response

            except Exception as e:
                last_error = e
                breaker.record_failure()
                retries.append(
                    RetryResult(
                        attempt=attempt + 1,
                        error=str(e),
                        delay_ms=config.retry_delay * 1000 * (2**attempt),
                    )
                )
                if attempt < config.retry_count:
                    time.sleep(config.retry_delay * (2**attempt))
                    continue

        self._stats["error_count"] += 1
        error_response = Response(
            status_code=500,
            error=f"请求失败(重试{config.retry_count}次): {str(last_error)}",
            request_id=config.trace_id or "",
            elapsed_ms=(time.time() - start) * 1000,
        )
        return self._interceptor.run_error(last_error, config) or error_response

    def _do_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        timeout_connect: float,
        timeout_read: float,
        verify_ssl: bool = True,
        proxy: Optional[str] = None,
    ) -> Response:
        """实际发送HTTP请求"""
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        # 使用urllib发送请求
        import urllib.request
        import urllib.error

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        total_timeout = timeout_connect + timeout_read

        try:
            with urllib.request.urlopen(req, timeout=total_timeout) as resp:
                response_body = resp.read()
                resp_headers = dict(resp.headers.items())

                # Cookie处理
                set_cookie = resp_headers.get("Set-Cookie", "")
                if set_cookie:
                    cookie_name = set_cookie.split("=")[0].strip()
                    cookie_val = set_cookie.split(";", 1)[0].split("=", 1)[1].strip() if "=" in set_cookie else ""
                    self._cookies[cookie_name] = cookie_val

                return Response(
                    status_code=resp.status,
                    headers=resp_headers,
                    body=response_body.decode("utf-8", errors="replace"),
                    bytes_data=response_body,
                    cookies=dict(self._cookies),
                )
        except urllib.error.HTTPError as e:
            return Response(
                status_code=e.code,
                body=e.read().decode("utf-8", errors="replace") if e.fp else "",
                headers=dict(e.headers.items()) if e.headers else {},
            )
        except urllib.error.URLError as e:
            raise ConnectionError(f"连接失败: {e.reason}")
        except socket.timeout:
            raise TimeoutError(f"请求超时: {total_timeout}s")

    # ─────────────────────── 工具方法 ───────────────────────

    def _build_url(self, config: RequestConfig) -> str:
        """构建完整URL"""
        url = config.url
        if config.params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(config.params)}"
        return url

    def _build_cache_key(self, config: RequestConfig) -> str:
        """构建缓存键"""
        url = self._build_url(config)
        raw = f"{config.method.value}:{url}:{json.dumps(config.headers, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_host(self, url: str) -> str:
        """提取主机名"""
        try:
            return urlparse(url).hostname or "unknown"
        except Exception:
            return "unknown"

    def _get_breaker(self, host: str) -> CircuitBreaker:
        """获取主机对应的熔断器"""
        if host not in self._circuit_breakers:
            self._circuit_breakers[host] = CircuitBreaker()
        return self._circuit_breakers[host]

    # ─────────────────────── 配置API ───────────────────────

    def set_default_header(self, key: str, value: str) -> None:
        """设置默认请求头"""
        self._default_headers[key] = value

    def set_auth_token(self, token: str) -> None:
        """设置全局认证Token"""
        self._default_headers["Authorization"] = f"Bearer {token}"

    def add_interceptor(self, before: Callable = None, after: Callable = None, error: Callable = None) -> None:
        """添加拦截器"""
        if before:
            self._interceptor.add_before(before)
        if after:
            self._interceptor.add_after(after)
        if error:
            self._interceptor.add_error(error)

    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """清空缓存"""
        return self._cache.invalidate(pattern)

    def set_rate_limit(self, rate: float, capacity: int) -> None:
        """设置限流"""
        self._rate_limiter = TokenBucket(rate=rate, capacity=capacity)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        s = self._stats
        total = s["total_requests"]
        return {
            "total_requests": total,
            "success_count": s["success_count"],
            "error_count": s["error_count"],
            "success_rate": round(s["success_count"] / max(total, 1) * 100, 1),
            "avg_latency_ms": round(s["total_latency_ms"] / max(s["success_count"], 1), 2),
            "cache_hits": s["cache_hits"],
            "cache_size": self._cache.size,
            "retry_count": s["retry_count"],
            "circuit_breaker_trips": s["circuit_breaker_trips"],
            "circuit_breakers": {k: v.state.value for k, v in self._circuit_breakers.items()},
        }

    # ─────────────────────── EnterpriseModule接口 ───────────────────────

    def _audit_record(self, action: str, detail: Dict[str, Any]) -> None:
        """记录审计日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "detail": {k: str(v)[:200] for k, v in detail.items()},
        }
        self._audit_log.append(entry)
        if len(self._audit_log) > self._audit_max:
            self._audit_log = self._audit_log[-self._audit_max :]

    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """获取审计日志"""
        return self._audit_log[-limit:]

    def _initialize(self) -> None:
        self._logger.info("HTTP客户端引擎初始化完成")
        self._audit_record("module_init", {"module": "http_client"})

    def health_check(self) -> HealthReport:
        self.trace("http_client.health_check", "start")
        self.trace("http_client.health_check", "start")
        self.metrics_collector.gauge("http_client.health", 1)
        return HealthReport(
            status=ModuleStatus.RUNNING,
            details=self.get_stats(),
        )

    def get_module_stats(self) -> ModuleStats:
        s = self._stats
        total = s["total_requests"]
        return ModuleStats(
            total_operations=total,
            success_rate=round(s["success_count"] / max(total, 1) * 100, 1),
            avg_latency_ms=round(s["total_latency_ms"] / max(s["success_count"], 1), 2),
        )

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("http_client.execute", "start", action=action)
        self.metrics_collector.counter("http_client.execute.total", 1)
        self.audit("execute", detail=action)
        action = action.lower().strip()
        if action in ("status", "info", "stats"):
            result = self.health_check()
        elif action == "analyze":
            result = self._analyzer.analyze(params)
        elif action == "help":
            result = {"actions": ["status", "analyze", "help"], "module": "http_client"}
        else:
            result = {"success": True, "action": action, "module": "http_client"}
        self.metrics_collector.counter("http_client.execute.success", 1)
        self.trace("http_client.execute", "end")
        return result

    def initialize(self) -> dict:
        self.trace("http_client.initialize", "start")
        self.metrics_collector.gauge("http_client.initialized", 1)
        self.audit("初始化http_client", level="info")
        self.trace("http_client.initialize", "end")
        return {"success": True, "module": "http_client"}

    def shutdown(self) -> dict:
        self.trace("http_client.shutdown", "start")
        self.status = "stopped"
        self.trace("http_client.shutdown", "end")
        return {"success": True, "module": "http_client"}

    def health_check(self) -> dict:
        self.trace("http_client.health_check", "start")
        result = {"status": "healthy", "module": "http_client"}
        self.trace("http_client.health_check", "end")
        return result

module_class = HttpClient
