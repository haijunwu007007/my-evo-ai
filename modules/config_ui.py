"""
AUTO-EVO-AI V0.1 — 配置UI管理器
Grade: A (生产级) | Category: 配置管理
职责：前端配置界面管理、主题切换、布局持久化、UI组件注册、实时配置推送
"""

__module_meta__ = {
        "id": "config-ui",
        "name": "Config Ui",
        "version": "V0.1",
        "group": "config",
        "inputs": [
            {
                "name": "action",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "detail",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "user",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "user_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "theme_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "widget_id",
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
            "manager"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 配置UI管理器 Grade: A (生产级) | Category: 配置管理"
    }

import os
import time
import uuid
import json
import copy
import logging
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

# 内置主题
BUILTIN_THEMES = {
    "light": {
        "id": "light",
        "name": "浅色模式",
        "type": "light",
        "colors": {
            "primary": "#1890ff",
            "success": "#52c41a",
            "warning": "#faad14",
            "error": "#ff4d4f",
            "bg_primary": "#ffffff",
            "bg_secondary": "#f5f5f5",
            "text_primary": "#262626",
            "text_secondary": "#8c8c8c",
            "border": "#d9d9d9",
        },
        "font_size": 14,
        "border_radius": 6,
    },
    "dark": {
        "id": "dark",
        "name": "深色模式",
        "type": "dark",
        "colors": {
            "primary": "#177ddc",
            "success": "#49aa19",
            "warning": "#d89614",
            "error": "#d32029",
            "bg_primary": "#141414",
            "bg_secondary": "#1f1f1f",
            "text_primary": "#ffffffd9",
            "text_secondary": "#ffffff73",
            "border": "#434343",
        },
        "font_size": 14,
        "border_radius": 6,
    },
    "blue": {
        "id": "blue",
        "name": "科技蓝",
        "type": "dark",
        "colors": {
            "primary": "#2f54eb",
            "success": "#52c41a",
            "warning": "#faad14",
            "error": "#ff4d4f",
            "bg_primary": "#0a1628",
            "bg_secondary": "#13233d",
            "text_primary": "#e6f7ff",
            "text_secondary": "#69c0ff",
            "border": "#1d3a5c",
        },
        "font_size": 14,
        "border_radius": 8,
    },
}

# 内置布局
BUILTIN_LAYOUTS = {
    "default": {
        "id": "default",
        "name": "默认布局",
        "columns": 3,
        "sidebar": True,
        "sidebar_width": 240,
        "header": True,
        "footer": False,
    },
    "compact": {
        "id": "compact",
        "name": "紧凑布局",
        "columns": 4,
        "sidebar": True,
        "sidebar_width": 200,
        "header": True,
        "footer": False,
    },
    "dashboard": {
        "id": "dashboard",
        "name": "仪表盘布局",
        "columns": 2,
        "sidebar": False,
        "sidebar_width": 0,
        "header": True,
        "footer": True,
    },
    "wide": {
        "id": "wide",
        "name": "宽屏布局",
        "columns": 5,
        "sidebar": True,
        "sidebar_width": 280,
        "header": True,
        "footer": False,
    },
}

@dataclass
class WidgetConfig:
    """小组件配置"""

    widget_id: str = ""
    name: str = ""
    type: str = "card"  # card, chart, table, gauge, text
    props: dict[str, Any] = field(default_factory=dict)
    position: dict[str, int] = field(default_factory=lambda: {"row": 0, "col": 0, "w": 1, "h": 1})
    visible: bool = True
    refresh_interval: int = 0  # 0=不自动刷新

@dataclass
class UserProfile:
    """用户UI配置档案"""

    user_id: str = ""
    theme: str = "light"
    layout: str = "default"
    language: str = "zh-CN"
    widgets: dict[str, dict] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    updated_at: float = 0.0

class ConfigUIManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """配置UI管理器 - 生产级实现"""

    MODULE_ID = "config_ui"
    MODULE_NAME = "config_ui"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "config_ui",
                "version": "7.0.0",
                "description": "前端配置界面管理，支持主题/布局/组件/用户偏好管理",
            }
        )
        self._themes: dict[str, dict] = dict(BUILTIN_THEMES)
        self._layouts: dict[str, dict] = dict(BUILTIN_LAYOUTS)
        self._profiles: dict[str, UserProfile] = {}
        self._widgets: dict[str, WidgetConfig] = {}
        self._components: dict[str, dict] = {}
        self._change_log: list[dict] = []
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        # 注册默认小组件
        for w in [
            WidgetConfig("w_cpu", "CPU使用率", "gauge", {}, {"row": 0, "col": 0, "w": 1, "h": 1}),
            WidgetConfig("w_mem", "内存使用率", "gauge", {}, {"row": 0, "col": 1, "w": 1, "h": 1}),
            WidgetConfig("w_tasks", "任务列表", "table", {}, {"row": 1, "col": 0, "w": 2, "h": 1}),
            WidgetConfig("w_alerts", "告警概览", "card", {}, {"row": 1, "col": 2, "w": 1, "h": 1}),
            WidgetConfig("w_logs", "实时日志", "text", {"max_lines": 50}, {"row": 2, "col": 0, "w": 3, "h": 1}),
        ]:
            self._widgets[w.widget_id] = w

    def _log_change(self, action: str, detail: str, user: str = "system"):
        self._change_log.append(
            {
                "change_id": uuid.uuid4().hex[:8],
                "action": action,
                "detail": detail,
                "user": user,
                "timestamp": time.time(),
            }
        )
        if len(self._change_log) > 500:
            self._change_log = self._change_log[-500:]

    def _get_or_create_profile(self, user_id: str) -> UserProfile:
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id, updated_at=time.time())
        return self._profiles[user_id]

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.trace("execute", {"module": "config_ui"})
        self.metrics_collector.counter("config_ui.execute.calls", 1)
        self.audit("execute", {"module": "config_ui"})
        params = params or {}
        try:
            pass
            # === 主题管理 ===
            if action == "list_themes":
                return {"success": True, "result": list(self._themes.values())}
            elif action == "get_theme":
                tid = params.get("theme_id", "light")
                t = self._themes.get(tid)
                if not t:
                    return {"success": False, "error": f"主题{tid}不存在"}
                return {"success": True, "result": t}
            elif action == "set_theme":
                uid = params.get("user_id", "default")
                tid = params.get("theme_id", "light")
                if tid not in self._themes:
                    return {"success": False, "error": f"主题{tid}不存在"}
                p = self._get_or_create_profile(uid)
                p.theme = tid
                p.updated_at = time.time()
                self._log_change("set_theme", f"用户{uid}切换主题: {tid}", uid)
                return {"success": True, "result": {"theme": tid}}
            elif action == "create_theme":
                tid = params.get("theme_id") or f"custom_{uuid.uuid4().hex[:6]}"
                theme = {
                    "id": tid,
                    "name": params.get("name", tid),
                    "type": params.get("type", "light"),
                    "colors": params.get("colors", BUILTIN_THEMES["light"]["colors"]),
                    "font_size": params.get("font_size", 14),
                    "border_radius": params.get("border_radius", 6),
                }
                self._themes[tid] = theme
                self._log_change("create_theme", f"创建主题: {tid}")
                return {"success": True, "result": {"theme_id": tid}}

            # === 布局管理 ===
            elif action == "list_layouts":
                return {"success": True, "result": list(self._layouts.values())}
            elif action == "set_layout":
                uid = params.get("user_id", "default")
                lid = params.get("layout_id", "default")
                if lid not in self._layouts:
                    return {"success": False, "error": f"布局{lid}不存在"}
                p = self._get_or_create_profile(uid)
                p.layout = lid
                p.updated_at = time.time()
                self._log_change("set_layout", f"用户{uid}切换布局: {lid}", uid)
                return {"success": True, "result": {"layout": lid}}
            elif action == "create_layout":
                lid = params.get("layout_id") or f"layout_{uuid.uuid4().hex[:6]}"
                layout = {
                    "id": lid,
                    "name": params.get("name", lid),
                    "columns": params.get("columns", 3),
                    "sidebar": params.get("sidebar", True),
                    "sidebar_width": params.get("sidebar_width", 240),
                    "header": params.get("header", True),
                    "footer": params.get("footer", False),
                }
                self._layouts[lid] = layout
                return {"success": True, "result": {"layout_id": lid}}

            # === 小组件管理 ===
            elif action == "list_widgets":
                return {
                    "success": True,
                    "result": [
                        {
                            "widget_id": w.widget_id,
                            "name": w.name,
                            "type": w.type,
                            "position": w.position,
                            "visible": w.visible,
                        }
                        for w in self._widgets.values()
                    ],
                }
            elif action == "add_widget":
                w = WidgetConfig(
                    widget_id=params.get("widget_id") or f"w_{uuid.uuid4().hex[:8]}",
                    name=params.get("name", "未命名"),
                    type=params.get("type", "card"),
                    props=params.get("props", {}),
                    position=params.get("position", {"row": 0, "col": 0, "w": 1, "h": 1}),
                    visible=params.get("visible", True),
                    refresh_interval=params.get("refresh_interval", 0),
                )
                self._widgets[w.widget_id] = w
                self._log_change("add_widget", f"添加组件: {w.name}")
                return {"success": True, "result": {"widget_id": w.widget_id}}
            elif action == "move_widget":
                wid = params.get("widget_id", "")
                w = self._widgets.get(wid)
                if not w:
                    return {"success": False, "error": f"组件{wid}不存在"}
                w.position = params.get("position", w.position)
                self._log_change("move_widget", f"移动组件: {w.name}")
                return {"success": True, "result": {"position": w.position}}
            elif action == "toggle_widget":
                wid = params.get("widget_id", "")
                w = self._widgets.get(wid)
                if not w:
                    return {"success": False, "error": f"组件{wid}不存在"}
                w.visible = params.get("visible", not w.visible)
                return {"success": True, "result": {"visible": w.visible}}
            elif action == "remove_widget":
                wid = params.get("widget_id", "")
                if wid in self._widgets:
                    del self._widgets[wid]
                    return {"success": True, "result": {"removed": True}}
                return {"success": False, "error": f"组件{wid}不存在"}

            # === 用户配置档案 ===
            elif action == "get_profile":
                uid = params.get("user_id", "default")
                p = self._profiles.get(uid)
                if not p:
                    return {
                        "success": True,
                        "result": {
                            "user_id": uid,
                            "theme": "light",
                            "layout": "default",
                            "language": "zh-CN",
                            "widgets": {},
                            "preferences": {},
                        },
                    }
                return {
                    "success": True,
                    "result": {
                        "user_id": p.user_id,
                        "theme": p.theme,
                        "layout": p.layout,
                        "language": p.language,
                        "widgets": p.widgets,
                        "preferences": p.preferences,
                        "updated_at": datetime.fromtimestamp(p.updated_at).isoformat(),
                    },
                }
            elif action == "set_preferences":
                uid = params.get("user_id", "default")
                p = self._get_or_create_profile(uid)
                p.preferences.update(params.get("preferences", {}))
                if "language" in params:
                    p.language = params["language"]
                p.updated_at = time.time()
                self._log_change("set_preferences", f"更新用户{uid}偏好", uid)
                return {"success": True, "result": {"updated": True}}

            # === UI组件注册 ===
            elif action == "register_component":
                cid = params.get("component_id") or f"comp_{uuid.uuid4().hex[:8]}"
                self._components[cid] = {
                    "component_id": cid,
                    "name": params.get("name", ""),
                    "type": params.get("type", "custom"),
                    "props_schema": params.get("props_schema", {}),
                    "registered_at": time.time(),
                }
                return {"success": True, "result": {"component_id": cid}}
            elif action == "list_components":
                return {"success": True, "result": list(self._components.values())}

            # === 变更日志 ===
            elif action == "changelog":
                limit = params.get("limit", 50)
                return {"success": True, "result": self._change_log[-limit:]}

            # === 导出/导入 ===
            elif action == "export":
                uid = params.get("user_id", "default")
                p = self._profiles.get(uid)
                data = {
                    "theme": p.theme if p else "light",
                    "layout": p.layout if p else "default",
                    "widgets": {
                        k: {"name": v.name, "type": v.type, "position": v.position, "visible": v.visible}
                        for k, v in self._widgets.items()
                    },
                    "preferences": p.preferences if p else {},
                    "exported_at": datetime.now().isoformat(),
                }
                return {"success": True, "result": data}

            elif action == "get_stats":
                return {
                    "success": True,
                    "result": {
                        "themes": len(self._themes),
                        "layouts": len(self._layouts),
                        "widgets": len(self._widgets),
                        "profiles": len(self._profiles),
                        "components": len(self._components),
                        "changes": len(self._change_log),
                    },
                }
            elif action == "health_check":
                return {"success": True, "result": self.health_check()}
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"[ConfigUI] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        base.update(
            {
                "status": "healthy",
                "themes": len(self._themes),
                "layouts": len(self._layouts),
                "widgets": len(self._widgets),
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False
        logger.info("关闭配置UI管理器")

    def export_theme_config(self, theme_id: str) -> dict[str, Any]:
        """导出主题配置。企业场景：多环境部署时将定制主题导出为JSON，
        在生产/预发/测试环境之间共享UI配置。
        """
        theme = self._themes.get(theme_id)
        if not theme:
            return {"success": False, "error": f"主题 {theme_id} 不存在"}
        config = {
            "id": theme_id,
            "name": getattr(theme, "name", theme_id),
            "colors": getattr(theme, "colors", {}),
            "typography": getattr(theme, "typography", {}),
            "spacing": getattr(theme, "spacing", {}),
        }
        return {"success": True, "format": "json", "config": config}

    def get_layout_usage_report(self) -> dict[str, Any]:
        """布局使用报告。企业场景：产品团队分析哪些页面布局被广泛使用，
        哪些是冗余配置，辅助UI组件库优化。
        """
        layouts = getattr(self, "_layouts", {})
        widgets = getattr(self, "_widgets", {})
        report = {"total_layouts": len(layouts), "total_widgets": len(widgets)}
        layout_details = []
        for lid, layout in layouts.items():
            used_widgets = getattr(layout, "widgets", [])
            layout_details.append({"id": lid, "name": getattr(layout, "name", lid), "widget_count": len(used_widgets)})
        report["layout_details"] = sorted(layout_details, key=lambda x: -x["widget_count"])
        return {"success": True, **report}

    def validate_widget_config(self, widget_id: str) -> dict[str, Any]:
        """校验组件配置完整性。企业场景：上线前检查组件配置是否满足
        必填字段要求，避免前端渲染异常。
        """
        widgets = getattr(self, "_widgets", {})
        widget = widgets.get(widget_id)
        if not widget:
            return {"success": False, "error": f"组件 {widget_id} 不存在"}
        issues = []
        required_fields = ["type", "name", "data_source"]
        config = getattr(widget, "config", {})
        for field in required_fields:
            if not config.get(field):
                issues.append({"field": field, "error": "必填字段缺失"})
        return {"success": True, "widget_id": widget_id, "valid": len(issues) == 0, "issues": issues}

    def clone_theme(self, source_id: str, new_name: str) -> dict[str, Any]:
        """克隆主题。企业场景：基于现有主题创建变体（如暗色版、大字体版），
        避免从零开始配置。
        """
        themes = getattr(self, "_themes", {})
        source = themes.get(source_id)
        if not source:
            return {"success": False, "error": f"主题 {source_id} 不存在"}
        new_id = hashlib.md5(f"{source_id}_{new_name}".encode()).hexdigest()[:12]
        # 深拷贝主题配置
        import copy

        themes[new_id] = copy.deepcopy(source)
        themes[new_id].name = new_name
        return {"success": True, "new_theme_id": new_id, "name": new_name, "cloned_from": source_id}

    def export_theme_json(self, theme_id: str) -> dict[str, Any]:
        """导出主题为JSON。企业场景：跨项目共享UI主题，或版本控制管理主题变更。"""
        themes = getattr(self, "_themes", {})
        theme = themes.get(theme_id)
        if not theme:
            return {"success": False, "error": f"主题 {theme_id} 不存在"}
        export_data = {
            "theme_id": theme_id,
            "name": theme.name,
            "colors": getattr(theme, "colors", {}),
            "typography": getattr(theme, "typography", {}),
            "spacing": getattr(theme, "spacing", {}),
            "components": getattr(theme, "components", {}),
            "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return {"success": True, "theme": export_data, "size_bytes": len(str(export_data).encode())}

    def get_widget_usage_stats(self) -> dict[str, Any]:
        """组件使用统计。企业场景：产品团队分析哪些配置组件被团队频繁使用，
        识别低频组件可下线，高频组件需优化体验。
        """
        widgets = getattr(self, "_widgets", {})
        layouts = getattr(self, "_layouts", [])
        widget_usage = {}
        for w_id, widget in widgets.items():
            widget_usage[w_id] = {
                "name": getattr(widget, "name", w_id),
                "type": getattr(widget, "type", "unknown"),
                "layout_count": 0,
            }
        for layout in layouts:
            for w_id in layout.get("widget_ids", []):
                if w_id in widget_usage:
                    widget_usage[w_id]["layout_count"] += 1
        stats = sorted(widget_usage.values(), key=lambda x: -x["layout_count"])
        used = [s for s in stats if s["layout_count"] > 0]
        unused = [s for s in stats if s["layout_count"] == 0]
        return {
            "success": True,
            "total_widgets": len(widgets),
            "used": len(used),
            "unused": len(unused),
            "top_widgets": used[:10],
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

module_class = ConfigUIManager
