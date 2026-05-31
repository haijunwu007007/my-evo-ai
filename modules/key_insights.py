"""
# Grade: A
AUTO-EVO-AI V0.1 — KeyInsights 关键洞察分析引擎

上市公司级 A级模块，提供多维数据分析与洞察提取能力：
- 统计分析引擎(StatisticalAnalyzer)：描述统计、相关性分析、趋势检测、分布拟合
- 异常检测引擎(AnomalyDetector)：Z-Score、移动窗口、阈值监控、Isolation Forest
- 洞察生成引擎(InsightGenerator)：趋势洞察、异常洞察、相关性洞察、建议生成
- 知识图谱引擎(KnowledgeGraphEngine)：实体抽取、关系推理、图谱查询、知识融合

适用于：数据分析、业务洞察、异常监控、决策支持。
"""

__module_meta__ = {
        "id": "key-insights",
        "name": "Key Insights",
        "version": "V0.1",
        "group": "security",
        "inputs": [
            {
                "name": "db_path",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "data",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "series_a",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "series_b",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "time_series",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "data_2",
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
            "engine",
            "key"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — KeyInsights 关键洞察分析引擎 上市公司级 A级模块，提供多维数据分析与洞察提取能力："
    }

import os
import time
import json
import math
import uuid
import hashlib
import logging
import threading
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque
from enum import Enum
import sqlite3
import re

from modules._base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

class InsightType(Enum):
    TREND = "trend"
    ANOMALY = "anomaly"
    CORRELATION = "correlation"
    PATTERN = "pattern"
    PREDICTION = "prediction"
    RECOMMENDATION = "recommendation"

class SeverityLevel(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ============================================================================
# 子引擎1：统计分析引擎
# ============================================================================

class StatisticalAnalyzer:
    """统计分析引擎 — 描述统计、相关性分析、趋势检测、分布拟合"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data", "key_insights.db"
        )
        self._init_db()
        self.lock = threading.RLock()
        self._operation_count = 0
        self._error_count = 0

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS stat_analyses (
                    id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL,
                    analysis_type TEXT NOT NULL, result_json TEXT NOT NULL,
                    created_at REAL NOT NULL, metadata_json TEXT)""")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_stat_ds ON stat_analyses(dataset_id)")
                conn.commit()
        except Exception as e:
            logger.warning("Stat DB init failed: {}".format(e))

    def describe(self, data: List[float]) -> Dict[str, Any]:
        """描述性统计分析"""
        self._operation_count += 1
        if not data:
            return {"error": "empty data"}
        n = len(data)
        mean_val = statistics.mean(data)
        median_val = statistics.median(data)
        stdev_val = statistics.stdev(data) if n > 1 else 0.0
        min_val = min(data)
        max_val = max(data)
        sorted_d = sorted(data)
        q1 = sorted_d[n // 4]
        q3 = sorted_d[3 * n // 4]
        iqr = q3 - q1
        result = {
            "count": n,
            "mean": round(mean_val, 6),
            "median": round(median_val, 6),
            "std": round(stdev_val, 6),
            "min": round(min_val, 6),
            "max": round(max_val, 6),
            "q1": round(q1, 6),
            "q3": round(q3, 6),
            "iqr": round(iqr, 6),
            "variance": round(stdev_val**2, 6) if n > 1 else 0.0,
            "cv": round(stdev_val / mean_val, 6) if mean_val != 0 else None,
        }
        with self.lock:
            aid = hashlib.md5("{}:{}".format(time.time(), json.dumps(data[:10])).encode()).hexdigest()[:16]
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO stat_analyses VALUES (?,?,?,?,?,?)",
                        (aid, "adhoc", "describe", json.dumps(result), time.time(), None),
                    )
                    conn.commit()
            except Exception:
                pass
        return result

    def correlation(self, series_a: List[float], series_b: List[float]) -> Dict[str, Any]:
        """Pearson相关系数"""
        self._operation_count += 1
        if len(series_a) != len(series_b) or len(series_a) < 2:
            return {"error": "invalid series length"}
        n = len(series_a)
        mean_a = statistics.mean(series_a)
        mean_b = statistics.mean(series_b)
        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(series_a, series_b)) / (n - 1)
        std_a = statistics.stdev(series_a)
        std_b = statistics.stdev(series_b)
        corr = cov / (std_a * std_b) if std_a > 0 and std_b > 0 else 0.0
        abs_r = abs(corr)
        if abs_r >= 0.8:
            strength = "very_strong"
        elif abs_r >= 0.6:
            strength = "strong"
        elif abs_r >= 0.4:
            strength = "moderate"
        elif abs_r >= 0.2:
            strength = "weak"
        else:
            strength = "very_weak"
        return {
            "pearson_correlation": round(corr, 6),
            "strength": strength,
            "sample_size": n,
            "covariance": round(cov, 6),
        }

    def trend(self, time_series: List[Tuple[float, float]]) -> Dict[str, Any]:
        """线性回归趋势检测"""
        self._operation_count += 1
        if len(time_series) < 2:
            return {"error": "need at least 2 points"}
        n = len(time_series)
        x_vals = [p[0] for p in time_series]
        y_vals = [p[1] for p in time_series]
        mean_x = statistics.mean(x_vals)
        mean_y = statistics.mean(y_vals)
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_vals))
        den = sum((x - mean_x) ** 2 for x in x_vals)
        slope = num / den if den != 0 else 0.0
        intercept = mean_y - slope * mean_x
        ss_tot = sum((y - mean_y) ** 2 for y in y_vals)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_vals, y_vals))
        r_sq = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
        return {
            "slope": round(slope, 6),
            "intercept": round(intercept, 6),
            "r_squared": round(r_sq, 6),
            "direction": direction,
            "strength": "strong" if r_sq > 0.7 else "moderate" if r_sq > 0.3 else "weak",
            "data_points": n,
        }

    def distribution_fit(self, data: List[float]) -> Dict[str, Any]:
        """分布拟合检测（偏度+峰度）"""
        self._operation_count += 1
        if len(data) < 3:
            return {"error": "need at least 3 data points"}
        n = len(data)
        mean_val = statistics.mean(data)
        std_val = statistics.stdev(data) if n > 1 else 0.0
        if std_val == 0:
            return {
                "mean": round(mean_val, 6),
                "std": 0,
                "skewness": 0,
                "kurtosis": 0,
                "is_normal_like": False,
                "distribution_guess": "constant",
                "sample_size": n,
            }
        skew = (sum((x - mean_val) ** 3 for x in data) / n) / (std_val**3)
        kurt = (sum((x - mean_val) ** 4 for x in data) / n) / (std_val**4) - 3.0
        is_normal = abs(skew) < 1.0 and abs(kurt) < 3.0
        return {
            "mean": round(mean_val, 6),
            "std": round(std_val, 6),
            "skewness": round(skew, 6),
            "kurtosis": round(kurt, 6),
            "is_normal_like": is_normal,
            "distribution_guess": "normal" if is_normal else "non_normal",
            "sample_size": n,
        }

