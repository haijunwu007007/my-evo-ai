"""
AUTO-EVO-AI V0.1 - CDN Invalidation Module (Grade: A Production)
CDN缓存管理：缓存失效、批量刷新、URL管理、命中率监控
"""

__module_meta__ = {
        "id": "cdn-invalidate",
        "name": "Cdn Invalidate",
        "version": "V0.1",
        "group": "cdn",
        "inputs": [
            {
                "name": "batch_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "urls",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "batch_id_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "invalidate_fn",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "batch_id_3",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "operation",
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
            "provider",
            "manager",
            "cdn"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 - CDN Invalidation Module (Grade: A Production) CDN缓存管理：缓存失效、批量刷新、URL管理、命中率监控"
    }

import os
import asyncio
import time
import logging
import uuid
import re
import fnmatch
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector, prometheus_timer
    from modules._base.audit import AuditLogger
except ImportError:

    class EnterpriseModule:
        def __init__(self):
            self._initialized = False
            self.logger = logging.getLogger(__name__)

        def initialize(self):
            self._initialized = True

        def shutdown(self):
            self._initialized = False

        def health_check(self):
            return {"status": "ok"}

    class CircuitBreakerMixin:
        pass

    class RateLimiterMixin:
        pass

    trace_operation = lambda x: lambda f: f
    prometheus_timer = lambda x: lambda f: f
    metrics_collector = None

    class AuditLogger:
        def log(self, *a, **k):
            pass

logger = logging.getLogger(__name__)

class InvalidationStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CDNProvider(Enum):
    CLOUDFLARE = "cloudflare"
    AKAMAI = "akamai"
    AWS_CLOUDFRONT = "aws_cloudfront"
    ALIYUN_CDN = "aliyun_cdn"
    FASTLY = "fastly"
    CUSTOM = "custom"

@dataclass
class CachedItem:
    url: str
    provider: CDNProvider
    cached_at: datetime
    expires_at: datetime
    size_bytes: int = 0
    content_type: str = ""
    status: str = "active"
    hits: int = 0
    last_hit: datetime | None = None

@dataclass
class InvalidationTask:
    task_id: str = field(default_factory=lambda: f"inv_{uuid.uuid4().hex[:8]}")
    urls: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    status: InvalidationStatus = InvalidationStatus.PENDING
    provider: CDNProvider = CDNProvider.CUSTOM
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    affected_items: int = 0
    failed_items: int = 0
    error_message: str = ""
    batch_id: str = ""

@dataclass
class HitRateSample:
    provider: CDNProvider
    timestamp: datetime
    requests: int
    hits: int
    misses: int
    bandwidth_bytes: int = 0

class InvalidationBatchProcessor:
    """缓存失效批处理器 - 批量URL失效、进度追踪、部分失败处理"""

    def __init__(self):
        self._batches: dict[str, list[str]] = {}
        self._batch_status: dict[str, str] = {}

    def create_batch(self, batch_id: str, urls: list[str]) -> None:
        self._batches[batch_id] = urls
        self._batch_status[batch_id] = "pending"

    def process_batch(self, batch_id: str, invalidate_fn: callable) -> dict:
        if batch_id not in self._batches:
            return {"error": "batch not found"}
        urls = self._batches[batch_id]
        self._batch_status[batch_id] = "processing"
        succeeded = 0
        failed = 0
        for url in urls:
            try:
                invalidate_fn(url)
                succeeded += 1
            except Exception:
                failed += 1
        self._batch_status[batch_id] = "completed"
        return {"batch_id": batch_id, "total": len(urls), "succeeded": succeeded, "failed": failed}

    def get_batch_status(self, batch_id: str) -> dict:
        return {
            "batch_id": batch_id,
            "status": self._batch_status.get(batch_id, "unknown"),
            "total": len(self._batches.get(batch_id, [])),
        }

class CDNInvalidateManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    def __init__(self):
        self._initialized = False

    """CDN缓存管理器"""

    def __init__(self):

        super().__init__()
        self.module_name = "cdn_invalidate"
        self.module_id = self.module_name
        self.module_version = "7.0.0"
        self._cache: dict[str, CachedItem] = {}
        self._tasks: dict[str, InvalidationTask] = {}
        self._hit_history: dict[CDNProvider, list[HitRateSample]] = defaultdict(list)
        self._audit = AuditLogger()
        self._total_invalidations = 0
        self._total_urls_invalidated = 0
        self._providers: dict[str, CDNProvider] = {
            "cf-us": CDNProvider.CLOUDFLARE,
            "ak-global": CDNProvider.AKAMAI,
            "aws-cf": CDNProvider.AWS_CLOUDFRONT,
            "ali-cdn": CDNProvider.ALIYUN_CDN,
            "fastly-edge": CDNProvider.FASTLY,
        }
        self._seed_cache()

    def _seed_cache(self):
        base_urls = [
            ("https://cdn.example.com/static/js/app.js", "application/javascript", 245000),
            ("https://cdn.example.com/static/css/style.css", "text/css", 89000),
            ("https://cdn.example.com/static/img/logo.png", "image/png", 34000),
            ("https://cdn.example.com/api/v1/data.json", "application/json", 1200),
            ("https://cdn.example.com/static/fonts/main.woff2", "font/woff2", 56000),
            ("https://cdn.example.com/static/img/banner.jpg", "image/jpeg", 180000),
            ("https://cdn.example.com/page/home.html", "text/html", 15000),
            ("https://cdn.example.com/page/about.html", "text/html", 12000),
        ]
        providers = list(CDNProvider)
        for url, ct, size in base_urls:
            provider = providers[hash(url) % len(providers)]
            key = f"{provider.value}:{url}"
            now = datetime.now()
            self._cache[key] = CachedItem(
                url=url,
                provider=provider,
                cached_at=now - timedelta(hours=2),
                expires_at=now + timedelta(hours=22),
                size_bytes=size,
                content_type=ct,
                hits=hash(url) % 500 + 100,
                last_hit=now - timedelta(minutes=5),
            )

    def initialize(self):
        self._record_hit_samples()
        logger.info("cdn_invalidate initialized")

    def _record_hit_samples(self):
        for provider in self._providers.values():
            now = datetime.now()
            requests = hash(provider.value) % 5000 + 2000
            hit_rate = 0.85 + (hash(provider.value + "hr") % 15) / 100
            hits = int(requests * hit_rate)
            misses = requests - hits
            self._hit_history[provider].append(HitRateSample(provider, now, requests, hits, misses, hits * 15000))

    async def execute(self, operation: str, params: dict[str, Any] = None) -> dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("cdn_invalidate_ops_total", labels={"action": operation})
        self.audit("execute", f"operation={operation}")
        params = params or {}
        if operation == "invalidate":
            return self._invalidate(params)
        elif operation == "invalidate_pattern":
            return self._invalidate_pattern(params)
        elif operation == "batch_invalidate":
            return self._batch_invalidate(params)
        elif operation == "get_task":
            return self._get_task(params)
        elif operation == "list_tasks":
            return self._list_tasks(params)
        elif operation == "cache_status":
            return self._cache_status(params)
        elif operation == "hit_rate":
            return self._hit_rate(params)
        elif operation == "list_cached":
            return self._list_cached(params)
        elif operation == "prefetch":
            return self._prefetch(params)
        elif operation == "purge_all":
            return self._purge_all(params)
        else:
            return {
                "success": False,
                "error": f"unknown op: {operation}",
                "available": [
                    "invalidate",
                    "invalidate_pattern",
                    "batch_invalidate",
                    "get_task",
                    "list_tasks",
                    "cache_status",
                    "hit_rate",
                    "list_cached",
                    "prefetch",
                    "purge_all",
                ],
            }

    def _invalidate(self, p: dict) -> dict:
        url = p.get("url", "")
        provider_name = p.get("provider", "")

        if not url:
            return {"success": False, "error": "missing url"}

        provider = self._resolve_provider(provider_name)
        task = InvalidationTask(
            urls=[url],
            provider=provider,
            status=InvalidationStatus.PROCESSING,
        )
        # Simulate processing
        affected = 0
        for key, item in list(self._cache.items()):
            if item.url == url and (not provider_name or item.provider == provider):
                item.status = "invalidated"
                affected += 1

        task.affected_items = affected
        task.status = InvalidationStatus.COMPLETED
        task.completed_at = datetime.now()
        self._tasks[task.task_id] = task
        self._total_invalidations += 1
        self._total_urls_invalidated += affected
        self._audit.log("invalidate", {"task_id": task.task_id, "url": url, "affected": affected})

        return {
            "success": True,
            "result": {
                "task_id": task.task_id,
                "url": url,
                "provider": provider.value,
                "affected": affected,
                "status": task.status.value,
            },
        }

    def _invalidate_pattern(self, p: dict) -> dict:
        pattern = p.get("pattern", "")
        provider_name = p.get("provider", "")

        if not pattern:
            return {"success": False, "error": "missing pattern"}

        provider = self._resolve_provider(provider_name)
        task = InvalidationTask(
            patterns=[pattern],
            provider=provider,
            status=InvalidationStatus.PROCESSING,
        )

        matched_urls = []
        for key, item in list(self._cache.items()):
            if fnmatch.fnmatch(item.url, pattern):
                if not provider_name or item.provider == provider:
                    item.status = "invalidated"
                    matched_urls.append(item.url)

        task.urls = matched_urls
        task.affected_items = len(matched_urls)
        task.status = InvalidationStatus.COMPLETED
        task.completed_at = datetime.now()
        self._tasks[task.task_id] = task
        self._total_invalidations += 1
        self._total_urls_invalidated += len(matched_urls)

        return {
            "success": True,
            "result": {
                "task_id": task.task_id,
                "pattern": pattern,
                "matched": len(matched_urls),
                "urls": matched_urls[:10],
                "status": task.status.value,
            },
        }

    def _batch_invalidate(self, p: dict) -> dict:
        urls = p.get("urls", [])
        patterns = p.get("patterns", [])

        if not urls and not patterns:
            return {"success": False, "error": "missing urls or patterns"}

        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        total_affected = 0
        task_ids = []

        for url in urls:
            r = self._invalidate({"url": url})
            if r["success"]:
                task_ids.append(r["result"]["task_id"])
                total_affected += r["result"]["affected"]

        for pat in patterns:
            r = self._invalidate_pattern({"pattern": pat})
            if r["success"]:
                task_ids.append(r["result"]["task_id"])
                total_affected += r["result"]["matched"]

        self._audit.log("batch_invalidate", {"batch_id": batch_id, "tasks": len(task_ids), "affected": total_affected})
        return {
            "success": True,
            "result": {
                "batch_id": batch_id,
                "tasks": task_ids,
                "total_affected": total_affected,
                "urls_requested": len(urls),
                "patterns_requested": len(patterns),
            },
        }

    def _get_task(self, p: dict) -> dict:
        task_id = p.get("task_id")
        if not task_id or task_id not in self._tasks:
            return {"success": False, "error": "task not found"}
        t = self._tasks[task_id]
        return {
            "success": True,
            "result": {
                "task_id": t.task_id,
                "status": t.status.value,
                "provider": t.provider.value,
                "urls": t.urls,
                "patterns": t.patterns,
                "affected": t.affected_items,
                "failed": t.failed_items,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            },
        }

    def _list_tasks(self, p: dict) -> dict:
        limit = p.get("limit", 20)
        status_filter = p.get("status")
        tasks = list(self._tasks.values())
        if status_filter:
            try:
                sf = InvalidationStatus(status_filter)
                tasks = [t for t in tasks if t.status == sf]
            except ValueError:
                pass
        tasks = tasks[-limit:]
        return {
            "success": True,
            "result": [
                {
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "provider": t.provider.value,
                    "affected": t.affected_items,
                    "created_at": t.created_at.isoformat(),
                }
                for t in tasks
            ],
            "total": len(tasks),
        }

    def _cache_status(self, p: dict) -> dict:
        url = p.get("url", "")
        if not url:
            return {"success": False, "error": "missing url"}

        items = [(k, v) for k, v in self._cache.items() if v.url == url]
        if not items:
            return {"success": True, "result": {"url": url, "cached": False, "providers": []}}

        result = []
        for key, item in items:
            result.append(
                {
                    "provider": item.provider.value,
                    "status": item.status,
                    "cached_at": item.cached_at.isoformat(),
                    "expires_at": item.expires_at.isoformat(),
                    "hits": item.hits,
                    "size_bytes": item.size_bytes,
                    "content_type": item.content_type,
                }
            )
        return {"success": True, "result": {"url": url, "cached": True, "entries": result}}

    def _hit_rate(self, p: dict) -> dict:
        provider_name = p.get("provider", "")

        if provider_name:
            try:
                provider = CDNProvider(provider_name)
                samples = self._hit_history.get(provider, [])
            except ValueError:
                return {"success": False, "error": f"unknown provider: {provider_name}"}
        else:
            samples = []
            for s_list in self._hit_history.values():
                samples.extend(s_list)

        if not samples:
            return {"success": True, "result": {"message": "no data"}}

        total_req = sum(s.requests for s in samples)
        total_hits = sum(s.hits for s in samples)
        total_misses = sum(s.misses for s in samples)
        rate = (total_hits / total_req * 100) if total_req > 0 else 0

        return {
            "success": True,
            "result": {
                "hit_rate_pct": round(rate, 1),
                "total_requests": total_req,
                "total_hits": total_hits,
                "total_misses": total_misses,
                "samples": len(samples),
                "bandwidth_served_gb": round(sum(s.bandwidth_bytes for s in samples) / 1e9, 2),
            },
        }

    def _list_cached(self, p: dict) -> dict:
        provider_name = p.get("provider", "")
        content_type = p.get("content_type", "")
        limit = p.get("limit", 50)
        status_filter = p.get("status", "active")

        items = list(self._cache.values())
        if provider_name:
            try:
                p_enum = CDNProvider(provider_name)
                items = [i for i in items if i.provider == p_enum]
            except ValueError:
                pass
        if content_type:
            items = [i for i in items if content_type in i.content_type]
        if status_filter:
            items = [i for i in items if i.status == status_filter]

        items = items[:limit]
        return {
            "success": True,
            "result": [
                {
                    "url": i.url,
                    "provider": i.provider.value,
                    "status": i.status,
                    "content_type": i.content_type,
                    "size_kb": round(i.size_bytes / 1024, 1),
                    "hits": i.hits,
                    "expires": i.expires_at.isoformat(),
                }
                for i in items
            ],
            "total": len(items),
        }

    def _prefetch(self, p: dict) -> dict:
        urls = p.get("urls", [])
        if not urls:
            return {"success": False, "error": "missing urls"}

        prefetched = 0
        for url in urls:
            provider = list(CDNProvider)[hash(url) % len(list(CDNProvider))]
            key = f"{provider.value}:{url}"
            if key in self._cache:
                self._cache[key].cached_at = datetime.now()
                self._cache[key].expires_at = datetime.now() + timedelta(hours=24)
                self._cache[key].status = "active"
                prefetched += 1
            else:
                self._cache[key] = CachedItem(
                    url=url,
                    provider=provider,
                    cached_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=24),
                    status="active",
                )
                prefetched += 1

        self._audit.log("prefetch", {"urls": len(urls), "prefetched": prefetched})
        return {"success": True, "result": {"requested": len(urls), "prefetched": prefetched}}

    def _purge_all(self, p: dict) -> dict:
        provider_name = p.get("provider", "")
        count_before = len(self._cache)

        if provider_name:
            try:
                p_enum = CDNProvider(provider_name)
                keys_to_remove = [k for k, v in self._cache.items() if v.provider == p_enum]
                for k in keys_to_remove:
                    del self._cache[k]
            except ValueError:
                pass
        else:
            self._cache.clear()

        purged = count_before - len(self._cache)
        self._audit.log("purge_all", {"provider": provider_name or "all", "purged": purged})
        return {"success": True, "result": {"purged": purged, "remaining": len(self._cache)}}

    def _resolve_provider(self, name: str) -> CDNProvider:
        if not name:
            return CDNProvider.CUSTOM
        try:
            return CDNProvider(name)
        except ValueError:
            return CDNProvider.CUSTOM

    def shutdown(self):
        self._initialized = False
        self._audit.log("shutdown", "cdn_invalidate shutdown")

    def health_check(self) -> dict[str, Any]:
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy" if self._initialized else "not_initialized",
                "cached_items": len(self._cache),
                "invalidation_tasks": len(self._tasks),
                "total_invalidations": self._total_invalidations,
                "total_urls_invalidated": self._total_urls_invalidated,
                "providers": len(self._providers),
            }
        )
        return result

    def get_invalidation_history(self, limit: int = 50) -> list[dict]:
        """获取缓存失效历史记录"""
        history = []
        for task in self._tasks.values() if hasattr(self, "_tasks") else []:
            if hasattr(task, "to_dict"):
                history.append(task.to_dict())
            else:
                history.append(
                    {
                        "id": getattr(task, "task_id", ""),
                        "url": getattr(task, "url", ""),
                        "status": getattr(task, "status", ""),
                        "created": str(getattr(task, "created_at", "")),
                    }
                )
        return history[-limit:]

    def get_hit_rate_summary(self) -> dict:
        """获取CDN命中率摘要"""
        samples = self._hit_rate_samples if hasattr(self, "_hit_rate_samples") else []
        if not samples:
            return {"average_hit_rate": 0, "samples": 0}
        rates = [s.hit_rate for s in samples if hasattr(s, "hit_rate")]
        return {
            "average_hit_rate": round(sum(rates) / len(rates), 4) if rates else 0,
            "min": round(min(rates), 4) if rates else 0,
            "max": round(max(rates), 4) if rates else 0,
            "samples": len(rates),
        }

    def get_invalidation_efficiency(self) -> dict[str, Any]:
        """计算缓存失效效率：平均传播延迟、失败率、节点覆盖率"""
        history = self._history if hasattr(self, "_history") else []
        if not history:
            return {"total_invalidations": 0}
        total = len(history)
        successful = sum(1 for h in history if h.get("status") == "success")
        failed = total - successful
        latencies = [h.get("propagation_ms", 0) for h in history if h.get("propagation_ms")]
        avg_latency = sum(latencies) / max(len(latencies), 1)
        node_counts = [h.get("nodes_affected", 0) for h in history if h.get("nodes_affected")]
        avg_nodes = sum(node_counts) / max(len(node_counts), 1)
        return {
            "total_invalidations": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / max(total, 1), 4),
            "avg_propagation_ms": round(avg_latency, 2),
            "avg_nodes_affected": round(avg_nodes, 1),
        }

module_class = CDNInvalidateManager
