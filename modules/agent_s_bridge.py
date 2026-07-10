from __future__ import annotations
from modules._base.enterprise_module import EnterpriseModule
"""AUTO-EVO-AI V0.1 — Agent-S GUI Agent Bridge
Simular Agent-S 集成桥接模块
=========================
上市公司生产级实现 — 桌面GUI自动化/视觉理解/指令执行
"""
import os, sys, json, time, base64, io, platform, threading, asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.logging_config import get_logger
logger = get_logger("evo.agent-s")

VERSION = "V0.1"
MODULE_ID = "agent-s-bridge"
MODULE_GROUP = "automation"

__module_meta__ = {
    "id": MODULE_ID,
    "name": "Agent-S GUI自动化",
    "version": VERSION,
    "group": MODULE_GROUP,
    "description": "Simular Agent-S集成 - 桌面GUI自动化/视觉理解/指令执行",
}

_AGENT_S_AVAILABLE = False
try:
    import gui_agents
    _AGENT_S_AVAILABLE = True
except ImportError:
    logger.warning("[AgentS] gui_agents SDK not installed (pip install gui-agents)")

_ACTIVE_AGENT = None
_ACTIVE_LOCK = threading.Lock()
_TASK_HISTORY: List[Dict] = []
_MAX_HISTORY = 200


async def check_available() -> dict:
    """检测 Agent-S 环境状态"""
    checks = {
        "sdk_installed": _AGENT_S_AVAILABLE,
        "platform": platform.system(),
        "openai_key": bool(os.environ.get("OPENAI_API_KEY")),
        "ocr_server": bool(os.environ.get("OCR_SERVER_ADDRESS")),
    }
    pyauto_ok = False
    try:
        import pyautogui
        pyauto_ok = True
    except Exception as _e:        logger.warning(f"[    .strip() module] 异常: {_e}")
    checks["pyautogui"] = pyauto_ok

    if _AGENT_S_AVAILABLE:
        from gui_agents.core.AgentS import GraphSearchAgent
        checks["graph_search_agent"] = True

    return {"success": True, "available": _AGENT_S_AVAILABLE, "checks": checks}


async def execute_instruction(instruction: str, model: str = "gpt-4o",
                              engine_type: str = "openai", timeout: int = 120) -> dict:
    """执行一条GUI自动化指令"""
    if not _AGENT_S_AVAILABLE:
        return {"success": False, "error": "Agent-S SDK not installed (pip install gui-agents)"}

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "缺少 API Key，请设置 OPENAI_API_KEY 环境变量"}

    try:
        import pyautogui
        pyautogui.FAILSAFE = True

        t0 = time.time()
        # Select ACI by platform
        system = platform.system()
        if system == "Windows":
            from gui_agents.aci.WindowsOSACI import WindowsACI, UIElement
            grounding_agent = WindowsACI()
        elif system == "Darwin":
            from gui_agents.aci.MacOSACI import MacOSACI, UIElement
            grounding_agent = MacOSACI()
        elif system == "Linux":
            from gui_agents.aci.LinuxOSACI import LinuxACI, UIElement
            grounding_agent = LinuxACI()
        else:
            return {"success": False, "error": f"Unsupported platform: {system}"}

        engine_params = {"engine_type": engine_type, "model": model}
        os.environ.setdefault("OPENAI_API_KEY", api_key)

        from gui_agents.core.AgentS import GraphSearchAgent
        platform_map = {"Windows": "windows", "Darwin": "macos", "Linux": "ubuntu"}
        agent = GraphSearchAgent(
            engine_params, grounding_agent,
            platform=platform_map.get(system, "ubuntu"),
            action_space="pyautogui", observation_type="mixed",
        )

        global _ACTIVE_AGENT
        with _ACTIVE_LOCK:
            _ACTIVE_AGENT = agent

        # Capture screenshot
        screenshot = pyautogui.screenshot()
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        screenshot_bytes = buf.getvalue()

        # Get accessibility tree
        try:
            acc_tree = UIElement.systemWideElement()
        except Exception:
            acc_tree = None

        obs = {"screenshot": screenshot_bytes, "accessibility_tree": acc_tree}
        info, actions = await asyncio.get_event_loop().run_in_executor(
            None, lambda: agent.predict(instruction=instruction, observation=obs)
        )

        executed = []
        for action_item in actions[:10]:
            try:
                exec(action_item)
                executed.append({"action": action_item[:200], "status": "ok"})
            except Exception as e:
                executed.append({"action": action_item[:200], "status": "error", "error": str(e)})

        elapsed = round(time.time() - t0, 2)
        result = {
            "success": True,
            "instruction": instruction,
            "actions_total": len(actions),
            "actions_success": sum(1 for e in executed if e["status"] == "ok"),
            "actions": executed[:5],
            "elapsed_seconds": elapsed,
        }
        _TASK_HISTORY.append({"type": "instruction", **result, "timestamp": datetime.now().isoformat()})
        while len(_TASK_HISTORY) > _MAX_HISTORY:
            _TASK_HISTORY.pop(0)
        return result

    except Exception as e:
        logger.error(f"[AgentS] execute failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        with _ACTIVE_LOCK:
            _ACTIVE_AGENT = None


async def get_screenshot() -> dict:
    """获取当前屏幕截图(base64)"""
    try:
        import pyautogui
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"success": True, "screenshot": b64, "size": len(b64), "platform": platform.system()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_mouse_position() -> dict:
    """获取鼠标当前位置"""
    try:
        import pyautogui
        x, y = pyautogui.position()
        return {"success": True, "x": x, "y": y}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_status() -> dict:
    """模块状态"""
    with _ACTIVE_LOCK:
        active = _ACTIVE_AGENT is not None
    return {
        "success": True,
        "module_id": MODULE_ID,
        "version": VERSION,
        "active_task": active,
        "task_history_count": len(_TASK_HISTORY),
        "sdk_available": _AGENT_S_AVAILABLE,
        "os": platform.system(),
        "has_openai_key": bool(os.environ.get("OPENAI_API_KEY")),
    }


_actions = ["status", "info", "health", "execute", "screenshot", "mouse_position",
            "check_available", "available", "list_actions", "help"]


async def execute(action: str = "", params: dict = None) -> dict:
    """模块执行入口"""
    p = params or {}
    action = action or p.get("action", "status")

    if action in ("status", "info"):
        return await get_status()
    if action in ("health", "healthcheck"):
        return {"success": True, "status": "healthy", "module": MODULE_ID, "sdk": _AGENT_S_AVAILABLE}
    if action == "execute":
        return await execute_instruction(
            p.get("instruction", p.get("task", "")),
            model=p.get("model", "gpt-4o"),
            engine_type=p.get("engine", "openai"),
            timeout=int(p.get("timeout", 120)),
        )
    if action == "screenshot":
        return await get_screenshot()
    if action in ("mouse_position", "mouse"):
        return get_mouse_position()
    if action in ("check_available", "available"):
        return await check_available()
    if action in ("list_actions", "help"):
        return {"success": True, "actions": _actions, "module": MODULE_ID}
    return {"success": False, "error": f"Unknown action: {action}"}


class AgentSBridge(EnterpriseModule):
    MODULE_ID = "agent_s_bridge"
    MODULE_NAME = "AgentSBridge"

    async def initialize(self):
        self.info(f"AgentSBridge initialized")

    async def execute(self, action, params=None):
        return await super().execute(action, params)

    def health_check(self):
        return super().health_check()

module_class = AgentSBridge