# ============================================================================
# 子引擎2：异常检测引擎
# ============================================================================

class AnomalyDetector:
    """异常检测引擎 — Z-Score、移动窗口、阈值监控"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data", "key_insights.db"
        )
        self.lock = threading.RLock()
        self._operation_count = 0
        self._error_count = 0
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS anomaly_results (
                    id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL,
                    method TEXT NOT NULL, anomalies_json TEXT NOT NULL,
                    threshold REAL, created_at REAL NOT NULL)""")
                conn.commit()
        except Exception:
            pass

    def _save_result(self, method: str, result: Dict[str, Any]):
        rid = hashlib.md5(
            "{}:{}:{}".format(method, time.time(), len(result.get("anomalies", []))).encode()
        ).hexdigest()[:16]
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO anomaly_results VALUES (?,?,?,?,?,?)",
                    (rid, "adhoc", method, json.dumps(result), result.get("threshold"), time.time()),
                )
                conn.commit()
        except Exception:
            pass

    def zscore_detect(self, data: List[float], threshold: float = 3.0) -> Dict[str, Any]:
        """Z-Score异常检测"""
        self._operation_count += 1
        if len(data) < 2:
            return {"error": "need at least 2 data points", "anomalies": []}
        mean_val = statistics.mean(data)
        std_val = statistics.stdev(data)
        anomalies = []
        for i, val in enumerate(data):
            z = abs((val - mean_val) / std_val) if std_val > 0 else 0.0
            if z > threshold:
                anomalies.append(
                    {"index": i, "value": val, "z_score": round(z, 6), "deviation": round(val - mean_val, 6)}
                )
        result = {
            "method": "z_score",
            "threshold": threshold,
            "total_points": len(data),
            "anomaly_count": len(anomalies),
            "anomaly_rate": round(len(anomalies) / max(len(data), 1), 6),
            "mean": round(mean_val, 6),
            "std": round(std_val, 6),
            "anomalies": anomalies[:50],
        }
        self._save_result("zscore", result)
        return result

    def moving_window_detect(self, data: List[float], window_size: int = 10, threshold: float = 2.0) -> Dict[str, Any]:
        """移动窗口异常检测"""
        self._operation_count += 1
        if len(data) < window_size:
            return {"error": "need at least {} data points".format(window_size), "anomalies": []}
        anomalies = []
        for i in range(window_size, len(data)):
            win = data[i - window_size : i]
            wm = statistics.mean(win)
            ws = statistics.stdev(win) if len(win) > 1 else 0.0
            z = abs((data[i] - wm) / ws) if ws > 0 else 0.0
            if z > threshold:
                anomalies.append({"index": i, "value": data[i], "window_mean": round(wm, 6), "z_score": round(z, 6)})
        result = {
            "method": "moving_window",
            "window_size": window_size,
            "threshold": threshold,
            "total_points": len(data),
            "anomaly_count": len(anomalies),
            "anomaly_rate": round(len(anomalies) / max(len(data), 1), 6),
            "anomalies": anomalies[:50],
        }
        self._save_result("moving_window", result)
        return result

    def threshold_detect(self, data: List[float], lower: float = None, upper: float = None) -> Dict[str, Any]:
        """阈值异常检测"""
        self._operation_count += 1
        anomalies = []
        for i, val in enumerate(data):
            if (lower is not None and val < lower) or (upper is not None and val > upper):
                atype = "low" if lower is not None and val < lower else "high"
                anomalies.append(
                    {"index": i, "value": val, "type": atype, "threshold": lower if atype == "low" else upper}
                )
        result = {
            "method": "threshold",
            "lower": lower,
            "upper": upper,
            "total_points": len(data),
            "anomaly_count": len(anomalies),
            "anomaly_rate": round(len(anomalies) / max(len(data), 1), 6),
            "anomalies": anomalies[:50],
        }
        self._save_result("threshold", result)
        return result

    def isolation_forest_detect(self, data: List[List[float]], contamination: float = 0.1) -> Dict[str, Any]:
        """简化版Isolation Forest异常检测"""
        self._operation_count += 1
        n = len(data)
        if n < 2:
            return {"error": "need at least 2 samples", "anomalies": []}
        scores = [math.sqrt(sum(x**2 for x in row)) for row in data]
        if not scores:
            return {"error": "empty scores", "anomalies": []}
        ms = statistics.mean(scores)
        ss = statistics.stdev(scores) if len(scores) > 1 else 0.0
        anomalies = []
        for i, s in enumerate(scores):
            z = (s - ms) / ss if ss > 0 else 0.0
            if abs(z) > 2.0:
                anomalies.append({"index": i, "score": round(s, 6), "z_score": round(z, 6)})
        result = {
            "method": "isolation_forest_simplified",
            "contamination": contamination,
            "total_samples": n,
            "anomaly_count": len(anomalies),
            "anomaly_rate": round(len(anomalies) / max(n, 1), 6),
            "anomalies": anomalies[:50],
        }
        self._save_result("isolation_forest", result)
        return result

