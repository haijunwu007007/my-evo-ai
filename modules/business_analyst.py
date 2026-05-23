"""
AUTO-EVO-AI V0.1 — 商业分析师模块
Grade: A (生产级) | Category: 智能分析
职责：商业智能分析、KPI追踪、营收预测、市场趋势分析、竞争情报、经营决策支持
"""

__module_meta__ = {
    "id": "business-analyst",
    "name": "Business Analyst",
    "version": "1.0.0",
    "group": "business",
    "inputs": [
        {"name": "metric_name", "type": "string", "required": True, "description": ""},
        {"name": "values", "type": "string", "required": True, "description": ""},
        {"name": "labels", "type": "string", "required": True, "description": ""},
        {"name": "current", "type": "string", "required": True, "description": ""},
        {"name": "previous_period", "type": "string", "required": True, "description": ""},
        {"name": "year_ago", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "event", "config": {"on": "business_analyst.trigger"}}],
    "depends_on": [],
    "tags": ["manager", "business"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 商业分析师模块 Grade: A (生产级) | Category: 智能分析",
}

import os
import asyncio
import time
import logging
import uuid
import math
import statistics
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger("business_analyst")

class AnalysisType(Enum):
    REVENUE = "revenue"
    PROFIT = "profit"
    GROWTH = "growth"
    MARKET_SHARE = "market_share"
    CUSTOMER = "customer"
    COMPETITIVE = "competitive"
    TREND = "trend"
    FORECAST = "forecast"

class InsightSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    POSITIVE = "positive"

@dataclass
class KPIDefinition:
    """KPI定义"""

    kpi_id: str
    name: str
    unit: str
    target: float
    warning_threshold: float
    critical_threshold: float
    direction: str = "higher"  # higher=越高越好, lower=越低越好
    category: str = "general"

@dataclass
class KPIDataPoint:
    """KPI数据点"""

    timestamp: datetime
    value: float
    dimension: str = "default"

@dataclass
class KPIStatus:
    """KPI状态"""

    kpi_id: str
    current_value: float
    target: float
    attainment: float  # 目标达成率
    trend: str  # up/down/stable
    change_pct: float
    status: str  # on_track/at_risk/critical/exceeded

@dataclass
class ForecastModel:
    """预测模型"""

    model_id: str
    name: str
    model_type: str  # linear/exponential/moving_avg/regression
    parameters: Dict[str, Any] = field(default_factory=dict)
    accuracy_score: float = 0.0

@dataclass
class ForecastResult:
    """预测结果"""

    forecast_id: str
    model_id: str
    metric_name: str
    predictions: List[Dict[str, Any]]  # [{date, value, confidence_low, confidence_high}]
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Insight:
    """洞察"""

    insight_id: str
    title: str
    description: str
    severity: InsightSeverity
    category: str
    metric: str
    action_items: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

class KPITrendAnalyzer(object):
    """KPI趋势分析引擎 — 多维度趋势分析、异常检测、同比环比计算"""

    def __init__(self):
        self._kpi_history: Dict[str, List[Dict[str, Any]]] = {}

    def analyze_trend(self, metric_name: str, values: List[float], labels: List[str] = None) -> Dict[str, Any]:
        """分析指标趋势，识别上升/下降/平稳"""
        n = len(values)
        if n < 2:
            return {"metric": metric_name, "trend": "insufficient_data", "confidence": 0}

        mean_val = sum(values) / n
        std_val = (sum((x - mean_val) ** 2 for x in values) / max(n - 1, 1)) ** 0.5
        cv = std_val / mean_val if mean_val != 0 else 0

        first_third = values[: n // 3]
        last_third = values[-(n // 3) :]
        first_mean = sum(first_third) / len(first_third)
        last_mean = sum(last_third) / len(last_third)

        change_pct = ((last_mean - first_mean) / first_mean * 100) if first_mean != 0 else 0
        if change_pct > 5:
            trend = "rising"
        elif change_pct < -5:
            trend = "declining"
        else:
            trend = "stable"

        volatility = "high" if cv > 0.3 else "medium" if cv > 0.1 else "low"

        return {
            "metric": metric_name,
            "trend": trend,
            "change_pct": round(change_pct, 2),
            "mean": round(mean_val, 4),
            "std": round(std_val, 4),
            "cv": round(cv, 4),
            "volatility": volatility,
            "data_points": n,
            "latest": round(values[-1], 4) if values else None,
        }

    def compute_yoy_qoq(self, current: float, previous_period: float, year_ago: float) -> Dict[str, Any]:
        """计算同比和环比变化"""
        qoq = ((current - previous_period) / previous_period * 100) if previous_period != 0 else None
        yoy = ((current - year_ago) / year_ago * 100) if year_ago != 0 else None

        momentum = "accelerating"
        if yoy is not None and qoq is not None:
            if qoq > yoy:
                momentum = "accelerating"
            elif qoq < yoy:
                momentum = "decelerating"
            else:
                momentum = "steady"

        return {
            "current": current,
            "previous_period": previous_period,
            "year_ago": year_ago,
            "qoq_pct": round(qoq, 2) if qoq is not None else None,
            "yoy_pct": round(yoy, 2) if yoy is not None else None,
            "momentum": momentum,
        }

    def detect_anomalies(self, values: List[float], threshold: float = 2.0) -> List[Dict[str, Any]]:
        """使用统计方法检测异常数据点"""
        if len(values) < 5:
            return []
        n = len(values)
        mean_val = sum(values) / n
        std_val = (sum((x - mean_val) ** 2 for x in values) / max(n - 1, 1)) ** 0.5
        if std_val == 0:
            return []

        anomalies = []
        for i, v in enumerate(values):
            z_score = (v - mean_val) / std_val
            if abs(z_score) > threshold:
                anomalies.append(
                    {
                        "index": i,
                        "value": round(v, 4),
                        "z_score": round(z_score, 2),
                        "direction": "above" if z_score > 0 else "below",
                        "severity": "high" if abs(z_score) > 3 else "medium",
                    }
                )
        return anomalies

    def generate_summary(self, metrics: Dict[str, List[float]]) -> Dict[str, Any]:
        """生成多指标综合分析摘要"""
        summary = {"total_metrics": len(metrics), "improving": [], "declining": [], "stable": []}
        for name, vals in metrics.items():
            analysis = self.analyze_trend(name, vals)
            bucket = summary.get(
                analysis["trend"] + "ing" if analysis["trend"] != "stable" else "stable", summary["stable"]
            )
            bucket.append({"metric": name, "change_pct": analysis["change_pct"]})

        summary["improving_count"] = len(summary["improving"])
        summary["declining_count"] = len(summary["declining"])
        summary["stable_count"] = len(summary["stable"])
        summary["health"] = "healthy" if summary["declining_count"] <= len(metrics) * 0.2 else "attention"
        return summary

class BusinessAnalystManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """商业分析师 — 提供全面的商业智能分析和决策支持"""

    def __init__(self):

        super().__init__()
        self.module_name = "business_analyst"
        self.module_id = self.module_name
        self.module_version = "1.0.0"
        self._initialized = False

        # KPI管理
        self._kpi_definitions: Dict[str, KPIDefinition] = {}
        self._kpi_history: Dict[str, List[KPIDataPoint]] = defaultdict(list)

        # 预测模型
        self._forecast_models: Dict[str, ForecastModel] = {}
        self._forecast_history: Dict[str, List[ForecastResult]] = defaultdict(list)

        # 洞察库
        self._insights: List[Insight] = []
        self._insight_counter = 0

        # 市场数据
        self._market_data: Dict[str, List[Dict]] = defaultdict(list)
        self._competitors: Dict[str, Dict] = {}

        # 分析统计
        self._total_analyses = 0
        self._total_forecasts = 0

        self._init_default_kpis()
        self._init_default_models()

    def _init_default_kpis(self):
        """初始化默认KPI定义"""
        defaults = [
            KPIDefinition("monthly_revenue", "月营收", "万元", 5000, 0.7, 0.5),
            KPIDefinition("gross_margin", "毛利率", "%", 45.0, 0.8, 0.6, "higher", "finance"),
            KPIDefinition("net_profit_margin", "净利润率", "%", 15.0, 0.8, 0.6, "higher", "finance"),
            KPIDefinition("customer_acquisition_cost", "获客成本", "元", 200, 0.5, 0.3, "lower", "marketing"),
            KPIDefinition("customer_lifetime_value", "客户终身价值", "元", 5000, 0.7, 0.5, "higher", "marketing"),
            KPIDefinition("churn_rate", "流失率", "%", 3.0, 0.5, 0.3, "lower", "customer"),
            KPIDefinition("nps_score", "NPS评分", "分", 50, 0.7, 0.5, "higher", "customer"),
            KPIDefinition("market_share", "市场份额", "%", 15.0, 0.7, 0.5, "higher", "market"),
        ]
        for kpi in defaults:
            self._kpi_definitions[kpi.kpi_id] = kpi

    def _init_default_models(self):
        """初始化默认预测模型"""
        self._forecast_models["moving_avg"] = ForecastModel("moving_avg", "移动平均", "moving_avg", {"window": 3})
        self._forecast_models["linear"] = ForecastModel("linear", "线性回归", "linear", {})
        self._forecast_models["exponential"] = ForecastModel("exponential", "指数平滑", "exponential", {"alpha": 0.3})

    def initialize(self):
        """初始化商业分析师"""
        if self._initialized:
            return
        # 模拟历史KPI数据
        self._generate_sample_data()
        self._initialized = True
        logger.info(
            f"[{self.module_name}] 初始化完成 | KPI: {len(self._kpi_definitions)} | 模型: {len(self._forecast_models)}"
        )

    def _generate_sample_data(self):
        """生成示例历史数据"""
        base_date = datetime.now() - timedelta(days=90)
        revenue_base = 4200.0
        margin_base = 42.0

        for i in range(90):
            date = base_date + timedelta(days=i)
            # 月营收：缓慢增长+波动
            revenue = revenue_base + i * 12 + (i % 7) * 50 - 150
            self._kpi_history["monthly_revenue"].append(KPIDataPoint(date, round(revenue, 2)))
            # 毛利率：小幅波动
            margin = margin_base + (i % 14 - 7) * 0.5
            self._kpi_history["gross_margin"].append(KPIDataPoint(date, round(margin, 2)))
            # 流失率
            churn = 2.5 + math.sin(i / 10) * 0.8
            self._kpi_history["churn_rate"].append(KPIDataPoint(date, round(churn, 2)))

    def _record_kpi(self, kpi_id: str, value: float, dimension: str = "default"):
        """记录KPI数据"""
        if kpi_id not in self._kpi_definitions:
            self._kpi_definitions[kpi_id] = KPIDefinition(kpi_id, kpi_id, "", 0, 0, 0)
        dp = KPIDataPoint(datetime.now(), value, dimension)
        self._kpi_history[kpi_id].append(dp)
        return {"recorded": True, "data_points": len(self._kpi_history[kpi_id])}

    def _get_kpi_status(self, kpi_id: str) -> Optional[KPIStatus]:
        """获取KPI当前状态"""
        defn = self._kpi_definitions.get(kpi_id)
        history = self._kpi_history.get(kpi_id, [])
        if not defn or len(history) < 2:
            return None

        current = history[-1].value
        previous = history[-2].value
        change_pct = (current - previous) / max(abs(previous), 0.001) * 100

        # 计算趋势（最近5个数据点）
        recent = history[-5:]
        if len(recent) >= 3:
            vals = [d.value for d in recent]
            if vals[-1] > vals[0] * 1.02:
                trend = "up"
            elif vals[-1] < vals[0] * 0.98:
                trend = "down"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # 达成率
        if defn.direction == "higher":
            attainment = current / max(defn.target, 0.001)
        else:
            attainment = defn.target / max(current, 0.001)

        # 状态判断
        if attainment >= 1.0:
            status = "exceeded"
        elif attainment >= defn.warning_threshold:
            status = "on_track"
        elif attainment >= defn.critical_threshold:
            status = "at_risk"
        else:
            status = "critical"

        return KPIStatus(
            kpi_id=kpi_id,
            current_value=round(current, 4),
            target=defn.target,
            attainment=round(attainment, 4),
            trend=trend,
            change_pct=round(change_pct, 2),
            status=status,
        )

    def _moving_average_forecast(self, values: List[float], window: int, periods: int) -> List[Dict]:
        """移动平均预测"""
        if len(values) < window:
            return []
        ma = sum(values[-window:]) / window
        predictions = []
        for i in range(periods):
            date = datetime.now() + timedelta(days=i + 1)
            predictions.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "value": round(ma + i * ma * 0.005, 2),
                    "confidence_low": round(ma * 0.9, 2),
                    "confidence_high": round(ma * 1.1, 2),
                }
            )
        return predictions

    def _linear_forecast(self, values: List[float], periods: int) -> List[Dict]:
        """线性回归预测"""
        n = len(values)
        if n < 2:
            return []
        x_vals = list(range(n))
        x_mean = statistics.mean(x_vals)
        y_mean = statistics.mean(values)

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, values))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)
        if denominator == 0:
            return []

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        y_std = statistics.stdev(values) if n > 1 else 0

        predictions = []
        for i in range(periods):
            date = datetime.now() + timedelta(days=i + 1)
            pred = intercept + slope * (n + i)
            predictions.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "value": round(pred, 2),
                    "confidence_low": round(pred - y_std, 2),
                    "confidence_high": round(pred + y_std, 2),
                }
            )
        return predictions

    def _exponential_forecast(self, values: List[float], alpha: float, periods: int) -> List[Dict]:
        """指数平滑预测"""
        if not values:
            return []
        smoothed = values[0]
        for v in values[1:]:
            smoothed = alpha * v + (1 - alpha) * smoothed

        predictions = []
        for i in range(periods):
            date = datetime.now() + timedelta(days=i + 1)
            predictions.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "value": round(smoothed, 2),
                    "confidence_low": round(smoothed * 0.92, 2),
                    "confidence_high": round(smoothed * 1.08, 2),
                }
            )
        return predictions

    def _generate_insights(self) -> List[Insight]:
        """基于KPI数据自动生成洞察"""
        insights = []
        for kpi_id, defn in self._kpi_definitions.items():
            status = self._get_kpi_status(kpi_id)
            if not status:
                continue

            if status.status == "critical":
                insight = Insight(
                    insight_id=f"ins_{uuid.uuid4().hex[:8]}",
                    title=f"{defn.name}严重偏离目标",
                    description=f"当前{defn.name}为{status.current_value}{defn.unit}，达成率仅{status.attainment * 100:.1f}%，趋势{status.trend}",
                    severity=InsightSeverity.CRITICAL,
                    category=defn.category,
                    metric=kpi_id,
                    action_items=[f"立即审查{defn.name}相关流程", "制定紧急改善计划", "每日跟踪直至恢复"],
                )
                insights.append(insight)
            elif status.status == "at_risk":
                insight = Insight(
                    insight_id=f"ins_{uuid.uuid4().hex[:8]}",
                    title=f"{defn.name}存在风险",
                    description=f"当前{defn.name}为{status.current_value}{defn.unit}，达成率{status.attainment * 100:.1f}%",
                    severity=InsightSeverity.WARNING,
                    category=defn.category,
                    metric=kpi_id,
                    action_items=["分析偏差原因", "制定改善措施"],
                )
                insights.append(insight)
            elif status.status == "exceeded" and status.trend == "up":
                insight = Insight(
                    insight_id=f"ins_{uuid.uuid4().hex[:8]}",
                    title=f"{defn.name}超额完成",
                    description=f"当前{defn.name}为{status.current_value}{defn.unit}，达成率{status.attainment * 100:.1f}%",
                    severity=InsightSeverity.POSITIVE,
                    category=defn.category,
                    metric=kpi_id,
                )
                insights.append(insight)

        self._insights.extend(insights)
        self._insight_counter += len(insights)
        return insights

    async def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行商业分析操作"""
        _ = self.trace("execute")
        metrics_collector.counter("business_analyst_ops_total", labels={"action": action})
        if not self._initialized:
            self.initialize()

        params = params or {}

        if action == "record_kpi":
            kpi_id = params.get("kpi_id")
            value = params.get("value")
            if not kpi_id or value is None:
                return {"success": False, "error": "缺少kpi_id或value"}
            result = self._record_kpi(kpi_id, float(value), params.get("dimension", "default"))
            return {"success": True, "result": result}

        elif action == "get_kpi_status":
            kpi_id = params.get("kpi_id")
            if not kpi_id:
                return {"success": False, "error": "缺少kpi_id"}
            status = self._get_kpi_status(kpi_id)
            if not status:
                return {"success": False, "error": f"KPI {kpi_id} 无足够数据"}
            return {
                "success": True,
                "result": {
                    "kpi_id": status.kpi_id,
                    "current_value": status.current_value,
                    "target": status.target,
                    "attainment": status.attainment,
                    "trend": status.trend,
                    "change_pct": status.change_pct,
                    "status": status.status,
                },
            }

        elif action == "get_all_kpi_status":
            results = []
            for kpi_id in self._kpi_definitions:
                status = self._get_kpi_status(kpi_id)
                if status:
                    results.append(
                        {
                            "kpi_id": status.kpi_id,
                            "current_value": status.current_value,
                            "target": status.target,
                            "attainment": status.attainment,
                            "trend": status.trend,
                            "change_pct": status.change_pct,
                            "status": status.status,
                        }
                    )
            return {"success": True, "result": results}

        elif action == "forecast":
            kpi_id = params.get("kpi_id", "monthly_revenue")
            model_id = params.get("model", "moving_avg")
            periods = params.get("periods", 7)

            history = self._kpi_history.get(kpi_id, [])
            if len(history) < 3:
                return {"success": False, "error": f"KPI {kpi_id} 数据不足"}

            values = [d.value for d in history]
            model = self._forecast_models.get(model_id, self._forecast_models["moving_avg"])

            if model.model_type == "moving_avg":
                window = model.parameters.get("window", 3)
                predictions = self._moving_average_forecast(values, window, periods)
            elif model.model_type == "linear":
                predictions = self._linear_forecast(values, periods)
            elif model.model_type == "exponential":
                alpha = model.parameters.get("alpha", 0.3)
                predictions = self._exponential_forecast(values, alpha, periods)
            else:
                predictions = self._moving_average_forecast(values, 3, periods)

            forecast = ForecastResult(
                forecast_id=f"fc_{uuid.uuid4().hex[:8]}", model_id=model_id, metric_name=kpi_id, predictions=predictions
            )
            self._forecast_history[kpi_id].append(forecast)
            self._total_forecasts += 1
            self._total_analyses += 1

            return {
                "success": True,
                "result": {
                    "forecast_id": forecast.forecast_id,
                    "model": model.name,
                    "metric": kpi_id,
                    "predictions": predictions,
                    "data_points_used": len(values),
                },
            }

        elif action == "analyze":
            """执行综合分析"""
            self.audit("execute", f"action={action}")

            kpi_id = params.get("kpi_id")
            analysis_type = params.get("analysis_type", "comprehensive")

            if kpi_id:
                status = self._get_kpi_status(kpi_id)
                history = self._kpi_history.get(kpi_id, [])
                values = [d.value for d in history]

                result = {
                    "kpi_id": kpi_id,
                    "data_points": len(values),
                }
                if values:
                    result["current"] = values[-1]
                    result["mean"] = round(statistics.mean(values), 2)
                    result["min"] = round(min(values), 2)
                    result["max"] = round(max(values), 2)
                    result["std_dev"] = round(statistics.stdev(values), 2) if len(values) > 1 else 0
                if status:
                    result["status"] = status.status
                    result["trend"] = status.trend
                    result["attainment"] = status.attainment

                self._total_analyses += 1
                return {"success": True, "result": result}

            # 全面分析
            kpi_statuses = {}
            for kid in self._kpi_definitions:
                s = self._get_kpi_status(kid)
                if s:
                    kpi_statuses[kid] = {"status": s.status, "attainment": s.attainment, "trend": s.trend}

            on_track = sum(1 for v in kpi_statuses.values() if v["status"] in ("on_track", "exceeded"))
            at_risk = sum(1 for v in kpi_statuses.values() if v["status"] == "at_risk")
            critical = sum(1 for v in kpi_statuses.values() if v["status"] == "critical")

            insights = self._generate_insights()
            self._total_analyses += 1

            return {
                "success": True,
                "result": {
                    "total_kpis": len(kpi_statuses),
                    "on_track": on_track,
                    "at_risk": at_risk,
                    "critical": critical,
                    "health_score": round(on_track / max(len(kpi_statuses), 1) * 100, 1),
                    "new_insights": len(insights),
                    "kpi_statuses": kpi_statuses,
                    "top_insights": [
                        {"title": i.title, "severity": i.severity.value, "category": i.category} for i in insights[:5]
                    ],
                },
            }

        elif action == "get_insights":
            severity_filter = params.get("severity")
            category_filter = params.get("category")
            limit = params.get("limit", 20)

            filtered = self._insights.copy()
            if severity_filter:
                filtered = [i for i in filtered if i.severity.value == severity_filter]
            if category_filter:
                filtered = [i for i in filtered if i.category == category_filter]

            filtered = filtered[-limit:]
            return {
                "success": True,
                "result": [
                    {
                        "insight_id": i.insight_id,
                        "title": i.title,
                        "severity": i.severity.value,
                        "category": i.category,
                        "description": i.description,
                        "action_items": i.action_items,
                        "created_at": i.created_at.isoformat(),
                    }
                    for i in filtered
                ],
                "total": len(self._insights),
            }

        elif action == "add_competitor":
            name = params.get("name")
            market_share = params.get("market_share", 0)
            strengths = params.get("strengths", [])
            weaknesses = params.get("weaknesses", [])
            if not name:
                return {"success": False, "error": "缺少name"}
            self._competitors[name] = {
                "name": name,
                "market_share": market_share,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "updated_at": datetime.now().isoformat(),
            }
            return {"success": True, "result": {"competitor": name, "total": len(self._competitors)}}

        elif action == "competitive_analysis":
            result = {
                "our_market_share": 12.5,
                "competitors": list(self._competitors.values()),
                "total_competitors": len(self._competitors),
                "market_concentration": "medium",
            }
            if self._competitors:
                shares = [12.5] + [c.get("market_share", 0) for c in self._competitors.values()]
                total = sum(shares)
                result["market_concentration"] = (
                    "high" if max(shares) / total > 0.4 else "medium" if max(shares) / total > 0.2 else "low"
                )
            self._total_analyses += 1
            return {"success": True, "result": result}

        elif action == "get_dashboard":
            """获取仪表盘汇总数据"""
            statuses = {}
            for kid in self._kpi_definitions:
                s = self._get_kpi_status(kid)
                if s:
                    statuses[kid] = {
                        "name": kid,
                        "value": s.current_value,
                        "target": s.target,
                        "attainment": round(s.attainment * 100, 1),
                        "trend": s.trend,
                        "status": s.status,
                    }

            total = len(statuses)
            on_track = sum(1 for v in statuses.values() if v["status"] in ("on_track", "exceeded"))
            critical_count = sum(1 for v in statuses.values() if v["status"] == "critical")

            return {
                "success": True,
                "result": {
                    "kpis": statuses,
                    "summary": {
                        "total": total,
                        "on_track": on_track,
                        "critical": critical_count,
                        "health_score": round(on_track / max(total, 1) * 100, 1),
                    },
                    "total_insights": len(self._insights),
                    "total_forecasts": self._total_forecasts,
                    "total_analyses": self._total_analyses,
                },
            }

        else:
            return {"success": False, "error": f"未知操作: {action}"}

    def shutdown(self) -> None:
        """优雅关闭"""
        self._initialized = False
        logger.info(f"[{self.module_name}] 已关闭")

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy" if self._initialized else "not_initialized",
                "kpis_tracked": len(self._kpi_definitions),
                "data_points": sum(len(v) for v in self._kpi_history.values()),
                "forecast_models": len(self._forecast_models),
                "insights": len(self._insights),
                "total_analyses": self._total_analyses,
                "total_forecasts": self._total_forecasts,
            }
        )
        return result

module_class = BusinessAnalystManager
