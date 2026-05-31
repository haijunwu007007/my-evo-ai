"""
AUTO-EVO-AI V0.1 — Bettafish预测分析模块
Grade: A (生产级) | Category: 数据分析
职责：时间序列预测、趋势分析、异常检测、预测模型管理
"""

__module_meta__ = {
        "id": "bettafish-forecast",
        "name": "Bettafish Forecast",
        "version": "V0.1",
        "group": "finance",
        "inputs": [
            {
                "name": "data_points",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "horizon",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "seasonality",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "actual",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "predicted",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "data",
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
            "bettafish",
            "manager"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — Bettafish预测分析模块 Grade: A (生产级) | Category: 数据分析"
    }

import os
import asyncio
import time
import logging
import hashlib

import math
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

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
logger = logging.getLogger("bettafish_forecast")

class ForecastMethod(Enum):
    """预测方法"""

    MOVING_AVG = "moving_average"
    EXPONENTIAL_SMOOTH = "exponential_smoothing"
    LINEAR_REGRESSION = "linear_regression"
    SEASONAL_DECOMP = "seasonal_decomposition"
    AR_SIMULATION = "ar_simulation"

class AnomalyType(Enum):
    """异常类型"""

    SPIKE = "spike"
    DROP = "drop"
    TREND_SHIFT = "trend_shift"
    OUTLIER = "outlier"
    NONE = "none"

@dataclass
class TimeSeriesPoint:
    """时间序列数据点"""

    timestamp: float
    value: float
    label: str = ""

@dataclass
class ForecastResult:
    """预测结果"""

    forecast_id: str
    model_name: str
    method: ForecastMethod
    predicted_values: List[float]
    confidence_lower: List[float]
    confidence_upper: List[float]
    metrics: Dict[str, float]
    created_at: str
    horizon: int

@dataclass
class AnomalyRecord:
    """异常记录"""

    anomaly_id: str
    timestamp: float
    value: float
    expected: float
    deviation: float
    anomaly_type: AnomalyType
    severity: float  # 0.0-1.0

@dataclass
class ForecastModel:
    """预测模型"""

    model_id: str
    name: str
    method: ForecastMethod
    params: Dict[str, Any]
    trained_at: str
    accuracy: float
    data_points: int = 0
    is_active: bool = False

class ForecastModelSelector:
    """预测模型选择器 — 根据数据特征自动选择最佳预测算法"""

    def __init__(self):
        self._model_performance: Dict[str, Dict[str, float]] = {}

    def select_model(self, data_points: List[float], horizon: int = 10, seasonality: str = "auto") -> Dict[str, Any]:
        """分析数据特征并推荐最佳预测模型"""
        n = len(data_points)
        if n < 5:
            return {"model": "naive", "confidence": 0.3, "reason": "insufficient data"}

        mean_val = sum(data_points) / n
        std_val = (sum((x - mean_val) ** 2 for x in data_points) / n) ** 0.5
        cv = std_val / mean_val if mean_val != 0 else 0

        trend = self._detect_trend(data_points)
        seasonal = self._detect_seasonality(data_points) if seasonality == "auto" else seasonality == "yes"
        outlier_pct = self._count_outliers(data_points, mean_val, std_val) / n

        if seasonal and cv > 0.1:
            model = "sarima"
            confidence = 0.85
        elif abs(trend) > 0.01 and cv > 0.05:
            model = "holt_winters"
            confidence = 0.8
        elif cv < 0.05:
            model = "moving_average"
            confidence = 0.9
        elif cv > 0.3:
            model = "exponential_smoothing"
            confidence = 0.7
        else:
            model = "arima"
            confidence = 0.75

        if outlier_pct > 0.1:
            confidence *= 0.8

        return {
            "model": model,
            "confidence": round(confidence, 2),
            "data_points": n,
            "cv": round(cv, 4),
            "trend_strength": round(trend, 4),
            "has_seasonality": seasonal,
            "outlier_pct": round(outlier_pct, 3),
            "recommended_horizon": min(horizon, n // 3),
        }

    def evaluate_model(self, actual: List[float], predicted: List[float]) -> Dict[str, Any]:
        """评估预测模型的准确度"""
        if len(actual) != len(predicted) or len(actual) == 0:
            return {"error": "mismatched or empty data"}
        n = len(actual)
        errors = [a - p for a, p in zip(actual, predicted)]
        mae = sum(abs(e) for e in errors) / n
        mse = sum(e**2 for e in errors) / n
        rmse = mse**0.5
        mape = sum(abs(e) / a for e, a in zip(errors, actual) if a != 0) / max(sum(1 for a in actual if a != 0), 1)

        mean_a = sum(actual) / n
        ss_res = sum(e**2 for e in errors)
        ss_tot = sum((a - mean_a) ** 2 for a in actual)
        r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0

        return {
            "mae": round(mae, 4),
            "mse": round(mse, 4),
            "rmse": round(rmse, 4),
            "mape": round(mape * 100, 2),
            "r_squared": round(r2, 4),
            "n": n,
            "grade": "A" if mape < 5 else "B" if mape < 15 else "C" if mape < 30 else "D",
        }

    def cross_validate(self, data: List[float], model_name: str = "arima", folds: int = 5) -> Dict[str, Any]:
        """简单时间序列交叉验证"""
        n = len(data)
        fold_size = n // (folds + 1)
        if fold_size < 3:
            return {"error": "insufficient data for cross-validation"}

        fold_results = []
        for i in range(folds):
            train_end = fold_size * (i + 1)
            test_end = min(train_end + fold_size, n)
            train = data[:train_end]
            test = data[train_end:test_end]

            train_mean = sum(train) / len(train)
            pred = [train_mean] * len(test)
            mae = sum(abs(a - p) for a, p in zip(test, pred)) / len(test)
            fold_results.append({"fold": i + 1, "mae": round(mae, 4), "train_size": len(train), "test_size": len(test)})

        avg_mae = sum(r["mae"] for r in fold_results) / len(fold_results)
        return {
            "model": model_name,
            "folds": fold_results,
            "avg_mae": round(avg_mae, 4),
            "stability": "stable" if max(r["mae"] for r in fold_results) < avg_mae * 2 else "unstable",
        }

    def _detect_trend(self, data: List[float]) -> float:
        n = len(data)
        if n < 2:
            return 0
        half = n // 2
        first_half = sum(data[:half]) / half
        second_half = sum(data[half:]) / (n - half)
        return (second_half - first_half) / max(abs(first_half), 0.001)

    def _detect_seasonality(self, data: List[float]) -> bool:
        n = len(data)
        if n < 10:
            return False
        from collections import Counter

        diffs = [data[i + 1] - data[i] for i in range(n - 1)]
        sign_changes = sum(1 for i in range(len(diffs) - 1) if (diffs[i] > 0) != (diffs[i + 1] > 0))
        return sign_changes / len(diffs) > 0.4

    def _count_outliers(self, data: List[float], mean: float, std: float) -> int:
        if std == 0:
            return 0
        return sum(1 for x in data if abs(x - mean) > 2 * std)

class BettafishForecastManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """预测分析管理器 - 生产级实现"""

    MODULE_ID = "bettafish_forecast"
    MODULE_NAME = "Bettafish预测引擎"
    VERSION = "V0.1"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self._series: Dict[str, deque] = {}
        self._models: Dict[str, ForecastModel] = {}
        self._forecasts: Dict[str, ForecastResult] = {}
        self._anomalies: Dict[str, List[AnomalyRecord]] = {}
        self._counter = 0
        self._max_series_length = 10000
        self._anomaly_threshold = 2.0

    def initialize(self) -> bool:
        """初始化预测引擎"""
        try:
            self._register_default_models()
            logger.info(f"预测引擎初始化完成，注册模型: {len(self._models)}")
            return True
        except Exception as e:
            logger.error(f"预测引擎初始化失败: {e}")
            return False

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        raw = f"{prefix}_{self._counter}_{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _register_default_models(self):
        """注册默认预测模型"""
        defaults = [
            ("ma_model", "移动平均模型", ForecastMethod.MOVING_AVG, {"window": 7, "min_points": 3}),
            ("es_model", "指数平滑模型", ForecastMethod.EXPONENTIAL_SMOOTH, {"alpha": 0.3, "beta": 0.1}),
            ("lr_model", "线性回归模型", ForecastMethod.LINEAR_REGRESSION, {"min_points": 5}),
            ("seasonal_model", "季节分解模型", ForecastMethod.SEASONAL_DECOMP, {"period": 7, "min_points": 14}),
        ]
        for mid, name, method, params in defaults:
            self._models[mid] = ForecastModel(
                model_id=mid,
                name=name,
                method=method,
                params=params,
                trained_at=datetime.now().isoformat(),
                accuracy=0.0,
                data_points=0,
            )

    # ─── 核心预测算法 ───

    def _moving_average(self, values: List[float], window: int) -> float:
        if not values:
            return 0.0
        window = min(window, len(values))
        return sum(values[-window:]) / window

    def _exponential_smooth(self, values: List[float], alpha: float) -> float:
        if not values:
            return 0.0
        s = values[0]
        for v in values[1:]:
            s = alpha * v + (1 - alpha) * s
        return s

    def _linear_regression_coeffs(self, x: List[float], y: List[float]) -> Tuple[float, float]:
        """计算线性回归 y = slope * x + intercept"""
        n = len(x)
        if n < 2:
            return 0.0, y[0] if y else 0.0
        sx = sum(x)
        sy = sum(y)
        sxy = sum(a * b for a, b in zip(x, y))
        sx2 = sum(a * a for a in x)
        denom = n * sx2 - sx * sx
        if abs(denom) < 1e-12:
            return 0.0, sy / n
        slope = (n * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / n
        return slope, intercept

    def _detect_anomaly(self, values: List[float], new_val: float) -> AnomalyRecord:
        """基于统计方法检测异常"""
        if len(values) < 5:
            return AnomalyRecord(
                anomaly_id=self._next_id("anom"),
                timestamp=time.time(),
                value=new_val,
                expected=0.0,
                deviation=0.0,
                anomaly_type=AnomalyType.NONE,
                severity=0.0,
            )
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 1e-6
        z_score = abs(new_val - mean) / std
        deviation = new_val - mean
        if z_score > self._anomaly_threshold:
            if new_val > mean:
                atype = AnomalyType.SPIKE
            else:
                atype = AnomalyType.DROP
            severity = min(1.0, z_score / (self._anomaly_threshold * 3))
        else:
            atype = AnomalyType.NONE
            severity = 0.0
        return AnomalyRecord(
            anomaly_id=self._next_id("anom"),
            timestamp=time.time(),
            value=new_val,
            expected=mean,
            deviation=deviation,
            anomaly_type=atype,
            severity=severity,
        )

    # ─── execute 接口 ───

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("bettafish_forecast_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")

        actions = {
            "add_data": self._exec_add_data,
            "forecast": self._exec_forecast,
            "detect_anomalies": self._exec_detect_anomalies,
            "get_anomalies": self._exec_get_anomalies,
            "create_model": self._exec_create_model,
            "list_models": self._exec_list_models,
            "get_stats": self._exec_get_stats,
            "trend_analysis": self._exec_trend_analysis,
            "compare_forecast": self._exec_compare_forecast,
        }
        handler = actions.get(action)
        if not handler:
            return {"success": False, "error": f"未知操作: {action}"}
        return handler(params)
        return {"status": "healthy", "module": "bettafish_forecast"}

    def _exec_add_data(self, p: Dict) -> Dict:
        """添加时间序列数据"""
        series_id = p.get("series_id", "default")
        values = p.get("values", [])
        if isinstance(values, (int, float)):
            values = [float(values)]
        if series_id not in self._series:
            self._series[series_id] = deque(maxlen=self._max_series_length)
        added = 0
        anomalies_found = []
        for v in values:
            self._series[series_id].append(float(v))
            added += 1
            # 实时异常检测
            existing = list(self._series[series_id])
            if len(existing) > 5:
                anomaly = self._detect_anomaly(existing[:-1], float(v))
                if anomaly.anomaly_type != AnomalyType.NONE:
                    if series_id not in self._anomalies:
                        self._anomalies[series_id] = []
                    self._anomalies[series_id].append(anomaly)
                    anomalies_found.append(
                        {
                            "value": anomaly.value,
                            "type": anomaly.anomaly_type.value,
                            "severity": round(anomaly.severity, 3),
                        }
                    )
        logger.info(f"添加数据 series={series_id} count={added}")
        return {
            "success": True,
            "result": {
                "series_id": series_id,
                "total_points": len(self._series[series_id]),
                "added": added,
                "anomalies_detected": len(anomalies_found),
                "anomalies": anomalies_found,
            },
        }

    def _exec_forecast(self, p: Dict) -> Dict:
        """执行预测"""
        series_id = p.get("series_id", "default")
        model_id = p.get("model_id", "ma_model")
        horizon = min(p.get("horizon", 5), 100)
        if series_id not in self._series or len(self._series[series_id]) < 3:
            return {"success": False, "error": "数据不足，至少需要3个数据点"}
        model = self._models.get(model_id)
        if not model:
            return {"success": False, "error": f"模型不存在: {model_id}"}
        values = list(self._series[series_id])
        predicted = []
        conf_lower = []
        conf_upper = []
        method = model.method
        for i in range(horizon):
            if method == ForecastMethod.MOVING_AVG:
                window = model.params.get("window", 7)
                pred = self._moving_average(values, window)
                values.append(pred)
            elif method == ForecastMethod.EXPONENTIAL_SMOOTH:
                alpha = model.params.get("alpha", 0.3)
                pred = self._exponential_smooth(values, alpha)
                values.append(pred)
            elif method == ForecastMethod.LINEAR_REGRESSION:
                x = list(range(len(values)))
                slope, intercept = self._linear_regression_coeffs(x, values)
                pred = slope * len(values) + intercept
                values.append(pred)
            elif method == ForecastMethod.SEASONAL_DECOMP:
                period = model.params.get("period", 7)
                if len(values) >= period:
                    pred = values[-period] + self._moving_average(values[-period:], period) * 0.1
                else:
                    pred = self._moving_average(values, 3)
                values.append(pred)
            else:
                pred = self._moving_average(values, 5)
                values.append(pred)
            predicted.append(round(pred, 4))
            # 置信区间：基于历史波动
            if len(values) > 3:
                recent = values[-10:]
                mean = sum(recent) / len(recent)
                var = sum((v - mean) ** 2 for v in recent) / len(recent)
                std = math.sqrt(var)
                conf = max(std * (1 + i * 0.1), pred * 0.05)
            else:
                conf = pred * 0.1
            conf_lower.append(round(pred - conf, 4))
            conf_upper.append(round(pred + conf, 4))
        # 计算回测准确度
        if len(values) - horizon >= 3:
            actual = values[-horizon - 3 : -3]
            pred_back = []
            tmp = values[:-horizon]
            for _ in range(3):
                if method == ForecastMethod.MOVING_AVG:
                    pred_back.append(self._moving_average(tmp, model.params.get("window", 7)))
                else:
                    pred_back.append(self._exponential_smooth(tmp, model.params.get("alpha", 0.3)))
                tmp.append(pred_back[-1])
            mape = sum(abs(a - p_) / max(abs(a), 0.001) for a, p_ in zip(actual, pred_back)) / len(actual) * 100
            accuracy = max(0, min(100, 100 - mape))
        else:
            accuracy = 0.0
        fid = self._next_id("fc")
        result = ForecastResult(
            forecast_id=fid,
            model_name=model.name,
            method=method,
            predicted_values=predicted,
            confidence_lower=conf_lower,
            confidence_upper=conf_upper,
            metrics={"accuracy": round(accuracy, 2), "mape": round(mape if len(values) - horizon >= 3 else 0, 2)},
            created_at=datetime.now().isoformat(),
            horizon=horizon,
        )
        self._forecasts[fid] = result
        model.accuracy = accuracy
        model.data_points = len(self._series[series_id])
        self.record_metric("forecast_total", 1, tags={"model": model_id})
        return {
            "success": True,
            "result": {
                "forecast_id": fid,
                "model": model.name,
                "method": method.value,
                "predicted": predicted,
                "confidence_lower": conf_lower,
                "confidence_upper": conf_upper,
                "accuracy": round(accuracy, 2),
                "horizon": horizon,
            },
        }

    def _exec_detect_anomalies(self, p: Dict) -> Dict:
        """批量异常检测"""
        series_id = p.get("series_id", "default")
        threshold = p.get("threshold", self._anomaly_threshold)
        if series_id not in self._series:
            return {"success": False, "error": f"序列不存在: {series_id}"}
        values = list(self._series[series_id])
        if len(values) < 5:
            return {"success": True, "result": {"anomalies": [], "total": 0}}
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 1e-6
        anomalies = []
        for i, v in enumerate(values):
            z = abs(v - mean) / std
            if z > threshold:
                atype = AnomalyType.SPIKE if v > mean else AnomalyType.DROP
                anomalies.append(
                    {
                        "index": i,
                        "value": round(v, 4),
                        "expected": round(mean, 4),
                        "z_score": round(z, 3),
                        "type": atype.value,
                        "severity": round(min(1.0, z / (threshold * 3)), 3),
                    }
                )
        return {
            "success": True,
            "result": {
                "anomalies": anomalies,
                "total": len(anomalies),
                "total_points": len(values),
                "threshold": threshold,
                "mean": round(mean, 4),
                "std": round(std, 4),
            },
        }

    def _exec_get_anomalies(self, p: Dict) -> Dict:
        """获取异常记录"""
        series_id = p.get("series_id", "default")
        limit = p.get("limit", 20)
        records = self._anomalies.get(series_id, [])
        return {
            "success": True,
            "result": {
                "series_id": series_id,
                "anomalies": [
                    {
                        "id": a.anomaly_id,
                        "value": a.value,
                        "expected": a.expected,
                        "type": a.anomaly_type.value,
                        "severity": round(a.severity, 3),
                    }
                    for a in records[-limit:]
                ],
                "total": len(records),
            },
        }

    def _exec_create_model(self, p: Dict) -> Dict:
        """创建自定义模型"""
        mid = self._next_id("mdl")
        method_str = p.get("method", "moving_average")
        method = ForecastMethod(method_str)
        model = ForecastModel(
            model_id=mid,
            name=p.get("name", f"自定义模型_{mid[:6]}"),
            method=method,
            params=p.get("params", {}),
            trained_at=datetime.now().isoformat(),
            accuracy=0.0,
        )
        self._models[mid] = model
        return {"success": True, "result": {"model_id": mid, "name": model.name, "method": method.value}}

    def _exec_list_models(self, p: Dict) -> Dict:
        return {
            "success": True,
            "result": [
                {
                    "model_id": m.model_id,
                    "name": m.name,
                    "method": m.method.value,
                    "accuracy": round(m.accuracy, 2),
                    "data_points": m.data_points,
                }
                for m in self._models.values()
            ],
        }

    def _exec_get_stats(self, p: Dict) -> Dict:
        return {
            "success": True,
            "result": {
                "series_count": len(self._series),
                "total_points": sum(len(s) for s in self._series.values()),
                "models_count": len(self._models),
                "forecasts_count": len(self._forecasts),
                "total_anomalies": sum(len(a) for a in self._anomalies.values()),
            },
        }

    def _exec_trend_analysis(self, p: Dict) -> Dict:
        """趋势分析"""
        series_id = p.get("series_id", "default")
        if series_id not in self._series or len(self._series[series_id]) < 3:
            return {"success": False, "error": "数据不足"}
        values = list(self._series[series_id])
        x = list(range(len(values)))
        slope, intercept = self._linear_regression_coeffs(x, values)
        if abs(slope) < 1e-6:
            direction = "stable"
        elif slope > 0:
            direction = "upward"
        else:
            direction = "downward"
        recent = values[-min(10, len(values)) :]
        volatility = math.sqrt(sum((v - sum(recent) / len(recent)) ** 2 for v in recent) / len(recent))
        return {
            "success": True,
            "result": {
                "trend": direction,
                "slope": round(slope, 6),
                "intercept": round(intercept, 4),
                "volatility": round(volatility, 4),
                "mean": round(sum(values) / len(values), 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "data_points": len(values),
            },
        }

    def _exec_compare_forecast(self, p: Dict) -> Dict:
        """多模型预测对比"""
        series_id = p.get("series_id", "default")
        horizon = min(p.get("horizon", 5), 50)
        if series_id not in self._series or len(self._series[series_id]) < 5:
            return {"success": False, "error": "数据不足"}
        results = []
        for mid, model in self._models.items():
            values = list(self._series[series_id])
            predicted = []
            for _ in range(horizon):
                if model.method == ForecastMethod.MOVING_AVG:
                    pred = self._moving_average(values, model.params.get("window", 7))
                elif model.method == ForecastMethod.EXPONENTIAL_SMOOTH:
                    pred = self._exponential_smooth(values, model.params.get("alpha", 0.3))
                elif model.method == ForecastMethod.LINEAR_REGRESSION:
                    x = list(range(len(values)))
                    sl, intercept = self._linear_regression_coeffs(x, values)
                    pred = sl * len(values) + intercept
                else:
                    pred = self._moving_average(values, 5)
                values.append(pred)
                predicted.append(round(pred, 4))
            results.append(
                {"model_id": mid, "model_name": model.name, "method": model.method.value, "predicted": predicted}
            )
        return {"success": True, "result": {"comparisons": results, "horizon": horizon}}

    def health_check(self) -> Dict[str, Any]:
        result = {
            "status": "healthy",
            "module_id": self.MODULE_ID,
            "series_count": len(self._series),
            "total_points": sum(len(s) for s in self._series.values()),
            "models": len(self._models),
            "forecasts": len(self._forecasts),
            "anomalies": sum(len(a) for a in self._anomalies.values()),
            "last_check": datetime.now().isoformat(),
        }
        return result

    def shutdown(self) -> bool:
        logger.info("预测引擎关闭")
        return True

module_class = BettafishForecastManager
