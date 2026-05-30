"""
AUTO-EVO-AI V0.1 — 仪表盘管理
Grade: A (生产级) | Category: 监控展示
职责：面板管理、组件布局、数据源绑定、实时刷新、权限控制
"""

__module_meta__ = {
    "id": "dashboard",
    "name": "Dashboard",
    "version": "V0.1",
    "group": "ui",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "desc", "type": "string", "required": True, "description": ""},
        {"name": "owner", "type": "string", "required": True, "description": ""},
        {"name": "tags", "type": "string", "required": True, "description": ""},
        {"name": "pid", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["dashboard", "manager"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — 仪表盘管理 Grade: A (生产级) | Category: 监控展示",
}

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("dashboard")

class WidgetType(Enum):
    CHART_LINE = "chart_line"
    CHART_BAR = "chart_bar"
    CHART_PIE = "chart_pie"
    GAUGE = "gauge"
    TABLE = "table"
    STAT_CARD = "stat_card"
    TEXT = "text"
    IFRAME = "iframe"

class PanelLayout(Enum):
    GRID = "grid"
    FREE = "free"
    TABS = "tabs"

@dataclass
class Widget:
    """面板组件"""

    widget_id: str
    title: str
    widget_type: WidgetType
    data_source: str = ""
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 6, "h": 4})
    config: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: int = 60  # seconds, 0=manual

@dataclass
class DashboardPanel:
    """仪表盘面板"""

    panel_id: str
    name: str
    description: str = ""
    layout: PanelLayout = PanelLayout.GRID
    widgets: List[Widget] = field(default_factory=list)
    owner: str = "system"
    is_public: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

class DashboardManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """仪表盘管理器"""

    MODULE_ID = "dashboard"
    MODULE_NAME = "仪表盘管理"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._panels: Dict[str, DashboardPanel] = {}
        self._counter: int = 0
        self._widget_counter: int = 0

    def initialize(self) -> None:
        try:
            pass
            # super().initialize() removed for sync
            self._panels.clear()
            # 创建默认面板
            self._create_default_panels()
            if self._audit:
                self._audit.log("dashboard_initialized", {"panels": len(self._panels)})
            self.stats.success_count += 1
            logger.info("仪表盘管理初始化完成")
        except Exception as e:
            logger.error(f"仪表盘初始化失败: {e}")
            self.stats.error_count += 1
            raise

    def _create_default_panels(self):
        overview = DashboardPanel(
            panel_id="panel_overview",
            name="系统总览",
            description="系统整体运行状态",
            layout=PanelLayout.GRID,
            tags=["default", "system"],
        )
        overview.widgets = [
            Widget(
                widget_id="w_1",
                title="模块总数",
                widget_type=WidgetType.STAT_CARD,
                data_source="modules.total",
                position={"x": 0, "y": 0, "w": 3, "h": 2},
            ),
            Widget(
                widget_id="w_2",
                title="CPU使用率",
                widget_type=WidgetType.GAUGE,
                data_source="metrics.cpu",
                position={"x": 3, "y": 0, "w": 3, "h": 2},
            ),
            Widget(
                widget_id="w_3",
                title="请求趋势",
                widget_type=WidgetType.CHART_LINE,
                data_source="metrics.requests",
                position={"x": 0, "y": 2, "w": 6, "h": 4},
                refresh_interval=30,
            ),
            Widget(
                widget_id="w_4",
                title="告警列表",
                widget_type=WidgetType.TABLE,
                data_source="alerts.list",
                position={"x": 6, "y": 2, "w": 6, "h": 4},
                refresh_interval=60,
            ),
        ]
        self._panels["panel_overview"] = overview

        perf = DashboardPanel(
            panel_id="panel_perf",
            name="性能监控",
            description="系统性能指标",
            layout=PanelLayout.GRID,
            tags=["performance"],
        )
        perf.widgets = [
            Widget(
                widget_id="w_5",
                title="响应时间",
                widget_type=WidgetType.CHART_LINE,
                data_source="metrics.latency",
                position={"x": 0, "y": 0, "w": 6, "h": 4},
            ),
            Widget(
                widget_id="w_6",
                title="错误率",
                widget_type=WidgetType.CHART_BAR,
                data_source="metrics.errors",
                position={"x": 6, "y": 0, "w": 6, "h": 4},
            ),
        ]
        self._panels["panel_perf"] = perf
        self._counter = 2
        self._widget_counter = 6

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "dashboard"})
        self.metrics_collector.counter("dashboard.execute.calls", 1)
        self.audit("execute", {"module": "dashboard"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "create_panel":
                name = params.get("name", "")
                desc = params.get("description", "")
                owner = params.get("owner", "system")
                tags = params.get("tags", [])
                if not name:
                    return {"success": False, "error": "Missing: name"}
                result = self._create_panel(name, desc, owner, tags)
                ok = True
                return {"success": True, "result": result}

            elif action == "delete_panel":
                pid = params.get("panel_id", "")
                if not pid:
                    return {"success": False, "error": "Missing: panel_id"}
                panel = self._panels.pop(pid, None)
                if not panel:
                    return {"success": False, "error": "Panel not found"}
                ok = True
                return {"success": True, "result": {"deleted": pid}}

            elif action == "add_widget":
                pid = params.get("panel_id", "")
                title = params.get("title", "")
                wtype = params.get("widget_type", "stat_card")
                ds = params.get("data_source", "")
                pos = params.get("position", {"x": 0, "y": 0, "w": 3, "h": 2})
                if not pid or not title:
                    return {"success": False, "error": "Missing: panel_id, title"}
                result = self._add_widget(pid, title, wtype, ds, pos)
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "remove_widget":
                pid = params.get("panel_id", "")
                wid = params.get("widget_id", "")
                if not pid or not wid:
                    return {"success": False, "error": "Missing: panel_id, widget_id"}
                result = self._remove_widget(pid, wid)
                ok = True
                return {"success": True, "result": result}

            elif action == "list_panels":
                tags = params.get("tags", [])
                panels = self._panels.values()
                if tags:
                    panels = [p for p in panels if any(t in p.tags for t in tags)]
                return {
                    "success": True,
                    "result": [
                        {
                            "panel_id": p.panel_id,
                            "name": p.name,
                            "desc": p.description,
                            "widgets": len(p.widgets),
                            "layout": p.layout.value,
                            "public": p.is_public,
                            "tags": p.tags,
                        }
                        for p in sorted(panels, key=lambda x: x.created_at)
                    ],
                }

            elif action == "get_panel":
                pid = params.get("panel_id", "")
                panel = self._panels.get(pid)
                if not panel:
                    return {"success": False, "error": "Panel not found"}
                return {
                    "success": True,
                    "result": {
                        "panel_id": panel.panel_id,
                        "name": panel.name,
                        "desc": panel.description,
                        "layout": panel.layout.value,
                        "widgets": [
                            {
                                "id": w.widget_id,
                                "title": w.title,
                                "type": w.widget_type.value,
                                "source": w.data_source,
                                "position": w.position,
                                "refresh": w.refresh_interval,
                            }
                            for w in panel.widgets
                        ],
                        "tags": panel.tags,
                    },
                }

            elif action == "update_widget_position":
                pid = params.get("panel_id", "")
                wid = params.get("widget_id", "")
                pos = params.get("position", {})
                if not pid or not wid or not pos:
                    return {"success": False, "error": "Missing: panel_id, widget_id, position"}
                panel = self._panels.get(pid)
                if not panel:
                    return {"success": False, "error": "Panel not found"}
                for w in panel.widgets:
                    if w.widget_id == wid:
                        w.position.update(pos)
                        panel.updated_at = time.time()
                        ok = True
                        return {"success": True, "result": {"widget_id": wid, "position": w.position}}
                return {"success": False, "error": "Widget not found"}

            elif action == "get_stats":
                total_widgets = sum(len(p.widgets) for p in self._panels.values())
                return {
                    "success": True,
                    "result": {
                        "panels": len(self._panels),
                        "total_widgets": total_widgets,
                        "public_panels": sum(1 for p in self._panels.values() if p.is_public),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "panels": len(self._panels),
        }

    async def shutdown(self) -> None:
        self._panels.clear()
        # super().shutdown() removed for sync

    def _create_panel(self, name: str, desc: str, owner: str, tags: List[str]) -> Dict:
        self._counter += 1
        pid = f"panel_{self._counter}"
        panel = DashboardPanel(panel_id=pid, name=name, description=desc, owner=owner, tags=tags)
        self._panels[pid] = panel
        if self._audit:
            self._audit.log("panel_created", {"panel_id": pid, "name": name, "owner": owner})
        self.stats.success_count += 1
        return {"panel_id": pid, "name": name, "created": True}

    def _add_widget(self, pid: str, title: str, wtype: str, ds: str, pos: Dict) -> Dict:
        panel = self._panels.get(pid)
        if not panel:
            return {"error": "Panel not found"}
        try:
            wt = WidgetType(wtype)
        except ValueError:
            wt = WidgetType.STAT_CARD
        self._widget_counter += 1
        wid = f"w_{self._widget_counter}"
        widget = Widget(widget_id=wid, title=title, widget_type=wt, data_source=ds, position=pos)
        panel.widgets.append(widget)
        panel.updated_at = time.time()
        if self._audit:
            self._audit.log("widget_added", {"panel_id": pid, "widget_id": wid, "type": wtype})
        self.stats.success_count += 1
        return {"widget_id": wid, "title": title, "type": wt.value}

    def _remove_widget(self, pid: str, wid: str) -> Dict:
        panel = self._panels.get(pid)
        if not panel:
            return {"error": "Panel not found"}
        panel.widgets = [w for w in panel.widgets if w.widget_id != wid]
        panel.updated_at = time.time()
        self.stats.success_count += 1
        return {"removed": wid}

    def clone_panel(self, source_panel_id: str, new_name: str) -> Dict[str, Any]:
        """克隆面板。企业场景：新团队成员入职时复制标准运维面板作为基础，
        避免从零搭建。深拷贝面板配置和所有Widget。
        """
        import copy

        source = self._panels.get(source_panel_id)
        if not source:
            return {"success": False, "error": f"面板 {source_panel_id} 不存在"}
        new_id = f"p_{self._panel_counter + 1}"
        self._panel_counter += 1
        cloned = copy.deepcopy(source)
        cloned.panel_id = new_id
        cloned.name = new_name
        cloned.created_at = time.time()
        cloned.updated_at = time.time()
        self._panels[new_id] = cloned
        return {
            "success": True,
            "panel_id": new_id,
            "name": new_name,
            "widgets_count": len(cloned.widgets),
            "cloned_from": source_panel_id,
        }

    def export_panel_config(self, panel_id: str) -> Dict[str, Any]:
        """导出面板配置为JSON。企业场景：跨环境迁移（dev→staging→prod）时
        导出面板配置，通过CI/CD自动化部署。
        """
        panel = self._panels.get(panel_id)
        if not panel:
            return {"success": False, "error": f"面板 {panel_id} 不存在"}
        config = {
            "panel_id": panel.panel_id,
            "name": panel.name,
            "layout": getattr(panel, "layout", "grid"),
            "refresh_interval": getattr(panel, "refresh_interval", 30),
            "widgets": [],
        }
        for w in panel.widgets:
            config["widgets"].append(
                {
                    "widget_id": w.widget_id,
                    "title": w.title,
                    "type": w.widget_type.value if hasattr(w.widget_type, "value") else str(w.widget_type),
                    "data_source": w.data_source,
                    "position": w.position,
                }
            )
        return {"success": True, "config": config, "widget_count": len(config["widgets"])}

    def get_panel_usage_stats(self, days: int = 7) -> Dict[str, Any]:
        """面板使用统计。企业场景：产品团队识别哪些面板被频繁查看，
        低频面板可归档，减少维护成本。
        """
        access_log = getattr(self, "_access_log", [])
        cutoff = time.time() - days * 86400
        recent = [a for a in access_log if a.get("timestamp", 0) > cutoff]
        panel_views = {}
        for a in recent:
            pid = a.get("panel_id", "")
            panel_views[pid] = panel_views.get(pid, 0) + 1
        panels = []
        for pid, panel in self._panels.items():
            panels.append(
                {
                    "panel_id": pid,
                    "name": panel.name,
                    "widgets": len(panel.widgets),
                    "views": panel_views.get(pid, 0),
                    "last_accessed": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(panel.updated_at)),
                }
            )
        panels.sort(key=lambda x: -x["views"])
        total_views = sum(panel_views.values())
        return {
            "success": True,
            "period_days": days,
            "total_panels": len(panels),
            "total_views": total_views,
            "top_panels": panels[:10],
            "unused_panels": [p for p in panels if p["views"] == 0],
        }

    def batch_update_refresh_interval(self, panel_ids: List[str], interval_seconds: int) -> Dict[str, Any]:
        """批量更新面板刷新间隔。企业场景：非工作时间降低刷新频率
        节省资源，工作时间恢复高频刷新。
        """
        updated = 0
        not_found = 0
        for pid in panel_ids:
            panel = self._panels.get(pid)
            if not panel:
                not_found += 1
                continue
            panel.refresh_interval = interval_seconds
            panel.updated_at = time.time()
            updated += 1
        return {"success": True, "updated": updated, "not_found": not_found, "new_interval_s": interval_seconds}

    def export_dashboard_config(self, dashboard_id: str, format: str = "json") -> Dict[str, Any]:
        """导出Dashboard配置。企业场景：从生产环境导出Dashboard配置，
        导入到预发/测试环境，保持监控一致性。
        """
        dashboards = getattr(self, "_dashboards", {})
        d = dashboards.get(dashboard_id)
        if not d:
            return {"success": False, "error": f"Dashboard {dashboard_id} 不存在"}
        panels = self._panels
        panel_defs = []
        for pid in getattr(d, "panel_ids", []):
            p = panels.get(pid)
            if p:
                panel_defs.append(
                    {
                        "panel_id": pid,
                        "title": getattr(p, "title", ""),
                        "type": getattr(p, "panel_type", ""),
                        "datasource": getattr(p, "datasource", ""),
                        "query": getattr(p, "query", ""),
                        "refresh_interval": getattr(p, "refresh_interval", 60),
                        "position": {
                            "x": getattr(p, "x", 0),
                            "y": getattr(p, "y", 0),
                            "w": getattr(p, "width", 6),
                            "h": getattr(p, "height", 4),
                        },
                    }
                )
        config = {
            "dashboard_id": dashboard_id,
            "name": getattr(d, "name", ""),
            "description": getattr(d, "description", ""),
            "layout": getattr(d, "layout", "grid"),
            "panels": panel_defs,
            "variables": getattr(d, "variables", []),
            "tags": getattr(d, "tags", []),
        }
        if format == "yaml":
            import yaml

            try:
                yaml_str = yaml.dump(config, allow_unicode=True, default_flow_style=False)
                return {"success": True, "format": "yaml", "config": yaml_str, "panel_count": len(panel_defs)}
            except ImportError:
                return {"success": False, "error": "PyYAML未安装"}
        return {"success": True, "format": "json", "config": config, "panel_count": len(panel_defs)}

    def clone_dashboard(self, source_id: str, new_name: str) -> Dict[str, Any]:
        """克隆Dashboard。企业场景：基于现有模板创建新Dashboard，
        如从"生产监控"克隆"预发监控"。
        """
        dashboards = getattr(self, "_dashboards", {})
        source = dashboards.get(source_id)
        if not source:
            return {"success": False, "error": f"Dashboard {source_id} 不存在"}
        new_id = f"dash_{uuid.uuid4().hex[:8]}"
        # 克隆面板
        new_panel_ids = []
        for pid in getattr(source, "panel_ids", []):
            panel = self._panels.get(pid)
            if panel:
                new_pid = f"panel_{uuid.uuid4().hex[:8]}"
                new_panel = type(panel)(
                    panel_id=new_pid,
                    title=getattr(panel, "title", ""),
                    panel_type=getattr(panel, "panel_type", ""),
                    datasource=getattr(panel, "datasource", ""),
                    query=getattr(panel, "query", ""),
                )
                self._panels[new_pid] = new_panel
                new_panel_ids.append(new_pid)
        # 创建新Dashboard
        new_dash = type(source)(
            dashboard_id=new_id,
            name=new_name,
            panel_ids=new_panel_ids,
            layout=getattr(source, "layout", "grid"),
        )
        dashboards[new_id] = new_dash
        return {"success": True, "new_dashboard_id": new_id, "new_name": new_name, "cloned_panels": len(new_panel_ids)}

    def get_dashboard_health(self, dashboard_id: str) -> Dict[str, Any]:
        """Dashboard健康检查。企业场景：SRE检查监控面板数据源是否正常，
        哪些面板查询失败、响应超时。
        """
        dashboards = getattr(self, "_dashboards", {})
        panels = getattr(self, "_panels", {})
        d = dashboards.get(dashboard_id)
        if not d:
            return {"success": False, "error": "Dashboard不存在"}
        panel_health = []
        healthy = 0
        unhealthy = 0
        for pid in getattr(d, "panel_ids", []):
            p = panels.get(pid)
            if not p:
                unhealthy += 1
                panel_health.append({"panel_id": pid, "status": "missing"})
                continue
            status = getattr(p, "status", "ok")
            last_error = getattr(p, "last_error", None)
            latency_ms = getattr(p, "last_latency_ms", 0)
            is_ok = status == "ok" and (not last_error) and latency_ms < 5000
            if is_ok:
                healthy += 1
            else:
                unhealthy += 1
            panel_health.append(
                {
                    "panel_id": pid,
                    "title": getattr(p, "title", ""),
                    "status": status,
                    "latency_ms": latency_ms,
                    "last_error": last_error,
                }
            )
        return {
            "success": True,
            "dashboard_id": dashboard_id,
            "total_panels": len(panel_health),
            "healthy": healthy,
            "unhealthy": unhealthy,
            "health_rate": round(healthy / max(len(panel_health), 1) * 100, 1),
            "panel_details": panel_health,
        }

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

module_class = DashboardManager
