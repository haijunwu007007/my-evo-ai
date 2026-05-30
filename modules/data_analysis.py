# -*- coding: utf-8 -*-
"""
# Grade: A
AUTO-EVO-AI V0.1 — 数据分析引擎（生产级）
========================================
模块ID: data-analysis
功能：描述统计/相关系数/回归/异常检测/聚类/归一化 + delegate读取sysmon数据+CSV导出
"""
__module_meta__ = {"id":"data-analysis","name":"Data Analysis","version":"V0.1","group":"data","grade":"A",
    "tags":["data","analysis","statistics","production"],
    "description":"数据分析引擎 - 统计/相关性/异常检测/回归/聚类 + sysmon数据集成 + CSV导出"}

import time, uuid, json, os, logging, math, sqlite3, csv, io
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport,
    CircuitBreakerMixin, RateLimiterMixin, Result)
from modules._base.metrics import metrics_collector

logger = logging.getLogger("evo.data-analysis")


class DataAnalysis(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """数据分析引擎 — 统计/相关系数/回归/异常检测/聚类/归一化 + 系统数据集成"""

    MODULE_ID = "data-analysis"
    MODULE_NAME = "数据分析"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config=None):
        super().__init__(config)
        self._results = {}

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING
        logger.info("数据分析引擎就绪")

    def health_check(self) -> HealthReport:
        return HealthReport(status=self.status.value, healthy=True, module_id=self.MODULE_ID)

    async def execute(self, action, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _dispatch(self, p):
        action = p.get("action", "describe")
        data = p.get("data", [])
        vals = [v for v in data if isinstance(v, (int, float))]
        dispatch = {
            "describe": lambda: self._describe(vals, p),
            "correlation": lambda: self._correlation(p),
            "outliers": lambda: self._outliers(vals, p),
            "anomaly": lambda: self._outliers(vals, p),
            "histogram": lambda: self._histogram(vals, p),
            "normalize": lambda: self._normalize(vals, p),
            "regression": lambda: self._regression(p),
            "clustering": lambda: self._clustering(vals, p),
            "summarize": lambda: self._summarize(p),
            "export_csv": lambda: self._export_csv(vals, p),
            "frequency": lambda: self._frequency(vals, p),
            "sysmon_data": lambda: self._load_sysmon_data(p.get("table","system_metrics"), p.get("limit",500)),
        }
        handler = dispatch.get(action)
        if handler:
            return handler()
        return {"error": f"unknown: {action}"}

    def _load_sysmon_data(self, table="system_metrics", limit=500):
        """从系统SQLite读取真实数据"""
        try:
            # 系统监控数据路径
            paths = ["backend/data/sysmon.db","data/sysmon.db","config/evo_system.db"]
            for p in paths:
                ap = os.path.join(os.path.dirname(os.path.dirname(__file__)), p)
                if os.path.exists(ap):
                    import pandas as pd
                    try:
                        # 参数化查询防止SQL注入
                        safe_tbl = "".join(c for c in table if c.isalnum() or c == "_")
                        if not safe_tbl:
                            return {"success": False, "error": f"非法表名: {table}"}
                        df = pd.read_sql(f"SELECT * FROM {safe_tbl} LIMIT ?", sqlite3.connect(ap), params=(int(limit),))
                        return {"success":True,"rows":len(df),"columns":list(df.columns),
                                "records":json.loads(df.to_json(orient="records"))}
                    except Exception:
                        pass
            return {"success":False,"error":"数据库未找到"}
        except ImportError:
            return {"success":False,"error":"pandas未安装"}
        except Exception as e:
            return {"success":False,"error":str(e)}

    def _require_data(self, vals, method="describe"):
        if not vals:
            return {"error": f"need numeric 'data' array for {method}",
                    "hint": {"action": method, "data": [1,2,3,4,5,6,7,8,9,10]}}
        return None

    def _basic_stats(self, vals):
        n = len(vals)
        mean = sum(vals) / n
        variance = sum((v-mean)**2 for v in vals) / n
        std = variance ** 0.5
        s_vals = sorted(vals)
        skew = sum((v-mean)**3 for v in vals) / (n * std**3 + 1e-10) if std > 0 else 0
        kurt = sum((v-mean)**4 for v in vals) / (n * std**4 + 1e-10) - 3 if std > 0 else 0
        return n, mean, std, variance, s_vals, skew, kurt

    def _percentile(self, s_vals, p):
        n = len(s_vals)
        idx = int(n * p / 100)
        return s_vals[min(idx, n-1)]

    # ── 动作实现 ──

    def _describe(self, vals, p):
        err = self._require_data(vals, "describe")
        if err: return err
        n, mean, std, variance, sv, skew, kurt = self._basic_stats(vals)
        return {"success": True, "stats": {
            "count": n, "mean": round(mean, 4), "std": round(std, 4),
            "variance": round(variance, 4), "min": min(vals),
            "p1": self._percentile(sv, 1), "p5": self._percentile(sv, 5),
            "p25": self._percentile(sv, 25),
            "p50": self._percentile(sv, 50),
            "p75": self._percentile(sv, 75),
            "p95": self._percentile(sv, 95), "p99": self._percentile(sv, 99),
            "max": max(vals), "range": max(vals)-min(vals),
            "skewness": round(skew, 4), "kurtosis": round(kurt, 4),
        }}

    def _correlation(self, p):
        x = p.get("x", [])
        y = p.get("y", [])
        if not x or not y or len(x) != len(y):
            return {"error": "need 'x' and 'y' arrays of equal length"}
        n = len(x)
        mx, my = sum(x)/n, sum(y)/n
        sx = math.sqrt(sum((v-mx)**2 for v in x)/n)
        sy = math.sqrt(sum((v-my)**2 for v in y)/n)
        r = sum((x[i]-mx)*(y[i]-my) for i in range(n)) / (n*sx*sy + 1e-10)
        return {"success": True, "pearson": round(r, 4),
                "interpretation": "strong positive" if r > 0.7 else "strong negative" if r < -0.7 else "moderate" if abs(r) >= 0.3 else "weak"}

    def _regression(self, p):
        x = p.get("x", [])
        y = p.get("y", [])
        if not x or not y or len(x) != len(y):
            return {"error": "need 'x' and 'y' arrays of equal length"}
        n = len(x)
        mx, my = sum(x)/n, sum(y)/n
        num = sum((x[i]-mx)*(y[i]-my) for i in range(n))
        den = sum((x[i]-mx)**2 for i in range(n))
        slope = num / (den + 1e-10)
        intercept = my - slope * mx
        residuals = [y[i] - (slope*x[i] + intercept) for i in range(n)]
        rmse = math.sqrt(sum(r**2 for r in residuals) / n)
        ss_res = sum(r**2 for r in residuals)
        ss_tot = sum((y[i]-my)**2 for i in range(n))
        r2 = 1 - ss_res / (ss_tot + 1e-10)
        return {"success": True, "slope": round(slope, 4), "intercept": round(intercept, 4),
                "r_squared": round(r2, 4), "rmse": round(rmse, 4),
                "formula": f"y = {round(slope,4)}x + {round(intercept,4)}",
                "residuals": [round(r, 4) for r in residuals[:20]],
                "n": n}

    def _outliers(self, vals, p):
        err = self._require_data(vals, "outliers")
        if err: return err
        n, mean, std, variance, sv, skew, kurt = self._basic_stats(vals)
        method = p.get("method", "iqr").lower()
        if method == "zscore":
            threshold = float(p.get("threshold", 2.5))
            anomalies = [v for v in vals if abs(v-mean) > threshold * (std or 1)]
            return {"success": True, "method": "zscore", "threshold": threshold,
                    "anomalies": anomalies, "anomaly_rate": round(len(anomalies)/n*100, 2),
                    "count": len(anomalies), "total": n}
        q1, q3 = sv[n//4], sv[3*n//4]
        iqr = q3 - q1
        lower, upper = q1 - 1.5*iqr, q3 + 1.5*iqr
        anomalies = [v for v in vals if v < lower or v > upper]
        return {"success": True, "method": "iqr", "q1": round(q1, 4), "q3": round(q3, 4),
                "iqr": round(iqr, 4), "lower_fence": round(lower, 4), "upper_fence": round(upper, 4),
                "anomalies": anomalies, "anomaly_rate": round(len(anomalies)/n*100, 2),
                "count": len(anomalies), "total": n}

    def _histogram(self, vals, p):
        err = self._require_data(vals, "histogram")
        if err: return err
        bins = max(2, min(int(p.get("bins", 10)), 100))
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return {"success": True, "histogram": [len(vals)], "bin_width": 0, "min": mn, "max": mx, "bins": 1}
        bw = (mx - mn) / bins
        hist = [0] * bins
        for v in vals:
            idx = min(bins-1, int((v - mn) / bw))
            hist[idx] += 1
        return {"success": True, "histogram": hist, "bin_width": round(bw, 4),
                "min": mn, "max": mx, "bins": bins}

    def _normalize(self, vals, p):
        err = self._require_data(vals, "normalize")
        if err: return err
        method = p.get("method", "minmax").lower()
        n, mean, std, variance, sv, skew, kurt = self._basic_stats(vals)
        if method == "minmax":
            mn, mx = min(vals), max(vals)
            nrm = [round((v-mn)/(mx-mn+1e-10), 4) for v in vals]
        elif method == "zscore":
            sigma = std if std > 0 else 1
            nrm = [round((v-mean)/sigma, 4) for v in vals]
        else:
            return {"error": f"unknown method: {method}"}
        return {"success": True, "method": method, "normalized": nrm,
                "min": round(min(nrm), 4), "max": round(max(nrm), 4)}

    def _clustering(self, vals, p):
        k = int(p.get("k", 2))
        n = len(vals)
        if k < 2 or k > n:
            return {"error": f"k must be 2-{n}"}
        centroids = [vals[i] for i in range(k)]
        for iteration in range(100):
            clusters = [[] for _ in range(k)]
            for v in vals:
                idx = min(range(k), key=lambda i: abs(v-centroids[i]))
                clusters[idx].append(v)
            new_centroids = [sum(c)/len(c) if c else centroids[i] for i, c in enumerate(clusters)]
            if all(abs(new_centroids[i]-centroids[i]) < 1e-8 for i in range(k)):
                break
            centroids = new_centroids
        wcss = sum(sum((v-centroids[i])**2 for v in c) for i, c in enumerate(clusters)) if clusters else 0
        return {"success": True, "k": k, "wcss": round(wcss, 4),
                "clusters": [{"centroid": round(centroids[i], 4), "size": len(clusters[i]),
                              "min": round(min(clusters[i]), 4) if clusters[i] else None,
                              "max": round(max(clusters[i]), 4) if clusters[i] else None,
                              "mean": round(sum(clusters[i])/len(clusters[i]), 4) if clusters[i] else None}
                             for i in range(k)],
                "iterations": iteration+1}

    def _summarize(self, p):
        """通过 delegate 读取 sysmon 数据库生成汇总报告"""
        report = {"source": "delegate.persistence", "tables_found": []}
        try:
            # 尝试通过 delegate 读取 sysmon 数据
            db_result = None
            try:
                db_result = self.delegate.persistence.query("sysmon_metrics", limit=20)
            except Exception:
                pass
            if db_result and isinstance(db_result, dict) and "data" in db_result:
                data = db_result["data"]
                report["tables_found"].append("sysmon_metrics")
                if data:
                    import statistics
                    cpus = [r.get("cpu", 0) for r in data if "cpu" in r]
                    mems = [r.get("memory", 0) for r in data if "memory" in r]
                    report["sysmon_metrics"] = {
                        "records": len(data),
                        "cpu": {"avg": round(statistics.mean(cpus), 1), "max": round(max(cpus), 1)} if cpus else None,
                        "memory": {"avg": round(statistics.mean(mems), 1), "max": round(max(mems), 1)} if mems else None,
                    }
                    return {"success": True, "report": report}
            # 兜底：直接读 sysmon.db
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sysmon.db")
            if os.path.exists(db_path):
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cur = conn.execute("SELECT COUNT(*) as cnt, AVG(cpu) as avg_cpu, AVG(memory) as avg_mem FROM sysmon_metrics")
                row = dict(cur.fetchone())
                conn.close()
                report["tables_found"].append("sysmon.db (direct)")
                report["sysmon_summary"] = {"records": row["cnt"], "avg_cpu": round(row["avg_cpu"] or 0, 1),
                                             "avg_memory": round(row["avg_mem"] or 0, 1)}
                return {"success": True, "report": report}
            return {"success": True, "report": report, "message": "no sysmon data available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _export_csv(self, vals, p):
        err = self._require_data(vals, "export_csv")
        if err: return err
        column = p.get("column", "value")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["index", column])
        for i, v in enumerate(vals):
            writer.writerow([i, v])
        csv_str = output.getvalue()
        output.close()
        return {"success": True, "csv": csv_str, "rows": len(vals), "filename": p.get("filename", "export.csv")}

    def _frequency(self, vals, p):
        err = self._require_data(vals, "frequency")
        if err: return err
        freq = {}
        for v in vals:
            freq[v] = freq.get(v, 0) + 1
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        limit = int(p.get("limit", 20))
        from collections import Counter
        counter = Counter(vals)
        return {"success": True, "total": len(vals), "unique": len(freq),
                "frequency": [{"value": k, "count": v, "percent": round(v/len(vals)*100, 2)}
                              for k, v in sorted_freq[:limit]]}

    async def shutdown(self) -> None:
        self._results.clear()
        self.status = ModuleStatus.STOPPED

module_class = DataAnalysis
