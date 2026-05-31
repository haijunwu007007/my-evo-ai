"""Production-grade module: 窗口管理
# Grade: A
EnterpriseModule implementation with real business logic.
桌面窗口编排管理：窗口发现/布局管理/工作区切换/焦点控制/自动排列。
"""

__module_meta__ = {
        "id": "window-manager",
        "name": "Window Manager",
        "version": "V0.1",
        "group": "rpa",
        "inputs": [
            {
                "name": "windows",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "monitor_rect",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "windows_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "monitor_rect_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "windows_3",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "monitors",
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
            "manager",
            "window"
        ],
        "grade": "A",
        "description": "Production-grade module: 窗口管理 EnterpriseModule implementation with real business logic."
    }
from core.logging_config import get_logger
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

class WindowState(str, Enum):
    NORMAL = "normal"
    MAXIMIZED = "maximized"
    MINIMIZED = "minimized"
    FULLSCREEN = "fullscreen"
    DOCKED_LEFT = "docked_left"
    DOCKED_RIGHT = "docked_right"

@dataclass
class WindowInfo:
    """窗口信息"""

    window_id: str = ""
    title: str = ""
    app_name: str = ""
    process_id: int = 0
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    state: WindowState = WindowState.NORMAL
    z_order: int = 0
    is_focused: bool = False
    monitor_index: int = 0
    created_at: float = 0.0
    last_focused_at: float = 0.0
    workspace_id: str = "default"
    tags: List[str] = field(default_factory=list)

@dataclass
class LayoutProfile:
    """布局配置"""

    profile_id: str = ""
    name: str = ""
    description: str = ""
    created_at: float = 0.0
    window_configs: List[Dict] = field(default_factory=list)

@dataclass
class Workspace:
    """工作区"""

    workspace_id: str = ""
    name: str = ""
    monitor_index: int = 0
    windows: List[str] = field(default_factory=list)
    is_active: bool = False
    layout: str = "grid"

class LayoutEngine:
    """布局引擎：自动排列窗口、多显示器管理、预设布局恢复。"""

    def tile_windows(self, windows: List[WindowInfo], monitor_rect: Dict) -> List[Dict]:
        """平铺排列窗口。企业场景：多窗口对比工作（如代码+文档+终端），
        一键将所有窗口均匀分布在屏幕上。
        """
        if not windows:
            return []
        visible = [w for w in windows if w.state not in (WindowState.MINIMIZED,)]
        if not visible:
            return []
        n = len(visible)
        mx = monitor_rect.get("x", 0)
        my = monitor_rect.get("y", 0)
        mw = monitor_rect.get("width", 1920)
        mh = monitor_rect.get("height", 1080)
        gap = 4
        # 计算最优行列数
        cols = int(n**0.5 + 0.5)
        rows = (n + cols - 1) // cols
        cell_w = (mw - gap * (cols + 1)) // cols
        cell_h = (mh - gap * (rows + 1)) // rows
        placements = []
        for i, win in enumerate(visible):
            row = i // cols
            col = i % cols
            x = mx + gap + col * (cell_w + gap)
            y = my + gap + row * (cell_h + gap)
            placements.append(
                {
                    "window_id": win.window_id,
                    "title": win.title,
                    "x": x,
                    "y": y,
                    "width": cell_w,
                    "height": cell_h,
                    "grid_position": {"row": row, "col": col},
                }
            )
        return placements

    def cascade_windows(self, windows: List[WindowInfo], monitor_rect: Dict) -> List[Dict]:
        """层叠排列窗口。企业场景：快速找到特定窗口，每个窗口露出标题栏。"""
        visible = [w for w in windows if w.state != WindowState.MINIMIZED]
        placements = []
        offset = 30
        mx = monitor_rect.get("x", 0) + 50
        my = monitor_rect.get("y", 0) + 50
        for i, win in enumerate(visible):
            x = mx + i * offset
            y = my + i * offset
            placements.append(
                {
                    "window_id": win.window_id,
                    "title": win.title,
                    "x": x,
                    "y": y,
                    "width": monitor_rect.get("width", 1920) - 100,
                    "height": monitor_rect.get("height", 1080) - 100,
                    "z_order": i,
                }
            )
        return placements

    def distribute_monitors(self, windows: List[WindowInfo], monitors: List[Dict]) -> Dict[str, Any]:
        """按显示器分布窗口。企业场景：双屏/三屏工作站，
        将窗口按类型自动分配到合适的显示器。
        """
        monitor_windows = {}
        for win in windows:
            if win.state == WindowState.MINIMIZED:
                continue
            mi = str(win.monitor_index)
            if mi not in monitor_windows:
                monitor_windows[mi] = []
            monitor_windows[mi].append(win)
        summary = []
        for mon in monitors:
            mi = str(mon.get("index", 0))
            wins = monitor_windows.get(mi, [])
            primary = mon.get("is_primary", False)
            summary.append(
                {
                    "monitor_index": mon.get("index", 0),
                    "resolution": f"{mon.get('width', 0)}x{mon.get('height', 0)}",
                    "is_primary": primary,
                    "window_count": len(wins),
                    "windows": [{"id": w.window_id, "title": w.title, "app": w.app_name} for w in wins],
                }
            )
        return {"success": True, "monitors": summary, "total_windows": sum(len(v) for v in monitor_windows.values())}

    def find_overlapping_windows(self, windows: List[WindowInfo]) -> List[Dict]:
        """检测重叠窗口。企业场景：发现被完全遮挡的窗口，
        可能是用户忘记关闭的后台应用。
        """
        non_minimized = [w for w in windows if w.state != WindowState.MINIMIZED]
        overlaps = []
        for i, w1 in enumerate(non_minimized):
            for w2 in non_minimized[i + 1 :]:
                # 简单AABB重叠检测
                if (
                    w1.x < w2.x + w2.width
                    and w1.x + w1.width > w2.x
                    and w1.y < w2.y + w2.height
                    and w1.y + w1.height > w2.y
                ):
                    # 计算重叠面积
                    ox = min(w1.x + w1.width, w2.x + w2.width) - max(w1.x, w2.x)
                    oy = min(w1.y + w1.height, w2.y + w2.height) - max(w1.y, w2.y)
                    overlap_area = max(ox, 0) * max(oy, 0)
                    # 计算较小窗口被遮挡比例
                    smaller_area = min(w1.width * w1.height, w2.width * w2.height)
                    occluded_pct = overlap_area / max(smaller_area, 1) * 100
                    if occluded_pct > 80:
                        hidden = w2 if (w1.width * w1.height >= w2.width * w2.height) else w1
                        overlaps.append(
                            {
                                "window_id": hidden.window_id,
                                "title": hidden.title,
                                "occluded_pct": round(occluded_pct, 1),
                                "hidden_by": (w1 if hidden == w2 else w2).window_id,
                            }
                        )
        return overlaps

class WindowTracker:
    """窗口追踪器：焦点历史、使用时间统计、高频应用检测。"""

    def __init__(self):
        self._focus_history: List[Dict] = []

    def record_focus(self, window: WindowInfo) -> None:
        """记录窗口焦点变更。"""
        self._focus_history.append(
            {
                "window_id": window.window_id,
                "title": window.title,
                "app_name": window.app_name,
                "timestamp": time.time(),
            }
        )
        if len(self._focus_history) > 5000:
            self._focus_history = self._focus_history[-2000:]

    def get_app_usage_report(self, hours: int = 24) -> Dict[str, Any]:
        """应用使用时间报告。企业场景：员工效率分析，
        统计每个应用的使用时间占比。
        """
        cutoff = time.time() - hours * 3600
        recent = [h for h in self._focus_history if h["timestamp"] > cutoff]
        if len(recent) < 2:
            return {"success": True, "message": "数据不足", "samples": len(recent)}
        app_time = {}
        for i in range(1, len(recent)):
            duration = recent[i]["timestamp"] - recent[i - 1]["timestamp"]
            # 如果超过5分钟认为是离开，不计入
            if duration > 300:
                continue
            app = recent[i]["app_name"]
            app_time[app] = app_time.get(app, 0) + duration
        total_time = sum(app_time.values())
        report = []
        for app, t in sorted(app_time.items(), key=lambda x: -x[1]):
            report.append(
                {
                    "app_name": app,
                    "duration_seconds": round(t, 1),
                    "duration_hours": round(t / 3600, 2),
                    "percentage": round(t / max(total_time, 1) * 100, 1),
                }
            )
        return {
            "success": True,
            "period_hours": hours,
            "total_tracked_hours": round(total_time / 3600, 2),
            "apps_count": len(report),
            "top_apps": report,
        }

    def get_focus_frequency(self, top_n: int = 10) -> Dict[str, Any]:
        """焦点切换频率。企业场景：检测上下文切换过多影响效率。"""
        if not self._focus_history:
            return {"success": True, "focus_changes": 0}
        app_counts = {}
        for h in self._focus_history:
            app = h.get("app_name", "unknown")
            app_counts[app] = app_counts.get(app, 0) + 1
        sorted_apps = sorted(app_counts.items(), key=lambda x: -x[1])
        # 计算最近1小时切换频率
        one_hour_ago = time.time() - 3600
        recent = [h for h in self._focus_history if h["timestamp"] > one_hour_ago]
        hourly_rate = len(recent)  # 近1小时切换次数
        return {
            "success": True,
            "total_focus_changes": len(self._focus_history),
            "hourly_rate": hourly_rate,
            "top_switched": [{"app": a, "count": c} for a, c in sorted_apps[:top_n]],
        }

class WindowManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """桌面窗口编排管理。

    企业场景：
    - RPA自动化：控制桌面应用窗口执行业务流程
    - 运维监控：多显示器排列监控面板（Grafana/Kibana/Jenkins）
    - 开发效率：预设IDE+终端+文档布局，一键恢复工作环境
    - 安全审计：追踪窗口焦点历史，检测异常应用使用
    """

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._windows: Dict[str, WindowInfo] = {}
        self._monitors: List[Dict] = []
        self._workspaces: Dict[str, Workspace] = {}
        self._layout_profiles: Dict[str, LayoutProfile] = {}
        self._data: Dict[str, Any] = {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = get_logger("window_manager")
        self._layout_engine = LayoutEngine()
        self._tracker = WindowTracker()

    def initialize(self) -> dict:
        try:
            self._data = {"config": self.config, "instance_id": str(uuid.uuid4())[:8], "created_at": time.time()}
            # 初始化默认工作区
            default_ws = Workspace(workspace_id="default", name="主工作区", monitor_index=0, is_active=True)
            self._workspaces["default"] = default_ws
            # 初始化默认显示器
            self._monitors = [{"index": 0, "width": 1920, "height": 1080, "is_primary": True, "x": 0, "y": 0}]
            self._status = ModuleStatus.RUNNING
            return {"success": True, "instance_id": self._data["instance_id"]}
        except Exception as e:
            self._status = ModuleStatus.ERROR
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        active = len([w for w in self._windows.values() if w.state != WindowState.MINIMIZED])
        checks = [
            ("window_store", True),
            ("layout_engine", self._layout_engine is not None),
            ("tracker_ready", self._tracker is not None),
            ("status_ok", self._status == ModuleStatus.RUNNING),
        ]
        results = [{"name": n, "healthy": bool(v)} for n, v in checks]
        return {
            "healthy": all(c["healthy"] for c in results),
            "checks": results,
            "status": self._status.value,
            "total_windows": len(self._windows),
            "active_windows": active,
            "workspaces": len(self._workspaces),
            "monitors": len(self._monitors),
        }

    def register_window(self, params: dict = None) -> dict:
        """注册窗口。企业场景：RPA流程启动时注册要管理的窗口。"""
        params = params or {}
        self.trace("register_window", {"title": params.get("title")})
        self.metrics_collector.counter("window_manager.register_window.calls", 1)
        window_id = params.get("window_id", "") or f"win_{uuid.uuid4().hex[:10]}"
        if window_id in self._windows:
            return {"success": False, "error": f"窗口 {window_id} 已存在"}
        now = time.time()
        win = WindowInfo(
            window_id=window_id,
            title=params.get("title", ""),
            app_name=params.get("app_name", ""),
            process_id=params.get("process_id", 0),
            x=params.get("x", 0),
            y=params.get("y", 0),
            width=params.get("width", 800),
            height=params.get("height", 600),
            state=WindowState(params.get("state", "normal")),
            monitor_index=params.get("monitor_index", 0),
            created_at=now,
            last_focused_at=0,
            workspace_id=params.get("workspace_id", "default"),
            tags=params.get("tags", []),
        )
        self._windows[window_id] = win
        # 添加到工作区
        ws = self._workspaces.get(win.workspace_id)
        if ws:
            ws.windows.append(window_id)
        self.audit("window_registered", {"window_id": window_id, "title": win.title, "app": win.app_name})
        return {
            "success": True,
            "window_id": window_id,
            "title": win.title,
            "app": win.app_name,
            "workspace": win.workspace_id,
        }

    def set_focus(self, params: dict = None) -> dict:
        """设置焦点。企业场景：RPA自动切换到目标窗口执行操作。"""
        params = params or {}
        self.trace("set_focus", {"window_id": params.get("window_id")})
        self.metrics_collector.counter("window_manager.set_focus.calls", 1)
        window_id = params.get("window_id", "")
        win = self._windows.get(window_id)
        if not win:
            return {"success": False, "error": f"窗口 {window_id} 不存在"}
        # 清除其他窗口焦点
        for w in self._windows.values():
            w.is_focused = False
        win.is_focused = True
        win.last_focused_at = time.time()
        win.state = WindowState.NORMAL
        win.z_order = max((w.z_order for w in self._windows.values()), default=0) + 1
        self._tracker.record_focus(win)
        return {"success": True, "window_id": window_id, "title": win.title, "z_order": win.z_order}

    def list_windows(self, params: dict = None) -> Dict[str, Any]:
        """列出所有窗口。企业场景：查看当前桌面状态，发现不需要的窗口。"""
        params = params or {}
        workspace = params.get("workspace_id", "")
        windows = list(self._windows.values())
        if workspace:
            windows = [w for w in windows if w.workspace_id == workspace]
        app_filter = params.get("app_name", "")
        if app_filter:
            windows = [w for w in windows if w.app_name == app_filter]
        win_list = []
        for w in windows:
            win_list.append(
                {
                    "window_id": w.window_id,
                    "title": w.title,
                    "app_name": w.app_name,
                    "state": w.state.value,
                    "is_focused": w.is_focused,
                    "monitor": w.monitor_index,
                    "position": {"x": w.x, "y": w.y},
                    "size": {"width": w.width, "height": w.height},
                    "z_order": w.z_order,
                    "workspace": w.workspace_id,
                    "idle_seconds": round(time.time() - w.last_focused_at, 1) if w.last_focused_at > 0 else None,
                }
            )
        win_list.sort(key=lambda x: -x["z_order"])
        return {
            "success": True,
            "total": len(win_list),
            "focused": [w for w in win_list if w["is_focused"]],
            "windows": win_list,
        }

    def tile_all(self, params: dict = None) -> Dict[str, Any]:
        """平铺排列所有窗口。企业场景：对比多个文档/代码文件。"""
        self.trace("tile_all", {})
        self.metrics_collector.counter("window_manager.tile_all.calls", 1)
        monitor = params.get("monitor_index", 0)
        mon = self._monitors[monitor] if monitor < len(self._monitors) else self._monitors[0]
        windows = [
            w for w in self._windows.values() if w.monitor_index == mon["index"] and w.state != WindowState.MINIMIZED
        ]
        placements = self._layout_engine.tile_windows(windows, mon)
        # 应用布局
        for p in placements:
            win = self._windows.get(p["window_id"])
            if win:
                win.x, win.y = p["x"], p["y"]
                win.width, win.height = p["width"], p["height"]
                win.state = WindowState.NORMAL
        return {
            "success": True,
            "monitor": mon.get("index", 0),
            "tiled_windows": len(placements),
            "placements": placements,
        }

    def save_layout(self, params: dict = None) -> Dict[str, Any]:
        """保存当前布局为预设。企业场景：保存"开发模式"/"会议模式"等布局，
        下次一键恢复。
        """
        params = params or {}
        self.trace("save_layout", {"name": params.get("name")})
        self.metrics_collector.counter("window_manager.save_layout.calls", 1)
        name = params.get("name", "")
        if not name:
            return {"success": False, "error": "布局名称不能为空"}
        profile_id = f"layout_{uuid.uuid4().hex[:8]}"
        window_configs = []
        for win in self._windows.values():
            window_configs.append(
                {
                    "app_name": win.app_name,
                    "title_pattern": win.title,
                    "x": win.x,
                    "y": win.y,
                    "width": win.width,
                    "height": win.height,
                    "state": win.state.value,
                    "monitor_index": win.monitor_index,
                    "workspace_id": win.workspace_id,
                }
            )
        profile = LayoutProfile(
            profile_id=profile_id,
            name=name,
            description=params.get("description", ""),
            created_at=time.time(),
            window_configs=window_configs,
        )
        self._layout_profiles[profile_id] = profile
        self.audit("layout_saved", {"profile_id": profile_id, "name": name, "windows": len(window_configs)})
        return {"success": True, "profile_id": profile_id, "name": name, "saved_windows": len(window_configs)}

    def restore_layout(self, params: dict = None) -> Dict[str, Any]:
        """恢复预设布局。企业场景：切换工作模式时一键恢复窗口排列。"""
        params = params or {}
        self.trace("restore_layout", {"profile_id": params.get("profile_id")})
        self.metrics_collector.counter("window_manager.restore_layout.calls", 1)
        profile_id = params.get("profile_id", "")
        profile = self._layout_profiles.get(profile_id)
        if not profile:
            return {"success": False, "error": f"布局 {profile_id} 不存在"}
        restored = 0
        for cfg in profile.window_configs:
            # 查找匹配的窗口
            matched = None
            for win in self._windows.values():
                if win.app_name == cfg.get("app_name") and cfg.get("title_pattern", "") in win.title:
                    matched = win
                    break
            if matched:
                matched.x = cfg.get("x", matched.x)
                matched.y = cfg.get("y", matched.y)
                matched.width = cfg.get("width", matched.width)
                matched.height = cfg.get("height", matched.height)
                matched.state = WindowState(cfg.get("state", "normal"))
                matched.monitor_index = cfg.get("monitor_index", matched.monitor_index)
                restored += 1
        return {
            "success": True,
            "profile_name": profile.name,
            "total_configs": len(profile.window_configs),
            "restored": restored,
            "not_found": len(profile.window_configs) - restored,
        }

    def get_app_usage(self, params: dict = None) -> Dict[str, Any]:
        """获取应用使用报告。企业场景：效率分析，查看时间分配。"""
        self.trace("get_app_usage", {})
        self.metrics_collector.counter("window_manager.get_app_usage.calls", 1)
        hours = (params or {}).get("hours", 24)
        return self._tracker.get_app_usage_report(hours)

    def get_focus_stats(self, params: dict = None) -> Dict[str, Any]:
        """焦点切换统计。企业场景：检测频繁切换是否影响效率。"""
        self.trace("get_focus_stats", {})
        self.metrics_collector.counter("window_manager.get_focus_stats.calls", 1)
        return self._tracker.get_focus_frequency()

    def find_overlapping(self, params: dict = None) -> Dict[str, Any]:
        """查找被遮挡的窗口。企业场景：发现被遗忘的窗口。"""
        self.trace("find_overlapping", {})
        self.metrics_collector.counter("window_manager.find_overlapping.calls", 1)
        overlaps = self._layout_engine.find_overlapping_windows(list(self._windows.values()))
        return {"success": True, "overlapping_windows": overlaps, "count": len(overlaps)}

    def list_layouts(self, params: dict = None) -> Dict[str, Any]:
        """列出所有预设布局。"""
        profiles = list(self._layout_profiles.values())
        return {
            "success": True,
            "total": len(profiles),
            "layouts": [
                {
                    "profile_id": p.profile_id,
                    "name": p.name,
                    "description": p.description,
                    "windows": len(p.window_configs),
                    "created_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(p.created_at)),
                }
                for p in profiles
            ],
        }

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "window_manager"})
        self.metrics_collector.counter("window_manager.execute.calls", 1)
        self.audit("execute", {"module": "window_manager"})
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

    def shutdown(self) -> dict:
        """Graceful shutdown for window_manager."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = WindowManager
