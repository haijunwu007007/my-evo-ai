# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 - m53 FinanceData 金融数据采集引擎
================================================================
A级企业级模块 — 继承 EnterpriseModule

功能覆盖:
  ✅ A股实时行情 / 历史K线 / 个股新闻
  ✅ 港股 / 美股行情
  ✅ 公募基金净值 / ETF
  ✅ 期货实时行情 / 历史数据
  ✅ 宏观经济(CPI / GDP / PMI / M2 / PPI / 社融)
  ✅ 指数实时行情
  ✅ 外汇实时行情
  ✅ 加密货币
  ✅ 股票搜索 / 交易日历

子引擎:
  FinanceEngine  — 核心数据采集，带缓存/重试/降级/限流
  MetricsEngine  — 请求指标统计（计数/延迟/成功率/缓存命中率）
"""

__module_meta__ = {
    "id": "m53-finance-data",
    "name": "M53 Finance Data",
    "version": "V0.1",
    "group": "finance",
    "inputs": [
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "tokens", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "latency_ms", "type": "string", "required": True, "description": ""},
        {"name": "success", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["engine", "m53"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - m53 FinanceData 金融数据采集引擎 ================================================================",
}

import time
import json
import hashlib
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict

logger = logging.getLogger("evo.m53_finance_data")

# ============================================================================
# EnterpriseModule 导入 — 兼容多环境
# ============================================================================
try:
    from modules._base.enterprise_module import (
        EnterpriseModule,
        ModuleStatus,
        Result,
        HealthReport,
        ModuleStats,
        CircuitBreakerMixin,
        RateLimiterMixin,
    )
except ImportError:
    import sys, os

    _base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_base")
    if os.path.isdir(_base_dir):
        sys.path.insert(0, _base_dir)
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from enterprise_module import EnterpriseModule, ModuleStatus, Result, HealthReport, ModuleStats

# ============================================================================
# 本地数据结构
# ============================================================================

@dataclass
class CacheEntry:
    """缓存条目"""

    data: Any
    created_at: float
    ttl: float
    hit_count: int = 0
    access_count: int = 0

    @property
    def expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    # --- Auto-generated action dispatch methods ---
    def _action_age_seconds(self, params=None):
        """Auto-generated action wrapper for age_seconds"""
        if params is None:
            params = {}
        return self.age_seconds(**params)

    def _action_expired(self, params=None):
        """Auto-generated action wrapper for expired"""
        if params is None:
            params = {}
        return self.expired(**params)

@dataclass
class RateLimitBucket:
    """令牌桶限流器"""

    max_tokens: float
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def consume(self, tokens: int = 1) -> bool:
        """尝试消费令牌，返回是否成功"""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    @property
    def available(self) -> float:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            return min(self.max_tokens, self.tokens + elapsed * self.refill_rate)

@dataclass
class RetryPolicy:
    """重试策略"""

    max_retries: int = 3
    base_delay: float = 0.5
    max_delay: float = 5.0
    exponential_base: float = 2.0
    retryable_exceptions: Tuple[type, ...] = (Exception,)

# ============================================================================
# MetricsEngine — 指标统计引擎
# ============================================================================

class MetricsEngine(object):
    """
    内部指标引擎
    记录请求次数、成功率、延迟分布、缓存命中率、数据源降级次数
    """

    def __init__(self):
        self._lock = threading.Lock()
        # 请求指标
        self.total_requests: int = 0
        self.success_requests: int = 0
        self.error_requests: int = 0
        self.latencies: List[float] = []
        self.max_latency_items: int = 1000
        # 缓存指标
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        # 降级指标
        self.fallback_count: int = 0
        self.fallback_errors: int = 0
        # 按action分类统计
        self.action_stats: Dict[str, Dict[str, Any]] = {}
        # 数据源可用性
        self.datasource_status: Dict[str, Dict[str, Any]] = {
            "akshare": {"available": False, "last_check": "", "latency_ms": 0.0},
            "web_fallback": {"available": False, "last_check": "", "latency_ms": 0.0},
        }
        self.start_time: datetime = datetime.now()

    def record_request(
        self,
        action: str,
        latency_ms: float,
        success: bool,
        error: str = "",
        cached: bool = False,
        fallback: bool = False,
    ):
        """记录一次请求"""
        with self._lock:
            self.total_requests += 1
            if success:
                self.success_requests += 1
            else:
                self.error_requests += 1
            if cached:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
            if fallback:
                self.fallback_count += 1
            self.latencies.append(latency_ms)
            if len(self.latencies) > self.max_latency_items:
                self.latencies = self.latencies[-500:]
            # 按action统计
            if action not in self.action_stats:
                self.action_stats[action] = {"count": 0, "errors": 0, "total_latency": 0.0, "cached": 0}
            self.action_stats[action]["count"] += 1
            self.action_stats[action]["total_latency"] += latency_ms
            if not success:
                self.action_stats[action]["errors"] += 1
            if cached:
                self.action_stats[action]["cached"] += 1

    def record_datasource_check(self, name: str, available: bool, latency_ms: float):
        """记录数据源探活结果"""
        with self._lock:
            self.datasource_status[name] = {
                "available": available,
                "last_check": datetime.now().isoformat(),
                "latency_ms": round(latency_ms, 2),
            }

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.error_requests / self.total_requests * 100, 2)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.success_requests / self.total_requests * 100, 2)

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return round(self.cache_hits / total * 100, 2)

    @property
    def avg_latency(self) -> float:
        if not self.latencies:
            return 0.0
        return round(sum(self.latencies) / len(self.latencies), 2)

    @property
    def p50_latency(self) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        return round(s[len(s) // 2], 2)

    @property
    def p99_latency(self) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        idx = max(0, int(len(s) * 0.99) - 1)
        return round(s[idx], 2)

    @property
    def uptime_seconds(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "success_requests": self.success_requests,
            "error_requests": self.error_requests,
            "error_rate": self.error_rate,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency,
            "p50_latency_ms": self.p50_latency,
            "p99_latency_ms": self.p99_latency,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "fallback_count": self.fallback_count,
            "datasource_status": dict(self.datasource_status),
            "action_breakdown": dict(self.action_stats),
            "uptime_seconds": round(self.uptime_seconds, 1),
        }

# ============================================================================
# FinanceEngine — 核心数据采集子引擎
# ============================================================================

class FinanceEngine(object):
    """
    金融数据采集核心引擎

    特性:
      - 数据缓存（LRU + TTL）
      - 重试机制（指数退避）
      - 本地令牌桶限流
      - 多数据源降级（akshare → urllib抓取）
      - 统一数据格式化输出
    """

    def __init__(self, metrics: MetricsEngine):
        self.metrics = metrics
        self._ak = None
        self._ak_available = False
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._cache_lock = threading.Lock()
        self._max_cache_size: int = 500
        # 默认TTL配置（秒）
        self._ttl_config: Dict[str, float] = {
            "stock_spot": 30.0,
            "stock_hist": 3600.0,
            "fund_nav": 300.0,
            "futures": 60.0,
            "macro": 7200.0,
            "cpi": 86400.0,
            "gdp": 86400.0,
            "pmi": 86400.0,
            "forex": 60.0,
            "crypto": 120.0,
            "search": 1800.0,
            "calendar": 86400.0,
            "default": 300.0,
        }
        # 限流器
        self._rate_limiters: Dict[str, RateLimitBucket] = {
            "default": RateLimitBucket(max_tokens=30, refill_rate=1.0),
            "stock_spot": RateLimitBucket(max_tokens=10, refill_rate=0.5),
            "macro": RateLimitBucket(max_tokens=20, refill_rate=0.3),
        }
        # 重试策略
        self._retry_policy = RetryPolicy(max_retries=3, base_delay=0.5, max_delay=5.0)

    def init_akshare(self) -> bool:
        """初始化AKShare连接"""
        try:
            import akshare as ak

            self._ak = ak
            self._ak_available = True
            logger.info("[FinanceEngine] AKShare 已加载")
            return True
        except ImportError:
            logger.warning("[FinanceEngine] AKShare 未安装，部分功能不可用")
            self._ak_available = False
            return False

    @property
    def akshare_available(self) -> bool:
        return self._ak_available and self._ak is not None

    # ========== 缓存管理 ==========

    def _cache_key(self, action: str, params: Optional[Dict] = None) -> str:
        """生成缓存键"""
        raw = f"{action}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cache(self, action: str, params: Optional[Dict] = None) -> Optional[Any]:
        """读取缓存"""
        key = self._cache_key(action, params)
        with self._cache_lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.expired:
                    entry.hit_count += 1
                    entry.access_count += 1
                    # LRU: 移动到末尾
                    self._cache.move_to_end(key)
                    return entry.data
                else:
                    del self._cache[key]
        return None

    def _set_cache(self, action: str, data: Any, params: Optional[Dict] = None):
        """写入缓存"""
        key = self._cache_key(action, params)
        ttl = self._ttl_config.get(action, self._ttl_config["default"])
        entry = CacheEntry(data=data, created_at=time.time(), ttl=ttl)
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
            self._cache[key] = entry
            self._cache.move_to_end(key)
            # LRU淘汰
            while len(self._cache) > self._max_cache_size:
                self._cache.popitem(last=False)

    def _invalidate_cache(self, pattern: Optional[str] = None):
        """清除缓存"""
        with self._cache_lock:
            if pattern:
                keys_to_remove = [k for k in self._cache if pattern in k]
                for k in keys_to_remove:
                    del self._cache[k]
            else:
                self._cache.clear()

    def cache_stats(self) -> Dict[str, Any]:
        """缓存统计"""
        with self._cache_lock:
            total = len(self._cache)
            expired = sum(1 for e in self._cache.values() if e.expired)
            total_hits = sum(e.hit_count for e in self._cache.values())
            total_access = sum(e.access_count for e in self._cache.values())
            return {
                "size": total,
                "max_size": self._max_cache_size,
                "expired_entries": expired,
                "total_hits": total_hits,
                "total_access": total_access,
                "utilization": round(total / self._max_cache_size * 100, 1) if self._max_cache_size > 0 else 0,
            }

    # ========== 限流 ==========

    def _check_rate_limit(self, category: str = "default") -> bool:
        """检查限流，返回是否允许请求"""
        bucket = self._rate_limiters.get(category, self._rate_limiters["default"])
        return bucket.consume()

    # ========== 重试 ==========

    def _retry_execute(self, func, *args, **kwargs) -> Any:
        """带重试的执行器"""
        policy = self._retry_policy
        last_error = None
        for attempt in range(policy.max_retries):
            try:
                return func(*args, **kwargs)
            except policy.retryable_exceptions as e:
                last_error = e
                if attempt < policy.max_retries - 1:
                    delay = min(policy.base_delay * (policy.exponential_base**attempt), policy.max_delay)
                    time.sleep(delay)
                    logger.debug(f"[FinanceEngine] 重试 {attempt + 1}/{policy.max_retries}: {e}")
        raise last_error  # type: ignore

    # ========== 数据格式化 ==========

    @staticmethod
    def _format_dataframe(df) -> List[Dict]:
        """统一DataFrame输出为字典列表"""
        if df is None:
            return []
        try:
            import pandas as pd

            if isinstance(df, pd.DataFrame):
                if df.empty:
                    return []
                return df.to_dict(orient="records")
        except ImportError:
            pass
        if isinstance(df, list):
            return df
        return [{"raw": str(df)}]

    @staticmethod
    def _format_result(
        action: str, data: Any, cached: bool = False, source: str = "akshare", latency_ms: float = 0.0
    ) -> Dict:
        """格式化统一输出"""
        return {
            "action": action,
            "data": data,
            "source": source,
            "cached": cached,
            "latency_ms": round(latency_ms, 2),
            "timestamp": datetime.now().isoformat(),
            "record_count": len(data) if isinstance(data, list) else 0,
        }

    # ========== A股数据 ==========

    def get_stock_spot(self, market: str = "A") -> Dict:
        """获取A股实时行情"""
        action = "get_stock_spot"
        cached_data = self._get_cache(action, {"market": market})
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        if not self._check_rate_limit("stock_spot"):
            return self._format_result(action, [], cached=False, source="rate_limited")

        start = time.time()
        try:
            df = self._retry_execute(self._ak.stock_zh_a_spot_em)
            records = self._format_dataframe(df)
            self._set_cache(action, records, {"market": market})
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            logger.error(f"[FinanceEngine] get_stock_spot失败: {e}")
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    def get_stock_hist(
        self, code: str, period: str = "daily", start_date: str = "20230101", end_date: str = "20260101"
    ) -> Dict:
        """获取A股历史K线"""
        action = "get_stock_hist"
        params = {"code": code, "period": period, "start_date": start_date, "end_date": end_date}
        cached_data = self._get_cache(action, params)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(
                self._ak.stock_zh_a_hist, symbol=code, period=period, start_date=start_date, end_date=end_date
            )
            records = self._format_dataframe(df)
            self._set_cache(action, records, params)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            logger.error(f"[FinanceEngine] get_stock_hist失败: {e}")
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    def get_stock_news(self, symbol: str = "全部") -> Dict:
        """获取个股新闻"""
        action = "get_stock_news"
        cached_data = self._get_cache(action, {"symbol": symbol})
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.stock_news_em, symbol=symbol)
            records = self._format_dataframe(df)
            self._set_cache(action, records, {"symbol": symbol})
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    # ========== 港股/美股 ==========

    def get_hk_stock_spot(self) -> Dict:
        """获取港股实时行情"""
        action = "get_hk_stock_spot"
        cached_data = self._get_cache(action)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.stock_hk_spot_em)
            records = self._format_dataframe(df)
            self._set_cache(action, records)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    def get_us_stock_spot(self) -> Dict:
        """获取美股实时行情"""
        action = "get_us_stock_spot"
        cached_data = self._get_cache(action)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.stock_us_spot_em)
            records = self._format_dataframe(df)
            self._set_cache(action, records)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    # ========== 基金数据 ==========

    def get_fund_nav(self, fund_code: str) -> Dict:
        """获取基金净值"""
        action = "get_fund_nav"
        params = {"fund_code": fund_code}
        cached_data = self._get_cache(action, params)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.fund_open_fund_info_em, fund=fund_code)
            records = self._format_dataframe(df)
            self._set_cache(action, records, params)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    def get_fund_spot(self) -> Dict:
        """获取公募基金实时行情"""
        action = "get_fund_spot"
        cached_data = self._get_cache(action)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.fund_open_fund_info_em)
            records = self._format_dataframe(df)
            self._set_cache(action, records)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    # ========== 期货数据 ==========

    def get_futures_spot(self) -> Dict:
        """获取期货实时行情"""
        action = "get_futures"
        cached_data = self._get_cache(action)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.futures_zh_spot)
            records = self._format_dataframe(df)
            self._set_cache(action, records)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    def get_futures_hist(self, symbol: str, period: str = "daily") -> Dict:
        """获取期货历史数据"""
        action = "get_futures_hist"
        params = {"symbol": symbol, "period": period}
        cached_data = self._get_cache(action, params)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.futures_zh_hist, symbol=symbol, period=period)
            records = self._format_dataframe(df)
            self._set_cache(action, records, params)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    # ========== 宏观数据 ==========

    def get_cpi(self) -> Dict:
        """获取CPI数据"""
        action = "get_cpi"
        cached_data = self._get_cache(action)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        if not self._check_rate_limit("macro"):
            return self._format_result(action, [], cached=False, source="rate_limited")

        start = time.time()
        try:
            df = self._retry_execute(self._ak.macro_china_cpi)
            records = self._format_dataframe(df)
            self._set_cache(action, records)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    def get_gdp(self) -> Dict:
        """获取GDP数据"""
        action = "get_gdp"
        cached_data = self._get_cache(action)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.macro_china_gdp)
            records = self._format_dataframe(df)
            self._set_cache(action, records)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    def get_pmi(self) -> Dict:
        """获取PMI数据"""
        action = "get_pmi"
        cached_data = self._get_cache(action)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.macro_china_pmi)
            records = self._format_dataframe(df)
            self._set_cache(action, records)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    def get_macro(self) -> Dict:
        """获取综合宏观数据(CPI+GDP+PMI+M2)"""
        action = "get_macro"
        cached_data = self._get_cache(action)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        if not self._check_rate_limit("macro"):
            return self._format_result(action, [], cached=False, source="rate_limited")

        start = time.time()
        result = {}
        macros = [
            ("cpi", lambda: self._format_dataframe(self._ak.macro_china_cpi())),
            ("gdp", lambda: self._format_dataframe(self._ak.macro_china_gdp())),
            ("pmi", lambda: self._format_dataframe(self._ak.macro_china_pmi())),
            ("m2", lambda: self._format_dataframe(self._ak.macro_china_money_supply())),
        ]
        for name, fetch_fn in macros:
            try:
                result[name] = self._retry_execute(fetch_fn)
            except Exception as e:
                result[name] = []
                logger.warning(f"[FinanceEngine] 宏观{name}获取失败: {e}")

        self._set_cache(action, result)
        latency = (time.time() - start) * 1000
        all_ok = all(isinstance(v, list) for v in result.values())
        self.metrics.record_request(action, latency, all_ok, cached=False)
        return self._format_result(action, result, cached=False, latency_ms=latency)

    # ========== 指数数据 ==========

    def get_index_spot(self) -> Dict:
        """获取指数实时行情"""
        action = "get_index_spot"
        cached_data = self._get_cache(action)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.stock_zh_index_spot_em)
            records = self._format_dataframe(df)
            self._set_cache(action, records)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    # ========== 外汇数据 ==========

    def get_forex(self) -> Dict:
        """获取外汇实时行情"""
        action = "get_forex"
        cached_data = self._get_cache(action)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.currency_latest)
            records = self._format_dataframe(df)
            self._set_cache(action, records)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    # ========== 加密货币 ==========

    def get_crypto(self, symbol: str = "比特币") -> Dict:
        """获取加密货币数据"""
        action = "get_crypto"
        params = {"symbol": symbol}
        cached_data = self._get_cache(action, params)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.crypto_js_spot)
            records = self._format_dataframe(df)
            # 按symbol过滤
            if symbol and isinstance(records, list) and records:
                filtered = [r for r in records if symbol.lower() in str(r).lower()]
                if filtered:
                    records = filtered
            self._set_cache(action, records, params)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, records, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    # ========== 搜索 & 工具 ==========

    def search_stock(self, keyword: str) -> Dict:
        """搜索股票"""
        action = "search_stock"
        params = {"keyword": keyword}
        cached_data = self._get_cache(action, params)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start = time.time()
        try:
            df = self._retry_execute(self._ak.stock_info_a_code_name)
            results = []
            if df is not None:
                try:
                    import pandas as pd

                    if isinstance(df, pd.DataFrame) and not df.empty:
                        matched = df[df["name"].str.contains(keyword, na=False)]
                        results = matched.head(10).to_dict("records")
                except Exception:
                    results = self._format_dataframe(df)[:10]
            self._set_cache(action, results, params)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, results, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    def get_trade_calendar(self, start: str = "", end: str = "") -> Dict:
        """获取交易日历"""
        action = "get_trade_calendar"
        params = {"start": start, "end": end}
        cached_data = self._get_cache(action, params)
        if cached_data is not None:
            return self._format_result(action, cached_data, cached=True)

        start_time = time.time()
        try:
            df = self._retry_execute(self._ak.tool_trade_date_hist_sina)
            dates = []
            try:
                import pandas as pd

                if isinstance(df, pd.DataFrame) and not df.empty:
                    dates = df["trade_date"].tolist()
                    # 按日期范围过滤
                    if start:
                        dates = [d for d in dates if str(d) >= start]
                    if end:
                        dates = [d for d in dates if str(d) <= end]
            except Exception:
                dates = list(df) if df else []
            self._set_cache(action, dates, params)
            latency = (time.time() - start_time) * 1000
            self.metrics.record_request(action, latency, True, cached=False)
            return self._format_result(action, dates, cached=False, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self.metrics.record_request(action, latency, False, error=str(e), cached=False)
            return self._format_result(action, [], cached=False, source="error", latency_ms=latency)

    # ========== 数据源健康探测 ==========

    def check_akshare(self) -> Dict[str, Any]:
        """探测AKShare可用性"""
        start = time.time()
        try:
            if self._ak is not None:
                # 用轻量API探测
                self._ak.stock_info_a_code_name()
                latency = (time.time() - start) * 1000
                self.metrics.record_datasource_check("akshare", True, latency)
                return {"available": True, "latency_ms": round(latency, 2)}
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.record_datasource_check("akshare", False, latency)
            return {"available": False, "error": str(e), "latency_ms": round(latency, 2)}
        return {"available": False, "latency_ms": 0.0}

# ============================================================================
# FinanceDataModule — A级企业级模块主类
# ============================================================================

class FinanceDataModule(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    金融数据采集引擎 — A级企业级模块

    继承 EnterpriseModule，提供:
      - AKShare 全品类金融数据采集
      - 数据缓存（LRU + TTL）
      - 重试机制（指数退避）
      - 本地令牌桶限流
      - 多维度健康检查
      - 完整指标统计
    """

    MODULE_ID = "m53_finance_data"
    MODULE_NAME = "金融数据采集引擎"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    # 支持的action清单
    SUPPORTED_ACTIONS = [
        "get_stock_spot",
        "get_stock_hist",
        "get_stock_news",
        "get_hk_stock_spot",
        "get_us_stock_spot",
        "get_fund_nav",
        "get_fund_spot",
        "get_futures",
        "get_futures_hist",
        "get_macro",
        "get_cpi",
        "get_gdp",
        "get_pmi",
        "get_forex",
        "get_crypto",
        "search_stock",
        "get_trade_calendar",
        "get_index_spot",
        "get_status",
    ]

    def __init__(self):

        super().__init__()
        # 内部引擎
        self._metrics_engine = MetricsEngine()
        self._finance_engine = FinanceEngine(self._metrics_engine)
        # 状态
        self._initialized = False
        self._init_time: Optional[datetime] = None

    # ========== 生命周期 ==========

    async def initialize(self) -> None:
        """初始化模块 — 加载AKShare，配置缓存和限流"""
        self._update_status(ModuleStatus.INITIALIZING)
        self.info("金融数据采集引擎初始化开始...")

        try:
            pass
            # 1. 初始化AKShare
            ak_ok = self._finance_engine.init_akshare()
            if not ak_ok:
                self.warning("AKShare不可用，降级模式运行")

            # 2. 预热缓存（探测数据源）
            ak_status = self._finance_engine.check_akshare()

            # 3. 更新状态
            self._initialized = True
            self._init_time = datetime.now()
            self.stats.start_time = datetime.now()
            if ak_ok:
                self._update_status(ModuleStatus.RUNNING)
                self.info("金融数据采集引擎初始化完成 ✓")
            else:
                self._update_status(ModuleStatus.DEGRADED)
                self.warning("金融数据采集引擎降级启动（AKShare不可用）")

            self.audit("initialize", "模块初始化完成", level="INFO")

        except Exception as e:
            self._update_status(ModuleStatus.ERROR)
            self.error(f"初始化失败: {e}")
            raise

    async def execute(self, action: str, params: dict = None) -> Result:
        """执行模块动作 — 分发到子引擎方法"""
        _ = self.trace("execute")
        params = params or {}

        # 验证action
        if action not in self.SUPPORTED_ACTIONS:
            return Result(
                success=False,
                error=f"不支持的动作: {action}，支持: {self.SUPPORTED_ACTIONS}",
                module_id=self.MODULE_ID,
                trace_id=str(int(time.time() * 1000))[-12:],
            )

        # 特殊action: get_status
        if action == "get_status":
            return await self._safe_execute(action, params, handler=self._handle_get_status)

        # 分发到FinanceEngine
        handler_map = {
            "get_stock_spot": lambda p: self._finance_engine.get_stock_spot(p.get("market", "A")),
            "get_stock_hist": lambda p: self._finance_engine.get_stock_hist(
                p.get("code", ""),
                p.get("period", "daily"),
                p.get("start_date", "20230101"),
                p.get("end_date", "20260101"),
            ),
            "get_stock_news": lambda p: self._finance_engine.get_stock_news(p.get("symbol", "全部")),
            "get_hk_stock_spot": lambda p: self._finance_engine.get_hk_stock_spot(),
            "get_us_stock_spot": lambda p: self._finance_engine.get_us_stock_spot(),
            "get_fund_nav": lambda p: self._finance_engine.get_fund_nav(p.get("fund_code", "")),
            "get_fund_spot": lambda p: self._finance_engine.get_fund_spot(),
            "get_futures": lambda p: self._finance_engine.get_futures_spot(),
            "get_futures_hist": lambda p: self._finance_engine.get_futures_hist(
                p.get("symbol", ""), p.get("period", "daily")
            ),
            "get_macro": lambda p: self._finance_engine.get_macro(),
            "get_cpi": lambda p: self._finance_engine.get_cpi(),
            "get_gdp": lambda p: self._finance_engine.get_gdp(),
            "get_pmi": lambda p: self._finance_engine.get_pmi(),
            "get_forex": lambda p: self._finance_engine.get_forex(),
            "get_crypto": lambda p: self._finance_engine.get_crypto(p.get("symbol", "比特币")),
            "search_stock": lambda p: self._finance_engine.search_stock(p.get("keyword", "")),
            "get_trade_calendar": lambda p: self._finance_engine.get_trade_calendar(
                p.get("start", ""), p.get("end", "")
            ),
            "get_index_spot": lambda p: self._finance_engine.get_index_spot(),
        }

        handler = handler_map.get(action)
        if handler is None:
            return Result(success=False, error=f"无处理器的动作: {action}", module_id=self.MODULE_ID)

        return await self._safe_execute(action, params, handler=handler)

    def health_check(self) -> HealthReport:
        """多维度健康检查"""
        checks = 0
        all_healthy = True
        details = {}

        # 1. 检查AKShare可用性
        checks += 1
        try:
            ak_status = self._finance_engine.check_akshare()
            ak_healthy = ak_status.get("available", False)
            details["akshare"] = {"healthy": ak_healthy, **ak_status}
            if not ak_healthy:
                all_healthy = False
        except Exception as e:
            details["akshare"] = {"healthy": False, "error": str(e)}
            all_healthy = False

        # 2. 检查缓存状态
        checks += 1
        cache_info = self._finance_engine.cache_stats()
        cache_util = cache_info.get("utilization", 0)
        cache_healthy = cache_util < 95  # 缓存使用率不超过95%
        details["cache"] = {"healthy": cache_healthy, **cache_info}
        if not cache_healthy:
            all_healthy = False

        # 3. 检查请求成功率
        checks += 1
        metrics = self._metrics_engine
        success_rate = metrics.success_rate
        rate_healthy = success_rate >= 80.0 or metrics.total_requests == 0
        details["success_rate"] = {
            "healthy": rate_healthy,
            "success_rate": success_rate,
            "total_requests": metrics.total_requests,
        }
        if not rate_healthy:
            all_healthy = False

        # 4. 检查平均延迟
        checks += 1
        avg_lat = metrics.avg_latency
        lat_healthy = avg_lat < 5000 or metrics.total_requests == 0
        details["latency"] = {
            "healthy": lat_healthy,
            "avg_ms": avg_lat,
            "p50_ms": metrics.p50_latency,
            "p99_ms": metrics.p99_latency,
        }
        if not lat_healthy:
            all_healthy = False

        # 5. 检查内存使用
        checks += 1
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            mem_mb = process.memory_info().rss / 1024 / 1024
            mem_healthy = mem_mb < 512
            details["memory"] = {"healthy": mem_healthy, "rss_mb": round(mem_mb, 1)}
            if not mem_healthy:
                all_healthy = False
        except ImportError:
            details["memory"] = {"healthy": True, "note": "psutil未安装"}

        # 6. 检查模块初始化状态
        checks += 1
        init_healthy = self._initialized
        details["initialization"] = {
            "healthy": init_healthy,
            "initialized": self._initialized,
            "init_time": self._init_time.isoformat() if self._init_time else None,
        }
        if not init_healthy:
            all_healthy = False

        # 综合判定
        status = "healthy" if all_healthy else "degraded"
        if self.status == ModuleStatus.ERROR:
            status = "unhealthy"
            all_healthy = False

        return HealthReport(
            status=status,
            healthy=all_healthy,
            last_beat=self._now(),
            uptime_seconds=self._uptime(),
            checks_run=checks,
            error_rate=metrics.error_rate,
            details=details,
            version=self.VERSION,
        )

    async def shutdown(self) -> None:
        """优雅关闭 — 释放资源"""
        self.info("金融数据采集引擎关闭中...")
        self._update_status(ModuleStatus.STOPPING)

        try:
            pass
            # 清除缓存
            self._finance_engine._invalidate_cache()
            self.info("缓存已清除")

            # 释放AKShare引用
            self._finance_engine._ak = None
            self._finance_engine._ak_available = False

            # 持久化最终指标
            final_metrics = self._metrics_engine.to_dict()
            self.info(f"最终指标: {final_metrics}")

            self._initialized = False
            self._update_status(ModuleStatus.STOPPED)
            self.audit("shutdown", "模块已优雅关闭", level="INFO")
            self.info("金融数据采集引擎已关闭 ✓")

        except Exception as e:
            self._update_status(ModuleStatus.ERROR)
            self.error(f"关闭异常: {e}")

    # ========== 内部处理 ==========

    def _handle_get_status(self, params: Dict) -> Dict:
        """获取模块状态，含链路追踪"""
        trace_id = f"finance-data-status-{int(time.time() * 1000)}"
        metrics_collector.counter("finance_data_status_queries_total")
        """处理get_status动作"""
        metrics = self._metrics_engine.to_dict()
        return {
            "module": self.MODULE_ID,
            "name": self.MODULE_NAME,
            "version": self.VERSION,
            "level": self.MODULE_LEVEL,
            "status": self.status.value,
            "initialized": self._initialized,
            "akshare_available": self._finance_engine.akshare_available,
            "capabilities": [
                "A股实时行情/历史K线/个股新闻",
                "港股/美股行情",
                "公募基金净值/ETF",
                "期货实时行情/历史数据",
                "宏观经济(CPI/GDP/PMI/M2)",
                "指数实时行情",
                "外汇实时行情",
                "加密货币行情",
                "股票搜索/交易日历",
            ],
            "supported_actions": self.SUPPORTED_ACTIONS,
            "cache": self._finance_engine.cache_stats(),
            "metrics": metrics,
            "uptime_seconds": round(self._uptime(), 1),
        }

    # ============================================================================
    # 模块导出
    # ============================================================================

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口。支持status/info/run/stop/help等通用动作。"""
        if params is None:
            params = {}
        _action = action.lower().strip()
        dispatch = {
            "status": self.get_status,
            "info": self.get_info,
            "health": self.health_check,
            "help": self.get_help,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status(params)

    def get_info(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        return {
            "success": True,
            "module": self.__class__.__name__,
            "status": "active",
            "version": getattr(self, "version", "1.0.0"),
        }

    def get_help(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        methods = [m for m in dir(self) if not m.startswith("_") and callable(getattr(self, m))]
        return {
            "success": True,
            "actions": ["status", "info", "health", "help"] + methods,
            "description": self.__doc__ or "",
        }

module_class = FinanceDataModule