# ============================================================================
# 子引擎3：洞察生成引擎
# ============================================================================

class InsightGenerator:
    """洞察生成引擎 — 趋势/异常/相关性洞察生成"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data", "key_insights.db"
        )
        self.lock = threading.RLock()
        self._operation_count = 0
        self._error_count = 0
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS insights (
                    id TEXT PRIMARY KEY, insight_type TEXT NOT NULL, title TEXT NOT NULL,
                    description TEXT NOT NULL, severity TEXT NOT NULL, confidence REAL NOT NULL,
                    data_json TEXT, created_at REAL NOT NULL, is_reviewed INTEGER DEFAULT 0)""")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ins_type ON insights(insight_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ins_sev ON insights(severity)")
                conn.commit()
        except Exception:
            pass

    def _save_insight(self, insight: Dict[str, Any]):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO insights
                    (id, insight_type, title, description, severity, confidence, data_json, created_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        insight["id"],
                        insight["type"],
                        insight["title"],
                        insight["description"],
                        insight["severity"],
                        insight["confidence"],
                        json.dumps(insight.get("data")),
                        time.time(),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def generate_trend_insight(
        self, time_series: List[Tuple[str, float]], metric_name: str = "metric"
    ) -> Dict[str, Any]:
        """生成趋势洞察"""
        self._operation_count += 1
        if len(time_series) < 2:
            return {"error": "need at least 2 data points", "insights": []}
        sa = StatisticalAnalyzer(self.db_path)
        ts = [(float(i), v) for i, v in enumerate(time_series)]
        trend_result = sa.trend(ts)
        slope = trend_result.get("slope", 0)
        direction = trend_result.get("direction", "stable")
        if direction == "increasing":
            title = "{} 呈上升趋势".format(metric_name)
            desc = "{} 持续上升，斜率 {:.4f}，拟合优度 {:.4f}".format(
                metric_name, slope, trend_result.get("r_squared", 0)
            )
            severity = "high" if abs(slope) > 1.0 else "medium"
        elif direction == "decreasing":
            title = "{} 呈下降趋势".format(metric_name)
            desc = "{} 持续下降，斜率 {:.4f}，拟合优度 {:.4f}".format(
                metric_name, slope, trend_result.get("r_squared", 0)
            )
            severity = "high" if abs(slope) > 1.0 else "medium"
        else:
            title = "{} 保持平稳".format(metric_name)
            desc = "{} 无明显趋势".format(metric_name)
            severity = "low"
        if direction == "increasing":
            rec = "{} 持续上升，建议评估资源".format(metric_name)
        elif direction == "decreasing":
            rec = "{} 持续下降，建议排查原因".format(metric_name)
        else:
            rec = "{} 保持平稳，保持当前策略".format(metric_name)
        insight = {
            "id": str(uuid.uuid4())[:8],
            "type": InsightType.TREND.value,
            "title": title,
            "description": desc,
            "severity": severity,
            "confidence": round(trend_result.get("r_squared", 0.5), 4),
            "data": {
                "metric_name": metric_name,
                "data_points": len(time_series),
                "slope": slope,
                "direction": direction,
            },
            "recommendation": rec,
        }
        self._save_insight(insight)
        return {"insights": [insight], "summary": "生成 1 条趋势洞察"}

    def generate_anomaly_insights(self, anomaly_result: Dict[str, Any], metric_name: str = "metric") -> Dict[str, Any]:
        """基于异常检测结果生成洞察"""
        self._operation_count += 1
        anomalies = anomaly_result.get("anomalies", [])
        if not anomalies:
            return {"insights": [], "summary": "未发现异常"}
        severity = "critical" if anomaly_result.get("anomaly_rate", 0) > 0.1 else "high"
        insight = {
            "id": str(uuid.uuid4())[:8],
            "type": InsightType.ANOMALY.value,
            "title": "{} 检测到 {} 个异常点".format(metric_name, len(anomalies)),
            "description": "异常率 {:.2%}，方法: {}".format(
                anomaly_result.get("anomaly_rate", 0), anomaly_result.get("method", "unknown")
            ),
            "severity": severity,
            "confidence": round(1.0 - anomaly_result.get("anomaly_rate", 0), 4),
            "data": {
                "metric_name": metric_name,
                "anomaly_count": len(anomalies),
                "anomaly_rate": anomaly_result.get("anomaly_rate", 0),
                "method": anomaly_result.get("method"),
            },
            "recommendation": "建议检查异常时间点对应的业务事件",
        }
        self._save_insight(insight)
        return {"insights": [insight], "summary": "生成 1 条异常洞察"}

    def generate_correlation_insights(
        self, corr_result: Dict[str, Any], series_a_name: str, series_b_name: str
    ) -> Dict[str, Any]:
        """生成相关性洞察"""
        self._operation_count += 1
        if "error" in corr_result:
            return {"insights": [], "summary": "数据不足"}
        corr_val = corr_result.get("pearson_correlation", 0)
        strength = corr_result.get("strength", "very_weak")
        if abs(corr_val) < 0.2:
            return {"insights": [], "summary": "相关性较弱"}
        direction = "正" if corr_val > 0 else "负"
        insight = {
            "id": str(uuid.uuid4())[:8],
            "type": InsightType.CORRELATION.value,
            "title": "{} 与 {} 存在 {} {}相关".format(series_a_name, series_b_name, strength, direction),
            "description": "Pearson相关系数 {:.4f}，样本量 {}".format(corr_val, corr_result.get("sample_size", 0)),
            "severity": "medium" if abs(corr_val) > 0.6 else "low",
            "confidence": round(abs(corr_val), 4),
            "data": {
                "series_a": series_a_name,
                "series_b": series_b_name,
                "correlation": corr_val,
                "strength": strength,
            },
            "recommendation": "可将 {} 作为 {} 的领先/滞后指标".format(series_b_name, series_a_name),
        }
        self._save_insight(insight)
        return {"insights": [insight], "summary": "生成 1 条相关性洞察"}

    def list_insights(self, insight_type: str = None, severity: str = None, limit: int = 50) -> Dict[str, Any]:
        """查询已生成的洞察"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    q = "SELECT * FROM insights WHERE 1=1"
                    p = []
                    if insight_type:
                        q += " AND insight_type = ?"
                        p.append(insight_type)
                    if severity:
                        q += " AND severity = ?"
                        p.append(severity)
                    q += " ORDER BY created_at DESC LIMIT ?"
                    p.append(limit)
                    rows = conn.execute(q, p).fetchall()
                    return {"insights": [dict(r) for r in rows], "total": len(rows)}
            except Exception as e:
                return {"insights": [], "error": str(e)}

# ============================================================================
# 子引擎4：知识图谱引擎
# ============================================================================

class KnowledgeGraphEngine:
    """知识图谱引擎 — 实体抽取、关系推理、图谱查询"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data", "key_insights.db"
        )
        self.lock = threading.RLock()
        self._operation_count = 0
        self._error_count = 0
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS kg_entities (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, entity_type TEXT NOT NULL,
                    properties_json TEXT, created_at REAL NOT NULL)""")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_name ON kg_entities(name)")
                conn.execute("""CREATE TABLE IF NOT EXISTS kg_relations (
                    id TEXT PRIMARY KEY, source_id TEXT NOT NULL, target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL, properties_json TEXT,
                    confidence REAL DEFAULT 1.0, created_at REAL NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES kg_entities(id),
                    FOREIGN KEY (target_id) REFERENCES kg_entities(id))""")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_src ON kg_relations(source_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_tgt ON kg_relations(target_id)")
                conn.commit()
        except Exception:
            pass

    def add_entity(self, name: str, entity_type: str = "concept", properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """添加实体"""
        self._operation_count += 1
        eid = hashlib.md5("{}:{}".format(name, entity_type).encode()).hexdigest()[:16]
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO kg_entities VALUES (?,?,?,?,?)",
                        (eid, name, entity_type, json.dumps(properties or {}), time.time()),
                    )
                    conn.commit()
            return {"entity_id": eid, "name": name, "type": entity_type}
        except Exception as e:
            self._error_count += 1
            return {"error": str(e)}

    def _get_or_create_entity(self, name: str, entity_type: str) -> Dict[str, Any]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM kg_entities WHERE name = ?", (name,)).fetchone()
                if row:
                    return {"entity_id": row["id"], "name": row["name"]}
                else:
                    return self.add_entity(name, entity_type)
        except Exception:
            return self.add_entity(name, entity_type)

    def add_relation(
        self,
        source_name: str,
        relation_type: str = "related_to",
        target_name: str = "",
        confidence: float = 1.0,
        properties: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """添加关系"""
        self._operation_count += 1
        if not source_name or not target_name:
            return {"error": "source_name and target_name required"}
        source = self._get_or_create_entity(source_name, "auto")
        target = self._get_or_create_entity(target_name, "auto")
        rid = hashlib.md5(
            "{}:{}:{}".format(source["entity_id"], target["entity_id"], relation_type).encode()
        ).hexdigest()[:16]
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO kg_relations VALUES (?,?,?,?,?,?,?)",
                        (
                            rid,
                            source["entity_id"],
                            target["entity_id"],
                            relation_type,
                            json.dumps(properties or {}),
                            confidence,
                            time.time(),
                        ),
                    )
                    conn.commit()
            return {
                "relation_id": rid,
                "source": source_name,
                "relation": relation_type,
                "target": target_name,
                "confidence": confidence,
            }
        except Exception as e:
            self._error_count += 1
            return {"error": str(e)}

    def query_entity(self, entity_name: str) -> Dict[str, Any]:
        """查询实体及其关联关系"""
        self._operation_count += 1
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                er = conn.execute("SELECT * FROM kg_entities WHERE name = ?", (entity_name,)).fetchone()
                if not er:
                    return {"error": "entity '{}' not found".format(entity_name)}
                out_r = conn.execute(
                    "SELECT r.*, e.name as target_name FROM kg_relations r JOIN kg_entities e ON r.target_id = e.id WHERE r.source_id = ?",
                    (er["id"],),
                ).fetchall()
                in_r = conn.execute(
                    "SELECT r.*, e.name as source_name FROM kg_relations r JOIN kg_entities e ON r.source_id = e.id WHERE r.target_id = ?",
                    (er["id"],),
                ).fetchall()
                return {
                    "entity": dict(er),
                    "out_relations": [dict(r) for r in out_r],
                    "in_relations": [dict(r) for r in in_r],
                }
        except Exception as e:
            self._error_count += 1
            return {"error": str(e)}

    def search_entities(self, keyword: str, entity_type: str = None) -> Dict[str, Any]:
        """搜索实体"""
        self._operation_count += 1
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                q = "SELECT * FROM kg_entities WHERE name LIKE ?"
                p = ["%{}%".format(keyword)]
                if entity_type:
                    q += " AND entity_type = ?"
                    p.append(entity_type)
                rows = conn.execute(q, p).fetchall()
                return {"entities": [dict(r) for r in rows], "total": len(rows)}
        except Exception as e:
            self._error_count += 1
            return {"entities": [], "error": str(e)}

    def get_graph_summary(self) -> Dict[str, Any]:
        """获取图谱概要统计"""
        self._operation_count += 1
        try:
            with sqlite3.connect(self.db_path) as conn:
                ec = conn.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]
                rc = conn.execute("SELECT COUNT(*) FROM kg_relations").fetchone()[0]
                et = conn.execute(
                    "SELECT entity_type, COUNT(*) as cnt FROM kg_entities GROUP BY entity_type"
                ).fetchall()
                rt = conn.execute(
                    "SELECT relation_type, COUNT(*) as cnt FROM kg_relations GROUP BY relation_type"
                ).fetchall()
                return {
                    "entity_count": ec,
                    "relation_count": rc,
                    "entity_types": {r["entity_type"]: r["cnt"] for r in et},
                    "relation_types": {r["relation_type"]: r["cnt"] for r in rt},
                }
        except Exception as e:
            self._error_count += 1
            return {"error": str(e)}

# ============================================================================
# 主模块：KeyInsights
# ============================================================================

class KeyInsights(EnterpriseModule):
    """关键洞察分析引擎 — 智能数据分析与洞察生成"""

    MODULE_ID = "key_insights"
    MODULE_NAME = "KeyInsights"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._operation_count = 0
        self._error_count = 0
        self._stat = StatisticalAnalyzer()
        self._anomaly = AnomalyDetector()
        self._insight = InsightGenerator()
        self._kg = KnowledgeGraphEngine()

    def action_describe(self, p: dict) -> dict:
        data = p.get("data", [])
        if not data:
            return {"success": False, "error": "data required"}
        return {"success": True, "data": self._stat.describe(data)}

    def action_correlation(self, p: dict) -> dict:
        a, b = p.get("series_a", []), p.get("series_b", [])
        if not a or not b:
            return {"success": False, "error": "series_a and series_b required"}
        return {"success": True, "data": self._stat.correlation(a, b)}

    def action_trend(self, p: dict) -> dict:
        ts = p.get("time_series", [])
        if not ts:
            return {"success": False, "error": "time_series required"}
        ts2 = [(float(k), float(v)) for k, v in ts]
        return {"success": True, "data": self._stat.trend(ts2)}

    def action_distribution_fit(self, p: dict) -> dict:
        data = p.get("data", [])
        if not data:
            return {"success": False, "error": "data required"}
        return {"success": True, "data": self._stat.distribution_fit(data)}

    def action_anomaly_zscore(self, p: dict) -> dict:
        data = p.get("data", [])
        threshold = float(p.get("threshold", 3.0))
        if not data:
            return {"success": False, "error": "data required"}
        return {"success": True, "data": self._anomaly.zscore_detect(data, threshold)}

    def action_anomaly_moving_window(self, p: dict) -> dict:
        data = p.get("data", [])
        ws = int(p.get("window_size", 10))
        threshold = float(p.get("threshold", 2.0))
        if not data:
            return {"success": False, "error": "data required"}
        return {"success": True, "data": self._anomaly.moving_window_detect(data, ws, threshold)}

    def action_anomaly_threshold(self, p: dict) -> dict:
        data = p.get("data", [])
        lower = p.get("lower")
        upper = p.get("upper")
        if not data:
            return {"success": False, "error": "data required"}
        if lower is not None:
            lower = float(lower)
        if upper is not None:
            upper = float(upper)
        return {"success": True, "data": self._anomaly.threshold_detect(data, lower, upper)}

    def action_anomaly_isolation_forest(self, p: dict) -> dict:
        data = p.get("data", [])
        contamination = float(p.get("contamination", 0.1))
        if not data:
            return {"success": False, "error": "data required"}
        return {"success": True, "data": self._anomaly.isolation_forest_detect(data, contamination)}

    def action_insight_trend(self, p: dict) -> dict:
        ts = p.get("time_series", [])
        mn = p.get("metric_name", "metric")
        if not ts:
            return {"success": False, "error": "time_series required"}
        return {"success": True, "data": self._insight.generate_trend_insight(ts, mn)}

    def action_insight_anomaly(self, p: dict) -> dict:
        ar = p.get("anomaly_result", {})
        mn = p.get("metric_name", "metric")
        if not ar:
            return {"success": False, "error": "anomaly_result required"}
        return {"success": True, "data": self._insight.generate_anomaly_insights(ar, mn)}

    def action_insight_correlation(self, p: dict) -> dict:
        cr = p.get("corr_result", {})
        sn = p.get("series_a_name", "Series A")
        tn = p.get("series_b_name", "Series B")
        if not cr:
            return {"success": False, "error": "corr_result required"}
        return {"success": True, "data": self._insight.generate_correlation_insights(cr, sn, tn)}

    def action_insight_list(self, p: dict) -> dict:
        it = p.get("insight_type")
        se = p.get("severity")
        limit = int(p.get("limit", 50))
        return {"success": True, "data": self._insight.list_insights(it, se, limit)}

    def action_kg_add_entity(self, p: dict) -> dict:
        name = p.get("name", "")
        et = p.get("entity_type", "concept")
        props = p.get("properties", {})
        if not name:
            return {"success": False, "error": "name required"}
        return {"success": True, "data": self._kg.add_entity(name, et, props)}

    def action_kg_add_relation(self, p: dict) -> dict:
        sn = p.get("source_name", "")
        rt = p.get("relation_type", "related_to")
        tn = p.get("target_name", "")
        cf = float(p.get("confidence", 1.0))
        if not sn or not tn:
            return {"success": False, "error": "source_name and target_name required"}
        return {"success": True, "data": self._kg.add_relation(sn, rt, tn, cf)}

    def action_kg_query_entity(self, p: dict) -> dict:
        en = p.get("entity_name", "")
        if not en:
            return {"success": False, "error": "entity_name required"}
        return {"success": True, "data": self._kg.query_entity(en)}

    def action_kg_search_entities(self, p: dict) -> dict:
        kw = p.get("keyword", "")
        et = p.get("entity_type")
        if not kw:
            return {"success": False, "error": "keyword required"}
        return {"success": True, "data": self._kg.search_entities(kw, et)}

    def action_kg_summary(self, p: dict) -> dict:
        return {"success": True, "data": self._kg.get_graph_summary()}

    def action_analyze_dataset(self, p: dict) -> dict:
        data = p.get("data", [])
        mn = p.get("metric_name", "metric")
        if not data:
            return {"success": False, "error": "data required"}
        stat_r = self._stat.describe(data)
        anom_r = self._anomaly.zscore_detect(data, 2.5)
        ins_r = self._insight.generate_anomaly_insights(anom_r, mn)
        return {
            "success": True,
            "data": {
                "metric_name": mn,
                "statistical_summary": stat_r,
                "anomaly_detection": anom_r,
                "insights": ins_r.get("insights", []),
                "summary": "分析完成，发现 {} 个异常点".format(anom_r.get("anomaly_count", 0)),
            },
        }

    def action_full_analysis(self, p: dict) -> dict:
        ts = p.get("time_series", [])
        mn = p.get("metric_name", "metric")
        if not ts:
            return {"success": False, "error": "time_series required"}
        values = [float(v) for _, v in ts]
        stat = self._stat.describe(values)
        trend = self._stat.trend([(float(i), v) for i, v in enumerate(ts)])
        az = self._anomaly.zscore_detect(values, 2.5)
        am = self._anomaly.moving_window_detect(values, min(10, max(3, len(values) // 3)))
        ti = self._insight.generate_trend_insight(ts, mn)
        ai = self._insight.generate_anomaly_insights(az, mn)
        return {
            "success": True,
            "data": {
                "metric_name": mn,
                "data_points": len(ts),
                "statistical_summary": stat,
                "trend_analysis": trend,
                "anomaly_detection": {"zscore": az, "moving_window": am},
                "insights": {"trend": ti.get("insights", []), "anomaly": ai.get("insights", [])},
                "summary": "全量分析完成，发现 {} 个异常".format(az.get("anomaly_count", 0)),
            },
        }

    def action_status(self, p: dict) -> dict:
        return {
            "success": True,
            "data": {
                "module": self.MODULE_ID,
                "version": self.VERSION,
                "status": "running",
                "operations": self._operation_count,
                "errors": self._error_count,
                "capabilities": [
                    "describe",
                    "correlation",
                    "trend",
                    "distribution_fit",
                    "anomaly_zscore",
                    "anomaly_moving_window",
                    "anomaly_threshold",
                    "anomaly_isolation_forest",
                    "insight_trend",
                    "insight_anomaly",
                    "insight_correlation",
                    "insight_list",
                    "kg_add_entity",
                    "kg_add_relation",
                    "kg_query_entity",
                    "kg_search_entities",
                    "kg_summary",
                    "analyze_dataset",
                    "full_analysis",
                ],
            },
        }

    def action_help(self, p: dict) -> dict:
        return {
            "success": True,
            "data": {
                "module": self.MODULE_ID,
                "version": self.VERSION,
                "level": self.MODULE_LEVEL,
                "actions": [
                    {"name": "describe", "desc": "描述性统计"},
                    {"name": "correlation", "desc": "相关性分析"},
                    {"name": "trend", "desc": "趋势检测"},
                    {"name": "distribution_fit", "desc": "分布拟合检测"},
                    {"name": "anomaly_zscore", "desc": "Z-Score异常检测"},
                    {"name": "anomaly_moving_window", "desc": "移动窗口异常检测"},
                    {"name": "anomaly_threshold", "desc": "阈值异常检测"},
                    {"name": "anomaly_isolation_forest", "desc": "Isolation Forest异常检测"},
                    {"name": "insight_trend", "desc": "生成趋势洞察"},
                    {"name": "insight_anomaly", "desc": "生成异常洞察"},
                    {"name": "insight_correlation", "desc": "生成相关性洞察"},
                    {"name": "insight_list", "desc": "查询洞察列表"},
                    {"name": "kg_add_entity", "desc": "添加知识图谱实体"},
                    {"name": "kg_add_relation", "desc": "添加知识图谱关系"},
                    {"name": "kg_query_entity", "desc": "查询知识图谱实体"},
                    {"name": "kg_search_entities", "desc": "搜索知识图谱实体"},
                    {"name": "kg_summary", "desc": "获取知识图谱概要"},
                    {"name": "analyze_dataset", "desc": "综合分析数据集"},
                    {"name": "full_analysis", "desc": "全量分析"},
                    {"name": "status", "desc": "模块状态"},
                    {"name": "help", "desc": "帮助信息"},
                ],
            },
        }

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self._operation_count += 1
        action_map = {
            "status": self.action_status,
            "help": self.action_help,
            "describe": self.action_describe,
            "correlation": self.action_correlation,
            "trend": self.action_trend,
            "distribution_fit": self.action_distribution_fit,
            "anomaly_zscore": self.action_anomaly_zscore,
            "anomaly_moving_window": self.action_anomaly_moving_window,
            "anomaly_threshold": self.action_anomaly_threshold,
            "anomaly_isolation_forest": self.action_anomaly_isolation_forest,
            "insight_trend": self.action_insight_trend,
            "insight_anomaly": self.action_insight_anomaly,
            "insight_correlation": self.action_insight_correlation,
            "insight_list": self.action_insight_list,
            "kg_add_entity": self.action_kg_add_entity,
            "kg_add_relation": self.action_kg_add_relation,
            "kg_query_entity": self.action_kg_query_entity,
            "kg_search_entities": self.action_kg_search_entities,
            "kg_summary": self.action_kg_summary,
            "analyze_dataset": self.action_analyze_dataset,
            "full_analysis": self.action_full_analysis,
        }
        try:
            handler = action_map.get(action)
            if handler:
                result = handler(params)
                return result
            return {
                "success": False,
                "error": "unknown action: {}".format(action),
                "available_actions": list(action_map.keys()),
            }
        except Exception as e:
            self._error_count += 1
            return {"success": False, "error": str(e)}

module_class = KeyInsights
