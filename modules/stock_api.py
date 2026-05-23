import time

"""
AUTO-EVO-AI - 股票数据API模块 (V0.1 真实版)
数据源: AKShare / 腾讯自选股API
功能: A股/港股/美股实时行情、K线、分钟线、财务数据、资金流向
"""

__module_meta__ = {
    "id": "stock-api",
    "name": "Stock Api",
    "version": "1.0.0",
    "group": "finance",
    "inputs": [
        {"name": "context", "type": "string", "required": True, "description": ""},
        {"name": "keyword", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "hours_a", "type": "string", "required": True, "description": ""},
        {"name": "hours_b", "type": "string", "required": True, "description": ""},
        {"name": "days", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "webhook", "config": {"path": "/hooks/stock_api", "method": "POST"}}],
    "depends_on": [],
    "tags": ["stock"],
    "grade": "C",
    "description": "AUTO-EVO-AI - 股票数据API模块 (V0.1 真实版) 数据源: AKShare / 腾讯自选股API",
}
import json, os, time, logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.stock")

__version__ = "6.37.0"

class StockApiAnalyzer(object):
    """stock_api 分析引擎 - 运营分析核心组件"""

    def __init__(self):
        self.name = "stock_api"
        self.version = "1.0.0"
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "StockApiAnalyzer",
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
        return {"total": len(self._history), "recent": len(self._history[-100:]), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        return {
            "total_records": total,
            "recent_count": min(100, total),
            "status": "healthy" if total > 0 else "no_data",
        }

    def validate_config(self) -> dict:
        return {"valid": True, "module": "stock_api"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== stock_api ===",
                f"Records: {s.get('total', 0)}",
                f"Status: {s.get('status', 'unknown')}",
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            "format": "text",
        }

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = [r for r in reversed(self._history) if keyword.lower() in str(r).lower()][:limit]
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
        return {"total": min(len(items), 50), "results": [self.analyze({"data": i}) for i in items[:50]]}

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

class StockAPI(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """股票数据API — 真实数据接口"""

    # 市场前缀映射
    MARKET_MAP = {
        "sh": "上证",
        "sz": "深证",
        "bj": "北交所",
        "hk": "港股",
        "us": "美股",
    }

    def __init__(self, data_source: str = "auto"):
        """
        Args:
            data_source: "akshare"(免费), "tencent"(腾讯), "auto"(自动选择)
        """
        super().__init__(module_id="stock_api", config={"data_source": data_source})
        self.data_source = data_source
        self._akshare = None
        self._tencent_available = False
        self._analyzer = StockApiAnalyzer()

    def _get_akshare(self):
        """延迟导入AKShare"""
        if self._akshare is None:
            import akshare as ak

            self._akshare = ak
            logger.info("[StockAPI] AKShare 已加载")
        return self._akshare

    def _get_tencent_quote(self, symbol: str) -> Optional[Dict]:
        """通过腾讯行情接口获取实时数据"""
        try:
            import urllib.request

            # 腾讯行情接口直接用 symbol 前缀 (sh/sz)
            url = f"https://qt.gtimg.cn/q={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=5)
            data = resp.read().decode("gbk", errors="replace")
            resp.close()
            fields = data.split("~")
            if len(fields) > 40:
                return {
                    "symbol": symbol,
                    "name": fields[1],
                    "price": float(fields[3]) if fields[3] else 0,
                    "change": float(fields[31]) if fields[31] else 0,
                    "change_pct": float(fields[32]) if fields[32] else 0,
                    "volume": int(fields[36]) if fields[36] else 0,
                    "amount": float(fields[37]) if fields[37] else 0,
                    "open": float(fields[5]) if fields[5] else 0,
                    "high": float(fields[33]) if fields[33] else 0,
                    "low": float(fields[34]) if fields[34] else 0,
                    "close_prev": float(fields[4]) if fields[4] else 0,
                    "timestamp": fields[30] if len(fields) > 30 else "",
                }
        except Exception as e:
            logger.warning(f"[StockAPI] 腾讯行情获取失败: {e}")
        return None

    def quote(self, symbols: List[str]) -> Dict[str, Any]:
        """
        获取实时行情（支持批量）

        Args:
            symbols: 股票代码列表，格式: sh600519, sz000001, hk00700, usAAPL
        """
        results = {}
        for sym in symbols:
            sym = sym.strip()
            if not sym:
                continue
            # 先尝试腾讯
            qt = self._get_tencent_quote(sym)
            if qt:
                results[sym] = qt
            else:
                # 降级到AKShare
                ak = self._get_akshare()
                if ak:
                    try:
                        df = ak.stock_zh_a_spot_em() if sym.startswith(("sh", "sz")) else ak.stock_hk_spot_em()
                        row = df[df["代码"] == sym.replace("sh", "").replace("sz", "")].iloc[0]
                        results[sym] = {
                            "symbol": sym,
                            "name": str(row.get("名称", "")),
                            "price": float(row.get("最新价", 0)),
                            "change": float(row.get("涨跌额", 0)),
                            "change_pct": float(row.get("涨跌幅", 0)),
                            "volume": int(row.get("成交量", 0)),
                            "amount": float(row.get("成交额", 0)),
                        }
                    except Exception as e:
                        logger.warning(f"[StockAPI] AKShare获取失败 {sym}: {e}")
                        results[sym] = {"symbol": sym, "error": str(e)}
                else:
                    results[sym] = {"symbol": sym, "error": "无可用数据源，请安装AKShare: pip install akshare"}
        return results

    def kline(self, symbol: str, period: str = "daily", count: int = 20) -> Dict[str, Any]:
        """
        获取K线数据

        Args:
            symbol: 股票代码
            period: daily/weekly/monthly/minute/5/15/30/60
            count: 数据条数
        """
        ak = self._get_akshare()
        if not ak:
            return {"success": False, "error": "AKShare未安装"}

        try:
            sym = symbol.replace("sh", "").replace("sz", "")
            period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
            df = ak.stock_zh_a_hist(symbol=sym, period=period_map.get(period, "daily"), adjust="qfq", count=count)
            records = []
            for _, row in df.iterrows():
                records.append(
                    {
                        "date": str(row.get("日期", "")),
                        "open": float(row.get("开盘", 0)),
                        "high": float(row.get("最高", 0)),
                        "low": float(row.get("最低", 0)),
                        "close": float(row.get("收盘", 0)),
                        "volume": int(row.get("成交量", 0)),
                        "amount": float(row.get("成交额", 0)),
                        "change_pct": float(row.get("涨跌幅", 0)),
                    }
                )
            return {"success": True, "symbol": symbol, "period": period, "count": len(records), "data": records}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fundamentals(self, symbol: str) -> Dict[str, Any]:
        """获取财务数据"""
        ak = self._get_akshare()
        if not ak:
            return {"success": False, "error": "AKShare未安装"}
        try:
            sym = symbol.replace("sh", "").replace("sz", "")
            df = ak.stock_financial_analysis_indicator(symbol=sym)
            latest = df.iloc[0]
            return {
                "success": True,
                "symbol": symbol,
                "roe": float(latest.get("净资产收益率(%)", 0) or 0),
                "eps": float(latest.get("基本每股收益", 0) or 0),
                "bvps": float(latest.get("每股净资产", 0) or 0),
                "pe": float(latest.get("市盈率", 0) or 0),
                "pb": float(latest.get("市净率", 0) or 0),
                "report_date": str(latest.get("日期", "")),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def capital_flow(self, symbol: str) -> Dict[str, Any]:
        """获取资金流向"""
        ak = self._get_akshare()
        if not ak:
            return {"success": False, "error": "AKShare未安装"}
        try:
            sym = symbol.replace("sh", "").replace("sz", "")
            df = ak.stock_individual_fund_flow(stock=sym, market="sh")
            if df is not None and len(df) > 0:
                row = df.iloc[0]
                return {
                    "success": True,
                    "symbol": symbol,
                    "的主力净流入": float(str(row.get("主力净流入-净额", "0")).replace(",", "")),
                    "超大单净流入": float(str(row.get("超大单净流入-净额", "0")).replace(",", "")),
                    "大单净流入": float(str(row.get("大单净流入-净额", "0")).replace(",", "")),
                    "中单净流入": float(str(row.get("中单净流入-净额", "0")).replace(",", "")),
                    "小单净流入": float(str(row.get("小单净流入-净额", "0")).replace(",", "")),
                }
        except Exception as e:
            pass
        return {"success": False, "error": str(e) if str(e) else "数据不可用"}

    def batch_quote(self, symbols: List[str]) -> Dict[str, Any]:
        """批量行情（主要接口）"""
        return self.quote(symbols)

    def search(self, keyword: str) -> Dict[str, Any]:
        """搜索股票"""
        ak = self._get_akshare()
        if not ak:
            return {"success": False, "error": "AKShare未安装"}
        try:
            df = ak.stock_info_a_code_name()
            results = df[df["name"].str.contains(keyword, na=False) | df["code"].str.contains(keyword, na=False)]
            return {
                "success": True,
                "results": [{"code": r["code"], "name": r["name"]} for _, r in results.head(10).iterrows()],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_market_summary(self) -> Dict[str, Any]:
        """市场概况（上证/深证/创业板/科创板）"""
        # 先尝试腾讯行情（无需安装）
        tencent_result = {}
        for code, prefix in [("000001", "sh"), ("399001", "sz"), ("399006", "sz"), ("000688", "sh")]:
            qt = self._get_tencent_quote(f"{prefix}{code}")
            if qt:
                tencent_result[code] = qt
        if len(tencent_result) >= 2:
            return {"success": True, "data": tencent_result, "source": "tencent"}
        # 降级AKShare
        ak = self._get_akshare()
        if not ak:
            return {"success": False, "error": "无可用数据源，请安装AKShare: pip install akshare"}
        try:
            df = ak.stock_zh_index_spot_em()
            summary = {}
            for _, row in df.iterrows():
                code = str(row.get("代码", ""))
                if code in ("000001", "399001", "399006", "000688"):
                    summary[code] = {
                        "name": row.get("名称", ""),
                        "price": float(row.get("最新价", 0)),
                        "change": float(row.get("涨跌额", 0)),
                        "change_pct": float(row.get("涨跌幅", 0)),
                        "volume": int(row.get("成交量", 0)),
                    }
            return {"success": True, "data": summary, "source": "akshare"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("stock_api.execute", "start", action=action)
        self.metrics_collector.counter("stock_api.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "help":
                result = {
                    "actions": ["quote", "kline", "fundamentals", "capital_flow", "search", "market_summary", "status"],
                    "module": "stock_api",
                }
            elif action in ("quote", "行情", "报价"):
                symbols = params.get("symbols", params.get("symbol", ""))
                if isinstance(symbols, str):
                    symbols = [s.strip() for s in symbols.replace("，", ",").split(",") if s.strip()]
                result = self.quote(symbols)
            elif action in ("kline", "k线", "k"):
                symbol = params.get("symbol", params.get("code", ""))
                period = params.get("period", "daily")
                count = int(params.get("count", 20))
                result = self.kline(symbol, period, count)
            elif action in ("fundamentals", "基本面", "财务"):
                symbol = params.get("symbol", params.get("code", ""))
                result = self.fundamentals(symbol)
            elif action in ("capital_flow", "资金流向", "资金"):
                symbol = params.get("symbol", params.get("code", ""))
                result = self.capital_flow(symbol)
            elif action in ("search", "搜索", "查找"):
                keyword = params.get("keyword", params.get("q", action))
                result = self.search(keyword)
            elif action in ("market_summary", "市场概况", "大盘", "指数"):
                result = self.get_market_summary()
            elif action in ("batch_quote", "批量行情"):
                symbols = params.get("symbols", [])
                result = self.batch_quote(symbols)
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "batch_analyze":
                result = self._analyze_batch_1(params)
            else:
                # 尝试解析自然语言: "上证指数今天收盘价" → market_summary
                if any(kw in action for kw in ["上证", "深证", "指数", "大盘", "收盘", "开盘", "涨停", "跌停", "行情"]):
                    result = self.get_market_summary()
                elif any(kw in action for kw in ["资金", "流向", "净流入"]):
                    symbol = params.get("symbol", params.get("code", "sh600519"))
                    result = self.capital_flow(symbol)
                else:
                    # 尝试当symbol搜索
                    result = self.search(action)
            self.metrics_collector.counter("stock_api.execute.success", 1)
            self.trace("stock_api.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("stock_api.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "stock_api"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "stock_api", "version": __version__, "data_source": self.data_source}

    def initialize(self) -> dict:
        self.trace("stock_api.initialize", "start")
        self.metrics_collector.gauge("stock_api.initialized", 1)
        self.audit("初始化stock_api", level="info")
        # 检测数据源可用性
        try:
            self._tencent_available = self._get_tencent_quote("sh000001") is not None
        except Exception:
            self._tencent_available = False
        self.trace("stock_api.initialize", "end")
        return {"success": True, "module": "stock_api", "tencent": self._tencent_available}

    def _analyze_batch_1(self, data: dict = None) -> dict:
        """批量分析操作 - 处理分组1的数据聚合和统计分析"""
        self.trace("stock_api._analyze_batch_1", "start")
        items = (data or {}).get("items", [])
        results = []
        for item in items[:50]:
            entry = {
                "id": item.get("id", ""),
                "status": "processed",
                "score": round(item.get("value", 0) * 1.0, 2),
                "group": 1,
                "timestamp": None,
            }
            results.append(entry)
        self.metrics_collector.counter("stock_api._analyze_batch_1", len(results))
        self.metrics_collector.counter("stock_api._analyze_batch_1.items_total", len(items))
        self.audit(
            "batch_analyze",
            {
                "module": "stock_api",
                "operation": "_analyze_batch_1",
                "input_count": len(items),
                "output_count": len(results),
            },
        )
        self.trace("stock_api._analyze_batch_1", "end")
        return {"success": True, "results": results, "count": len(results)}

def get_stock_api() -> StockAPI:
    return StockAPI()

module_class = StockAPI
