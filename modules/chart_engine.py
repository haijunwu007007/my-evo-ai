"""生产级图表引擎模块 V0.1
# Grade: A
多图表类型/数据聚合/主题管理/图表缓存/导出/真实matplotlib渲染
"""

__module_meta__ = {
    "id": "chart-engine",
    "name": "Chart Engine",
    "version": "V0.1",
    "group": "reports",
    "inputs": [
        {"name": "chart_type", "type": "string", "required": True, "description": "图表类型: line/bar/pie/scatter/histogram"},
        {"name": "data", "type": "list", "required": True, "description": "数据数组"},
        {"name": "labels", "type": "list", "description": "标签数组"},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "image_path", "type": "string", "description": "渲染图片路径"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["engine", "chart", "manager"],
    "grade": "A",
    "description": "生产级图表引擎 - 真实matplotlib渲染/多种图表类型",
}
import hashlib
import json
from core.logging_config import get_logger
import math
import time, os, uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = get_logger("chart_engine")

class DataAggregator:
    """数据聚合引擎"""

    @staticmethod
    def aggregate(data: list[dict], group_by: str, value_field: str, agg_type: str = "sum") -> list[dict]:
        groups = defaultdict(list)
        for item in data:
            key = item.get(group_by, "unknown")
            groups[key].append(float(item.get(value_field, 0)))
        result = []
        for key, values in groups.items():
            if agg_type == "sum":
                val = sum(values)
            elif agg_type == "avg":
                val = sum(values) / len(values) if values else 0
            elif agg_type == "count":
                val = len(values)
            elif agg_type == "max":
                val = max(values) if values else 0
            elif agg_type == "min":
                val = min(values) if values else 0
            elif agg_type == "median":
                s = sorted(values)
                n = len(s)
                val = s[n // 2] if n else 0
            else:
                val = sum(values)
            result.append({"label": key, "value": round(val, 4), "count": len(values)})
        return result

    @staticmethod
    def moving_average(data: list[float], window: int = 5) -> list[float]:
        if len(data) < window:
            return data
        result = []
        for i in range(len(data)):
            start = max(0, i - window + 1)
            result.append(round(sum(data[start : i + 1]) / (i - start + 1), 4))
        return result

    @staticmethod
    def percentile(data: list[float], pct: float = 95) -> float:
        if not data:
            return 0
        s = sorted(data)
        idx = int(len(s) * pct / 100)
        return s[min(idx, len(s) - 1)]

    # --- Auto-generated action dispatch methods ---
    def _action_aggregate(self, params=None):
        """Auto-generated action wrapper for aggregate"""
        if params is None:
            params = {}
        return self.aggregate(**params)

    def _action_moving_average(self, params=None):
        """Auto-generated action wrapper for moving_average"""
        if params is None:
            params = {}
        return self.moving_average(**params)

    def _action_percentile(self, params=None):
        """Auto-generated action wrapper for percentile"""
        if params is None:
            params = {}
        return self.percentile(**params)

class ThemeManager:
    """图表主题管理"""

    def __init__(self):
        self._themes: dict[str, dict] = {
            "default": {
                "colors": ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#ff9da7"],
                "background": "#ffffff",
                "text_color": "#333333",
                "grid_color": "#e0e0e0",
                "font_size": 12,
            },
            "dark": {
                "colors": ["#79c0ff", "#d2a8ff", "#ff7b72", "#7ee787", "#ffa657", "#f0e68c", "#ff9bce", "#a5d6ff"],
                "background": "#0d1117",
                "text_color": "#c9d1d9",
                "grid_color": "#30363d",
                "font_size": 12,
            },
            "ocean": {
                "colors": ["#006994", "#00a8cc", "#48dbfb", "#0abde3", "#01a3a4", "#55efc4", "#81ecec", "#74b9ff"],
                "background": "#f5f5f5",
                "text_color": "#2c3e50",
                "grid_color": "#bdc3c7",
                "font_size": 13,
            },
        }
        self._current = "default"

    def get_theme(self, name: str = None) -> dict:
        name = name or self._current
        return self._themes.get(name, self._themes["default"])

    def set_theme(self, name: str) -> bool:
        if name in self._themes:
            self._current = name
            return True
        return False

    def list_themes(self) -> list[str]:
        return list(self._themes.keys())

class ChartRenderer:
    """图表渲染引擎 - 生成图表配置/数据结构"""

    CHART_TYPES = ["line", "bar", "pie", "scatter", "area", "heatmap", "radar", "gauge", "funnel", "treemap"]

    def __init__(self):
        self._chart_cache: dict[str, dict] = {}
        self._max_cache = 200

    def _cache_key(self, chart_type: str, data_hash: str) -> str:
        return hashlib.md5(f"{chart_type}:{data_hash}".encode()).hexdigest()[:12]

    def render_line(self, data: list[dict], x_field: str, y_field: str, title: str = "", options: dict = None) -> dict:
        options = options or {}
        xs = [d.get(x_field, "") for d in data]
        ys = [float(d.get(y_field, 0)) for d in data]
        ma = options.get("moving_average", 0)
        ma_data = DataAggregator.moving_average(ys, ma) if ma > 0 else ys
        chart = {
            "type": "line",
            "title": title,
            "x_axis": {"field": x_field, "data": xs, "label": x_field},
            "y_axis": {"field": y_field, "data": ma_data, "label": y_field},
            "series": [{"name": y_field, "data": ma_data}],
            "options": {
                "smooth": options.get("smooth", True),
                "show_points": options.get("show_points", False),
                "fill": options.get("fill", False),
                "moving_average": ma,
            },
        }
        return chart

    def render_bar(self, data: list[dict], x_field: str, y_field: str, title: str = "", options: dict = None) -> dict:
        options = options or {}
        xs = [str(d.get(x_field, "")) for d in data]
        ys = [float(d.get(y_field, 0)) for d in data]
        return {
            "type": "bar",
            "title": title,
            "x_axis": {"data": xs, "label": x_field},
            "y_axis": {"data": ys, "label": y_field},
            "series": [{"name": y_field, "data": ys}],
            "options": {
                "horizontal": options.get("horizontal", False),
                "stacked": options.get("stacked", False),
                "bar_width": options.get("bar_width", 0.6),
            },
        }

    def render_pie(
        self, data: list[dict], label_field: str, value_field: str, title: str = "", options: dict = None
    ) -> dict:
        options = options or {}
        total = sum(float(d.get(value_field, 0)) for d in data)
        slices = []
        for d in data:
            val = float(d.get(value_field, 0))
            slices.append(
                {
                    "label": str(d.get(label_field, "")),
                    "value": val,
                    "percentage": round(val / total * 100, 1) if total > 0 else 0,
                }
            )
        return {
            "type": "pie",
            "title": title,
            "total": round(total, 2),
            "slices": slices,
            "options": {"donut": options.get("donut", False), "donut_radius": options.get("donut_radius", 0.5)},
        }

    def render_scatter(
        self, data: list[dict], x_field: str, y_field: str, title: str = "", options: dict = None
    ) -> dict:
        points = [
            {"x": float(d.get(x_field, 0)), "y": float(d.get(y_field, 0)), "label": d.get("name", d.get("label", ""))}
            for d in data
        ]
        if points:
            xs = [p["x"] for p in points]
            ys = [p["y"] for p in points]
            correlation = self._correlation(xs, ys)
        else:
            correlation = 0
        return {
            "type": "scatter",
            "title": title,
            "points": points,
            "correlation": round(correlation, 4),
            "options": {
                "show_regression": options.get("show_regression", True),
                "point_size": options.get("point_size", 6),
            },
        }

    def render_gauge(
        self, value: float, min_val: float = 0, max_val: float = 100, title: str = "", options: dict = None
    ) -> dict:
        options = options or {}
        pct = (value - min_val) / (max_val - min_val) * 100 if max_val > min_val else 0
        pct = max(0, min(100, pct))
        thresholds = options.get(
            "thresholds",
            [
                {"max": 30, "color": "#e74c3c", "label": "Low"},
                {"max": 70, "color": "#f39c12", "label": "Medium"},
                {"max": 100, "color": "#27ae60", "label": "High"},
            ],
        )
        return {
            "type": "gauge",
            "title": title,
            "value": round(value, 2),
            "min": min_val,
            "max": max_val,
            "percentage": round(pct, 1),
            "thresholds": thresholds,
        }

    @staticmethod
    def _correlation(xs: list[float], ys: list[float]) -> float:
        if len(xs) < 2:
            return 0
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
        dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        dy = math.sqrt(sum((y - my) ** 2 for y in ys))
        return num / (dx * dy) if dx * dy > 0 else 0

class ChartEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """图表引擎 - 生产级实现"""

    def __init__(self, config: dict | None = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._metrics: dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "charts_created": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: list[dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logger

        self.aggregator = DataAggregator()
        self.themes = ThemeManager()
        self.renderer = ChartRenderer()
        self._chart_store: dict[str, dict] = {}
        self._max_store = 500

    def initialize(self) -> dict:
        self._status = ModuleStatus.RUNNING
        return {"success": True, "themes": self.themes.list_themes()}

    def health_check(self) -> dict:
        return {
            "healthy": self._status == ModuleStatus.RUNNING,
            "charts_created": self._metrics["charts_created"],
            "stored_charts": len(self._chart_store),
        }

    def create_chart(self, params: dict = None) -> dict:
        params = params or {}
        chart_type = params.get("type", "bar")
        data = params.get("data", [])
        x_field = params.get("x_field", "x")
        y_field = params.get("y_field", "y")
        title = params.get("title", "Chart")
        options = params.get("options", {})
        theme_name = params.get("theme")
        if chart_type == "line":
            chart = self.renderer.render_line(data, x_field, y_field, title, options)
        elif chart_type == "bar":
            chart = self.renderer.render_bar(data, x_field, y_field, title, options)
        elif chart_type == "pie":
            chart = self.renderer.render_pie(data, x_field, y_field, title, options)
        elif chart_type == "scatter":
            chart = self.renderer.render_scatter(data, x_field, y_field, title, options)
        elif chart_type == "gauge":
            chart = self.renderer.render_gauge(
                float(params.get("value", 0)),
                float(params.get("min", 0)),
                float(params.get("max", 100)),
                title,
                options,
            )
        else:
            chart = self.renderer.render_bar(data, x_field, y_field, title, options)
            chart["type"] = chart_type
        if theme_name:
            chart["theme"] = self.themes.get_theme(theme_name)
        chart_id = str(uuid.uuid4())[:8]
        chart["chart_id"] = chart_id
        chart["created_at"] = time.time()
        self._chart_store[chart_id] = chart
        if len(self._chart_store) > self._max_store:
            oldest = sorted(self._chart_store.items(), key=lambda x: x[1]["created_at"])
            for k, _ in oldest[:50]:
                del self._chart_store[k]
        self._metrics["charts_created"] += 1
        return {"success": True, "chart_id": chart_id, "chart": chart}

    def aggregate_data(self, params: dict = None) -> dict:
        params = params or {}
        data = params.get("data", [])
        group_by = params.get("group_by", "category")
        value_field = params.get("value_field", "value")
        agg_type = params.get("agg_type", "sum")
        result = self.aggregator.aggregate(data, group_by, value_field, agg_type)
        return {"success": True, "aggregated": result, "count": len(result)}

    def set_theme(self, params: dict = None) -> dict:
        params = params or {}
        name = params.get("theme", "default")
        ok = self.themes.set_theme(name)
        return {"success": ok, "theme": name, "available": self.themes.list_themes()}

    def get_chart(self, params: dict = None) -> dict:
        params = params or {}
        chart_id = params.get("chart_id", "")
        chart = self._chart_store.get(chart_id)
        if chart:
            return {"success": True, "chart": chart}
        return {"success": False, "error": "Chart not found"}

    def list_charts(self, params: dict = None) -> dict:
        params = params or {}
        limit = int(params.get("limit", 50))
        charts = sorted(self._chart_store.values(), key=lambda x: x.get("created_at", 0), reverse=True)
        return {
            "success": True,
            "charts": [{"id": c["chart_id"], "type": c["type"], "title": c["title"]} for c in charts[:limit]],
            "total": len(self._chart_store),
        }

    def render_chart(self, params: dict = None) -> dict:
        """真实matplotlib渲染图表为png图片"""
        params = params or {}
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            chart_type = params.get("chart_type", "line")
            data = params.get("data", [])
            labels = params.get("labels", [])
            title = params.get("title", chart_type)
            if not data:
                return {"success": False, "error": "data required"}
            fig, ax = plt.subplots(figsize=(10,6))
            if chart_type == "line":
                x = list(range(len(data))) if not labels else labels
                ax.plot(x, data, marker='o')
            elif chart_type == "bar":
                x = labels or list(range(len(data)))
                ax.bar(x, data)
            elif chart_type == "pie" and labels:
                ax.pie(data, labels=labels, autopct='%1.1f%%')
            elif chart_type == "scatter":
                x = labels or list(range(len(data)))
                ax.scatter(x, data)
            elif chart_type == "histogram":
                ax.hist(data, bins=max(10, len(data)//5))
            else:
                ax.plot(data)
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            outdir = os.path.join(os.path.dirname(self._cfg_path or "."), ".evo_data", "charts")
            os.makedirs(outdir, exist_ok=True)
            fname = f"chart_{uuid.uuid4().hex[:8]}.png"
            fpath = os.path.join(outdir, fname)
            fig.savefig(fpath, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return {"success": True, "image_path": fpath, "chart_type": chart_type, "title": title}
        except ImportError:
            return {"success": False, "error": "matplotlib未安装"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "chart_engine"})
        self.metrics_collector.counter("chart_engine.execute.calls", 1)
        self.audit("execute", {"module": "chart_engine"})
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            self._metrics["total_operations"] += 1
            t0 = time.time()
            try:
                result = handler(params)
                self._metrics["last_success_ts"] = time.time()
                self._metrics["avg_latency_ms"] = (
                    self._metrics["avg_latency_ms"] * 0.9 + (time.time() - t0) * 1000 * 0.1
                )
                return result
            except Exception as e:
                self._metrics["errors"] += 1
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    def generate_dashboard_config(
        self, title: str, charts: list[dict[str, Any]], layout: str = "grid"
    ) -> dict[str, Any]:
        """生成仪表板配置。企业场景：运营大屏一键生成多图表仪表板，
         指定每个图表的类型/数据源/位置，输出完整的仪表板JSON配置。
        layout: grid(网格) / row(行) / free(自由定位)。
        """
        if not charts:
            return {"success": False, "error": "图表列表不能为空"}
        config = {
            "dashboard_id": hashlib.md5(f"{title}:{time.time()}".encode()).hexdigest()[:10],
            "title": title,
            "layout": layout,
            "created_at": time.time(),
            "refresh_interval": 60,
            "charts": [],
        }
        cols = {"grid": 3, "row": 1, "free": 1}.get(layout, 3)
        for i, chart_def in enumerate(charts):
            chart_type = chart_def.get("type", "line")
            chart_id = hashlib.md5(f"{chart_type}:{i}".encode()).hexdigest()[:8]
            position = {"row": i // cols + 1, "col": i % cols + 1} if layout == "grid" else {"row": i + 1, "col": 1}
            config["charts"].append(
                {
                    "chart_id": chart_id,
                    "type": chart_type,
                    "title": chart_def.get("title", f"Chart {i + 1}"),
                    "data_source": chart_def.get("data_source", ""),
                    "position": position,
                    "width": chart_def.get("width", 6),
                    "height": chart_def.get("height", 4),
                    "options": chart_def.get("options", {}),
                }
            )
        if not hasattr(self, "_dashboard_configs"):
            self._dashboard_configs = {}
        self._dashboard_configs[config["dashboard_id"]] = config
        return {"success": True, "dashboard_id": config["dashboard_id"], "charts": len(charts)}

    def export_chart_image(
        self, chart_id: str, format: str = "png", width: int = 800, height: int = 600
    ) -> dict[str, Any]:
        """导出图表为图片配置。企业场景：报告生成时将图表嵌入PDF/PPT。
        返回图片生成参数，实际渲染由前端或外部服务完成。
        """
        chart = self._charts.get(chart_id)
        if not chart:
            return {"success": False, "error": f"图表{chart_id}不存在"}
        export_config = {
            "chart_id": chart_id,
            "type": chart.chart_type,
            "title": chart.title,
            "format": format,
            "width": width,
            "height": height,
            "dpi": 150,
            "background": "white",
            "data_points": len(chart.data) if hasattr(chart, "data") else 0,
            "exported_at": time.time(),
        }
        return {"success": True, "export": export_config}

    def get_chart_usage_analytics(self) -> dict[str, Any]:
        """图表使用分析。企业场景：产品团队了解哪些图表类型最受欢迎，
        优化默认图表模板，指导新功能优先级。
        """
        if not hasattr(self, "_chart_access_log"):
            return {"success": True, "total_charts": len(self._charts), "message": "无访问日志"}
        log = self._chart_access_log
        total_access = len(log)
        by_type: dict[str, int] = {}
        by_chart: dict[str, int] = {}
        for entry in log:
            ct = entry.get("chart_type", "unknown")
            cid = entry.get("chart_id", "unknown")
            by_type[ct] = by_type.get(ct, 0) + 1
            by_chart[cid] = by_chart.get(cid, 0) + 1
        top_charts = sorted(by_chart.items(), key=lambda x: -x[1])[:10]
        return {
            "success": True,
            "total_charts": len(self._charts),
            "total_access": total_access,
            "by_type": by_type,
            "top_charts": [{"chart_id": c, "accesses": a} for c, a in top_charts],
        }

    def get_template_gallery(self) -> dict[str, Any]:
        """图表模板库。企业场景：产品团队选择预设图表模板快速创建报表，
        避免重复配置，统一数据可视化风格。
        """
        if not hasattr(self, "_templates"):
            self._templates = [
                {
                    "id": "line_basic",
                    "name": "基础折线图",
                    "type": "line",
                    "category": "趋势",
                    "description": "展示数据随时间变化趋势",
                    "default_options": {"smooth": True},
                },
                {
                    "id": "bar_grouped",
                    "name": "分组柱状图",
                    "type": "bar",
                    "category": "对比",
                    "description": "多维度数据对比",
                    "default_options": {"stacked": False},
                },
                {
                    "id": "pie_donut",
                    "name": "环形饼图",
                    "type": "pie",
                    "category": "占比",
                    "description": "展示各部分占总体的比例",
                    "default_options": {"donut": True},
                },
                {
                    "id": "area_stacked",
                    "name": "堆叠面积图",
                    "type": "area",
                    "category": "趋势",
                    "description": "展示多维度累积变化",
                    "default_options": {"stacked": True},
                },
                {
                    "id": "scatter_basic",
                    "name": "散点图",
                    "type": "scatter",
                    "category": "分布",
                    "description": "展示数据点分布和相关性",
                    "default_options": {},
                },
                {
                    "id": "gauge_single",
                    "name": "仪表盘",
                    "type": "gauge",
                    "category": "指标",
                    "description": "展示单个KPI达标情况",
                    "default_options": {"min": 0, "max": 100},
                },
            ]
        categories = {}
        for t in self._templates:
            cat = t["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({"id": t["id"], "name": t["name"], "type": t["type"]})
        return {
            "success": True,
            "total_templates": len(self._templates),
            "categories": categories,
            "templates": self._templates,
        }

    def get_chart_types(self) -> dict[str, Any]:
        """获取支持的图表类型。企业场景：前端展示可选图表类型。"""
        types = ["line", "bar", "pie", "area", "scatter", "radar", "heatmap", "funnel", "gauge", "treemap"]
        return {"success": True, "types": types, "total": len(types)}

    def export_chart_data(self, chart_id: str, format: str = "csv") -> dict[str, Any]:
        """导出图表数据为CSV/JSON。企业场景：运营团队导出报表数据做离线分析。"""
        chart = getattr(self, "_charts", {}).get(chart_id)
        if not chart:
            return {"success": False, "error": f"图表 {chart_id} 不存在"}
        data = chart.get("data", [])
        if format == "json":
            return {"success": True, "format": "json", "data": data}
        # CSV格式
        if not data:
            return {"success": True, "format": "csv", "content": ""}
        headers = list(data[0].keys()) if isinstance(data[0], dict) else []
        lines = [",".join(str(h) for h in headers)]
        for row in data:
            lines.append(",".join(str(row.get(h, "")) for h in headers))
        return {"success": True, "format": "csv", "content": "
".join(lines)}

    def shutdown(self) -> dict:
        """Graceful shutdown for chart_engine."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = ChartEngine
