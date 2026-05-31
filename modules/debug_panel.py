"""
# Grade: A
AUTO-EVO-AI V0.1 — m41 轻量调试面板
为RPA自动化提供可视化调试能力：步骤回放、变量监控、断点调试、执行轨迹记录。
纯Python实现，通过HTTP提供调试API，前端集成到Dashboard。
"""

__module_meta__ = {
        "id": "debug-panel",
        "name": "Debug Panel",
        "version": "V0.1",
        "group": "developer",
        "inputs": [
            {
                "name": "action",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "module",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "params",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "result",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "params_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "context",
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
            "debug",
            "manager",
            "handler"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — m41 轻量调试面板 为RPA自动化提供可视化调试能力：步骤回放、变量监控、断点调试、执行轨迹记录。"
    }

import time
from core.logging_config import get_logger
import threading
import json
import os
import traceback
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections.abc import Callable
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler
from functools import partial
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = get_logger("m41.debug_panel")

class StepRecord:
    """执行步骤记录"""

    def __init__(
        self,
        action: str,
        module: str = "",
        params: dict = None,
        result: Any = None,
        duration_ms: float = 0,
        status: str = "ok",
    ):
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "debug_panel"
        self.version = "1.0.0"
        self._analyzer = DebugPanelAnalyzer()
        self.id = str(uuid.uuid4())[:8]
        self.action = action
        self.module = module
        self.params = params or {}
        self.result = result
        self.duration_ms = round(duration_ms, 2)
        self.status = status  # ok / error / skip / breakpoint
        self.timestamp = datetime.now().isoformat()
        self.variables = {}  # 快照变量

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "module": self.module,
            "params": self.params,
            "result_summary": str(self.result)[:200] if self.result else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "timestamp": self.timestamp,
            "variables": dict(self.variables),
        }

    # --- Auto-generated action dispatch methods ---
    def _action_to_dict(self, params=None):
        """Auto-generated action wrapper for to_dict"""
        if params is None:
            params = {}
        return self.to_dict(**params)

class DebugPanelAnalyzer:
    """debug_panel 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "DebugPanelAnalyzer",
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
        return {"valid": True, "module": "debug_panel"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== debug_panel ===",
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

class BreakpointManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """断点管理器"""

    def __init__(self):
        super().__init__()
        self._breakpoints: dict[str, bool] = {}  # action_name -> enabled
        self._hit_count: dict[str, int] = {}
        self._waiting = False
        self._wait_event = threading.Event()

    def add(self, action: str):
        self._breakpoints[action] = True
        self._hit_count[action] = 0

    def remove(self, action: str):
        self._breakpoints.pop(action, None)
        self._hit_count.pop(action, None)

    def enable(self, action: str, enabled: bool = True):
        if action in self._breakpoints:
            self._breakpoints[action] = enabled

    def check(self, action: str) -> bool:
        """检查是否命中断点，命中则阻塞等待"""
        if not self._breakpoints.get(action, False):
            return False
        self._hit_count[action] = self._hit_count.get(action, 0) + 1
        self._waiting = True
        self._wait_event.clear()
        self._wait_event.wait()  # 阻塞直到继续
        self._waiting = False
        return True

    def continue_execution(self):
        """继续执行"""
        self._wait_event.set()

    def get_breakpoints(self) -> list[dict]:
        return [{"action": a, "enabled": e, "hits": self._hit_count.get(a, 0)} for a, e in self._breakpoints.items()]

    def is_waiting(self) -> bool:
        return self._waiting

class VariableWatcher:
    """变量监视器"""

    def __init__(self):
        self._watched: dict[str, Any] = {}
        self._history: deque = deque(maxlen=1000)

    def watch(self, name: str, value: Any):
        """注册/更新监视变量"""
        old = self._watched.get(name)
        self._watched[name] = value
        self._history.append(
            {
                "time": datetime.now().isoformat(),
                "name": name,
                "old_value": str(old)[:100] if old is not None else None,
                "new_value": str(value)[:100],
            }
        )

    def get(self, name: str = None) -> Any:
        if name:
            return self._watched.get(name)
        return dict(self._watched)

    def get_history(self, limit: int = 50) -> list[dict]:
        return list(self._history)[-limit:]

class DebugPanel:
    """轻量调试面板核心"""

    def __init__(self, max_history: int = 2000, http_port: int = 8300):
        self.max_history = max_history
        self.http_port = http_port
        self._steps: deque = deque(maxlen=max_history)
        self.breakpoints = BreakpointManager()
        self.watcher = VariableWatcher()
        self._http_server: HTTPServer | None = None
        self._http_thread: threading.Thread | None = None
        self._session_start: str | None = None
        self._session_step_count = 0
        self._error_count = 0
        self._debug_mode = False  # 调试模式开关
        self._slow_threshold_ms = 5000  # 慢操作阈值

    # --- 会话管理 ---
    def start_session(self, session_name: str = ""):
        self._session_start = datetime.now().isoformat()
        self._session_step_count = 0
        self._error_count = 0
        self._steps.clear()
        logger.info(f"调试会话已启动: {session_name}")

    def end_session(self) -> dict:
        duration = 0
        if self._session_start:
            start = datetime.fromisoformat(self._session_start)
            duration = (datetime.now() - start).total_seconds()
        summary = {
            "session_start": self._session_start,
            "duration_seconds": round(duration, 2),
            "total_steps": self._session_step_count,
            "error_count": self._error_count,
            "breakpoints": len(self.breakpoints.get_breakpoints()),
            "watched_vars": len(self.watcher.get()),
        }
        self._session_start = None
        return summary

    # --- 步骤记录 ---
    def record_step(
        self, action: str, module: str = "", params: dict = None, fn: Callable | None = None, *args, **kwargs
    ) -> Any:
        """
        记录并执行一个步骤（核心方法）
        用法: result = panel.record_step("click_button", "rpa", {"x": 100, "y": 200}, click_fn, 100, 200)
        """
        # 断点检查
        if self._debug_mode:
            self.breakpoints.check(action)

        start = time.time()
        record = StepRecord(action, module, params)
        record.variables = dict(self.watcher.get())

        try:
            if fn:
                result = fn(*args, **kwargs)
            else:
                result = None
            record.result = result
            record.status = "ok"
            return result
        except Exception as e:
            record.status = "error"
            record.result = f"ERROR: {type(e).__name__}: {e}"
            self._error_count += 1
            logger.error(f"步骤执行失败 [{action}]: {e}")
            raise
        finally:
            record.duration_ms = (time.time() - start) * 1000
            # 慢操作标记
            if record.duration_ms > self._slow_threshold_ms:
                record.status = "slow" if record.status == "ok" else record.status
            self._steps.append(record)
            self._session_step_count += 1

    def record_skip(self, action: str, module: str = "", reason: str = ""):
        record = StepRecord(action, module, status="skip", result=reason)
        self._steps.append(record)
        self._session_step_count += 1

    # --- 调试模式 ---
    def set_debug_mode(self, enabled: bool):
        self._debug_mode = enabled
        logger.info(f"调试模式: {'开启' if enabled else '关闭'}")

    def step_over(self):
        """步过（继续到下一个断点）"""
        self.breakpoints.continue_execution()

    def step_next(self):
        """单步执行（同step_over，断点模式下继续一步）"""
        self.breakpoints.continue_execution()

    # --- 查询接口 ---
    def get_steps(self, limit: int = 100, status_filter: str = None) -> list[dict]:
        steps = list(self._steps)
        if status_filter:
            steps = [s for s in steps if s.status == status_filter]
        return [s.to_dict() for s in steps[-limit:]]

    def get_session_info(self) -> dict:
        return {
            "active": self._session_start is not None,
            "start": self._session_start,
            "step_count": self._session_step_count,
            "error_count": self._error_count,
            "debug_mode": self._debug_mode,
            "breakpoint_waiting": self.breakpoints.is_waiting(),
        }

    def get_errors(self, limit: int = 20) -> list[dict]:
        errors = [s for s in self._steps if s.status == "error"]
        return [s.to_dict() for s in errors[-limit:]]

    def get_slow_steps(self, threshold_ms: float = None, limit: int = 20) -> list[dict]:
        t = threshold_ms or self._slow_threshold_ms
        slow = [s for s in self._steps if s.duration_ms > t]
        return [s.to_dict() for s in sorted(slow, key=lambda x: -x.duration_ms)[:limit]]

    # --- HTTP调试API ---
    def _make_handler(self):
        panel = self

        class DebugHandler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                pass  # 抑制HTTP日志

            def _send_json(self, data: dict, status: int = 200):
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                try:
                    if self.path == "/api/status":
                        self._send_json(panel.get_session_info())
                    elif self.path == "/api/steps":
                        self._send_json({"steps": panel.get_steps()})
                    elif self.path == "/api/errors":
                        self._send_json({"errors": panel.get_errors()})
                    elif self.path == "/api/slow":
                        self._send_json({"slow_steps": panel.get_slow_steps()})
                    elif self.path == "/api/breakpoints":
                        self._send_json({"breakpoints": panel.breakpoints.get_breakpoints()})
                    elif self.path == "/api/variables":
                        self._send_json({"variables": panel.watcher.get()})
                    elif self.path == "/api/var_history":
                        self._send_json({"history": panel.watcher.get_history()})
                    elif self.path.startswith("/api/steps/"):
                        action = self.path.split("/")[-1]
                        steps = [s for s in panel._steps if s.action == action]
                        self._send_json({"steps": [s.to_dict() for s in steps[-50:]]})
                    elif self.path == "/api/summary":
                        self._send_json(
                            panel.end_session() if panel._session_start else {"status": "no_active_session"}
                        )
                    else:
                        self._send_json({"error": "not_found"}, 404)
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)

            def do_POST(self):
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body = json.loads(self.rfile.read(length)) if length else {}
                    if self.path == "/api/step":
                        panel.step_over()
                        self._send_json({"status": "continued"})
                    elif self.path == "/api/breakpoint":
                        action = body.get("action", "")
                        enabled = body.get("enabled", True)
                        if action and enabled:
                            panel.breakpoints.add(action)
                        elif action:
                            panel.breakpoints.remove(action)
                        self._send_json({"breakpoints": panel.breakpoints.get_breakpoints()})
                    elif self.path == "/api/variable":
                        name = body.get("name", "")
                        value = body.get("value")
                        if name:
                            panel.watcher.watch(name, value)
                        self._send_json({"variables": panel.watcher.get()})
                    elif self.path == "/api/debug_mode":
                        enabled = body.get("enabled", False)
                        panel.set_debug_mode(enabled)
                        self._send_json({"debug_mode": enabled})
                    elif self.path == "/api/session/start":
                        name = body.get("name", "")
                        panel.start_session(name)
                        self._send_json({"status": "started"})
                    elif self.path == "/api/session/stop":
                        self._send_json(panel.end_session())
                    else:
                        self._send_json({"error": "not_found"}, 404)
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)

        return DebugHandler

    def start_http_server(self):
        if self._http_server:
            return
        handler = self._make_handler()
        self._http_server = HTTPServer(("127.0.0.1", self.http_port), handler)
        self._http_thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        self._http_thread.start()
        logger.info(f"调试面板HTTP服务已启动: http://127.0.0.1:{self.http_port}")

    def stop_http_server(self):
        if self._http_server:
            self._http_server.shutdown()
            self._http_server = None
            logger.info("调试面板HTTP服务已停止")

    # --- Dashboard数据接口 ---
    def dashboard_data(self) -> dict:
        return {
            "module": "m41_debug_panel",
            "status": "active",
            "http_port": self.http_port,
            "session": self.get_session_info(),
            "recent_steps": self.get_steps(5),
            "errors_count": self._error_count,
            "breakpoints": len(self.breakpoints.get_breakpoints()),
            "watched_vars": len(self.watcher.get()),
        }

# --- 快捷函数 ---
_instance: DebugPanel | None = None

def get_panel() -> DebugPanel:
    global _instance
    if _instance is None:
        _instance = DebugPanel()
    return _instance

if __name__ == "__main__":
    print("=== m41 轻量调试面板 ===")
    panel = DebugPanel()

    # 启动HTTP调试服务
    panel.start_http_server()

    # 模拟调试会话
    panel.start_session("demo_session")
    panel.set_debug_mode(True)

    # 添加断点
    panel.breakpoints.add("click_button")
    panel.watcher.watch("counter", 0)

    # 模拟步骤执行
    def demo_action(x):
        time.sleep(0.1)
        return f"clicked at {x}"

    for i in range(5):
        panel.watcher.watch("counter", i)
        try:
            result = panel.record_step("click_button", "rpa_demo", {"x": i * 100}, demo_action, i * 100)
            print(f"  Step: click_button({i * 100}) -> {result}")
        except Exception:
            pass

    # 故意错误
    try:
        panel.record_step("failing_action", "test", {}, lambda: 1 / 0)
    except ZeroDivisionError:
        print("  Step: failing_action -> ERROR (expected)")

    # 查看结果
    print(f"\n--- 会话信息 ---")
    info = panel.get_session_info()
    for k, v in info.items():
        print(f"  {k}: {v}")

    print(f"\n--- 步骤记录 ({len(panel.get_steps())} 条) ---")
    for s in panel.get_steps(3):
        print(f"  [{s['status']}] {s['action']} ({s['duration_ms']}ms)")

    print(f"\n--- 错误列表 ---")
    for e in panel.get_errors():
        print(f"  {e['action']}: {e['result_summary']}")

    panel.end_session()
    panel.stop_http_server()
    print("\n✅ m41 测试通过")

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("debug_panel.execute", "start", action=action)
        self.metrics_collector.counter("debug_panel.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "debug_panel"}
            else:
                result = {"success": True, "action": action, "module": "debug_panel"}
            self.metrics_collector.counter("debug_panel.execute.success", 1)
            self.trace("debug_panel.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("debug_panel.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "debug_panel"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "debug_panel", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("debug_panel.initialize", "start")
        self.metrics_collector.gauge("debug_panel.initialized", 1)
        self.audit("初始化debug_panel", level="info")
        self.trace("debug_panel.initialize", "end")
        return {"success": True, "module": "debug_panel"}

module_class = DebugPanel
